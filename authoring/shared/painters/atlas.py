"""Continuous strategic maps painted from geography: one landscape, no tiles in the picture.

The picture is built for a Frame (a pixel window on a map projection) in passes:
water and coast from the land outline; relief from named ranges and authored
ridge lines; ground colour from interpreted land-cover samples; then the
engraver's layers on top: sea lining, hachures, wood and ground marks, rivers,
lakes and the coast line. Nothing political is drawn.

Two things keep a large map affordable and seamless. Slow fields (far distances,
the relief envelope, ground cover) are surveyed once for the whole picture at a
quarter of its resolution. Detail is then painted window by window, and every
placement is in map units and every random choice is hashed from map position,
so a window paints the same ground whichever window it is. Memory stays bounded
and windows meet without a seam.

The recipe (JSON beside batch.json) names what to draw; this module names no
place. `paint` cuts the finished picture into the region's delivery chunks.
"""
import math

import cairo
import numpy as np
from PIL import Image

from ..kit import field, geo
from ..kit.draw import rgba
from ..kit.field import smoothstep
from ..kit.sheet import Work

STILL = {'still': {'frames': [0], 'fps': 1, 'loop': False}}
QUARTER = 4          # the survey works at a quarter of the picture's resolution
TILE = 1024          # largest window painted in one piece
OVERLAP = 16         # neighbouring windows cross-fade over this many pixels
_NORMAL_P = np.linspace(0.001, 0.999, 201)


class RecipeError(ValueError):
    pass


def _inverse_normal(p):
    """Standard normal quantile by bisection on erf; used once to fill a lookup table."""
    low, high = -6.0, 6.0
    for _ in range(60):
        middle = (low + high) / 2
        if 0.5 * (1 + math.erf(middle / math.sqrt(2))) < p:
            low = middle
        else:
            high = middle
    return (low + high) / 2


_NORMAL_Z = np.array([_inverse_normal(p) for p in _NORMAL_P], dtype=np.float32)


def white(ix, iy, seed):
    """Uniform 0..1 hashed from integer lattice coordinates."""
    return field._hash(np.asarray(ix), np.asarray(iy), seed).astype(np.float32) / np.float32(4294967296.0)


def trace(ctx, points, closed):
    ctx.new_sub_path()
    ctx.move_to(points[0][0], points[0][1])
    for x, y in points[1:]:
        ctx.line_to(x, y)
    if closed:
        ctx.close_path()


def mix(a, b, t):
    """Blend colour fields; `t` is a scalar or an (h, w) field."""
    t = t[..., None] if isinstance(t, np.ndarray) and t.ndim == 2 else t
    return a + (b - a) * t


def near_reach(recipe):
    """How far (map units) exact coast distance is needed: the lining, the coast rim, the shore slope."""
    sea, distance, gap = recipe['sea'], recipe['sea']['lining_start'], recipe['sea']['lining_gap']
    for _ in range(int(sea['lining_count']) - 1):
        distance, gap = distance + gap, gap * sea['lining_growth']
    return max(distance * 1.25, recipe['coast']['rim'] * 5, recipe['relief']['shore'] * 1.5)


# ------------------------------------------------------------------ sheets

class Sheet:
    """A pixel grid on the map with the recipe and palette: the base of the survey and of each window."""

    def __init__(self, frame, recipe, palette):
        self.frame, self.recipe, self.palette = frame, recipe, palette
        self.width, self.height, self.unit = frame.width, frame.height, frame.units_per_pixel
        self.seed = int(recipe.get('seed', 0))
        self._grid = None

    def grid(self):
        if self._grid is None:
            self._grid = self.frame.grid()
        return self._grid

    def colour(self, role):
        return np.array(self.palette(role)[:3], dtype=np.float32)

    def px(self, distance):
        """Map units -> pixels."""
        return distance / self.unit

    def mask(self, polygons=(), lines=()):
        """Antialiased coverage (0..1) of polygons (lists of rings) and stroked (path, width) lines."""
        surface = cairo.ImageSurface(cairo.FORMAT_A8, self.width, self.height)
        ctx = cairo.Context(surface)
        ctx.set_antialias(cairo.ANTIALIAS_BEST)
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        for rings in polygons:
            for ring in rings:
                trace(ctx, ring, True)
            ctx.fill()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        for path, line_width in lines:
            ctx.set_line_width(line_width)
            trace(ctx, path, False)
            ctx.stroke()
        surface.flush()
        data = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape(self.height, surface.get_stride())
        return data[:, :self.width].astype(np.float32) / 255.0

    def gather(self, rounds, layers):
        """Project the named layers and keep what this sheet can see."""
        recipe, frame, dataset = self.recipe, self.frame, self.recipe['geodata']
        hydro = recipe.get('hydrography', {})
        omit_lakes, open_water = set(hydro.get('omit_lakes', [])), set(hydro.get('open_to_sea', []))
        omit_rivers = set(hydro.get('omit_rivers', []))

        def polygons(features):
            for feature in features:
                rings = [geo.chaikin(frame.path(ring), rounds, True) for ring in feature['rings']]
                if frame.sees(rings[0], 8):
                    yield feature, rings

        scene = {'land': [], 'lakes': [], 'open': [], 'rivers': [], 'regions': {}, 'classes': {}}
        scene['land'] = [rings for _, rings in polygons(geo.layer(dataset, 'land'))]
        scene['open'] = [[geo.chaikin(frame.path(np.asarray(entry['ring'], dtype=np.float64)), rounds, True)]
                         for entry in hydro.get('flooded', [])]
        for feature, rings in polygons(geo.layer(dataset, 'lakes')):
            if feature['name'] not in omit_lakes:
                scene['open' if feature['name'] in open_water else 'lakes'].append(rings)
        for feature in geo.layer(dataset, 'rivers'):
            path = geo.chaikin(frame.path(feature['line']), rounds, False)
            if frame.sees(path, 8) and feature['name'] not in omit_rivers:
                scene['rivers'].append((feature, path))
        if 'regions' in layers:
            for feature, rings in polygons(geo.layer(dataset, 'regions')):
                scene['regions'].setdefault(feature['name'], []).append(rings)
                scene['classes'].setdefault(feature['class'], []).append(rings)
        return scene

    def land_mask(self, scene):
        """Land coverage: the outline, less waters the recipe opens to the sea, less the straits it cuts.

        1:50m outlines pinch narrow straits shut or leave them thinner than a
        pen line. A strategic map needs its crossings visible, so the recipe
        may cut named straits to a minimum drawn width (cartographic
        exaggeration, recorded in the recipe).
        """
        land = self.mask(scene['land'])
        if scene['open']:
            land = land * (1.0 - self.mask(scene['open']))
        hydro = self.recipe.get('hydrography', {})
        cuts = [(self.frame.path(np.asarray(strait['line'], dtype=np.float64)),
                 max(self.px(strait['width']), hydro.get('strait_min_px', 0.0)))
                for strait in hydro.get('straits', [])]
        cuts = [(path, width) for path, width in cuts if self.frame.sees(path, width)]
        if cuts:
            land = land * (1.0 - self.mask(lines=cuts))
        return land


# ------------------------------------------------------------------ survey

class Survey(Sheet):
    """Slow fields for a whole picture, built once at 1/QUARTER of its resolution."""

    def __init__(self, frame, recipe, palette, margin):
        pad = math.ceil(margin / QUARTER) + 3
        unit = frame.units_per_pixel * QUARTER
        coarse = geo.Frame(frame.projection, frame.west - pad * unit, frame.north + pad * unit, unit,
                           math.ceil(frame.width / QUARTER) + 2 * pad, math.ceil(frame.height / QUARTER) + 2 * pad)
        super().__init__(coarse, recipe, palette)
        scene = self.gather(0, ('regions',))
        solid = self.land_mask(scene) > 0.5
        self.fields = {
            'offshore': field.distance(solid, self.px(recipe['sea']['deep_at'])) * self.unit,
            'inland': field.distance(~solid, self.px(recipe['hydrography']['river_reach'] * 3)) * self.unit,
        }
        reach = max(recipe['relief']['valley'], recipe['cover']['river_green'] * 5)
        lines = [(path, 1.3) for _, path in scene['rivers']]
        self.fields['rivers'] = field.distance(self.mask(lines=lines) > 0.3, self.px(reach)) * self.unit if lines else \
            np.full(solid.shape, reach, dtype=np.float32)
        self.fields['envelope'] = self.envelope(scene)
        self.fields.update(self.cover(scene))

    def envelope(self, scene):
        """Relief envelope 0..1 from named range outlines and authored ridge lines."""
        relief, unit = self.recipe['relief'], self.unit
        x, y = self.grid()
        ragged = field.fbm(x / relief['ragged_cell'], y / relief['ragged_cell'], self.seed + 15, 3)
        envelope = np.zeros((self.height, self.width), dtype=np.float32)
        for entry in relief.get('ranges', []):
            polygons = scene['regions'].get(entry['region'])
            if not polygons:
                continue
            inside = self.mask(polygons) > 0.5
            if not inside.any():
                continue
            depth = field.distance(~inside, entry['rise'] * 3 / unit + 2) * unit * (1.0 + relief['ragged'] * ragged)
            body = smoothstep(0.0, entry['rise'], depth) ** 1.2
            spine = np.clip(depth / (entry['rise'] * 3), 0.0, 1.0)
            envelope = np.maximum(envelope, entry['height'] * (0.78 * body + 0.22 * spine))
        gx, gy = np.meshgrid(np.arange(self.width, dtype=np.float32) + 0.5, np.arange(self.height, dtype=np.float32) + 0.5)
        for entry in relief.get('spines', []):
            path = self.frame.path(np.asarray(entry['line'], dtype=np.float64))
            reach = entry['half_width'] / unit * (1.0 + relief['ragged'])
            x0, x1 = int(max(0, path[:, 0].min() - reach)), int(min(self.width, path[:, 0].max() + reach + 1))
            y0, y1 = int(max(0, path[:, 1].min() - reach)), int(min(self.height, path[:, 1].max() + reach + 1))
            if x0 >= x1 or y0 >= y1:
                continue
            window = (slice(y0, y1), slice(x0, x1))
            near = polyline_distance(gx[window], gy[window], path) / (1.0 + relief['ragged'] * ragged[window])
            profile = entry['height'] * (1.0 - smoothstep(0.0, entry['half_width'] / unit, near))
            envelope[window] = np.maximum(envelope[window], profile)
        for entry in relief.get('basins', []):                      # hollows inside a range outline
            path = self.frame.path(np.asarray(entry['line'], dtype=np.float64))
            near = polyline_distance(gx, gy, path) / (1.0 + relief['ragged'] * ragged)
            envelope *= 1.0 - entry['depth'] * (1.0 - smoothstep(0.0, entry['half_width'] / unit, near))
        return field.blur(envelope, 0.8)

    def cover(self, scene):
        """Ground colour and mark densities from interpreted samples and region rules."""
        cover = self.recipe['cover']
        grounds = list(cover['grounds'])
        x, y = self.grid()
        wx = field.fbm(x / cover['warp_cell'], y / cover['warp_cell'], self.seed + 21, 3) * cover['warp']
        wy = field.fbm(x / cover['warp_cell'], y / cover['warp_cell'], self.seed + 22, 3) * cover['warp']
        x, y = x + wx, y + wy
        weights = np.zeros((len(grounds),) + x.shape, dtype=np.float32)
        soft, power = cover['soften'] ** 2, cover['power'] / 2.0
        for lon, lat, ground in cover['samples']:
            sx, sy = self.frame.projection.forward(lon, lat)
            weights[grounds.index(ground)] += 1.0 / ((x - np.float32(sx)) ** 2 + (y - np.float32(sy)) ** 2 + soft) ** power
        weights /= np.maximum(weights.sum(axis=0), 1e-30)
        for rule in cover.get('regions', []):
            polygons = scene['classes'].get(rule['class'], []) if 'class' in rule else scene['regions'].get(rule['region'], [])
            if not polygons:
                continue
            inside = field.blur(self.mask(polygons), rule.get('feather', 30.0) / self.unit) * rule.get('strength', 1.0)
            weights *= 1.0 - inside
            weights[grounds.index(rule['ground'])] += inside
        fields = {'colour': sum(weights[index][..., None] * self.colour(cover['grounds'][name]['colour'])
                                for index, name in enumerate(grounds))}
        for key in ('woods', 'fir', 'grass', 'sand', 'marsh', 'dry', 'tilled'):
            fields[key] = sum(weights[index] * cover['grounds'][name].get(key, 0.0) for index, name in enumerate(grounds))
        green = np.exp(-self.fields['rivers'] / cover['river_green']) * smoothstep(0.35, 0.8, fields['dry'])
        fields['colour'] = mix(fields['colour'], self.colour(cover['river_colour']), green * 0.9)
        for key in ('sand', 'dry', 'grass'):
            fields[key] = fields[key] * (1.0 - green)
        fields['tilled'] = np.maximum(fields['tilled'], green * 0.8)
        return fields

    def over(self, name, plate):
        """A survey field resampled onto a window's pixels (bilinear in map position)."""
        array = self.fields[name]
        columns = (plate.frame.west - self.frame.west) / self.unit + (np.arange(plate.width) + 0.5) * plate.unit / self.unit - 0.5
        rows = (self.frame.north - plate.frame.north) / self.unit + (np.arange(plate.height) + 0.5) * plate.unit / self.unit - 0.5
        columns, rows = np.clip(columns, 0, self.width - 1.001), np.clip(rows, 0, self.height - 1.001)
        c0, r0 = columns.astype(np.int64), rows.astype(np.int64)
        fc, fr = (columns - c0).astype(np.float32), (rows - r0).astype(np.float32)
        if array.ndim == 3:
            fc, fr = fc[None, :, None], fr[:, None, None]
        else:
            fc, fr = fc[None, :], fr[:, None]
        top = array[np.ix_(r0, c0)] * (1 - fc) + array[np.ix_(r0, c0 + 1)] * fc
        bottom = array[np.ix_(r0 + 1, c0)] * (1 - fc) + array[np.ix_(r0 + 1, c0 + 1)] * fc
        return top * (1 - fr) + bottom * fr


def polyline_distance(px, py, path):
    """Distance from grid points to a polyline (or a single point), in the grid's units."""
    if len(path) == 1:
        return np.hypot(px - path[0, 0], py - path[0, 1])
    best = np.full(px.shape, np.inf, dtype=np.float32)
    for (ax, ay), (bx, by) in zip(path[:-1], path[1:]):
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / length, 0.0, 1.0) if length > 0 else 0.0
        best = np.minimum(best, np.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


# ------------------------------------------------------------------ window

class Plate(Sheet):
    """One window being painted, widened by a margin so fields and strokes are settled at its edge."""

    def __init__(self, frame, recipe, palette, survey, margin):
        self.margin = margin
        super().__init__(frame.window(-margin, -margin, frame.width + 2 * margin, frame.height + 2 * margin), recipe, palette)
        self.survey = survey
        self.left = int(round(self.frame.west / self.unit))      # this window's corner on the picture's pixel lattice
        self.top = int(round(-self.frame.north / self.unit))
        self.scene = self.gather(int(recipe.get('smooth', 0)), ())
        reach = self.px(near_reach(recipe))
        self.land = self.land_mask(self.scene)
        self.lakes = self.mask(self.scene['lakes']) * self.land if self.scene['lakes'] else np.zeros_like(self.land)
        self.ground = self.land * (1.0 - self.lakes)
        solid = self.land > 0.5
        near_sea = field.blur(field.distance(solid, reach), 0.8)
        far = smoothstep(reach * 0.7, reach * 0.98, near_sea)     # beyond the exact reach, the survey takes over
        self.offshore = near_sea * self.unit * (1 - far) + np.maximum(survey.over('offshore', self), near_sea * self.unit) * far
        self.shore = field.distance(~solid, reach) * self.unit    # exact distance inland, capped at the reach
        self.cover = {key: survey.over(key, self) for key in ('woods', 'fir', 'grass', 'sand', 'marsh', 'dry', 'tilled')}

    def over(self, name):
        return self.survey.over(name, self)

    def scatter(self, spacing, seed):
        """Jittered points, one per `spacing`-pixel cell of the picture's lattice: px, py, two random numbers.

        Cells belong to the lattice, not the window, so a mark lands on the same
        ground whichever window is being painted.
        """
        columns = np.arange(math.floor(self.left / spacing), math.ceil((self.left + self.width) / spacing) + 1)
        rows = np.arange(math.floor(self.top / spacing), math.ceil((self.top + self.height) / spacing) + 1)
        ci, cj = np.meshgrid(columns, rows)
        seed += self.seed
        px = (ci + white(ci, cj, seed)) * spacing - self.left
        py = (cj + white(ci, cj, seed + 1)) * spacing - self.top
        inside = (px >= 0) & (px < self.width) & (py >= 0) & (py < self.height)
        return px[inside], py[inside], white(ci, cj, seed + 2)[inside], white(ci, cj, seed + 3)[inside]

    def lattice(self):
        """Integer coordinates of every pixel on the picture's lattice."""
        return np.meshgrid(np.arange(self.width, dtype=np.int64) + self.left, np.arange(self.height, dtype=np.int64) + self.top)


def relief_field(plate):
    """Height 0..1: the surveyed envelope broken into crests by ridged noise, cut by valleys and the shore."""
    relief = plate.recipe['relief']
    envelope = plate.over('envelope')
    x, y = plate.grid()
    cell, warp = relief['crest_cell'], relief['warp']
    wx = field.fbm(x / (cell * 2.3), y / (cell * 2.3), plate.seed + 11, 2) * warp
    wy = field.fbm(x / (cell * 2.3), y / (cell * 2.3), plate.seed + 12, 2) * warp
    crests = field.ridged((x + wx) / cell, (y + wy) / cell, plate.seed + 13, relief['octaves'], relief['gain'],
                          sharpness=relief['sharpness'])
    rolling = field.fbm(x / relief['rolling_cell'], y / relief['rolling_cell'], plate.seed + 14, 4) * 0.5 + 0.5
    floor = relief['floor']
    height_field = envelope * (floor + (1.0 - floor) * crests) + relief['rolling'] * rolling ** 2 * (1.0 - envelope)
    scarps = field.ridged(x / relief['scarp_cell'], y / relief['scarp_cell'], plate.seed + 16, 3, sharpness=0.4)
    height_field = height_field + relief['scarp'] * scarps * rolling * plate.cover['dry'] * (1.0 - envelope)   # bare, broken dry country
    valley = smoothstep(0.0, relief['valley'], plate.over('rivers'))
    height_field = height_field * (relief['valley_floor'] + (1.0 - relief['valley_floor']) * valley)
    shore = smoothstep(-relief['shore'] * 0.2, relief['shore'], plate.shore)
    return (height_field * (0.25 + 0.75 * shore)).astype(np.float32), envelope


def zone(plate, name):
    """A height band (low, high) that falls with latitude, as tree, rock and snow lines do: two fields."""
    if 'latitude' not in plate.__dict__:
        coarse = np.meshgrid(np.arange(0, plate.width + 16, 16, dtype=np.float64), np.arange(0, plate.height + 16, 16, dtype=np.float64))
        plate.latitude = field.resize(plate.frame.to_lonlat(*coarse)[1].astype(np.float32), plate.width, plate.height, cubic=False)
    zones = plate.recipe['relief']['zones']
    south, north = zones['latitude']
    return tuple(np.interp(plate.latitude, [south, north], [zones[name][0][edge], zones[name][1][edge]]).astype(np.float32)
                 for edge in (0, 1))


def wood_density(plate, height_field):
    """Share of ground under trees, 0..1: the cover's woods gathered into forests and thinned by height.

    Gathering keeps the cover's share: a ground that is 30% wooded shows forests on
    about 30% of its area, in masses with a ragged edge, not an even speckle.
    """
    recipe, relief = plate.recipe['woods'], plate.recipe['relief']
    x, y = plate.grid()
    band_low, band_high = relief['woods_band']
    slopes_bonus = smoothstep(band_low, band_high, height_field) * (1.0 - plate.cover['dry']) ** 2
    share = np.clip(plate.cover['woods'] + recipe['slope_bonus'] * slopes_bonus, 0.0, 0.985)
    masses = field.fbm(x / recipe['mass_cell'], y / recipe['mass_cell'], plate.seed + 52, 3)
    clumps = field.fbm(x / recipe['clump_cell'], y / recipe['clump_cell'], plate.seed + 51, recipe['clump_octaves'], recipe['clump_gain'])
    gather = (masses * recipe['mass_weight'] + clumps * (1.0 - recipe['mass_weight'])) / recipe['clump_spread']   # about unit normal
    threshold = np.interp(1.0 - share, _NORMAL_P, _NORMAL_Z)
    gathered = smoothstep(-recipe['clump_edge'], recipe['clump_edge'], gather - threshold) * smoothstep(0.0, 0.04, share)
    tree_low, tree_high = zone(plate, 'treeline')
    return (gathered * (1.0 - smoothstep(tree_low, tree_high, height_field))).astype(np.float32)


# ------------------------------------------------------------------ colour passes

def paint_sea(plate):
    sea = plate.recipe['sea']
    x, y = plate.grid()
    offshore = plate.offshore
    depth = smoothstep(sea['shelf'] * 0.6, sea['deep_at'], offshore)
    rgb = mix(plate.colour(sea['colour']), plate.colour(sea['deep']), depth)
    rgb = mix(rgb, plate.colour(sea['shallow']), np.exp(-offshore / sea['shelf']) * sea['shallow_strength'])
    swell = field.fbm(x / sea['swell_cell'], y / (sea['swell_cell'] * 0.42), plate.seed + 31, 4)
    storm = field.fbm(x / sea['storm_cell'], y / sea['storm_cell'], plate.seed + 32, 3)
    rgb = rgb * (1.0 + sea['swell'] * swell + sea['storm'] * storm)[..., None]

    ink = np.zeros(offshore.shape, dtype=np.float32)
    offshore_px = offshore / plate.unit
    distance, gap, strength = sea['lining_start'], sea['lining_gap'], sea['lining_ink']
    for _ in range(int(sea['lining_count'])):                      # coast-parallel lines, opening out to sea
        band = np.clip(1.0 - np.abs(offshore_px - distance / plate.unit) / 0.62, 0.0, 1.0)
        ink = np.maximum(ink, band * strength)
        distance, gap, strength = distance + gap, gap * sea['lining_growth'], strength * sea['lining_fade']
    row = (plate.top + np.arange(plate.height, dtype=np.float32) + 0.5) * plate.unit      # ruled swell lines
    ruling = np.clip(1.0 - np.abs((row / sea['ruling_gap']) % 1.0 - 0.5) * sea['ruling_gap'] / plate.unit / 0.55, 0.0, 1.0)
    breaks = smoothstep(-0.05, 0.25, field.fbm(x / sea['ruling_run'], y / (sea['ruling_run'] * 0.12), plate.seed + 33, 2))
    open_water = smoothstep(distance * 0.5, distance * 1.1, offshore)
    ink = np.maximum(ink, ruling[:, None] * breaks * open_water * sea['ruling_ink'])
    rgb = mix(rgb, plate.colour(sea['ink']), ink)

    lines = graticule(plate)
    if lines is not None:
        rgb = mix(rgb, plate.colour(plate.recipe['graticule']['ink']), lines)
    return rgb


def paint_land(plate, height_field, woods):
    style, relief, coast = plate.recipe['land'], plate.recipe['relief'], plate.recipe['coast']
    x, y = plate.grid()
    rgb = plate.over('colour')
    pooling = field.fbm(x / style['pool_cell'], y / style['pool_cell'], plate.seed + 41, 4)
    patches = field.fbm(x / style['patch_cell'], y / style['patch_cell'], plate.seed + 43, 2) * plate.cover['tilled']
    drift = field.fbm(x / style['drift_cell'], y / style['drift_cell'], plate.seed + 42, 2)
    rgb = rgb * (1.0 + style['pool'] * pooling + style['drift'] * drift + style['patch'] * patches)[..., None]
    rgb = mix(rgb, plate.colour(style['upland']), smoothstep(relief['upland'][0], relief['upland'][1], height_field) * style['upland_strength'])
    rgb = mix(rgb, plate.colour(style['wood_floor']), woods * style['wood_floor_strength'])

    rock_low, rock_high = zone(plate, 'rock')
    rgb = mix(rgb, plate.colour(style['rock']), smoothstep(rock_low, rock_high, height_field) * style['rock_strength'])
    snow_low, snow_high = zone(plate, 'snow')
    rgb = mix(rgb, plate.colour(style['snow']), smoothstep(snow_low, snow_high, height_field))

    scale = relief['exaggeration'] / plate.unit
    slope_y, slope_x = np.gradient(height_field)
    slope_x, slope_y = slope_x * scale, slope_y * scale
    lx, ly, lz = relief['light']
    norm = math.sqrt(lx * lx + ly * ly + lz * lz)
    shade = (-slope_x * lx - slope_y * ly + lz) / (np.sqrt(slope_x ** 2 + slope_y ** 2 + 1.0) * norm)
    flat = lz / norm
    lit = np.clip((shade - flat) / (1.0 - flat), 0.0, 1.0)
    dark = np.clip((flat - shade) / flat, 0.0, 1.0)
    rgb = mix(rgb, plate.colour(style['light']), lit * style['light_strength'])
    rgb = mix(rgb, plate.colour(style['shadow']), np.minimum(dark * style['shadow_strength'], style['shadow_limit']))

    rgb = mix(rgb, plate.colour(coast['rim_colour']), np.exp(-plate.shore / coast['rim']) * coast['rim_strength'])
    return rgb, (slope_x, slope_y, dark)


def graticule(plate):
    """Meridians and parallels as a faint ruling on the sea only."""
    recipe = plate.recipe.get('graticule')
    if not recipe:
        return None
    step = recipe['step']
    lon, lat = plate.frame.to_lonlat(np.array([0, plate.width, 0, plate.width, plate.width / 2, plate.width / 2]),
                                     np.array([0, 0, plate.height, plate.height, 0, plate.height]))
    west, east = math.floor(lon.min() / step) * step - step, math.ceil(lon.max() / step) * step + step
    south, north = max(-85, math.floor(lat.min() / step) * step - step), min(85, math.ceil(lat.max() / step) * step + step)
    lines = []
    for meridian in np.arange(west, east + 1e-6, step):
        latitudes = np.linspace(south, north, 160)
        lines.append((plate.frame.path(np.stack([np.full_like(latitudes, meridian), latitudes], axis=1)), recipe['width']))
    for parallel in np.arange(south, north + 1e-6, step):
        longitudes = np.linspace(west, east, 320)
        lines.append((plate.frame.path(np.stack([longitudes, np.full_like(longitudes, parallel)], axis=1)), recipe['width']))
    return plate.mask(lines=lines) * (1.0 - plate.land) * recipe['alpha']


# ------------------------------------------------------------------ engraver's layers

class Overlay:
    """Transparent drawing layer the size of the plate, composited onto the colour in float."""

    def __init__(self, plate):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, plate.width, plate.height)
        self.ctx = cairo.Context(self.surface)
        self.ctx.set_antialias(cairo.ANTIALIAS_BEST)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    def onto(self, rgb):
        self.surface.flush()
        height, width = rgb.shape[:2]
        data = np.frombuffer(self.surface.get_data(), dtype=np.uint8).reshape(height, self.surface.get_stride() // 4, 4)
        data = data[:, :width].astype(np.float32) / 255.0
        return rgb * (1.0 - data[..., 3:4]) + data[..., 2::-1]       # cairo stores premultiplied BGRA


def source(ctx, plate, role, alpha=1.0):
    ctx.set_source_rgba(*rgba(plate.palette(role), alpha))


def draw_hachures(ctx, plate, slope):
    """Short strokes down the slope, heavier where it is steeper and on the side away from the light."""
    recipe = plate.recipe['hachure']
    slope_x, slope_y, dark = slope
    px, py, r1, r2 = plate.scatter(recipe['spacing'], 61)
    sx, sy = field.sample(slope_x, px, py), field.sample(slope_y, px, py)
    steep = np.hypot(sx, sy)
    strength = smoothstep(recipe['from'], recipe['full'], steep)
    keep = (r1 < strength * 1.15) & (field.sample(plate.ground, px, py) > 0.7)
    px, py, sx, sy, steep, strength, r2 = (a[keep] for a in (px, py, sx, sy, steep, strength, r2))
    shadow = field.sample(dark, px, py)
    ux, uy = -sx / steep, -sy / steep                                  # downhill
    length = (recipe['length'][0] + (recipe['length'][1] - recipe['length'][0]) * strength) * (0.8 + 0.4 * r2)
    weight = strength * (recipe['lit_weight'] + (1.0 - recipe['lit_weight']) * np.clip(shadow * 2.2, 0.0, 1.0))
    bins = np.minimum((weight * recipe['classes']).astype(int), recipe['classes'] - 1)
    for index in range(recipe['classes']):
        chosen = bins == index
        if not chosen.any():
            continue
        t = (index + 0.5) / recipe['classes']
        for x, y, dx, dy, half in zip(px[chosen], py[chosen], ux[chosen], uy[chosen], length[chosen] / 2):
            ctx.move_to(x - dx * half, y - dy * half)
            ctx.line_to(x + dx * half, y + dy * half)
        source(ctx, plate, recipe['ink'], recipe['alpha'][0] + (recipe['alpha'][1] - recipe['alpha'][0]) * t)
        ctx.set_line_width(recipe['width'][0] + (recipe['width'][1] - recipe['width'][0]) * t)
        ctx.stroke()


def draw_woods(ctx, plate, woods):
    recipe = plate.recipe['woods']
    px, py, r1, r2 = plate.scatter(recipe['spacing'], 71)
    keep = (r1 < field.sample(woods, px, py) * recipe['fill']) & (field.sample(plate.ground, px, py) > 0.8)
    px, py, r1, r2 = px[keep], py[keep], r1[keep], r2[keep]
    fir = field.sample(plate.cover['fir'], px, py) > (r2 * 7.3) % 1.0
    size = recipe['size'] * (0.8 + 0.4 * r2)
    order = np.argsort(py, kind='stable')
    px, py, fir, size = px[order], py[order], fir[order], size[order]

    for x, y, s in zip(px, py, size):                                   # cast shadows, south-east
        ctx.new_sub_path()
        ctx.arc(x + s * 0.55, y + s * 0.45, s * 0.85, 0, math.tau)
    source(ctx, plate, recipe['shadow'], recipe['shadow_alpha'])
    ctx.fill()
    for is_fir, body, light in ((False, recipe['leaf'], recipe['leaf_light']), (True, recipe['fir'], recipe['fir_light'])):
        chosen = fir == is_fir
        for x, y, s in zip(px[chosen], py[chosen], size[chosen]):
            if is_fir:
                ctx.move_to(x, y - s * 1.45)
                ctx.line_to(x + s * 0.95, y + s * 0.75)
                ctx.line_to(x - s * 0.95, y + s * 0.75)
                ctx.close_path()
            else:
                ctx.new_sub_path()
                ctx.arc(x, y, s, 0, math.tau)
        source(ctx, plate, body)
        ctx.fill()
        for x, y, s in zip(px[chosen], py[chosen], size[chosen]):
            ctx.new_sub_path()
            ctx.arc(x - s * 0.32, y - s * (0.55 if is_fir else 0.36), s * 0.42, 0, math.tau)
        source(ctx, plate, light, recipe['light_alpha'])
        ctx.fill()


def draw_ground_marks(ctx, plate, envelope, woods):
    """Engraver's signs for open country: stipple on tilled land, ticks on steppe, dots and dunes on sand, reeds on marsh."""
    recipe = plate.recipe['marks']
    open_ground = (1.0 - smoothstep(0.12, 0.4, envelope)) * (1.0 - woods)

    def chosen(key, spacing, seed, gate=None):
        px, py, r1, r2 = plate.scatter(spacing, seed)
        density = field.sample(plate.cover[key], px, py) * field.sample(open_ground if gate is None else gate, px, py)
        keep = (r1 < density) & (field.sample(plate.ground, px, py) > 0.85)
        return px[keep], py[keep], r2[keep]

    tilled = recipe['tilled']
    px, py, r = chosen('tilled', tilled['spacing'], 80)
    for x, y, t in zip(px, py, r):
        ctx.new_sub_path()
        ctx.arc(x, y, tilled['size'] * (0.7 + 0.6 * t), 0, math.tau)
    source(ctx, plate, tilled['ink'], tilled['alpha'])
    ctx.fill()

    grass = recipe['grass']
    px, py, r = chosen('grass', grass['spacing'], 81)
    for x, y, t in zip(px, py, r):
        ctx.move_to(x - grass['length'] / 2, y)
        ctx.line_to(x + grass['length'] / 2, y + (t - 0.5) * 0.7)
    source(ctx, plate, grass['ink'], grass['alpha'])
    ctx.set_line_width(grass['width'])
    ctx.stroke()

    sand = recipe['sand']
    px, py, r = chosen('sand', sand['spacing'], 82)
    for x, y, t in zip(px, py, r):
        ctx.new_sub_path()
        ctx.arc(x, y, sand['size'] * (0.7 + 0.6 * t), 0, math.tau)
    source(ctx, plate, sand['ink'], sand['alpha'])
    ctx.fill()
    px, py, r = chosen('sand', sand['dune_spacing'], 83)
    for x, y, t in zip(px, py, r):                                      # dune crests: shallow arcs, open to the south-east
        ctx.new_sub_path()
        ctx.arc(x, y + sand['dune'], sand['dune'] * (0.8 + 0.5 * t), math.pi * 1.12, math.pi * 1.72)
    source(ctx, plate, sand['ink'], sand['dune_alpha'])
    ctx.set_line_width(sand['dune_width'])
    ctx.stroke()

    marsh = recipe['marsh']
    px, py, r = chosen('marsh', marsh['spacing'], 84, gate=np.ones_like(envelope))
    for x, y, t in zip(px, py, r):
        half = marsh['length'] * (0.7 + 0.6 * t) / 2
        ctx.move_to(x - half, y)
        ctx.line_to(x + half, y)
    source(ctx, plate, marsh['water'], marsh['alpha'])
    ctx.set_line_width(marsh['width'])
    ctx.stroke()
    for x, y, t in zip(px[::2], py[::2], r[::2]):
        for lean in (-0.8, 0.0, 0.8):
            ctx.move_to(x + lean * 0.5, y - 0.6)
            ctx.line_to(x + lean * 1.5, y - 0.6 - marsh['reed'])
    source(ctx, plate, marsh['ink'], marsh['reed_alpha'])
    ctx.set_line_width(marsh['reed_width'])
    ctx.stroke()


def draw_rivers(ctx, plate):
    """Rivers by rank, thinning with distance from the sea; the broadest carry a light channel inside the line."""
    recipe = plate.recipe['hydrography']
    widths = {int(rank): value for rank, value in recipe['river_width'].items()}
    inland = plate.over('inland')
    strokes = []
    for feature, path in plate.scene['rivers']:
        base = widths.get(int(feature['rank']), recipe['river_width_other'])
        taper = np.exp(-field.sample(inland, path[:, 0], path[:, 1]) / recipe['river_reach'])
        strokes.append((base, path, base * (recipe['river_taper'] + (1.0 - recipe['river_taper']) * taper)))
    strokes.sort(key=lambda item: item[0])
    for casing in (True, False):
        source(ctx, plate, recipe['river_ink'] if casing else recipe['river_water'], recipe['river_alpha'] if casing else 0.92)
        for base, path, width in strokes:
            for (ax, ay), (bx, by), wa, wb in zip(path[:-1], path[1:], width[:-1], width[1:]):
                span = (wa + wb) / 2
                if not casing:
                    span -= recipe['river_casing']
                    if span < 0.5:
                        continue
                ctx.set_line_width(span)
                ctx.move_to(ax, ay)
                ctx.line_to(bx, by)
                ctx.stroke()


def draw_lake_shores(ctx, plate):
    recipe = plate.recipe['hydrography']
    for rings in plate.scene['lakes']:
        for ring in rings:
            trace(ctx, ring, True)
    source(ctx, plate, recipe['river_ink'], recipe['lake_shore_alpha'])
    ctx.set_line_width(recipe['lake_shore'])
    ctx.stroke()


def coast_line(plate):
    """Ink coverage of the coast line, taken from the land mask so it follows cut straits and opened waters.

    A second pass nudged south-east makes shores that face away from the light draw heavier.
    """
    coast = plate.recipe['coast']
    soft = field.box_blur(plate.land, 1)
    spread = math.sqrt(2.0 / 3.0 + 1.0 / 12.0)      # an antialiased edge under a 3-pixel box: about a normal ramp this wide

    def level(offset):
        """Coverage, measured from one half, found `offset` pixels from the edge."""
        return 0.5 * math.erf(offset / (spread * math.sqrt(2.0)))

    inner, outer = level(max(0.05, coast['line'] / 2 - 0.3)), level(coast['line'] / 2 + 0.3)

    def line(mask):
        return np.clip((outer - np.abs(mask - 0.5)) / (outer - inner), 0.0, 1.0)

    f = coast['shade_offset']
    shifted = (soft * (1 - f) ** 2 + np.roll(soft, 1, axis=1) * f * (1 - f) + np.roll(soft, 1, axis=0) * f * (1 - f)
               + np.roll(np.roll(soft, 1, axis=0), 1, axis=1) * f * f)
    ink = np.maximum(line(soft) * coast['alpha'], line(shifted) * coast['shade_alpha'])
    # Water too thin to hold two coast lines (an estuary, a creek) would fill with ink; mark it to be drawn as a channel.
    water = 1.0 - plate.land
    opened = neighbourhood(neighbourhood(water, np.minimum), np.maximum)
    sliver = neighbourhood(np.clip(water - opened, 0.0, 1.0), np.maximum)
    return ink, sliver


def neighbourhood(array, reduce):
    """Minimum or maximum over each pixel's 3x3 neighbourhood (erosion or dilation of a coverage field)."""
    padded = np.pad(array, 1, mode='edge')
    height, width = array.shape
    out = array
    for dy in range(3):
        for dx in range(3):
            out = reduce(out, padded[dy:dy + height, dx:dx + width])
    return out


# ------------------------------------------------------------------ whole picture

def paint_window(frame, recipe, palette, survey, margin):
    """Float RGB (0..255, not yet rounded) of the map as seen through `frame`."""
    plate = Plate(frame, recipe, palette, survey, margin)
    hydro = recipe['hydrography']
    height_field, envelope = relief_field(plate)
    woods = wood_density(plate, height_field)
    land, slope = paint_land(plate, height_field, woods)
    rgb = mix(paint_sea(plate), land, plate.land)
    lake = mix(plate.colour(hydro['lake']), plate.colour(hydro['lake_deep']),
               smoothstep(0.0, 1.0, field.blur(plate.lakes, plate.px(hydro['lake_depth'])) * 2.0 - 1.0))

    overlay = Overlay(plate)
    draw_ground_marks(overlay.ctx, plate, envelope, woods)
    draw_woods(overlay.ctx, plate, woods)
    draw_hachures(overlay.ctx, plate, slope)
    rgb = overlay.onto(rgb)
    overlay = Overlay(plate)
    draw_rivers(overlay.ctx, plate)
    rgb = mix(overlay.onto(rgb), lake, plate.lakes)                 # lakes cover the rivers that run through them
    overlay = Overlay(plate)
    draw_lake_shores(overlay.ctx, plate)
    ink, sliver = coast_line(plate)
    pen = mix(plate.colour(recipe['coast']['ink']), plate.colour(hydro['river_ink']), sliver)
    rgb = mix(overlay.onto(rgb), pen, ink * (1.0 - 0.3 * sliver))

    finish = recipe['finish']
    ix, iy = plate.lattice()
    x, y = plate.grid()
    tooth = (white(ix, iy, plate.seed + 91) - 0.5) * 2.0 * finish['grain']
    tooth = tooth + field.fbm(x / finish['mottle_cell'], y / finish['mottle_cell'], plate.seed + 92, 2) * finish['mottle']
    rgb = rgb * (1.0 + tooth)[..., None]
    grey = (rgb @ np.array([0.3, 0.59, 0.11], dtype=np.float32))[..., None]
    rgb = np.clip(grey + (rgb - grey) * finish['saturation'], 0.0, 1.0) ** finish['gamma']                  # the plate's overall tone
    rgb = rgb * 255.0 + (white(ix, iy, plate.seed + 93)[..., None] - 0.5)                                    # dither, rounded once by the caller
    return rgb[margin:plate.height - margin, margin:plate.width - margin]


def render(frame, recipe, palette, tile=TILE):
    """Paint the map as seen through `frame`; returns an opaque RGBA image of the frame's size."""
    margin = math.ceil(near_reach(recipe) / frame.units_per_pixel) + 10
    survey = Survey(frame, recipe, palette, margin)
    total = np.zeros((frame.height, frame.width, 3), dtype=np.float32)
    for top in range(0, frame.height, tile):
        for left in range(0, frame.width, tile):
            x0, y0 = max(0, left - OVERLAP), max(0, top - OVERLAP)
            x1, y1 = min(frame.width, left + tile), min(frame.height, top + tile)
            piece = paint_window(frame.window(x0, y0, x1 - x0, y1 - y0), recipe, palette, survey, margin)
            ramp_x = np.clip((np.arange(x0, x1) - x0 + 0.5) / OVERLAP, 0.0, 1.0) if x0 > 0 else np.ones(x1 - x0)
            ramp_y = np.clip((np.arange(y0, y1) - y0 + 0.5) / OVERLAP, 0.0, 1.0) if y0 > 0 else np.ones(y1 - y0)
            share = (ramp_y[:, None] * ramp_x[None, :]).astype(np.float32)
            region = (slice(y0, y1), slice(x0, x1))
            total[region] = total[region] * (1.0 - share[..., None]) + piece * share[..., None]
    pixels = np.rint(np.clip(total, 0.0, 255.0)).astype(np.uint8)
    return Image.fromarray(np.dstack([pixels, np.full(pixels.shape[:2], 255, dtype=np.uint8)]), 'RGBA')


def level_entry(region, level):
    for entry in region['levels']:
        if entry['level'] == level:
            return entry
    raise RecipeError(f'Region {region["id"]!r} has no level {level}')


def check_recipe(recipe):
    """Refuse a recipe that names geography the layers do not hold: a typo would otherwise just draw nothing."""
    dataset = recipe['geodata']
    lakes = {feature['name'] for feature in geo.layer(dataset, 'lakes')}
    rivers = {feature['name'] for feature in geo.layer(dataset, 'rivers')}
    regions = {feature['name'] for feature in geo.layer(dataset, 'regions')}
    classes = {feature['class'] for feature in geo.layer(dataset, 'regions')}
    hydro = recipe.get('hydrography', {})
    wanted = [('lake', name, lakes) for name in hydro.get('omit_lakes', []) + hydro.get('open_to_sea', [])]
    wanted += [('river', name, rivers) for name in hydro.get('omit_rivers', [])]
    wanted += [('range outline', entry['region'], regions) for entry in recipe['relief'].get('ranges', [])]
    for rule in recipe['cover'].get('regions', []):
        wanted.append(('region class', rule['class'], classes) if 'class' in rule else ('region', rule['region'], regions))
        if rule['ground'] not in recipe['cover']['grounds']:
            raise RecipeError(f'Cover rule names unknown ground {rule["ground"]!r}')
    for kind, name, known in wanted:
        if name not in known:
            raise RecipeError(f'Recipe names {kind} {name!r}, which is not in the {dataset} layers')
    for lon, lat, ground in recipe['cover']['samples']:
        if ground not in recipe['cover']['grounds']:
            raise RecipeError(f'Cover sample at {lon}, {lat} names unknown ground {ground!r}')


def paint(spec):
    """Build every delivery chunk of one level: {'r<row>c<column>': Work}."""
    recipe = spec.data(spec.params['recipe'])
    region = spec.data(recipe['region'])
    try:
        check_recipe(recipe)
        entry = level_entry(region, int(spec.params.get('level', 0)))
    except RecipeError as error:
        raise RecipeError(f'{spec.id}: {error}') from error
    chunk, skirt = entry['chunk'], entry['skirt']
    if spec.frame != (chunk + 2 * skirt, chunk + 2 * skirt):
        raise RecipeError(f'{spec.id}: format frame {spec.frame} does not match chunk {chunk} with a {skirt} px skirt')
    picture = render(geo.frame_for(region, entry['level'], margin=skirt), recipe, spec.palette)
    parts = {}
    for row in range(entry['rows']):
        for column in range(entry['columns']):
            left, top = column * chunk, row * chunk
            tile = picture.crop((left, top, left + chunk + 2 * skirt, top + chunk + 2 * skirt))
            parts[f'r{row}c{column}'] = Work(frames=[tile], clips=dict(STILL))
    return parts
