"""Neutral pointy-top hex geometry from ASSET-SPEC, in frame pixels.

A terrain frame is 128x144 and shows at 64x72. Neighbouring centres are 128 px
apart along a row and (64, 108) px apart between rows, so artwork that repeats
on those translations joins without seams.
"""
from . import draw

FRAME = (128, 144)
CENTER = (64.0, 72.0)
# Offsets to the six neighbours, by compass name.
NEIGHBOURS = {'e': (128, 0), 'se': (64, 108), 'sw': (-64, 108),
              'w': (-128, 0), 'nw': (-64, -108), 'ne': (64, -108)}


def corners(inset=0.0, center=CENTER):
    """Hex corners clockwise from the top; a negative inset bleeds outward."""
    cx, cy = center
    half_width, half_height = 64.0 - inset, 72.0 - inset * 1.125
    quarter = half_height / 2
    return [(cx, cy - half_height), (cx + half_width, cy - quarter), (cx + half_width, cy + quarter),
            (cx, cy + half_height), (cx - half_width, cy + quarter), (cx - half_width, cy - quarter)]


def edge(direction, center=CENTER):
    """The two corners bounding the edge that faces a neighbour."""
    points = corners(center=center)
    index = {'ne': 0, 'e': 1, 'se': 2, 'sw': 3, 'w': 4, 'nw': 5}[direction]
    return points[index], points[(index + 1) % 6]


def path(ctx, inset=0.0, center=CENTER):
    draw.polygon(ctx, corners(inset, center))


def repeat(ctx, paint):
    """Call paint() at the home cell and its six neighbours so features wrap."""
    for dx, dy in [(0, 0), *NEIGHBOURS.values()]:
        ctx.save()
        ctx.translate(dx, dy)
        paint()
        ctx.restore()


def scatter(rng, count, margin=0.0):
    """Random points inside the home hex, sorted back-to-front for overlap."""
    points = []
    while len(points) < count:
        x, y = rng.uniform(0, 128), rng.uniform(0, 144)
        if inside((x, y), margin):
            points.append((x, y))
    return sorted(points, key=lambda point: point[1])


def inside(point, margin=0.0):
    dx, dy = abs(point[0] - CENTER[0]), abs(point[1] - CENTER[1])
    half_width, half_height = 64.0 - margin, 72.0 - margin
    return dx <= half_width and dy <= half_height - dx * (half_height / 2) / half_width
