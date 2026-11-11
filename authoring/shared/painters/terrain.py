"""Terrain pieces for a continuous map: the hex grid places them but never shows.

Every ground texture repeats on the hex lattice, so a piece that spills over
its neighbours lays down exactly the paint they would. Sea tiles fill their
hex. Land pieces are larger than the hex and end in an irregular feathered
edge, so country flows into country with no straight boundary. Coasts are
three under-layers drawn beneath all land (shallows, surf, sand); their union
makes one organic shoreline whatever the hex arrangement. See design/art/maps.md.
"""
import math
import random

import cairo
import numpy as np
from PIL import Image

from ..kit import draw, hexgrid, sheet
from ..kit.raster import array_to_image, image_to_array, paper_grain

STILL = {'still': {'frames': [0], 'fps': 1, 'loop': False}}


# ---------------------------------------------------------------- shared pieces

def wrapped_points(rng, count, spacing, margin=0.0, attempts=4000):
    """Evenly spread points in the home hex; spacing also holds across the lattice wrap."""
    points = []
    offsets = [(0, 0), *hexgrid.NEIGHBOURS.values()]
    for _ in range(attempts):
        if len(points) >= count:
            break
        candidate = (rng.uniform(0, 128), rng.uniform(0, 144))
        if not hexgrid.inside(candidate, margin):
            continue
        if all(math.hypot(candidate[0] - x - dx, candidate[1] - y - dy) >= spacing
               for x, y in points for dx, dy in offsets):
            points.append(candidate)
    return sorted(points, key=lambda point: point[1])


def soft_blob(ctx, x, y, radius, colour, alpha):
    pattern = cairo.RadialGradient(x, y, 0, x, y, radius)
    r, g, b, _ = colour
    pattern.add_color_stop_rgba(0, r, g, b, alpha)
    pattern.add_color_stop_rgba(1, r, g, b, 0)
    ctx.set_source(pattern)
    draw.ellipse(ctx, x, y, radius, radius)
    ctx.fill()


def wash_ground(ctx, pal, rng, base, light, deep, blobs=7):
    """Flat wash with slow tonal pooling, the way gouache settles on paper."""
    draw.source(ctx, pal(base))
    ctx.paint()
    pools = [(rng.uniform(0, 128), rng.uniform(0, 144), rng.uniform(26, 46), rng.random() < 0.5)
             for _ in range(blobs)]

    def paint():
        for x, y, radius, lighter in pools:
            if hexgrid.inside((x, y)):
                soft_blob(ctx, x, y, radius, pal(light if lighter else deep), 0.42 if lighter else 0.30)
    hexgrid.repeat(ctx, paint)


def tuft(ctx, pal, x, y, size, rng):
    draw.source(ctx, pal('grass_ink'), 0.62)
    ctx.set_line_width(1.0)
    for lean in (-0.55, 0.0, 0.5):
        ctx.move_to(x + lean * 1.2, y)
        ctx.line_to(x + lean * size * 0.9 + rng.uniform(-0.3, 0.3), y - size * (1.0 - abs(lean) * 0.35))
    ctx.stroke()


def round_tree(ctx, pal, x, y, size, rng):
    """Deciduous map symbol: lobed crown, lit upper left, shadow cast to the south-east."""
    draw.shadow_blob(ctx, x + size * 0.34, y + size * 0.02, size * 0.56, size * 0.20, pal('forest_shadow'), 0.55)
    ctx.move_to(x, y)
    ctx.line_to(x - size * 0.02, y - size * 0.34)
    draw.line(ctx, pal('bark'), max(1.4, size * 0.09))
    cx, cy = x, y - size * 0.72
    lobes = [(cx + math.cos(a) * size * 0.24 * rng.uniform(0.8, 1.15),
              cy + math.sin(a) * size * 0.20 * rng.uniform(0.8, 1.15),
              size * rng.uniform(0.25, 0.32))
             for a in [i * math.tau / 5 + rng.uniform(-0.3, 0.3) for i in range(5)]]
    lobes.append((cx, cy, size * 0.33))
    for lx, ly, radius in lobes:                      # one ink contour around the union
        draw.ellipse(ctx, lx, ly, radius + 0.9, radius + 0.9)
    draw.wash(ctx, pal('ink'), 0.88)
    for lx, ly, radius in lobes:
        draw.ellipse(ctx, lx, ly, radius, radius)
    draw.wash(ctx, pal('forest'))
    ctx.save()
    for lx, ly, radius in lobes:
        draw.ellipse(ctx, lx, ly, radius, radius)
    ctx.clip()
    soft_blob(ctx, cx + size * 0.22, cy + size * 0.24, size * 0.5, pal('forest_deep'), 0.85)
    soft_blob(ctx, cx - size * 0.2, cy - size * 0.2, size * 0.42, pal('forest_light'), 0.95)
    draw.source(ctx, pal('ink'), 0.42)                # engraved leaf marks on the shaded side
    ctx.set_line_width(0.9)
    for index in range(3):
        ax, ay = cx + size * (0.02 + index * 0.13), cy + size * (0.16 - index * 0.07)
        ctx.new_sub_path()
        ctx.arc(ax, ay, size * 0.13, 0.15, 1.5)
    ctx.stroke()
    ctx.restore()


def fir_tree(ctx, pal, x, y, size, rng):
    draw.shadow_blob(ctx, x + size * 0.3, y + size * 0.02, size * 0.46, size * 0.17, pal('forest_shadow'), 0.55)
    ctx.move_to(x, y)
    ctx.line_to(x, y - size * 0.25)
    draw.line(ctx, pal('bark'), max(1.3, size * 0.08))
    tiers = [(0.20, 0.62, 0.36), (0.42, 0.86, 0.29), (0.66, 1.12, 0.20)]
    for base, top, half in tiers:
        points = [(x - size * half, y - size * base), (x - size * half * 0.35, y - size * (base + top) / 2),
                  (x, y - size * top), (x + size * half * 0.35, y - size * (base + top) / 2),
                  (x + size * half, y - size * base), (x, y - size * (base - 0.05))]
        draw.polygon(ctx, points)
        draw.inked(ctx, pal('fir'), pal('ink'), 1.0, ink_alpha=0.88)
        draw.polygon(ctx, [points[0], points[1], points[2], (x - size * 0.02, y - size * base)])
        draw.wash(ctx, pal('forest_light'), 0.55)


# ---------------------------------------------------------------- base tiles

def paint_plain(ctx, pal, rng, params):
    wash_ground(ctx, pal, rng, 'grass', 'grass_light', 'grass_deep')
    for _ in range(params.get('fields', 0)):          # strip farming: a small patchwork of tilled plots
        cx, cy, angle = rng.uniform(40, 88), rng.uniform(44, 100), rng.uniform(-0.45, 0.45)
        plots, breadth, cursor = rng.randint(2, 3), rng.uniform(24, 30), 0.0
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(angle)
        ctx.translate(-plots * 8.0, -breadth / 2)
        for plot in range(plots):
            width = rng.uniform(13, 18)
            draw.rounded_rect(ctx, cursor, rng.uniform(-2, 2), width, breadth + rng.uniform(-3, 3), 2.0)
            draw.wash(ctx, pal('field' if plot % 2 == 0 else 'fallow'), 0.86, preserve=True)
            draw.line(ctx, pal('field_ink'), 0.9, 0.55, preserve=True)
            ctx.save()
            ctx.clip()
            draw.hatch(ctx, (cursor, -4, cursor + width, breadth + 4), math.pi / 2 if plot % 2 else 0.0, 3.0,
                       pal('field_ink'), 0.75, 0.42)
            ctx.restore()
            cursor += width + 1.2
        ctx.restore()
    tufts = wrapped_points(rng, params.get('tufts', 9), 26)
    sizes = [rng.uniform(3.6, 5.2) for _ in tufts]

    def paint():
        for (x, y), size in zip(tufts, sizes):
            tuft(ctx, pal, x, y, size, random.Random(int(x * 131 + y)))
    hexgrid.repeat(ctx, paint)


def paint_forest(ctx, pal, rng, params):
    """Open grass at the rim so the wood grows out of its neighbours; shade pools under the canopy."""
    wash_ground(ctx, pal, rng, 'grass', 'grass_light', 'grass_deep')
    soft_blob(ctx, 64, 74, 70, pal('forest_floor'), 0.95)
    soft_blob(ctx, 64, 74, 46, pal('forest_deep'), 0.38)


def forest_canopy(ctx, pal, rng, params):
    trees = wrapped_points(rng, params.get('trees', 13), 21, margin=9)
    for x, y in trees:
        size = rng.uniform(21, 27)
        if rng.random() < params.get('fir_share', 0.3):
            fir_tree(ctx, pal, x, y + size * 0.42, size * 1.04, rng)
        else:
            round_tree(ctx, pal, x, y + size * 0.45, size, rng)


def wave_mark(ctx, x, y, half, rise):
    ctx.move_to(x - half, y)
    ctx.curve_to(x - half * 0.6, y - rise, x - half * 0.3, y - rise, x, y)
    ctx.curve_to(x + half * 0.3, y + rise, x + half * 0.6, y + rise, x + half, y)


def paint_water(ctx, pal, rng, params):
    shallow = params.get('shallow', False)
    base, light, deep = ('shallows', 'shallows_light', 'sea') if shallow else ('sea', 'sea_light', 'sea_deep')
    wash_ground(ctx, pal, rng, base, light, deep, blobs=6)
    marks = wrapped_points(rng, params.get('waves', 15), 21)
    styles = [(rng.uniform(5.0, 8.0), rng.uniform(1.4, 2.2), rng.random() < 0.42) for _ in marks]
    shoals = []
    for _ in range(params.get('shoals', 0)):          # sandbanks showing through shallow water
        cx, cy, turn = rng.uniform(36, 92), rng.uniform(40, 104), rng.uniform(-0.5, 0.5)
        rx, ry = rng.uniform(13, 20), rng.uniform(4.5, 7.5)
        outline = []
        for step in range(9):
            angle = step * math.tau / 9
            reach = rng.uniform(0.72, 1.12)
            px, py = math.cos(angle) * rx * reach, math.sin(angle) * ry * reach
            outline.append((cx + px * math.cos(turn) - py * math.sin(turn), cy + px * math.sin(turn) + py * math.cos(turn)))
        dots = [(cx + rng.uniform(-rx, rx) * 0.6, cy + rng.uniform(-ry, ry) * 0.5) for _ in range(7)]
        shoals.append((outline, dots))

    def paint():
        for outline, dots in shoals:
            draw.smooth(ctx, outline)
            draw.wash(ctx, pal('sand'), 0.30)
            for x, y in dots:
                draw.ellipse(ctx, x, y, 0.55, 0.55)
            draw.wash(ctx, pal('sea_ink'), 0.30)
        ctx.set_line_width(1.15)
        for (x, y), (half, rise, bright) in zip(marks, styles):
            wave_mark(ctx, x, y, half, rise)
            draw.source(ctx, pal('foam' if bright else 'sea_ink'), 0.72 if bright else 0.50)
            ctx.stroke()
    hexgrid.repeat(ctx, paint)
    strokes = [(rng.uniform(0, 128), y + rng.uniform(-1.5, 1.5), rng.uniform(18, 46)) for y in range(4, 144, 9) for _ in range(2)]

    def lining():                                             # the engraver's sea: broken horizontal rules
        for x, y, length in strokes:
            ctx.move_to(x, y)
            ctx.line_to(x + length, y)
        draw.line(ctx, pal('sea_ink'), 0.75, 0.17)
    hexgrid.repeat(ctx, lining)


GROUNDS = {'plain': paint_plain, 'forest': paint_forest, 'water': paint_water}
PIECE = (176, 198)                         # land pieces: the 128x144 hex plus room to feather out
MARGIN = ((PIECE[0] - hexgrid.FRAME[0]) / 2, (PIECE[1] - hexgrid.FRAME[1]) / 2)


def hex_distance(size, _margin=None):
    """Per-pixel distance outside the hex (negative inside), for a frame with the hex centred."""
    ys, xs = np.mgrid[0:size[1], 0:size[0]].astype(np.float32)
    dx, dy = np.abs(xs + 0.5 - size[0] / 2), np.abs(ys + 0.5 - size[1] / 2)
    slant = (dx * 36.0 + dy * 64.0 - 64.0 * 72.0) / math.hypot(36.0, 64.0)
    return np.maximum(dx - 64.0, slant)


def edge_noise(size, seed, cell=22, amplitude=1.0):
    """Slow wander for a boundary, so no edge runs straight."""
    rng = np.random.default_rng(seed)
    cells = (size[1] // cell + 3, size[0] // cell + 3)
    coarse = Image.fromarray((rng.random(cells, dtype=np.float32) * 255).astype(np.uint8), 'L')
    field = np.asarray(coarse.resize(size, Image.BICUBIC), dtype=np.float32) / 255.0
    return (field - 0.5) * 2.0 * amplitude


def smoothstep(low, high, value):
    t = np.clip((value - low) / (high - low), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def boundary(size, spec):
    """Distance field for this piece's wandering outline; params shape_seed, wander and wander_cell set it."""
    seed = spec.params.get('shape_seed', 11)
    wander = spec.params.get('wander', 5.0)
    return hex_distance(size, None) + edge_noise(size, seed, spec.params.get('wander_cell', 22), wander) \
        + edge_noise(size, seed + 1, cell=9, amplitude=min(wander, 6.0) * 0.28)


def lattice_ground(ctx, pal, rng, kind, params):
    """Paint a ground across the whole piece; it repeats on the lattice, so overspill matches the neighbours."""
    for dx, dy in [(0, 0), *hexgrid.NEIGHBOURS.values()]:
        ctx.save()
        ctx.translate(dx, dy)
        hexgrid.path(ctx, inset=-1.0)
        ctx.clip()
        GROUNDS[kind](ctx, pal, random.Random(rng), params)
        ctx.restore()


def paint(spec):
    """One terrain piece. params: kind (plain | forest | water), plus that kind's options.

    Water fills the plain 128x144 hex. Land is painted on the larger piece canvas
    and cut to a feathered, wandering outline.
    """
    kind = spec.params['kind']
    if kind not in GROUNDS:
        raise KeyError(f'{spec.id}: unknown terrain kind {kind!r}; known: {sorted(GROUNDS)}')
    pal = spec.palette
    if kind == 'water':
        def draw_sea(ctx, _index):
            ctx.save()
            hexgrid.path(ctx, inset=-1.0)                  # a pixel of bleed hides seams on the slanted edges
            ctx.clip()
            paint_water(ctx, pal, random.Random(spec.seed), spec.params)
            ctx.restore()
        frames = sheet.render(spec.frame, draw_sea, 1, lambda image, _i: paper_grain(image, spec.seed, mottle=0))
        return sheet.Work(frames=frames, clips=dict(STILL), vector=draw_sea)

    if tuple(spec.frame) != PIECE:
        raise ValueError(f'{spec.id}: land pieces use the terrain-piece format {PIECE}, not {tuple(spec.frame)}')
    feather = spec.params.get('feather', [2.0, 10.0])

    def draw_ground(ctx, _index):
        ctx.translate(*MARGIN)
        lattice_ground(ctx, pal, spec.seed, kind, spec.params)

    def draw_canopy(ctx, _index):
        ctx.translate(*MARGIN)
        if kind == 'forest':
            rng = random.Random(spec.seed + 7)
            forest_canopy(ctx, pal, rng, spec.params)

    ground = image_to_array(sheet.render(spec.frame, draw_ground, 1)[0])
    ground[..., 3] *= 1.0 - smoothstep(feather[0], feather[1], boundary(PIECE, spec))
    image = array_to_image(ground)
    image.alpha_composite(sheet.render(spec.frame, draw_canopy, 1)[0])
    return sheet.Work(frames=[paper_grain(image, spec.seed, mottle=0)], clips=dict(STILL))


def paint_coast(spec):
    """Coast under-layers, drawn beneath every land piece. params: layer (shallows | surf | sand).

    All three share shape_seed, so the surf is an even rim around the sand. Drawn
    in passes (all shallows, all surf, all sand) their unions form one shoreline.
    """
    layer = spec.params['layer']
    pal = spec.palette
    size = tuple(spec.frame)
    reach = spec.params.get('reach', 12.0)
    wander = spec.params.get('wander', 5.0)
    room = min((size[0] - hexgrid.FRAME[0]) / 2, (size[1] - hexgrid.FRAME[1]) / 2)
    needed = reach + wander * 1.3 + (16.0 if layer == 'shallows' else 4.0)
    if needed > room:
        raise ValueError(f'{spec.id}: reach {reach} + wander {wander} needs {needed:.0f}px beyond the hex; frame leaves {room:.0f}px')
    distance = boundary(size, spec)
    array = np.zeros((size[1], size[0], 4), dtype=np.float32)
    if layer == 'shallows':
        array[..., :3] = np.array(pal('shallows')[:3]) * 255
        array[..., 3] = 255 * 0.86 * (1.0 - smoothstep(reach + 2.0, reach + 15.0, distance))
    elif layer == 'surf':
        array[..., :3] = np.array(pal('foam')[:3]) * 255
        array[..., 3] = 255 * 0.95 * (1.0 - smoothstep(reach + 1.8, reach + 3.2, distance))
    elif layer == 'sand':
        wet = smoothstep(reach - 4.0, reach - 0.5, distance)[..., None]        # darker where the tide reaches
        array[..., :3] = (np.array(pal('sand_light')[:3]) * (1 - wet) + np.array(pal('sand')[:3]) * wet) * 255
        array[..., 3] = 255 * (1.0 - smoothstep(reach - 0.7, reach + 0.7, distance))
    else:
        raise KeyError(f'{spec.id}: unknown coast layer {layer!r}; known: shallows, surf, sand')
    image = array_to_image(array)
    if layer == 'sand':
        image = paper_grain(image, spec.seed, fine=0.05, mottle=0)
    return sheet.Work(frames=[image], clips=dict(STILL))


def paint_grid(spec):
    """Optional hex outline the game can show on demand (movement range, selection). Never baked into terrain."""
    pal = spec.palette

    def draw_frame(ctx, _index):
        hexgrid.path(ctx, inset=0.8)
        ctx.set_dash([2.2, 3.6])
        draw.line(ctx, pal('ink'), 1.3, spec.params.get('alpha', 0.42))
        ctx.set_dash([])

    return sheet.Work(frames=sheet.render(spec.frame, draw_frame, 1), clips=dict(STILL), vector=draw_frame)
