"""Keyframe sampling: clip data -> one pose per exported frame.

Timing lives in the pose-set JSON. A clip is either `keys` (named poses at
normalised times, eased between) or a procedural cycle handled by its painter.
Poses are flat or nested dicts of numbers; nested lists interpolate per item.
"""
import math

EASINGS = {
    'linear': lambda t: t,
    'in': lambda t: t * t,
    'out': lambda t: 1 - (1 - t) * (1 - t),
    'inout': lambda t: 0.5 - math.cos(math.pi * t) / 2,
    'snap': lambda t: 1 - (1 - t) ** 3,
    'hold': lambda t: 0.0,
}


def blend(a, b, t):
    """Interpolate two pose values of the same shape."""
    if isinstance(a, dict):
        return {key: blend(a[key], b.get(key, a[key]), t) for key in a}
    if isinstance(a, (list, tuple)):
        return [blend(x, y, t) for x, y in zip(a, b)]
    if isinstance(a, bool) or isinstance(a, str) or a is None:
        return a if t < 0.5 else b
    return a + (b - a) * t


def resolve(pose, poses, base=None):
    """Expand a pose reference: a name, or {'pose': name, ...overrides}."""
    if isinstance(pose, str):
        if pose not in poses:
            raise KeyError(f'Unknown pose {pose!r}; known poses: {sorted(poses)}')
        return resolve(poses[pose], poses, base)
    result = dict(base or {})
    if 'pose' in pose:
        result.update(resolve(pose['pose'], poses, base))
    for key, value in pose.items():
        if key != 'pose':
            result[key] = merge(result.get(key), value)
    return result


def merge(current, override):
    if isinstance(current, dict) and isinstance(override, dict):
        merged = dict(current)
        for key, value in override.items():
            merged[key] = merge(current.get(key), value)
        return merged
    return override


def sample_keys(clip, poses, base=None, mix=blend):
    """Return clip['frames'] poses sampled evenly across the keyed timeline.

    A looping clip samples t = i/n so its last frame leads back into the first;
    a one-shot samples t = i/(n-1) so it lands exactly on its final key.
    """
    keys = clip['keys']
    if not keys:
        raise ValueError('Keyed clip has no keys')
    times = [key['t'] for key in keys]
    if times != sorted(times):
        raise ValueError(f'Key times must ascend: {times}')
    resolved = [resolve(key['pose'], poses, base) for key in keys]
    count = clip['frames']
    frames = []
    for index in range(count):
        t = index / count if clip.get('loop') else (index / (count - 1) if count > 1 else 0.0)
        t = times[0] + t * (times[-1] - times[0])
        segment = max(i for i, start in enumerate(times) if start <= t + 1e-9)
        if segment >= len(keys) - 1:
            frames.append(resolved[-1])
            continue
        span = times[segment + 1] - times[segment]
        local = (t - times[segment]) / span if span else 0.0
        ease = EASINGS[keys[segment + 1].get('ease', 'inout')]
        frames.append(mix(resolved[segment], resolved[segment + 1], ease(local)))
    return frames


def clip_table(clips):
    """Pack consecutive clips into one sheet: name -> manifest clip record."""
    table, cursor = {}, 0
    for name, clip in clips.items():
        count = clip['frames']
        table[name] = {'frames': list(range(cursor, cursor + count)), 'fps': clip['fps'], 'loop': clip['loop']}
        cursor += count
    return table, cursor
