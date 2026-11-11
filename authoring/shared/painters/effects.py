"""Battlefield effects as short one-shot sheets.

An effect is a recipe (JSON) of timed layers: burst, sparks, smoke, debris. Each
layer is drawn as a function of normalised time, so changing frame count or fps
in the recipe retimes the whole effect. The anchor is the frame centre: the
point of impact stays put while everything else moves.
"""
import math
import random

from ..kit import draw, sheet
from ..kit.raster import paper_grain

CENTRE = (64.0, 64.0)


def ease_out(t):
    return 1 - (1 - min(max(t, 0.0), 1.0)) ** 3


def window(t, start, end):
    """0 before start, 1 after end, linear between."""
    return min(max((t - start) / (end - start), 0.0), 1.0)


def burst(ctx, pal, rng, layer, t):
    """Impact flash: a jagged star that snaps open and is gone."""
    life = window(t, layer.get('start', 0.0), layer.get('end', 0.45))
    if life >= 1.0:
        return
    grow = ease_out(life * 3.0)                      # open at once; an impact does not swell
    alpha = 1.0 - life ** 1.5
    spikes = layer.get('spikes', 11)
    lengths = [rng.uniform(0.62, 1.0) for _ in range(spikes)]
    twist = rng.uniform(0, math.tau)
    for colour, scale in ((layer.get('edge', 'flash_edge'), 1.0), (layer.get('core', 'flash_core'), 0.72),
                          (layer.get('heart', 'flash_white'), 0.42)):
        radius = layer.get('radius', 30.0) * scale * (0.35 + 0.65 * grow)
        points = []
        for index in range(spikes):
            angle = twist + index * math.tau / spikes
            points.append((CENTRE[0] + math.cos(angle) * radius * lengths[index], CENTRE[1] + math.sin(angle) * radius * lengths[index]))
            between = angle + math.pi / spikes
            points.append((CENTRE[0] + math.cos(between) * radius * 0.34, CENTRE[1] + math.sin(between) * radius * 0.34))
        draw.polygon(ctx, points)
        draw.wash(ctx, pal(colour), alpha)


def sparks(ctx, pal, rng, layer, t):
    """Hot fragments thrown outward, drooping under their own weight."""
    life = window(t, layer.get('start', 0.05), layer.get('end', 0.8))
    count = layer.get('count', 10)
    for _ in range(count):
        angle, speed, length = rng.uniform(0, math.tau), rng.uniform(0.55, 1.0), rng.uniform(5.0, 10.0)
        if life <= 0 or life >= 1:
            continue
        reach = layer.get('reach', 46.0) * speed * ease_out(life)
        drop = layer.get('gravity', 20.0) * life * life
        head = (CENTRE[0] + math.cos(angle) * reach, CENTRE[1] + math.sin(angle) * reach + drop)
        tail_reach = max(0.0, reach - length * (1 - life * 0.6))
        tail = (CENTRE[0] + math.cos(angle) * tail_reach, CENTRE[1] + math.sin(angle) * tail_reach + drop * 0.8)
        alpha = (1 - life) ** 0.9
        ctx.move_to(*tail)
        ctx.line_to(*head)
        draw.line(ctx, pal(layer.get('edge', 'flash_edge')), 2.6, alpha)
        ctx.move_to(*draw.lerp_point(tail, head, 0.35))
        ctx.line_to(*head)
        draw.line(ctx, pal(layer.get('core', 'flash_core')), 1.3, alpha)


def smoke(ctx, pal, rng, layer, t):
    """Engraved smoke: scalloped puffs that swell, drift up and thin away."""
    life = window(t, layer.get('start', 0.12), layer.get('end', 1.0))
    puffs = [(rng.uniform(0, math.tau), rng.uniform(0.3, 1.0), rng.uniform(0.7, 1.15)) for _ in range(layer.get('count', 6))]
    if life <= 0:
        return
    alpha = math.sin(math.pi * min(1.0, life * 0.5 + 0.5)) ** 1.2 if life > 0.5 else min(1.0, life * 4.0)
    alpha *= layer.get('strength', 0.92)
    placed = []
    for angle, distance, scale in puffs:
        spread = layer.get('spread', 20.0) * distance * ease_out(life)
        radius = layer.get('size', 9.0) * scale * (0.45 + 0.75 * ease_out(life))
        placed.append((CENTRE[0] + math.cos(angle) * spread, CENTRE[1] + math.sin(angle) * spread * 0.8 - layer.get('rise', 12.0) * life, radius))
    for x, y, radius in placed:
        draw.ellipse(ctx, x, y, radius + 1.0, radius + 1.0)
    draw.wash(ctx, pal('ink'), 0.55 * alpha)
    for x, y, radius in placed:
        draw.ellipse(ctx, x, y, radius, radius)
    draw.wash(ctx, pal(layer.get('colour', 'powder_smoke')), alpha)
    for x, y, radius in placed:
        ctx.new_sub_path()
        ctx.arc(x + radius * 0.12, y + radius * 0.1, radius * 0.56, 0.3, 2.3)
    draw.line(ctx, pal('ink'), 0.8, 0.34 * alpha)


def debris(ctx, pal, rng, layer, t):
    """Clods and splinters on short ballistic arcs."""
    life = window(t, layer.get('start', 0.05), layer.get('end', 0.9))
    for _ in range(layer.get('count', 8)):
        angle, speed, size = rng.uniform(math.pi * 1.05, math.pi * 1.95), rng.uniform(0.5, 1.0), rng.uniform(1.0, 2.1)
        if life <= 0 or life >= 1:
            continue
        x = CENTRE[0] + math.cos(angle) * layer.get('reach', 30.0) * speed * life
        y = CENTRE[1] + math.sin(angle) * layer.get('reach', 30.0) * speed * life + layer.get('gravity', 46.0) * life * life
        draw.polygon(ctx, [(x - size, y), (x, y - size), (x + size, y + size * 0.3), (x, y + size * 0.8)])
        draw.wash(ctx, pal(layer.get('colour', 'ink')), (1 - life) ** 0.6)


LAYERS = {'burst': burst, 'sparks': sparks, 'smoke': smoke, 'debris': debris}


def paint(spec):
    """params: recipes (JSON path beside batch.json), recipe (key in that file)."""
    recipes = spec.data(spec.params['recipes'])
    name = spec.params['recipe']
    if name not in recipes['effects']:
        raise KeyError(f'{spec.id}: effect {name!r} not in {spec.params["recipes"]}; has {sorted(recipes["effects"])}')
    recipe = recipes['effects'][name]
    for layer in recipe['layers']:
        if layer['type'] not in LAYERS:
            raise KeyError(f'{spec.id}: unknown effect layer {layer["type"]!r}; known: {sorted(LAYERS)}')
    count, pal = recipe['frames'], spec.palette

    def draw_frame(ctx, index):
        t = index / (count - 1) if count > 1 else 0.0
        for number, layer in enumerate(recipe['layers']):
            LAYERS[layer['type']](ctx, pal, random.Random(spec.seed + number), layer, t)   # same seed each frame: stable motion

    frames = sheet.render(spec.frame, draw_frame, count, lambda image, index: paper_grain(image, spec.seed, fine=0.02, mottle=0))
    clips = {'play': {'frames': list(range(count)), 'fps': recipe['fps'], 'loop': False}}
    return sheet.Work(frames=frames, clips=clips, vector=draw_frame)
