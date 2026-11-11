"""Raster fields for painted maps: noise anchored to map coordinates, distance, blur.

Noise takes coordinates, not pixel indices, so a feature sits at the same place
on the ground at every level of detail and in every window.
"""
import math

import numpy as np
from PIL import Image

_ANGLES = np.arange(256, dtype=np.float32) * (math.tau / 256)
_GRADIENTS = np.stack([np.cos(_ANGLES), np.sin(_ANGLES)], axis=1)


def smoothstep(low, high, value):
    t = np.clip((value - low) / (high - low), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _hash(ix, iy, seed):
    with np.errstate(over='ignore'):
        h = (ix.astype(np.uint32) * np.uint32(374761393) + iy.astype(np.uint32) * np.uint32(668265263)
             + np.uint32(seed & 0xffffffff) * np.uint32(2246822519))
        h = (h ^ (h >> np.uint32(13))) * np.uint32(1274126177)
        return h ^ (h >> np.uint32(16))


def noise(x, y, seed=0):
    """Gradient noise in about -1..1 with one feature per unit of x and y."""
    x, y = np.asarray(x, dtype=np.float32), np.asarray(y, dtype=np.float32)
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = x - x0, y - y0
    ix, iy = x0.astype(np.int64), y0.astype(np.int64)
    total = None
    u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    for dx, dy, weight in ((0, 0, (1 - u) * (1 - v)), (1, 0, u * (1 - v)), (0, 1, (1 - u) * v), (1, 1, u * v)):
        gradient = _GRADIENTS[_hash(ix + dx, iy + dy, seed) & np.uint32(255)]
        corner = (gradient[..., 0] * (fx - dx) + gradient[..., 1] * (fy - dy)) * weight
        total = corner if total is None else total + corner
    return total * 1.41421


def fbm(x, y, seed=0, octaves=4, gain=0.5, lacunarity=2.0):
    """Fractal sum of noise, about -1..1."""
    total, amplitude, norm = 0.0, 1.0, 0.0
    for octave in range(octaves):
        total = total + noise(x, y, seed + octave * 1013) * amplitude
        norm += amplitude
        amplitude *= gain
        x, y = x * lacunarity, y * lacunarity
    return total / norm


def ridged(x, y, seed=0, octaves=4, gain=0.5, lacunarity=2.0, sharpness=1.0):
    """Ridged fractal in 0..1: creases of the noise become crests, each octave weighted by the last."""
    total, amplitude, norm, weight = 0.0, 1.0, 0.0, 1.0
    for octave in range(octaves):
        crest = 1.0 - np.abs(noise(x, y, seed + octave * 1013))
        crest = crest ** (1.0 + sharpness)
        total = total + crest * amplitude * weight
        norm += amplitude
        weight = np.clip(crest * 1.6, 0.0, 1.0)
        amplitude *= gain
        x, y = x * lacunarity, y * lacunarity
    return total / norm


def distance(seeds, limit):
    """Distance in cells from every cell to the nearest True cell, capped at `limit`.

    Jump flooding: each pass lets a cell adopt the nearest seed known to a
    neighbour `step` cells away, halving the step. Exact within about a cell,
    which is all a painted edge needs.
    """
    seeds = np.asarray(seeds, dtype=bool)
    height, width = seeds.shape
    rows, columns = np.mgrid[0:height, 0:width].astype(np.float32)
    far = np.float32(-4.0 * (height + width + limit))
    seed_row = np.where(seeds, rows, far)
    seed_column = np.where(seeds, columns, far)
    best = (rows - seed_row) ** 2 + (columns - seed_column) ** 2
    step = 1 << max(0, math.ceil(math.log2(max(2.0, limit))))
    steps = []
    while step >= 1:
        steps.append(step)
        step //= 2
    steps.append(1)
    for step in steps:
        for dy in (-step, 0, step):
            for dx in (-step, 0, step):
                if dy == 0 and dx == 0:
                    continue
                target = (slice(max(0, dy), height + min(0, dy)), slice(max(0, dx), width + min(0, dx)))
                origin = (slice(max(0, -dy), height + min(0, -dy)), slice(max(0, -dx), width + min(0, -dx)))
                if target[0].start >= target[0].stop or target[1].start >= target[1].stop:
                    continue
                candidate_row, candidate_column = seed_row[origin], seed_column[origin]
                candidate = (rows[target] - candidate_row) ** 2 + (columns[target] - candidate_column) ** 2
                better = candidate < best[target]
                best[target] = np.where(better, candidate, best[target])
                seed_row[target] = np.where(better, candidate_row, seed_row[target])
                seed_column[target] = np.where(better, candidate_column, seed_column[target])
    return np.minimum(np.sqrt(best), np.float32(limit))


def box_blur(array, radius):
    """Mean over a (2r+1) square, edges held; `array` is 2-D or has trailing channels."""
    radius = int(radius)
    if radius < 1:
        return array
    for axis in (0, 1):
        pad = [(0, 0)] * array.ndim
        pad[axis] = (radius + 1, radius)
        total = np.cumsum(np.pad(array, pad, mode='edge'), axis=axis, dtype=np.float64)
        size = array.shape[axis]
        upper = np.take(total, np.arange(2 * radius + 1, 2 * radius + 1 + size), axis=axis)
        lower = np.take(total, np.arange(0, size), axis=axis)
        array = ((upper - lower) / (2 * radius + 1)).astype(np.float32)
    return array


def blur(array, sigma):
    """Near-Gaussian blur as three box passes."""
    if sigma <= 0.3:
        return array
    radius = max(1, int(round(math.sqrt(12.0 * sigma * sigma / 3 + 1) / 2 - 0.5)))
    for _ in range(3):
        array = box_blur(array, radius)
    return array


def resize(array, width, height, cubic=True):
    """Resample a float field (2-D or with channels) to width x height."""
    method = Image.BICUBIC if cubic else Image.BILINEAR
    if array.ndim == 2:
        return np.asarray(Image.fromarray(array.astype(np.float32), 'F').resize((width, height), method))
    return np.stack([resize(array[..., channel], width, height, cubic) for channel in range(array.shape[2])], axis=2)


def sample(array, px, py):
    """Nearest-cell lookup of a field at pixel positions, clamped to the field."""
    rows = np.clip(np.asarray(py).astype(np.int64), 0, array.shape[0] - 1)
    columns = np.clip(np.asarray(px).astype(np.int64), 0, array.shape[1] - 1)
    return array[rows, columns]
