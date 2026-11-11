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


# ---------------------------------------------------------------- grids in logical units
# A grid record: {"columns", "rows", "origin": [x, y], "step": [64, 54], "odd_row_offset": 32, "hex_size": [64, 72]}.
# Cell (row, column) has its centre at origin + (step_x * column + odd_row_offset * (row % 2), step_y * row).

def cell_centre(grid, row, column):
    return (grid['origin'][0] + grid['step'][0] * column + grid['odd_row_offset'] * (row % 2),
            grid['origin'][1] + grid['step'][1] * row)


def cell_corners(grid, row, column):
    cx, cy = cell_centre(grid, row, column)
    half_width, half_height = grid['hex_size'][0] / 2, grid['hex_size'][1] / 2
    return [(cx, cy - half_height), (cx + half_width, cy - half_height / 2), (cx + half_width, cy + half_height / 2),
            (cx, cy + half_height), (cx - half_width, cy + half_height / 2), (cx - half_width, cy - half_height / 2)]


def neighbours(grid, row, column):
    """The up to six cells that share an edge with (row, column)."""
    shift = row % 2
    around = [(row, column - 1), (row, column + 1), (row - 1, column - 1 + shift), (row - 1, column + shift),
              (row + 1, column - 1 + shift), (row + 1, column + shift)]
    return [(r, c) for r, c in around if 0 <= r < grid['rows'] and 0 <= c < grid['columns']]


def cell_map(grid, width, height, scale=1.0):
    """Which cell each pixel belongs to: an int32 array of row * columns + column, or -1 outside the grid.

    `scale` is pixels per logical unit. Cells are filled without antialiasing, so
    every pixel belongs to exactly one cell.
    """
    import cairo
    import numpy as np
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
    ctx = cairo.Context(surface)
    ctx.scale(scale, scale)
    ctx.set_antialias(cairo.ANTIALIAS_NONE)
    ctx.set_operator(cairo.OPERATOR_SOURCE)
    for row in range(grid['rows']):
        for column in range(grid['columns']):
            identifier = row * grid['columns'] + column + 1
            ctx.set_source_rgb(((identifier >> 16) & 255) / 255.0, ((identifier >> 8) & 255) / 255.0, (identifier & 255) / 255.0)
            draw.polygon(ctx, cell_corners(grid, row, column))
            ctx.fill()
    surface.flush()
    data = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape(height, surface.get_stride() // 4, 4)[:, :width]
    return (data[..., 2].astype(np.int32) << 16 | data[..., 1].astype(np.int32) << 8 | data[..., 0].astype(np.int32)) - 1


def cell_at(grid, x, y):
    """The cell containing a logical point, or None: the nearest centre among the rows the point can lie in."""
    best, found = None, None
    guess = round((y - grid['origin'][1]) / grid['step'][1])
    for row in (guess - 1, guess, guess + 1):
        if not 0 <= row < grid['rows']:
            continue
        column = round((x - grid['origin'][0] - grid['odd_row_offset'] * (row % 2)) / grid['step'][0])
        if not 0 <= column < grid['columns']:
            continue
        cx, cy = cell_centre(grid, row, column)
        dx, dy = abs(x - cx), abs(y - cy)
        half_width, half_height = grid['hex_size'][0] / 2, grid['hex_size'][1] / 2
        if dx <= half_width and dy <= half_height - dx * (half_height / 2) / half_width:
            distance = dx * dx + dy * dy
            if best is None or distance < best:
                best, found = distance, (row, column)
    return found
