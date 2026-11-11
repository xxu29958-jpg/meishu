"""Flags as painted cloth, described by data.

A flag record gives a field of bands and optional charges (cross, saltire,
canton, disc). The painter adds what every flag shares: a slight fall of the
cloth, a hem, and the ink line. Heraldic detail beyond these primitives is a
new charge function here plus a record that uses it.
"""
import math

from ..kit import draw, sheet
from ..kit.raster import paper_grain

STILL = {'still': {'frames': [0], 'fps': 1, 'loop': False}}
INSET = (5.0, 5.0)


def field(ctx, pal, record, width, height):
    bands = record['bands']
    weights = record.get('weights', [1] * len(bands))
    total, cursor = float(sum(weights)), 0.0
    for colour, weight in zip(bands, weights):
        share = weight / total
        if record.get('layout', 'vertical') == 'vertical':
            ctx.rectangle(cursor * width, 0, share * width + 0.5, height)
        else:
            ctx.rectangle(0, cursor * height, width, share * height + 0.5)
        draw.wash(ctx, pal(colour))
        cursor += share


def cross(ctx, pal, charge, width, height):
    arm = charge.get('arm', 0.2) * height
    cx, cy = charge.get('centre', [0.5, 0.5])[0] * width, charge.get('centre', [0.5, 0.5])[1] * height
    ctx.rectangle(0, cy - arm / 2, width, arm)
    ctx.rectangle(cx - arm / 2, 0, arm, height)
    draw.wash(ctx, pal(charge['colour']))


def saltire(ctx, pal, charge, width, height):
    for start, end in (((0, 0), (width, height)), ((0, height), (width, 0))):
        ctx.move_to(*start)
        ctx.line_to(*end)
    ctx.set_line_cap(0)
    draw.line(ctx, pal(charge['colour']), charge.get('arm', 0.2) * height)
    ctx.set_line_cap(1)


def canton(ctx, pal, charge, width, height):
    ctx.rectangle(0, 0, charge.get('size', [0.5, 0.5])[0] * width, charge.get('size', [0.5, 0.5])[1] * height)
    draw.wash(ctx, pal(charge['colour']))


def disc(ctx, pal, charge, width, height):
    centre = charge.get('centre', [0.5, 0.5])
    radius = charge.get('radius', 0.3) * height
    draw.ellipse(ctx, centre[0] * width, centre[1] * height, radius, radius)
    draw.wash(ctx, pal(charge['colour']))


CHARGES = {'cross': cross, 'saltire': saltire, 'canton': canton, 'disc': disc}


def paint(spec):
    """params: flags (JSON path beside batch.json), flag (key in that file)."""
    flags = spec.data(spec.params['flags'])
    name = spec.params['flag']
    if name not in flags['flags']:
        raise KeyError(f'{spec.id}: flag {name!r} not in {spec.params["flags"]}; has {sorted(flags["flags"])}')
    record, pal = flags['flags'][name], spec.palette
    width, height = spec.frame[0] - 2 * INSET[0], spec.frame[1] - 2 * INSET[1]

    def draw_frame(ctx, _index):
        ctx.save()
        ctx.translate(*INSET)
        draw.rounded_rect(ctx, 1.5, 2.0, width, height, 1.5)                 # cast shadow
        draw.wash(ctx, pal('ink'), 0.35)
        draw.rounded_rect(ctx, 0, 0, width, height, 1.5)
        ctx.clip()
        field(ctx, pal, record, width, height)
        for charge in record.get('charges', []):
            if charge['type'] not in CHARGES:
                raise KeyError(f'{spec.id}: unknown charge {charge["type"]!r}; known: {sorted(CHARGES)}')
            CHARGES[charge['type']](ctx, pal, charge, width, height)
        for index in range(4):                                               # the cloth falls in soft folds
            x = width * (0.14 + index * 0.26)
            draw.shadow_blob(ctx, x, height * 0.5, width * 0.07, height * 0.9, pal('ink'), 0.20)
            draw.shadow_blob(ctx, x + width * 0.12, height * 0.5, width * 0.06, height * 0.9, pal('paper'), 0.16)
        ctx.rectangle(0, 0, width * 0.035, height)                           # hoist hem
        draw.wash(ctx, pal('ink'), 0.28)
        ctx.restore()
        ctx.save()
        ctx.translate(*INSET)
        draw.rounded_rect(ctx, 0, 0, width, height, 1.5)
        draw.line(ctx, pal('ink'), 1.4)
        ctx.restore()

    frames = sheet.render(spec.frame, draw_frame, 1, lambda image, _i: paper_grain(image, spec.seed, fine=0.03, mottle=0.02))
    return sheet.Work(frames=frames, clips=dict(STILL), vector=draw_frame)
