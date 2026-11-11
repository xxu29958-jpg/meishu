"""Painter registry. batch.json names a painter; the build looks it up here.

A painter is `paint(spec) -> Work`. Adding a kind of artwork means adding a
module and one line below; adding another asset of an existing kind is data.
"""
import importlib

PAINTERS = {
    'terrain': 'shared.painters.terrain',
    'coast': 'shared.painters.terrain:paint_coast',
    'grid': 'shared.painters.terrain:paint_grid',
    'building': 'shared.painters.buildings',
    'infantry': 'shared.painters.infantry',
    'cavalry': 'shared.painters.cavalry',
    'effect': 'shared.painters.effects',
    'flag': 'shared.painters.flags',
    'ui': 'shared.painters.ui',
    'illustration': 'shared.painters.illustration',
    'crop': 'shared.painters.illustration:paint_crop',
    'atlas': 'shared.painters.atlas',
}


def find_painter(name):
    if name not in PAINTERS:
        raise KeyError(f'Unknown painter {name!r}; known painters: {sorted(PAINTERS)}')
    module_name, _, function = PAINTERS[name].partition(':')
    return getattr(importlib.import_module(module_name), function or 'paint')
