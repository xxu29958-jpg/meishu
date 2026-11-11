"""Derive a regional map's per-hex terrain table from the fields that painted it.

    python authoring/hexes.py authoring/atlas-europe-01/hexes.json design/maps/europe-hexes.json

The rules file names the recipe, the classes (ordered tests on measured shares)
and any small islands to keep as land. The grid comes from the region record's
`hex_grid`. Each hex is measured over its own pixels with the painter's fields
(land, lakes, relief, woods, ground cover), so the table agrees with the
picture. The output is design data for integration and for content records; it
carries physical terrain only, no rules and no politics.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared.kit import geo, hexgrid  # noqa: E402
from shared.kit.palette import Palette  # noqa: E402
from shared.painters import atlas  # noqa: E402


class HexError(ValueError):
    pass


def matches(when, measures, index, cover):
    for key, bounds in when.items():
        if key == 'cover':
            if cover not in bounds:
                return False
        elif not bounds[0] <= measures[key][index] < bounds[1]:
            return False
    return True


def classify(classes, measures, index, cover, land_only=False):
    for rule in classes:
        if land_only and rule.get('water', False):
            continue
        if matches(rule.get('when', {}), measures, index, cover):
            return rule['terrain']
    raise HexError('No class matched; end the class list with a rule that has no conditions')


def river_cells(frame, grid, cells, recipe, rules):
    """Named rivers as the cells they run through, in the order the data draws them."""
    omit = set(recipe.get('hydrography', {}).get('omit_rivers', []))
    alias, limit = rules.get('river_names', {}), rules.get('river_rank', 99)
    found = {}
    for feature in geo.layer(recipe['geodata'], 'rivers'):
        name = feature['name']
        if name is None or name in omit or feature['rank'] > limit:
            continue
        path = frame.path(feature['line'])
        if not frame.sees(path):
            continue
        entry = found.setdefault(alias.get(name, name), {'rank': feature['rank'], 'cells': []})
        entry['rank'] = min(entry['rank'], feature['rank'])
        for start, end in zip(path[:-1], path[1:]):
            steps = max(1, int(np.hypot(*(end - start)) / 3))
            for t in np.linspace(0.0, 1.0, steps + 1):
                x, y = start + (end - start) * t
                if 0 <= x < frame.width and 0 <= y < frame.height:
                    cell = int(cells[int(y), int(x)])
                    if cell >= 0:
                        position = [cell // grid['columns'], cell % grid['columns']]
                        if position not in entry['cells']:
                            entry['cells'].append(position)
    return [{'name': name, 'rank': entry['rank'], 'cells': entry['cells']}
            for name, entry in sorted(found.items(), key=lambda item: (item[1]['rank'], item[0])) if entry['cells']]


def derive(rules_path):
    rules_path = Path(rules_path).resolve()
    rules = json.loads(rules_path.read_text(encoding='utf-8'))
    recipe = json.loads((rules_path.parent / rules['recipe']).read_text(encoding='utf-8'))
    region = json.loads((rules_path.parent / recipe['region']).resolve().read_text(encoding='utf-8'))
    palette = Palette.load(rules_path.parent / rules['palette'])
    if 'hex_grid' not in region:
        raise HexError(f'Region {region["id"]!r} has no hex_grid; the scale must be decided first')
    grid, level = region['hex_grid'], rules.get('level', 0)
    frame = geo.frame_for(region, level)
    scale = region['levels'][0]['units_per_pixel'] / frame.units_per_pixel          # pixels per logical unit
    cells = hexgrid.cell_map(grid, frame.width, frame.height, scale)
    count = grid['rows'] * grid['columns']
    measures, survey = atlas.measure(frame, recipe, palette, cells, count)
    full = grid['hex_size'][0] * grid['step'][1] * scale * scale
    if measures['pixels'].min() < full * 0.98:
        raise HexError('Some hexes fall partly outside the painted map; check hex_grid against the level size')

    codes = rules['codes']
    terrain = [[None] * grid['columns'] for _ in range(grid['rows'])]
    for row in range(grid['rows']):
        for column in range(grid['columns']):
            x, y = hexgrid.cell_centre(grid, row, column)
            cover = survey.ground_at(frame.west + x * scale * frame.units_per_pixel, frame.north - y * scale * frame.units_per_pixel)
            terrain[row][column] = classify(rules['classes'], measures, row * grid['columns'] + column, cover)

    water = {rule['terrain'] for rule in rules['classes'] if rule.get('water', False)}

    def cell_of(place):
        px, py = frame.to_pixels(place['lon'], place['lat'])
        cell = hexgrid.cell_at(grid, float(px) / scale, float(py) / scale)
        if cell is None:
            raise HexError(f'{place["name"]!r} lies outside the grid')
        return cell

    kept = []
    for place in rules.get('keep_land', []):                       # land that matters but fills less of its hex than the rule asks
        row, column = cell_of(place)
        index = row * grid['columns'] + column
        entry = {'name': place['name'], 'row': row, 'column': column, 'land_share': round(float(measures['ground'][index]), 2),
                 'forced': terrain[row][column] in water, 'why': place['why']}
        if entry['forced']:
            cover = survey.ground_at(*(float(v) for v in frame.projection.forward(place['lon'], place['lat'])))
            terrain[row][column] = classify(rules['classes'], measures, index, cover, land_only=True)
        entry['terrain'] = terrain[row][column]
        kept.append(entry)

    basin = {}                                                     # sea cells joined edge to edge form a basin
    for row in range(grid['rows']):
        for column in range(grid['columns']):
            if terrain[row][column] != 'sea' or (row, column) in basin:
                continue
            identifier, queue = (max(basin.values()) + 1 if basin else 0), [(row, column)]
            basin[(row, column)] = identifier
            while queue:
                here = queue.pop()
                for there in hexgrid.neighbours(grid, *here):
                    if terrain[there[0]][there[1]] == 'sea' and there not in basin:
                        basin[there] = identifier
                        queue.append(there)
    edges = {'north': lambda r, c: r == 0, 'south': lambda r, c: r == grid['rows'] - 1,
             'west': lambda r, c: c == 0, 'east': lambda r, c: c == grid['columns'] - 1}
    ocean = {value for (r, c), value in basin.items() if any(edges[name](r, c) for name in rules.get('open_edges', []))}
    if ocean:                                                      # water that runs off an open edge is one ocean beyond the map
        basin = {cell: min(ocean) if value in ocean else value for cell, value in basin.items()}
    renumber = {old: new for new, old in enumerate(sorted(set(basin.values())))}
    basin = {cell: renumber[value] for cell, value in basin.items()}
    basins = [{'id': identifier, 'cells': sum(1 for value in basin.values() if value == identifier), 'waters': []}
              for identifier in sorted(set(basin.values()))]
    unplaced = []
    for place in rules.get('waters', []):
        cell = cell_of(place)
        (basins[basin[cell]]['waters'] if cell in basin else unplaced).append(place['name'])
    passages = []
    for place in rules.get('passages', []):
        row, column = cell_of(place)
        around = [(row, column)] + hexgrid.neighbours(grid, row, column)
        passages.append({'name': place['name'], 'row': row, 'column': column, 'terrain': terrain[row][column],
                         'open_sea': (row, column) in basin, 'basins_touched': sorted({basin[cell] for cell in around if cell in basin})})

    coastal = 0
    for row in range(grid['rows']):
        for column in range(grid['columns']):
            if terrain[row][column] not in water and any(terrain[r][c] == 'sea' for r, c in hexgrid.neighbours(grid, row, column)):
                coastal += 1
    counts = {}
    for line in terrain:
        for name in line:
            counts[name] = counts.get(name, 0) + 1
    checks = []
    for point in region.get('check_points', []):
        px, py = frame.to_pixels(point['lon'], point['lat'])
        cell = hexgrid.cell_at(grid, float(px) / scale, float(py) / scale)
        if cell is not None:
            checks.append({'name': point['name'], 'row': cell[0], 'column': cell[1], 'terrain': terrain[cell[0]][cell[1]]})
    return {
        'record': 'region-hexes', 'version': 1,
        'status': 'derived proposal for integration: physical terrain per hex at the scale the Owner chose; classes and thresholds are open to change',
        'region': region['id'], 'level': level,
        'derived_by': f'python authoring/hexes.py {rules_path.relative_to(Path(__file__).resolve().parents[1]).as_posix()}',
        'grid': grid,
        'legend': {codes[name]: name for name in codes},
        'terrain': [''.join(codes[name] for name in line) for line in terrain],
        'counts': dict(sorted(counts.items(), key=lambda item: -item[1])),
        'land_cells': sum(value for name, value in counts.items() if name not in water),
        'coastal_land_cells': coastal,
        'kept_as_land': kept,
        'sea_basins': basins,
        'waters_without_a_sea_cell': unplaced,
        'passages': passages,
        'rivers': river_cells(frame, grid, cells, recipe, rules),
        'check_points': checks,
    }


def write(table, path):
    """One row of the grid per line, lists of cell pairs on one line: readable in review."""
    text = json.dumps(table, ensure_ascii=False, indent=2)
    import re
    text = re.sub(r'\[\s+(-?\d+),\s+(-?\d+)\s+\]', r'[\1, \2]', text)
    text = re.sub(r'\[\s+(\[[^\[\]\n]*\](?:,\s+\[[^\[\]\n]*\])*)\s+\]', lambda m: '[' + re.sub(r'\s*\n\s*', ' ', m.group(1)) + ']', text)
    Path(path).write_text(text + '\n', encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('rules', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    try:
        table = derive(args.rules)
    except (HexError, atlas.RecipeError, OSError, KeyError) as error:
        parser.exit(1, f'HEXES FAILED: {error}\n')
    write(table, args.out)
    print(f'{args.out}: {table["grid"]["columns"]} x {table["grid"]["rows"]} cells, {table["land_cells"]} land; {table["counts"]}')


if __name__ == '__main__':
    main()
