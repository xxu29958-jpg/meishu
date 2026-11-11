"""Interface chrome: the campaign desk in brass, oxblood, gunmetal and parchment.

Every control is one function of (size, state, options). The four contract
states are painted, not filtered: pressed sinks and darkens, selected takes a
gilt rule and glow, disabled loses its colour and its relief. Text and numbers
are never painted here; layouts supply them. Stretch insets live in batch.json
beside each asset and must clear the corner ornament drawn here.
"""
import math
import random

import cairo

from ..kit import draw, sheet
from ..kit.raster import desaturate, glow, paper_grain

STATES = ('normal', 'pressed', 'selected', 'disabled')


def vertical(ctx, y0, y1, top, bottom):
    gradient = cairo.LinearGradient(0, y0, 0, y1)
    gradient.add_color_stop_rgba(0, *top)
    gradient.add_color_stop_rgba(1, *bottom)
    ctx.set_source(gradient)


def rivet(ctx, pal, x, y, radius=2.2):
    draw.ellipse(ctx, x, y, radius, radius)
    draw.inked(ctx, pal('ui_brass'), pal('ink'), 0.8)
    draw.ellipse(ctx, x - radius * 0.3, y - radius * 0.3, radius * 0.4, radius * 0.4)
    draw.wash(ctx, pal('ui_brass_light'))


def parchment(ctx, pal, x, y, width, height, radius, tone=1.0):
    """Aged sheet: warm centre, edges toned down as if handled for a campaign."""
    draw.rounded_rect(ctx, x, y, width, height, radius)
    path = ctx.copy_path()
    draw.wash(ctx, pal.tone('ui_parchment', tone))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    edge = pal.tone('ui_parchment_deep', tone)
    reach = min(width, height) * 0.34
    for step in range(7):                                    # even toning toward every edge
        draw.rounded_rect(ctx, x, y, width, height, radius)
        draw.line(ctx, edge, reach * (1 - step / 7) * 2, 0.085)
    ctx.restore()


def panel(ctx, pal, width, height, state, options):
    pressed, selected = state == 'pressed', state == 'selected'
    draw.rounded_rect(ctx, 5, 7, width - 8, height - 9, 8)                           # cast shadow
    draw.wash(ctx, pal('ink'), 0.42)
    draw.rounded_rect(ctx, 3, 3, width - 8, height - 9, 7)                           # iron-bound frame
    vertical(ctx, 3, height - 6, pal('ui_frame_light'), pal('ui_frame'))
    ctx.fill_preserve()
    draw.line(ctx, pal('ink'), 1.6)
    draw.rounded_rect(ctx, 5.5, 5.5, width - 13, height - 14, 5.5)
    draw.line(ctx, pal('ui_brass_light' if selected else 'ui_brass'), 1.4 if selected else 1.0)
    parchment(ctx, pal, 13, 13, width - 28, height - 29, 3, 0.9 if pressed else 1.0)
    draw.rounded_rect(ctx, 13, 13, width - 28, height - 29, 3)
    draw.line(ctx, pal('ink'), 1.3)
    if pressed:                                                                       # the sheet sits deeper in its frame
        ctx.save()
        draw.rounded_rect(ctx, 13, 13, width - 28, height - 29, 3)
        ctx.clip()
        draw.shadow_blob(ctx, width / 2, 13, width * 0.6, 16, pal('ink'), 0.42)
        ctx.restore()
    rule = pal('ui_brass_light') if selected else pal('ink', 0.62)
    draw.rounded_rect(ctx, 19, 19, width - 40, height - 41, 1.5)                     # engraved double rule
    draw.line(ctx, rule, 1.8 if selected else 1.2)
    draw.rounded_rect(ctx, 22.5, 22.5, width - 47, height - 48, 1)
    draw.line(ctx, rule, 0.7, 0.7)
    for cx, cy, sx, sy in ((3, 3, 1, 1), (width - 5, 3, -1, 1), (3, height - 6, 1, -1), (width - 5, height - 6, -1, -1)):
        corner = [(cx, cy), (cx + 23 * sx, cy), (cx + 23 * sx, cy + 6 * sy), (cx + 9 * sx, cy + 9 * sy), (cx + 6 * sx, cy + 23 * sy), (cx, cy + 23 * sy)]
        draw.polygon(ctx, corner)                                                    # brass corner plates
        draw.inked(ctx, pal('ui_brass_light' if selected else 'ui_brass'), pal('ink'), 1.1)
        draw.polygon(ctx, [(cx + 2 * sx, cy + 2 * sy), (cx + 20 * sx, cy + 2 * sy), (cx + 20 * sx, cy + 3.4 * sy), (cx + 3.4 * sx, cy + 3.4 * sy),
                           (cx + 3.4 * sx, cy + 20 * sy), (cx + 2 * sx, cy + 20 * sy)])
        draw.wash(ctx, pal('ui_brass_light'), 0.7)
        rivet(ctx, pal, cx + 6.2 * sx, cy + 6.2 * sy, 1.9)


def button(ctx, pal, width, height, state, options):
    pressed, selected = state == 'pressed', state == 'selected'
    body = options.get('body', 'ui_red')
    sink = 2.0 if pressed else 0.0
    draw.rounded_rect(ctx, 5, 8, width - 10, height - 12, 9)                         # shadow on the desk
    draw.wash(ctx, pal('ink'), 0.25 if pressed else 0.48)
    x, y, w, h = 4, 4 + sink, width - 8, height - 12
    draw.rounded_rect(ctx, x, y, w, h, 9)                                             # brass casing
    vertical(ctx, y, y + h, pal('ui_brass_light' if selected else 'ui_brass'), pal('ui_brass_deep'))
    ctx.fill_preserve()
    draw.line(ctx, pal('ink'), 1.6)
    draw.rounded_rect(ctx, x + 4, y + 4, w - 8, h - 8, 6)                             # enamel face
    face = ctx.copy_path()
    top = pal.tone(body + '_light', 0.82 if pressed else 1.0)
    bottom = pal.tone(body + '_deep' if pressed else body, 1.0)
    vertical(ctx, y + 4, y + h - 4, top, bottom)
    ctx.fill_preserve()
    draw.line(ctx, pal('ink'), 1.1)
    ctx.save()
    ctx.append_path(face)
    ctx.clip()
    if pressed:
        draw.shadow_blob(ctx, width / 2, y + 4, width * 0.6, 12, pal('ink'), 0.55)
    else:
        draw.rounded_rect(ctx, x + 7, y + 6.5, w - 14, (h - 8) * 0.36, 4)             # light along the upper bevel
        draw.wash(ctx, pal('paper'), 0.13)
    ctx.restore()
    draw.rounded_rect(ctx, x + 7.5, y + 7.5, w - 15, h - 15, 3.5)                     # inner gilt rule
    draw.line(ctx, pal('ui_brass_light' if selected else 'ui_brass'), 1.5 if selected else 0.9, 1.0 if selected else 0.8)
    for cx, flip in ((x + 17, 1), (x + w - 17, -1)):                                  # end studs
        cy = y + h / 2
        draw.polygon(ctx, [(cx - 5 * flip, cy), (cx, cy - 5), (cx + 5 * flip, cy), (cx, cy + 5)])
        draw.inked(ctx, pal('ui_brass_light' if selected else 'ui_brass'), pal('ink'), 0.9)
        draw.ellipse(ctx, cx, cy, 1.4, 1.4)
        draw.wash(ctx, pal('ui_brass_deep'))


def tab(ctx, pal, width, height, state, options):
    pressed, selected = state == 'pressed', state == 'selected'
    top = 4 if selected else 9
    outline = [(4, height), (4, top + 9), (13, top), (width - 13, top), (width - 4, top + 9), (width - 4, height)]
    draw.polygon(ctx, [(x + 2, y + 2) for x, y in outline])
    draw.wash(ctx, pal('ink'), 0.3)
    draw.polygon(ctx, outline)
    path = ctx.copy_path()
    tone = 1.0 if selected else (0.74 if pressed else 0.86)
    draw.wash(ctx, pal.tone('ui_parchment' if selected else 'ui_parchment_shade', tone))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    draw.shadow_blob(ctx, width / 2, height, width * 0.6, 12 if selected else 22, pal('ui_parchment_deep'), 0.7)
    if selected:
        ctx.rectangle(0, top, width, 4.5)
        draw.wash(ctx, pal('ui_red'))
        ctx.rectangle(0, top + 4.5, width, 1.4)
        draw.wash(ctx, pal('ui_brass_light'))
    ctx.restore()
    draw.polygon(ctx, outline, closed=False)
    draw.line(ctx, pal('ink'), 1.4)
    if not selected:                                                                   # unselected tabs sit behind the sheet
        ctx.move_to(4, height - 0.7)
        ctx.line_to(width - 4, height - 0.7)
        draw.line(ctx, pal('ink'), 1.4)


def row(ctx, pal, width, height, state, options):
    pressed, selected = state == 'pressed', state == 'selected'
    draw.rounded_rect(ctx, 3, 3, width - 6, height - 6, 4)
    path = ctx.copy_path()
    if selected:
        vertical(ctx, 3, height - 3, pal('ui_red_light', 0.94), pal('ui_red', 0.94))
        ctx.fill()
    else:
        draw.wash(ctx, pal('ui_parchment_deep'), 0.62 if pressed else 0.26)
    ctx.append_path(path)
    draw.line(ctx, pal('ui_brass_light') if selected else pal('ink', 0.5), 1.5 if selected else 1.0)
    if selected:
        draw.rounded_rect(ctx, 3, 3, 7, height - 6, 3)
        draw.wash(ctx, pal('ui_brass_light'))
        draw.rounded_rect(ctx, 6.5, 6.5, width - 13, height - 13, 2.5)
        draw.line(ctx, pal('ui_brass'), 0.8, 0.8)
    if pressed:
        ctx.save()
        ctx.append_path(path)
        ctx.clip()
        draw.shadow_blob(ctx, width / 2, 3, width * 0.6, 10, pal('ink'), 0.4)
        ctx.restore()


def chip(ctx, pal, width, height, state, options):
    pressed, selected = state == 'pressed', state == 'selected'
    radius = (height - 8) / 2
    draw.rounded_rect(ctx, 5, 6, width - 8, height - 8, radius)
    draw.wash(ctx, pal('ink'), 0.4)
    draw.rounded_rect(ctx, 3, 3, width - 8, height - 8, radius)
    vertical(ctx, 3, height - 5, pal('ui_steel_light' if not pressed else 'ui_steel'), pal('ui_steel_deep'))
    ctx.fill_preserve()
    draw.line(ctx, pal('ink'), 1.4)
    draw.rounded_rect(ctx, 5.2, 5.2, width - 12.4, height - 12.4, radius - 2)
    draw.line(ctx, pal('ui_brass_light' if selected else 'ui_brass'), 1.5 if selected else 1.0)
    well = (3 + radius, 3 + radius)
    draw.ellipse(ctx, well[0], well[1], radius - 4, radius - 4)                       # icon well
    draw.inked(ctx, pal('ui_frame'), pal('ui_brass'), 1.0)


def rule(ctx, pal, width, height, state, options):
    """Section divider: engraved line swelling into a central diamond."""
    y = height / 2
    for x0, x1 in ((6, width / 2 - 12), (width / 2 + 12, width - 6)):
        ctx.move_to(x0, y)
        ctx.line_to(x1, y)
    draw.line(ctx, pal('ink'), 1.2, 0.7)
    for x0, x1 in ((6, width / 2 - 16), (width / 2 + 16, width - 6)):
        ctx.move_to(x0, y + 3)
        ctx.line_to(x1, y + 3)
    draw.line(ctx, pal('ink'), 0.6, 0.5)
    draw.polygon(ctx, [(width / 2 - 8, y + 1), (width / 2, y - 6), (width / 2 + 8, y + 1), (width / 2, y + 8)])
    draw.inked(ctx, pal('ui_red'), pal('ink'), 1.0)
    draw.ellipse(ctx, width / 2, y + 1, 2.0, 2.0)
    draw.wash(ctx, pal('ui_brass_light'))


def icon_gold(ctx, pal, size):
    for offset in (9, 5, 1):                                                          # a stack of napoleons
        draw.ellipse(ctx, size * 0.5, size * 0.62 - offset, size * 0.3, size * 0.13)
        draw.inked(ctx, pal('ui_brass_deep' if offset else 'ui_brass'), pal('ink'), 1.1)
    draw.ellipse(ctx, size * 0.5, size * 0.62 - 12, size * 0.3, size * 0.13)
    draw.inked(ctx, pal('ui_brass_light'), pal('ink'), 1.1)
    draw.ellipse(ctx, size * 0.5, size * 0.62 - 12, size * 0.2, size * 0.075)
    draw.line(ctx, pal('ui_brass_deep'), 0.9)


def icon_men(ctx, pal, size):
    cx = size * 0.5                                                                   # head and shoulders under a cocked hat
    draw.smooth(ctx, [(cx - 15, size * 0.92), (cx - 13, size * 0.68), (cx - 5, size * 0.6), (cx + 5, size * 0.6), (cx + 13, size * 0.68), (cx + 15, size * 0.92)], tension=0.4)
    draw.inked(ctx, pal('fr_blue'), pal('ink'), 1.2)
    draw.polygon(ctx, [(cx - 4, size * 0.62), (cx + 4, size * 0.62), (cx, size * 0.86)])
    draw.wash(ctx, pal('cloth_white'))
    draw.ellipse(ctx, cx, size * 0.46, 7.2, 8.0)
    draw.inked(ctx, pal('skin'), pal('ink'), 1.1)
    draw.smooth(ctx, [(cx - 18, size * 0.36), (cx - 9, size * 0.2), (cx, size * 0.12), (cx + 9, size * 0.2), (cx + 18, size * 0.36), (cx, size * 0.31)], tension=0.4)
    draw.inked(ctx, pal('hat_black'), pal('ink'), 1.2)
    draw.ellipse(ctx, cx + 3, size * 0.22, 2.4, 2.4)
    draw.wash(ctx, pal('fr_red'))


def icon_guns(ctx, pal, size):
    ctx.save()                                                                        # field gun in profile
    ctx.translate(size * 0.5, size * 0.6)
    ctx.rotate(-0.22)
    draw.rounded_rect(ctx, -17, -5, 34, 8, 3)
    draw.inked(ctx, pal('ui_brass'), pal('ink'), 1.2)
    draw.rounded_rect(ctx, 14, -6.5, 4, 11, 1.5)
    draw.inked(ctx, pal('ui_brass_light'), pal('ink'), 1.0)
    ctx.restore()
    ctx.move_to(size * 0.42, size * 0.66)
    ctx.line_to(size * 0.12, size * 0.9)
    draw.line(ctx, pal('ink'), 4.2)
    ctx.move_to(size * 0.42, size * 0.66)
    ctx.line_to(size * 0.12, size * 0.9)
    draw.line(ctx, pal('timber'), 2.4)
    draw.ellipse(ctx, size * 0.5, size * 0.72, 10.5, 10.5)
    draw.inked(ctx, pal('timber'), pal('ink'), 1.3)
    draw.ellipse(ctx, size * 0.5, size * 0.72, 7.2, 7.2)
    draw.line(ctx, pal('ink'), 0.9)
    for index in range(6):
        angle = index * math.pi / 3
        ctx.move_to(size * 0.5, size * 0.72)
        ctx.line_to(size * 0.5 + math.cos(angle) * 10, size * 0.72 + math.sin(angle) * 10)
    draw.line(ctx, pal('ink'), 0.9)
    draw.ellipse(ctx, size * 0.5, size * 0.72, 2.2, 2.2)
    draw.wash(ctx, pal('ui_brass'))


ICONS = {'gold': icon_gold, 'men': icon_men, 'guns': icon_guns}


def icon(ctx, pal, width, height, state, options):
    if state == 'selected':
        draw.ellipse(ctx, width / 2, height / 2, width * 0.46, height * 0.46)
        draw.wash(ctx, pal('ui_brass_light'), 0.28)
    ctx.save()
    if state == 'pressed':
        ctx.translate(width * 0.04, height * 0.06)
        ctx.scale(0.94, 0.94)
    ICONS[options['icon']](ctx, pal, width)
    ctx.restore()


def backdrop(ctx, pal, width, height, state, options):
    """The campaign desk: a chart under lamplight, corners lost in shadow."""
    rng = random.Random(options.get('seed', 1805))
    vertical(ctx, 0, height, pal('ui_wood'), pal('ui_wood_deep'))
    ctx.paint()
    for index in range(int(height / 64) + 1):                                         # desk boards
        y = index * 64 + rng.uniform(-3, 3)
        ctx.move_to(0, y)
        ctx.line_to(width, y + rng.uniform(-2, 2))
    draw.line(ctx, pal('ink'), 1.4, 0.5)
    ctx.save()
    ctx.translate(width * 0.56, height * 0.52)
    ctx.rotate(-0.035)
    sheet_w, sheet_h = width * 0.76, height * 0.84
    draw.rounded_rect(ctx, -sheet_w / 2 + 10, -sheet_h / 2 + 14, sheet_w, sheet_h, 4)
    draw.wash(ctx, pal('ink'), 0.5)
    parchment(ctx, pal, -sheet_w / 2, -sheet_h / 2, sheet_w, sheet_h, 3, 0.94)
    ctx.rectangle(-sheet_w / 2, -sheet_h / 2, sheet_w, sheet_h)
    ctx.clip()
    for index in range(1, 12):                                                        # graticule
        x = -sheet_w / 2 + sheet_w * index / 12
        ctx.move_to(x, -sheet_h / 2)
        ctx.line_to(x, sheet_h / 2)
    for index in range(1, 7):
        y = -sheet_h / 2 + sheet_h * index / 7
        ctx.move_to(-sheet_w / 2, y)
        ctx.line_to(sheet_w / 2, y)
    draw.line(ctx, pal('ink'), 0.7, 0.2)
    for _ in range(options.get('lands', 5)):                                          # imagined coasts, engraved and washed
        cx, cy = rng.uniform(-sheet_w * 0.4, sheet_w * 0.4), rng.uniform(-sheet_h * 0.36, sheet_h * 0.36)
        rx, ry = rng.uniform(90, 260), rng.uniform(60, 150)
        points = []
        for step in range(22):
            angle = step * math.tau / 22
            reach = rng.uniform(0.62, 1.12)
            points.append((cx + math.cos(angle) * rx * reach, cy + math.sin(angle) * ry * reach))
        for grow, alpha in ((16, 0.10), (9, 0.16)):
            draw.smooth(ctx, [(cx + (x - cx) * (1 + grow / rx), cy + (y - cy) * (1 + grow / ry)) for x, y in points], tension=0.6)
            draw.line(ctx, pal('sea_ink'), 0.9, alpha * 2)
        draw.smooth(ctx, points, tension=0.6)
        draw.wash(ctx, pal('grass'), 0.34, preserve=True)
        draw.line(ctx, pal('ink'), 1.3, 0.72)
    compass = (sheet_w * 0.36, sheet_h * 0.3)
    for index in range(16):                                                           # compass rose
        angle = index * math.tau / 16
        long = 46 if index % 4 == 0 else (30 if index % 2 == 0 else 18)
        tip = (compass[0] + math.cos(angle) * long, compass[1] + math.sin(angle) * long)
        left = (compass[0] + math.cos(angle + 0.2) * 7, compass[1] + math.sin(angle + 0.2) * 7)
        right = (compass[0] + math.cos(angle - 0.2) * 7, compass[1] + math.sin(angle - 0.2) * 7)
        draw.polygon(ctx, [left, tip, right])
        draw.inked(ctx, pal('ui_red' if index % 4 == 0 else 'ui_parchment_deep'), pal('ink'), 0.8, fill_alpha=0.8, ink_alpha=0.75)
    draw.ellipse(ctx, compass[0], compass[1], 52, 52)
    draw.line(ctx, pal('ink'), 0.8, 0.55)
    ctx.restore()
    shade = cairo.RadialGradient(width * 0.42, height * 0.4, height * 0.15, width * 0.5, height * 0.5, width * 0.66)
    shade.add_color_stop_rgba(0, 1.0, 0.82, 0.5, 0.10)                                # lamplight, then the dark
    shade.add_color_stop_rgba(0.45, 0, 0, 0, 0.0)
    shade.add_color_stop_rgba(1, 0.05, 0.03, 0.02, 0.86)
    ctx.set_source(shade)
    ctx.paint()


COMPONENTS = {'panel': panel, 'button': button, 'tab': tab, 'row': row, 'chip': chip, 'rule': rule, 'icon': icon, 'backdrop': backdrop}
STATIC = {'rule', 'backdrop'}             # one painted frame serves all four states


def finish(image, state, kind, seed):
    if kind == 'backdrop':
        return paper_grain(image, seed, fine=0.035, mottle=0.05, mottle_cell=90)
    image = paper_grain(image, seed, fine=0.022, mottle=0.012, mottle_cell=40)
    if state == 'selected' and kind in ('button', 'chip', 'icon'):
        image = glow(image, 3.2, 0.75, tint=(255, 214, 120))
    if state == 'disabled':
        image = desaturate(image, 0.82, lift=0.10)
    return image


def paint(spec):
    """params: kind (panel | button | tab | row | chip | rule | icon | backdrop) plus that component's options."""
    kind = spec.params['kind']
    if kind not in COMPONENTS:
        raise KeyError(f'{spec.id}: unknown UI component {kind!r}; known: {sorted(COMPONENTS)}')
    pal, (width, height) = spec.palette, spec.frame
    states = ('normal',) if kind in STATIC else STATES

    def draw_frame(ctx, index):
        state = states[index]
        COMPONENTS[kind](ctx, pal, width, height, 'normal' if state == 'disabled' else state, spec.params)

    frames = sheet.render(spec.frame, draw_frame, len(states), lambda image, index: finish(image, states[index], kind, spec.seed))
    clips = {state: {'frames': [0 if kind in STATIC else index], 'fps': 1, 'loop': False} for index, state in enumerate(STATES)}
    return sheet.Work(frames=frames, clips=clips, vector=draw_frame)
