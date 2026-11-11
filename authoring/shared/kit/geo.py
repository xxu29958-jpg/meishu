"""Geography for painted maps: projections, pixel frames and the derived data layers.

A projection turns longitude and latitude (degrees) into map units, x to the
east and y to the north. A Frame lays a pixel grid over map units. Painters
work in pixels; everything they place comes through a Frame, so one recipe
renders at any level of detail and any window.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

GEODATA = Path(__file__).resolve().parents[2] / 'geodata'
EARTH_RADIUS_KM = 6371.0088


class LambertAzimuthalEqualArea:
    """Equal-area on a sphere: every square kilometre of ground gets the same area of map. Units: km."""

    def __init__(self, centre_lon, centre_lat, radius=EARTH_RADIUS_KM):
        self.lon0, self.lat0, self.radius = math.radians(centre_lon), math.radians(centre_lat), radius

    def forward(self, lon, lat):
        lam = np.radians(np.asarray(lon, dtype=np.float64)) - self.lon0
        phi = np.radians(np.asarray(lat, dtype=np.float64))
        cos_c = math.sin(self.lat0) * np.sin(phi) + math.cos(self.lat0) * np.cos(phi) * np.cos(lam)
        k = self.radius * np.sqrt(2.0 / np.maximum(1.0 + cos_c, 1e-9))
        x = k * np.cos(phi) * np.sin(lam)
        y = k * (math.cos(self.lat0) * np.sin(phi) - math.sin(self.lat0) * np.cos(phi) * np.cos(lam))
        return x, y

    def inverse(self, x, y):
        x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
        rho = np.hypot(x, y)
        c = 2.0 * np.arcsin(np.clip(rho / (2.0 * self.radius), 0.0, 1.0))
        safe = np.where(rho > 1e-12, rho, 1.0)
        phi = np.arcsin(np.clip(np.cos(c) * math.sin(self.lat0) + y * np.sin(c) * math.cos(self.lat0) / safe, -1.0, 1.0))
        lam = self.lon0 + np.arctan2(x * np.sin(c), safe * math.cos(self.lat0) * np.cos(c) - y * math.sin(self.lat0) * np.sin(c))
        phi = np.where(rho > 1e-12, phi, self.lat0)
        lam = np.where(rho > 1e-12, lam, self.lon0)
        return np.degrees(lam), np.degrees(phi)


class Equirectangular:
    """Plate carrée, the world-map convention of ASSET-SPEC. Units: degrees."""

    def forward(self, lon, lat):
        return np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64)

    def inverse(self, x, y):
        return np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)


def projection_from(record):
    kind = record['type']
    if kind == 'lambert-azimuthal-equal-area':
        return LambertAzimuthalEqualArea(record['centre']['lon'], record['centre']['lat'],
                                         record.get('sphere_radius_km', EARTH_RADIUS_KM))
    if kind == 'equirectangular':
        return Equirectangular()
    raise ValueError(f'Unknown projection {kind!r}; known: lambert-azimuthal-equal-area, equirectangular')


class Frame:
    """A pixel grid over map units. Pixel (0, 0) has its top-left corner at (west, north)."""

    def __init__(self, projection, west, north, units_per_pixel, width, height):
        self.projection, self.west, self.north = projection, float(west), float(north)
        self.units_per_pixel, self.width, self.height = float(units_per_pixel), int(width), int(height)

    def to_pixels(self, lon, lat):
        x, y = self.projection.forward(lon, lat)
        return (x - self.west) / self.units_per_pixel, (self.north - y) / self.units_per_pixel

    def to_lonlat(self, px, py):
        return self.projection.inverse(self.west + np.asarray(px) * self.units_per_pixel,
                                       self.north - np.asarray(py) * self.units_per_pixel)

    def window(self, left, top, width, height):
        """The same map seen through another pixel rectangle (may reach outside this one)."""
        return Frame(self.projection, self.west + left * self.units_per_pixel, self.north - top * self.units_per_pixel,
                     self.units_per_pixel, width, height)

    def grid(self, step=1):
        """Map-unit coordinates of pixel centres, every `step` pixels: (x, y) float32 arrays."""
        columns = (np.arange(0, self.width, step, dtype=np.float32) + step / 2) * self.units_per_pixel + self.west
        rows = self.north - (np.arange(0, self.height, step, dtype=np.float32) + step / 2) * self.units_per_pixel
        return np.meshgrid(columns, rows)

    def path(self, points):
        """Project an (n, 2) array of lon, lat to an (n, 2) array of pixels."""
        px, py = self.to_pixels(points[:, 0], points[:, 1])
        return np.stack([px, py], axis=1)

    def sees(self, pixels, margin=0.0):
        """Whether a projected path's bounding box touches the frame."""
        low, high = pixels.min(axis=0), pixels.max(axis=0)
        return bool(high[0] >= -margin and low[0] <= self.width + margin
                    and high[1] >= -margin and low[1] <= self.height + margin)


def frame_for(region, level, margin=0):
    """Frame for one detail level of a region record (design/maps/*.json), widened by `margin` pixels."""
    levels = {entry['level']: entry for entry in region['levels']}
    if level not in levels:
        raise KeyError(f'Region {region["id"]!r} has no level {level}; known: {sorted(levels)}')
    entry, window = levels[level], region['window']
    scale = entry['units_per_pixel']
    width, height = entry['size']
    expected = ((window['east'] - window['west']) / scale, (window['north'] - window['south']) / scale)
    if abs(expected[0] - width) > 1e-6 or abs(expected[1] - height) > 1e-6:
        raise ValueError(f'Region {region["id"]!r} level {level}: size {entry["size"]} does not match the window '
                         f'at {scale} units per pixel ({expected[0]:g} x {expected[1]:g})')
    frame = Frame(projection_from(region['projection']), window['west'], window['north'], scale, width, height)
    return frame.window(-margin, -margin, width + 2 * margin, height + 2 * margin)


@lru_cache(maxsize=None)
def layer(dataset, name):
    """Features of one derived layer. Rings and lines become (n, 2) float arrays of lon, lat."""
    path = GEODATA / dataset / f'{name}.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except OSError as error:
        raise FileNotFoundError(f'Geography layer {dataset}/{name} is missing: {error}') from error
    scale = data['scale']

    def points(flat):
        return np.asarray(flat, dtype=np.float64).reshape(-1, 2) / scale

    features = []
    for feature in data['features']:
        feature = dict(feature)
        if 'rings' in feature:
            feature['rings'] = [points(ring) for ring in feature['rings']]
        if 'line' in feature:
            feature['line'] = points(feature['line'])
        features.append(feature)
    return features


def chaikin(points, rounds, closed):
    """Corner-cutting: each round replaces every corner by two points a quarter along its sides."""
    for _ in range(rounds):
        following = np.roll(points, -1, axis=0) if closed else points[1:]
        current = points if closed else points[:-1]
        cut = np.empty((len(current) * 2, 2), dtype=points.dtype)
        cut[0::2] = current * 0.75 + following * 0.25
        cut[1::2] = current * 0.25 + following * 0.75
        points = cut if closed else np.concatenate([points[:1], cut, points[-1:]])
    return points
