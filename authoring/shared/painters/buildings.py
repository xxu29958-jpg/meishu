"""Map structures as bird's-eye vignettes assembled from a small primitive library.

A plan (JSON) lists parts on a ground grid; this module only knows how to draw a
house, tower, dome, wall and so on. A regional family is a new plan file; a new
architectural element is one more primitive here. Frame 0 is intact, frame 1 is
the same plan with each part's declared damage applied.

World axes: +x runs right-and-down the screen, +y left-and-down, +z up. Light
comes from the upper left, so faces looking toward +y are lit and +x are shaded.
"""
import math
import random

from ..kit import draw, sheet
from ..kit.raster import paper_grain
from .terrain import fir_tree, round_tree

CLIPS = {'still': {'frames': [0], 'fps': 1, 'loop': False},
         'damaged': {'frames': [1], 'fps': 1, 'loop': False}}
GROUND = (64.0, 116.0)        # frame point of the plan origin; shared by every building, just above the anchor
AXIS_X, AXIS_Y, RISE = (0.866, 0.36), (-0.866, 0.36), 1.0
INK = 1.05


def iso(x, y, z=0.0):
    return (GROUND[0] + x * AXIS_X[0] + y * AXIS_Y[0], GROUND[1] + x * AXIS_X[1] + y * AXIS_Y[1] - z * RISE)


class Scene:
    """Drawing state for one frame of one plan."""

    def __init__(self, ctx, pal, rng, damaged):
        self.ctx, self.pal, self.rng, self.damaged = ctx, pal, rng, damaged

    def face(self, points, colour, ink_alpha=0.9):
        draw.polygon(self.ctx, [iso(*point) for point in points])
        draw.inked(self.ctx, self.pal(colour), self.pal('ink'), INK, ink_alpha=ink_alpha)

    def tint(self, points, colour, alpha):
        draw.polygon(self.ctx, [iso(*point) for point in points])
        draw.wash(self.ctx, self.pal(colour), alpha)

    def stroke(self, points, colour, width, alpha=1.0):
        draw.polygon(self.ctx, [iso(*point) for point in points], closed=False)
        draw.line(self.ctx, self.pal(colour), width, alpha)


# ------------------------------------------------------------------ primitives

def ground(scene, part):
    """Trodden earth under the settlement, with its cast shadow to the south-east."""
    ctx, pal = scene.ctx, scene.pal
    rx, ry = part['radius']
    cx, cy = iso(*part.get('at', [0, 0]))
    rng = random.Random(part.get('seed', 7))
    outline = []
    for step in range(14):
        angle = step * math.tau / 14
        reach = rng.uniform(0.88, 1.08)
        outline.append((cx + math.cos(angle) * rx * reach, cy + math.sin(angle) * ry * reach))
    draw.shadow_blob(ctx, cx + 3, cy + 2.5, rx * 1.1, ry * 1.18, pal('ink'), 0.30)
    draw.smooth(ctx, outline)
    draw.wash(ctx, pal(part.get('colour', 'earth')), preserve=True)
    draw.line(ctx, pal('ink'), 0.9, 0.45)
    ctx.save()
    draw.smooth(ctx, outline)
    ctx.clip()
    draw.source(ctx, pal('ink'), 0.20)
    for _ in range(int(rx * 0.5)):                       # cobbles and wheel ruts
        px, py = cx + rng.uniform(-rx, rx), cy + rng.uniform(-ry, ry)
        draw.ellipse(ctx, px, py, 0.7, 0.5)
    ctx.fill()
    ctx.restore()


def windows(scene, x0, y0, x1, y1, base, height, count, rows=1, door=False):
    """Dark openings along a wall running between two ground points."""
    for row in range(rows):
        level = base + height * (0.34 + 0.40 * row / max(1, rows - 0.4))
        for index in range(count):
            t = (index + 0.5) / count
            px, py = draw.lerp(x0, x1, t), draw.lerp(y0, y1, t)
            dx, dy = (x1 - x0) / count * 0.20, (y1 - y0) / count * 0.20
            size = height * (0.18 if rows > 1 else 0.24)
            scene.tint([(px - dx, py - dy, level), (px + dx, py + dy, level),
                        (px + dx, py + dy, level + size), (px - dx, py - dy, level + size)], 'window', 0.92)
    if door:
        px, py = draw.lerp(x0, x1, 0.5), draw.lerp(y0, y1, 0.5)
        dx, dy = (x1 - x0) * 0.07, (y1 - y0) * 0.07
        scene.tint([(px - dx, py - dy, base), (px + dx, py + dy, base),
                    (px + dx, py + dy, base + height * 0.42), (px - dx, py - dy, base + height * 0.42)], 'window', 0.95)


def soot(scene, x, y, z, spread):
    cx, cy = iso(x, y, z)
    draw.shadow_blob(scene.ctx, cx, cy - spread * 0.4, spread * 0.8, spread * 1.3, scene.pal('ink'), 0.62)


def rubble(scene, x, y, spread, count=7):
    rng = scene.rng
    for _ in range(count):
        px, py = iso(x + rng.uniform(-spread, spread), y + rng.uniform(-spread, spread))
        size = rng.uniform(0.8, 1.7)
        draw.polygon(scene.ctx, [(px - size, py), (px, py - size * 0.9), (px + size, py - size * 0.1), (px + size * 0.3, py + size * 0.5)])
        draw.inked(scene.ctx, scene.pal('stone_shade'), scene.pal('ink'), 0.6, ink_alpha=0.8)


def house(scene, part):
    """Gabled block. size=[w, d, h], roof=rise, ridge='x'|'y'. damage: roofless | burnt."""
    x0, y0 = part['at']
    w, d, h = part['size']
    x1, y1, rise = x0 + w, y0 + d, part.get('roof', h * 0.6)
    wall, shade = part.get('wall', 'plaster'), part.get('wall', 'plaster') + '_shade'
    roof = part.get('roof_colour', 'tile')
    damage = part.get('damage') if scene.damaged else None
    floors = part.get('floors', 1)
    ridge_x = part.get('ridge', 'x') == 'x'
    if damage == 'roofless':
        scene.face([(x0, y0, h * 0.8), (x1, y0, h), (x1, y0, 0), (x0, y0, 0)], shade)      # inner far walls
        scene.face([(x0, y0, h * 0.8), (x0, y1, h * 0.55), (x0, y1, 0), (x0, y0, 0)], shade)
        scene.tint([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], 'ink', 0.55)
        scene.face([(x1, y0, 0), (x1, y1, 0), (x1, y1, h * 0.62), (x1, (y0 + y1) / 2, h * 0.9), (x1, y0, h)], shade)
        scene.face([(x0, y1, 0), (x1, y1, 0), (x1, y1, h * 0.62), ((x0 + x1) / 2, y1, h * 0.78), (x0, y1, h * 0.55)], wall)
        for t in (0.3, 0.62):                                # charred rafters
            scene.stroke([(draw.lerp(x0, x1, t), y1, h * 0.7), (draw.lerp(x0, x1, t) - w * 0.1, (y0 + y1) / 2, h + rise * 0.5)],
                         'ink', 1.2, 0.9)
        soot(scene, (x0 + x1) / 2, y1, h * 0.6, max(w, d) * 0.28)
        rubble(scene, x1 + 1.5, y1 + 1.5, max(w, d) * 0.35)
        return
    if ridge_x:
        ym = (y0 + y1) / 2
        scene.face([(x0, y0, h), (x1, y0, h), (x1, ym, h + rise), (x0, ym, h + rise)], roof + '_shade')
        scene.face([(x1, y0, 0), (x1, y1, 0), (x1, y1, h), (x1, ym, h + rise), (x1, y0, h)], shade)
        scene.face([(x0, y1, 0), (x1, y1, 0), (x1, y1, h), (x0, y1, h)], wall)
        windows(scene, x0, y1, x1, y1, 0, h, part.get('bays', max(2, int(w / 4))), floors, part.get('door', False))
        windows(scene, x1, y1, x1, y0, 0, h, max(1, int(d / 5)), floors)
        scene.face([(x0, y1, h), (x1, y1, h), (x1, ym, h + rise), (x0, ym, h + rise)], roof)
        scene.tint([(x0, y1, h), (x1, y1, h), (x1, y1 - d * 0.14, h + rise * 0.28), (x0, y1 - d * 0.14, h + rise * 0.28)],
                   roof + '_shade', 0.45)                    # eaves in shadow give the roof thickness
    else:
        xm = (x0 + x1) / 2
        scene.face([(x0, y0, h), (x0, y1, h), (xm, y1, h + rise), (xm, y0, h + rise)], roof)
        scene.face([(x1, y0, 0), (x1, y1, 0), (x1, y1, h), (x1, y0, h)], shade)
        scene.face([(x0, y1, 0), (x1, y1, 0), (x1, y1, h), (xm, y1, h + rise), (x0, y1, h)], wall)
        windows(scene, x0, y1, x1, y1, 0, h, max(1, int(w / 5)), floors, part.get('door', False))
        windows(scene, x1, y1, x1, y0, 0, h, part.get('bays', max(2, int(d / 4))), floors)
        scene.face([(x1, y0, h), (x1, y1, h), (xm, y1, h + rise), (xm, y0, h + rise)], roof + '_shade')
    if part.get('chimney', True):
        cx, cy = x0 + w * 0.28, y0 + d * 0.5
        top = h + rise * (1.25 if ridge_x else 0.9)
        scene.face([(cx, cy + 1.2, h + rise * 0.5), (cx + 1.4, cy + 1.2, h + rise * 0.5), (cx + 1.4, cy + 1.2, top), (cx, cy + 1.2, top)],
                   'stone', 0.8)
        scene.face([(cx + 1.4, cy, h + rise * 0.5), (cx + 1.4, cy + 1.2, h + rise * 0.5), (cx + 1.4, cy + 1.2, top), (cx + 1.4, cy, top)],
                   'stone_shade', 0.8)
    if damage == 'burnt':
        soot(scene, (x0 + x1) / 2, y1, h * 0.75, max(w, d) * 0.22)
        scene.tint([(x0 + w * 0.35, y1, h), (x0 + w * 0.7, y1, h), (x0 + w * 0.62, (y0 + y1) / 2, h + rise * 0.8),
                    (x0 + w * 0.42, y1 - d * 0.2, h + rise * 0.5)], 'ink', 0.82)    # hole burnt through the roof
        rubble(scene, x1 + 1, y1 + 1, max(w, d) * 0.25, 4)


def tower(scene, part):
    """Square tower. cap: 'spire' | 'pyramid' | 'battlement' | 'lantern'. damage: broken."""
    x0, y0 = part['at']
    w, h = part['size']
    x1, y1 = x0 + w, y0 + w
    wall = part.get('wall', 'stone')
    cap, rise = part.get('cap', 'spire'), part.get('rise', h * 0.7)
    broken = scene.damaged and part.get('damage') == 'broken'
    top = h * (0.72 if broken else 1.0)
    scene.face([(x1, y0, 0), (x1, y1, 0), (x1, y1, top), (x1, y0, top * (0.86 if broken else 1))], wall + '_shade')
    scene.face([(x0, y1, 0), (x1, y1, 0), (x1, y1, top), (x0, y1, top * (0.9 if broken else 1))], wall)
    for level in part.get('openings', [0.7]):
        z = h * level
        if z < top - 2:
            mx = (x0 + x1) / 2
            scene.tint([(mx - w * 0.14, y1, z), (mx + w * 0.14, y1, z), (mx + w * 0.14, y1, z + w * 0.5), (mx - w * 0.14, y1, z + w * 0.5)],
                       'window', 0.92)
            my = (y0 + y1) / 2
            scene.tint([(x1, my - w * 0.14, z), (x1, my + w * 0.14, z), (x1, my + w * 0.14, z + w * 0.5), (x1, my - w * 0.14, z + w * 0.5)],
                       'window', 0.92)
    if broken:
        scene.tint([(x0, y0, top * 0.8), (x1, y0, top * 0.86), (x1, y1, top), (x0, y1, top * 0.9)], 'ink', 0.6)
        soot(scene, (x0 + x1) / 2, y1, top * 0.9, w * 0.55)
        rubble(scene, x1 - 1.0, y1 - 1.0, w * 0.5)
        return
    roof = part.get('roof_colour', 'slate')
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    if cap in ('spire', 'pyramid'):
        over = 0.6 if cap == 'pyramid' else 0.3
        scene.face([(x1 + over, y0 - over, h), (x1 + over, y1 + over, h), (mx, my, h + rise)], roof + '_shade')
        scene.face([(x0 - over, y1 + over, h), (x1 + over, y1 + over, h), (mx, my, h + rise)], roof)
        if part.get('finial', cap == 'spire'):
            scene.stroke([(mx, my, h + rise), (mx, my, h + rise + 3.2)], 'ink', 0.9)
            scene.stroke([(mx - 1.0, my, h + rise + 2.1), (mx + 1.0, my, h + rise + 2.1)], 'ink', 0.9)
    elif cap == 'battlement':
        scene.face([(x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h)], wall)
        for t in (0.0, 0.4, 0.8):
            a = draw.lerp(x0, x1, t)
            scene.face([(a, y1, h), (a + w * 0.2, y1, h), (a + w * 0.2, y1, h + 1.6), (a, y1, h + 1.6)], wall, 0.8)
            b = draw.lerp(y1, y0, t)
            scene.face([(x1, b, h), (x1, b - w * 0.2, h), (x1, b - w * 0.2, h + 1.6), (x1, b, h + 1.6)], wall + '_shade', 0.8)
    elif cap == 'lantern':                                   # lighthouse head
        scene.face([(x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h)], wall)
        inset = w * 0.2
        scene.face([(x1 - inset, y0 + inset, h), (x1 - inset, y1 - inset, h), (x1 - inset, y1 - inset, h + rise * 0.55), (x1 - inset, y0 + inset, h + rise * 0.55)], 'glass_shade')
        scene.face([(x0 + inset, y1 - inset, h), (x1 - inset, y1 - inset, h), (x1 - inset, y1 - inset, h + rise * 0.55), (x0 + inset, y1 - inset, h + rise * 0.55)], 'glass')
        scene.face([(x1 - inset + 0.5, y0 + inset - 0.5, h + rise * 0.55), (x1 - inset + 0.5, y1 - inset + 0.5, h + rise * 0.55), (mx, my, h + rise)], roof + '_shade')
        scene.face([(x0 + inset - 0.5, y1 - inset + 0.5, h + rise * 0.55), (x1 - inset + 0.5, y1 - inset + 0.5, h + rise * 0.55), (mx, my, h + rise)], roof)


def dome(scene, part):
    """Drum and dome with a lantern. at=[centre x, y], radius, drum, base (height of the block below)."""
    ctx, pal = scene.ctx, scene.pal
    cx, cy = part['at']
    radius, drum, base = part['radius'], part.get('drum', 5), part.get('base', 0)
    colour = part.get('colour', 'slate')
    broken = scene.damaged and part.get('damage') == 'broken'
    px, py = iso(cx, cy, base)
    rx, ry = radius * 0.866 * 1.41, radius * 0.36 * 1.41       # the drum's circle seen at the plan angle
    ctx.new_path()                                              # drum
    ctx.move_to(px - rx, py - drum)
    ctx.line_to(px - rx, py)
    ctx.save()
    ctx.translate(px, py)
    ctx.scale(rx, ry)
    ctx.arc_negative(0, 0, 1, math.pi, 0)
    ctx.restore()
    ctx.line_to(px + rx, py - drum)
    ctx.close_path()
    draw.inked(ctx, pal('stone'), pal('ink'), INK, ink_alpha=0.9)
    ctx.save()
    ctx.rectangle(px + rx * 0.15, py - drum - 1, rx, drum + ry + 2)
    ctx.clip()
    draw.ellipse(ctx, px, py - drum / 2, rx, drum / 2 + ry)
    draw.wash(ctx, pal('stone_shade'), 0.75)
    ctx.restore()
    for t in (-0.6, -0.2, 0.2, 0.6):                            # drum windows
        wx = px + rx * t
        wy = py - drum * 0.75 + ry * math.sqrt(max(0, 1 - t * t))
        ctx.rectangle(wx - 0.7, wy, 1.4, drum * 0.5)
    draw.wash(ctx, pal('window'), 0.9)
    top = py - drum
    height = radius * (0.62 if broken else 1.25)
    ctx.new_path()                                              # dome shell
    ctx.move_to(px - rx, top)
    ctx.curve_to(px - rx, top - height * 0.75, px - rx * 0.55, top - height, px, top - height)
    ctx.curve_to(px + rx * 0.55, top - height, px + rx, top - height * 0.75, px + rx, top)
    ctx.save()
    ctx.translate(px, top)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, math.pi)
    ctx.restore()
    ctx.close_path()
    path = ctx.copy_path()
    draw.inked(ctx, pal(colour), pal('ink'), INK, ink_alpha=0.9)
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    draw.ellipse(ctx, px + rx * 0.62, top - height * 0.35, rx * 0.72, height * 0.95)
    draw.wash(ctx, pal(colour + '_shade'), 0.85)
    draw.ellipse(ctx, px - rx * 0.42, top - height * 0.62, rx * 0.26, height * 0.3)
    draw.wash(ctx, pal(colour + '_light'), 0.8)
    for t in (-0.55, 0.0, 0.5):                                 # gilt ribs
        ctx.move_to(px + rx * t, top + ry * math.sqrt(max(0, 1 - t * t)))
        ctx.curve_to(px + rx * t, top - height * 0.6, px + rx * t * 0.5, top - height * 0.95, px, top - height)
    draw.line(ctx, pal('gilt'), 0.9, 0.85)
    if broken:
        draw.polygon(ctx, [(px - rx * 0.2, top - height * 1.1), (px + rx * 0.7, top - height * 1.1), (px + rx * 0.9, top - height * 0.3),
                           (px + rx * 0.3, top - height * 0.55), (px + rx * 0.05, top - height * 0.2), (px - rx * 0.3, top - height * 0.6)])
        draw.wash(ctx, pal('ink'), 0.85)
    ctx.restore()
    if broken:
        soot(scene, cx, cy, base + drum + height, radius * 0.7)
        return
    draw.rounded_rect(ctx, px - 1.5, top - height - 3.6, 3.0, 4.0, 0.6)   # lantern
    draw.inked(ctx, pal('gilt'), pal('ink'), 0.8)
    ctx.move_to(px, top - height - 3.6)
    ctx.line_to(px, top - height - 8.0)
    draw.line(ctx, pal('ink'), 0.9)
    draw.ellipse(ctx, px, top - height - 5.2, 1.0, 1.0)
    draw.wash(ctx, pal('gilt'))


def wall(scene, part):
    """Curtain wall between ground points. path=[[x,y],...], height. damage: breach."""
    points, h = part['path'], part.get('height', 4)
    material = part.get('wall', 'stone')
    for index, (a, b) in enumerate(zip(points, points[1:])):
        faces_light = abs(b[0] - a[0]) > abs(b[1] - a[1])     # runs along x: its visible side looks toward +y
        colour = material if faces_light else material + '_shade'
        breach = scene.damaged and part.get('damage') == 'breach' and index == part.get('breach_at', 0)
        if breach:
            m1, m2 = draw.lerp_point(a, b, 0.36), draw.lerp_point(a, b, 0.64)
            scene.face([(a[0], a[1], 0), (m1[0], m1[1], 0), (m1[0], m1[1], h * 0.5), (a[0], a[1], h)], colour)
            scene.face([(m2[0], m2[1], 0), (b[0], b[1], 0), (b[0], b[1], h), (m2[0], m2[1], h * 0.35)], colour)
            mid = draw.lerp_point(a, b, 0.5)
            rubble(scene, mid[0] + 1, mid[1] + 1, 3.0, 9)
            continue
        scene.face([(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], h), (a[0], a[1], h)], colour)
        merlons = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 3.2))
        for step in range(merlons):
            t0, t1 = (step + 0.15) / merlons, (step + 0.6) / merlons
            p, q = draw.lerp_point(a, b, t0), draw.lerp_point(a, b, t1)
            scene.face([(p[0], p[1], h), (q[0], q[1], h), (q[0], q[1], h + 1.3), (p[0], p[1], h + 1.3)], colour, 0.75)
        if part.get('gate') == index:
            mid = draw.lerp_point(a, b, 0.5)
            dx, dy = (b[0] - a[0]) * 0.09, (b[1] - a[1]) * 0.09
            scene.tint([(mid[0] - dx, mid[1] - dy, 0), (mid[0] + dx, mid[1] + dy, 0), (mid[0] + dx, mid[1] + dy, h * 0.7),
                        (mid[0], mid[1], h * 0.92), (mid[0] - dx, mid[1] - dy, h * 0.7)], 'window', 0.95)


def basin(scene, part):
    """Harbour water enclosed by quay stone. rect=[x0,y0,x1,y1]."""
    x0, y0, x1, y1 = part['rect']
    depth = part.get('depth', 2.2)
    scene.face([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], 'sea')
    scene.tint([(x0, y0, 0), (x1, y0, 0), (x1, y0 + depth, 0), (x0, y0 + depth, 0)], 'sea_deep', 0.8)      # quay wall shadow
    scene.tint([(x0, y0, 0), (x0 + depth, y0, 0), (x0 + depth, y1, 0), (x0, y1, 0)], 'sea_deep', 0.8)
    rng = random.Random(part.get('seed', 3))
    ctx = scene.ctx
    for _ in range(part.get('ripples', 9)):
        wx, wy = rng.uniform(x0 + 3, x1 - 3), rng.uniform(y0 + 3, y1 - 3)
        px, py = iso(wx, wy)
        ctx.move_to(px - 2.4, py)
        ctx.curve_to(px - 1.2, py - 0.9, px, py - 0.9, px + 0.2, py)
        ctx.curve_to(px + 1.0, py + 0.8, px + 1.8, py + 0.8, px + 2.6, py)
    draw.line(ctx, scene.pal('foam'), 0.8, 0.75)


def ship(scene, part):
    """Moored merchantman, bow toward +x. damage: wreck (dismasted, listing)."""
    ctx, pal = scene.ctx, scene.pal
    x, y = part['at']
    length, beam = part.get('length', 16), part.get('beam', 4.5)
    wreck = scene.damaged and part.get('damage') == 'wreck'
    deck = 2.6 if not wreck else 1.4
    hull = [(x, y - beam / 2, 0), (x + length * 0.78, y - beam / 2, 0), (x + length, y, 0), (x + length * 0.78, y + beam / 2, 0),
            (x, y + beam / 2, 0)]
    draw.shadow_blob(ctx, *iso(x + length / 2 + 1.5, y + 1.5), length * 0.62, beam * 0.75, pal('sea_ink'), 0.5)
    scene.face([(x, y + beam / 2, 0), (x + length * 0.78, y + beam / 2, 0), (x + length, y, 0), (x + length, y, deck + 1.2),
                (x + length * 0.78, y + beam / 2, deck), (x, y + beam / 2, deck + 0.9)], 'hull')
    scene.face([(px, py, deck + (0.9 if px == x else 0)) for px, py, _ in hull], 'deck')
    scene.stroke([(x, y + beam / 2, deck * 0.55), (x + length * 0.78, y + beam / 2, deck * 0.5), (x + length, y, deck * 0.8)],
                 'hull_stripe', 1.1)
    tall = part.get('masts', 20.0)
    masts = [(0.24, tall * 0.86), (0.52, tall), (0.76, tall * 0.7)] if not wreck else [(0.24, 5.0)]
    for position, height in masts:
        mx = x + length * position
        scene.stroke([(mx, y, deck), (mx + (2.5 if wreck else 0), y, deck + height)], 'ink', 1.25)
        if wreck:
            continue
        for level, half in ((0.46, beam * 0.95), (0.74, beam * 0.72)):   # yards with furled sail
            scene.stroke([(mx, y - half, deck + height * level), (mx, y + half, deck + height * level)], 'ink', 1.0)
            scene.stroke([(mx, y - half * 0.85, deck + height * level - 0.7), (mx, y + half * 0.85, deck + height * level - 0.7)],
                         'sail', 1.5)
        scene.stroke([(mx, y, deck + height), (x + length * (position + 0.3), y, deck + 0.5)], 'ink', 0.45, 0.8)   # stays
        scene.stroke([(mx, y, deck + height), (x + length * (position - 0.2), y, deck + 0.9)], 'ink', 0.45, 0.8)
    if not wreck:
        scene.stroke([(x + length * 0.9, y, deck + 1.2), (x + length * 1.22, y, deck + 3.4)], 'ink', 1.0)          # bowsprit
    else:
        soot(scene, x + length * 0.5, y, deck + 2, 4.0)


def crane(scene, part):
    """Treadwheel harbour crane."""
    x, y = part['at']
    if scene.damaged and part.get('damage') == 'ruin':
        rubble(scene, x, y, 2.5, 6)
        scene.stroke([(x, y, 0), (x + 3.0, y, 3.2)], 'ink', 1.2)
        return
    house(scene, {'at': [x - 3, y - 3], 'size': [6, 6, 7], 'roof': 3.5, 'wall': 'timber', 'roof_colour': 'slate', 'chimney': False})
    scene.stroke([(x, y, 9.0), (x + 11, y, 17.0)], 'timber_shade', 2.6)
    scene.stroke([(x, y, 9.0), (x + 11, y, 17.0)], 'ink', 0.8)
    scene.stroke([(x + 3, y, 8.0), (x + 7, y, 14.2)], 'ink', 0.8)
    scene.stroke([(x + 11, y, 17.0), (x + 11, y, 5.0)], 'ink', 0.7)
    px, py = iso(x + 11, y, 3.8)
    draw.rounded_rect(scene.ctx, px - 1.3, py - 1.0, 2.6, 2.2, 0.4)
    draw.inked(scene.ctx, scene.pal('timber'), scene.pal('ink'), 0.7)


def crates(scene, part):
    rng = random.Random(part.get('seed', 5))
    x, y = part['at']
    for _ in range(part.get('count', 4)):
        cx, cy, size = x + rng.uniform(-3, 3), y + rng.uniform(-3, 3), rng.uniform(1.4, 2.0)
        if rng.random() < 0.4:                                # barrel
            px, py = iso(cx, cy, 0)
            draw.rounded_rect(scene.ctx, px - 1.1, py - 2.6, 2.2, 2.8, 0.9)
            draw.inked(scene.ctx, scene.pal('timber'), scene.pal('ink'), 0.7)
            continue
        scene.face([(cx + size, cy, 0), (cx + size, cy + size, 0), (cx + size, cy + size, size), (cx + size, cy, size)], 'timber_shade', 0.8)
        scene.face([(cx, cy + size, 0), (cx + size, cy + size, 0), (cx + size, cy + size, size), (cx, cy + size, size)], 'timber', 0.8)
        scene.face([(cx, cy, size), (cx + size, cy, size), (cx + size, cy + size, size), (cx, cy + size, size)], 'timber', 0.8)


def trees(scene, part):
    for x, y, size in part['at']:
        px, py = iso(x, y)
        if scene.damaged and part.get('damage') == 'burnt':
            scene.ctx.move_to(px, py)
            scene.ctx.line_to(px - 0.5, py - size * 0.55)
            scene.ctx.move_to(px - 0.3, py - size * 0.35)
            scene.ctx.line_to(px + 2.0, py - size * 0.6)
            draw.line(scene.ctx, scene.pal('ink'), 1.2, 0.9)
            continue
        (fir_tree if part.get('kind') == 'fir' else round_tree)(scene.ctx, scene.pal, px, py, size, random.Random(int(x * 31 + y * 17)))


def smoke(scene, part):
    """Standing smoke, only on the damaged frame: engraved curls drifting down-wind."""
    if not scene.damaged:
        return
    ctx, pal = scene.ctx, scene.pal
    px, py = iso(*part['at'])
    rng = random.Random(part.get('seed', 11))
    puffs, lean = part.get('puffs', 5), part.get('lean', 0.55)
    for index in range(puffs):
        t = index / max(1, puffs - 1)
        radius = part.get('size', 4.0) * (0.55 + t * 0.85)
        cx, cy = px + lean * t * 16 + rng.uniform(-1, 1), py - t * 20 - radius * 0.2
        draw.ellipse(ctx, cx, cy, radius, radius * 0.86)
        draw.wash(ctx, pal('smoke'), 0.78 - t * 0.34, preserve=True)
        draw.line(ctx, pal('ink'), 0.7, 0.5 - t * 0.3)
        ctx.new_sub_path()
        ctx.arc(cx - radius * 0.2, cy + radius * 0.1, radius * 0.5, math.pi * 0.9, math.pi * 1.7)
        draw.line(ctx, pal('ink'), 0.6, 0.38 - t * 0.2)


PRIMITIVES = {'ground': ground, 'house': house, 'tower': tower, 'dome': dome, 'wall': wall, 'basin': basin,
              'ship': ship, 'crane': crane, 'crates': crates, 'trees': trees, 'smoke': smoke}


def depth(part):
    """Painter's-algorithm key: nearer parts (larger x + y) draw later."""
    if 'order' in part:
        return part['order']
    if part['type'] == 'ground':
        return -1e9
    if part['type'] == 'basin':
        return -1e8
    if part['type'] == 'wall':
        return max(point[0] + point[1] for point in part['path'])
    if part['type'] == 'trees':
        return max(x + y for x, y, _ in part['at'])
    x, y = part['at'][0], part['at'][1]
    size = part.get('size')
    if part['type'] == 'house':
        return x + y + size[0] + size[1]
    if part['type'] == 'tower':
        return x + y + size[0] * 2
    if part['type'] == 'dome':
        return x + y + part['radius'] * 2
    return x + y


def paint(spec):
    """params: plans (JSON path beside batch.json), plan (key in that file)."""
    plans = spec.data(spec.params['plans'])
    name = spec.params['plan']
    if name not in plans['plans']:
        raise KeyError(f'{spec.id}: plan {name!r} not in {spec.params["plans"]}; has {sorted(plans["plans"])}')
    parts = sorted(plans['plans'][name]['parts'], key=depth)
    for part in parts:
        if part['type'] not in PRIMITIVES:
            raise KeyError(f'{spec.id}: unknown part type {part["type"]!r}; known: {sorted(PRIMITIVES)}')
    pal = spec.palette

    scale = plans['plans'][name].get('scale', 1.0)

    def draw_frame(ctx, index):
        scene = Scene(ctx, pal, random.Random(spec.seed), damaged=index == 1)
        ctx.save()
        ctx.translate(*GROUND)                                 # plans scale about the shared ground point
        ctx.scale(scale, scale)
        ctx.translate(-GROUND[0], -GROUND[1])
        for part in parts:
            PRIMITIVES[part['type']](scene, part)
        ctx.restore()

    frames = sheet.render(spec.frame, draw_frame, 2, lambda image, index: paper_grain(image, spec.seed + index, mottle=0))
    return sheet.Work(frames=frames, clips={name: dict(clip) for name, clip in CLIPS.items()}, vector=draw_frame)
