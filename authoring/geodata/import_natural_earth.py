"""Derive the compact geography layers the map painters read from Natural Earth GeoJSON.

    python -I authoring/geodata/import_natural_earth.py DOWNLOAD_DIR

DOWNLOAD_DIR holds the files named in natural-earth-50m/SOURCE.json, fetched
from the pinned commit. Each is checked against its recorded SHA-256 before it
is read, so a rebuild from a fresh download gives the same layers. Raw
downloads never enter the repository; only the derived layers do.

What changes on the way in: coordinates are rounded to 0.001 degree (about
100 m, far finer than 1:50m data), attributes are cut to name, class and rank,
and region polygons that only repeat the land outline (continents, islands,
peninsulas, coasts) are left out. No geometry is moved or invented here;
anything historical (dropping modern reservoirs, for instance) is a decision
of the map recipe that uses the layers, not of this import.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / 'natural-earth-50m'
SCALE = 1000
GROUND_CLASSES = {'Range/mtn', 'Plateau', 'Desert', 'Plain', 'Delta', 'Basin', 'Valley', 'Lowland', 'Tundra',
                  'Foothills', 'Wetlands', 'Gorge'}


def quantise(points, closed):
    out = []
    for lon, lat, *_ in points:
        point = (round(lon * SCALE), round(lat * SCALE))
        if not out or out[-1] != point:
            out.append(point)
    if closed and len(out) > 1 and out[0] == out[-1]:
        out.pop()
    if len(out) < (3 if closed else 2):
        return None
    return [value for point in out for value in point]


def polygons(geometry):
    if geometry is None:
        return []
    if geometry['type'] == 'Polygon':
        return [geometry['coordinates']]
    if geometry['type'] == 'MultiPolygon':
        return geometry['coordinates']
    raise ValueError(f'Unexpected geometry {geometry["type"]}')


def lines(geometry):
    if geometry is None:
        return []
    if geometry['type'] == 'LineString':
        return [geometry['coordinates']]
    if geometry['type'] == 'MultiLineString':
        return geometry['coordinates']
    raise ValueError(f'Unexpected geometry {geometry["type"]}')


def rings_of(polygon):
    """Exterior first, then holes; rings that collapse under rounding are dropped."""
    rings = [quantise(ring, True) for ring in polygon]
    if rings[0] is None:
        return None
    return [ring for ring in rings if ring is not None]


def prop(properties, name):
    return properties.get(name, properties.get(name.upper()))


def read(directory, pins, stem):
    path = directory / f'{stem}.geojson'
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != pins[path.name]['sha256']:
        raise SystemExit(f'{path.name}: SHA-256 {digest} does not match SOURCE.json; wrong release?')
    return json.loads(content)['features']


def write(name, features):
    body = ',\n'.join(json.dumps(feature, ensure_ascii=False, separators=(',', ':')) for feature in features)
    text = f'{{"layer":"{name}","scale":{SCALE},"features":[\n{body}\n]}}\n'
    (TARGET / f'{name}.json').write_text(text, encoding='utf-8', newline='\n')
    print(f'{name:<8} {len(features):>5} features  {len(text) / 1024:8.0f} KiB')


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    directory = Path(sys.argv[1]).resolve()
    pins = json.loads((TARGET / 'SOURCE.json').read_text(encoding='utf-8'))['files']

    land = []
    for feature in read(directory, pins, 'ne_50m_land'):
        for polygon in polygons(feature['geometry']):
            rings = rings_of(polygon)
            if rings:
                land.append({'rings': rings})
    write('land', land)

    lakes = []
    for feature in read(directory, pins, 'ne_50m_lakes'):
        properties = feature['properties']
        for polygon in polygons(feature['geometry']):
            rings = rings_of(polygon)
            if rings:
                lakes.append({'name': prop(properties, 'name'), 'rank': prop(properties, 'scalerank'), 'rings': rings})
    write('lakes', lakes)

    rivers = []
    for feature in read(directory, pins, 'ne_50m_rivers_lake_centerlines'):
        properties = feature['properties']
        kind = 'lake-centerline' if prop(properties, 'featurecla') == 'Lake Centerline' else 'river'
        for line in lines(feature['geometry']):
            points = quantise(line, False)
            if points:
                rivers.append({'name': prop(properties, 'name'), 'rank': prop(properties, 'scalerank'), 'kind': kind,
                               'line': points})
    write('rivers', rivers)

    regions = []
    for feature in read(directory, pins, 'ne_50m_geography_regions_polys'):
        properties = feature['properties']
        if prop(properties, 'featurecla') not in GROUND_CLASSES:
            continue
        for polygon in polygons(feature['geometry']):
            rings = rings_of(polygon)
            if rings:
                regions.append({'name': prop(properties, 'name'), 'class': prop(properties, 'featurecla'),
                                'rank': prop(properties, 'scalerank'), 'rings': rings})
    write('regions', regions)

    points = []
    for feature in read(directory, pins, 'ne_50m_geography_regions_elevation_points'):
        properties = feature['properties']
        lon, lat = feature['geometry']['coordinates'][:2]
        points.append({'name': prop(properties, 'name'), 'class': prop(properties, 'featurecla'),
                       'elevation': prop(properties, 'elevation'), 'lon': round(lon, 3), 'lat': round(lat, 3)})
    write('points', points)


if __name__ == '__main__':
    main()
