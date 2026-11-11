"""Text map layouts -> preview scenes, following the layered map recipe.

A layout is display data: rows of single-character terrain codes and a legend.
It carries no rules. The scene it produces draws, bottom to top: the sea under
every cell; then for all land cells the coast under-layers, one full pass per
layer; then the land pieces row by row; then placed items. Because each pass
covers the whole map before the next begins, shorelines form from unions and
no hex edge shows. design/art/maps.md gives the same recipe for integration.
"""


def hex_position(layout, row, column):
    """Logical position of a hex centre relative to the scene origin."""
    step_x, step_y = layout['hex']['step']
    return [column * step_x + (row % 2) * layout['hex']['odd_row_offset'], row * step_y]


def cells(layout):
    for row, line in enumerate(layout['rows']):
        for column, code in enumerate(line):
            if code == ' ':
                continue
            if code not in layout['legend']:
                raise KeyError(f'Layout row {row} column {column}: code {code!r} is not in the legend')
            yield row, column, code


def scene_from_layout(layout):
    legend, sea_codes = layout['legend'], set(layout.get('sea', []))
    tiles, land, features = [], [], []
    for row, column, code in cells(layout):
        is_sea = code in sea_codes
        tiles.append({'row': row, 'column': column, 'asset': legend[code] if is_sea else layout['sea_under_land'], 'clip': 'still'})
        if not is_sea:
            land.append((row, column, legend[code]))
    items = []
    for layer in layout.get('coast_layers', []):                       # one complete pass per under-layer
        items.extend({'asset': layer, 'clip': 'still', 'position': hex_position(layout, row, column), 'scale': 1}
                     for row, column, _ in land)
    items.extend({'asset': asset, 'clip': 'still', 'position': hex_position(layout, row, column), 'scale': 1}
                 for row, column, asset in sorted(land))
    for item in layout.get('items', []):
        position = hex_position(layout, item['row'], item['column'])
        offset = item.get('offset', [0, 0])
        features.append({'asset': item['asset'], 'clip': item['clip'],
                         'position': [position[0] + offset[0], position[1] + offset[1]], 'scale': item.get('scale', 1)})
    features.sort(key=lambda item: item['position'][1])               # painter's order: far rows first
    return {'contract_version': 1, 'canvas_size': layout['canvas_size'], 'origin': layout['origin'],
            'hex': layout['hex'], 'tiles': tiles, 'items': items + features}


def scene_from_region(region, level):
    """Preview scene that lays out one level of a regional map from its chunks.

    Chunks are anchored at their centre: chunk (row, column) sits at
    ((column + 0.5) * chunk, (row + 0.5) * chunk) in the level's pixels, and its
    skirt overlaps its neighbours. The scene's origin is the centre of hex
    (0, 0) of the region's hex grid, so a viewer's cell picking matches the
    grid the region record proposes.
    """
    entries = {entry['level']: entry for entry in region['levels']}
    if level not in entries:
        raise KeyError(f'Region {region["id"]!r} has no level {level}; known: {sorted(entries)}')
    entry = entries[level]
    chunk = entry['chunk']
    grid = region.get('hex_grid', {'origin': [0, 0], 'step': [64, 54], 'odd_row_offset': 32})
    origin = grid['origin']
    items = [{'asset': entry['id_pattern'].format(row=row, column=column), 'clip': 'still',
              'position': [(column + 0.5) * chunk - origin[0], (row + 0.5) * chunk - origin[1]], 'scale': 1}
             for row in range(entry['rows']) for column in range(entry['columns'])]
    return {'contract_version': 1, 'canvas_size': list(entry['size']), 'origin': list(origin),
            'hex': {'step': list(grid['step']), 'odd_row_offset': grid['odd_row_offset']}, 'tiles': [], 'items': items}
