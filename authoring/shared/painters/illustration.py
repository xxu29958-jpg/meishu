"""Character illustrations: one original per character, every crop drawn from it.

A character lives in its own directory beside batch.json:

    <character>/illustration.py   draw(ctx, pal, character) on the 512x640 bust canvas
    <character>/character.json    identity, costume notes, crop boxes

`illustration` paints the bust. `crop` re-renders the same drawing through a
crop box from character.json, so an avatar is the identical artwork at native
resolution, never a resample. Adding a commander adds a directory and two
asset entries; nothing in this module names a person.
"""
import importlib.util
import json

from ..kit import sheet
from ..kit.raster import paper_grain

STILL = {'still': {'frames': [0], 'fps': 1, 'loop': False}}
BUST = (512, 640)


def load_character(spec):
    directory = spec.batch_dir / spec.params['character']
    record_path, module_path = directory / 'character.json', directory / 'illustration.py'
    if not record_path.is_file() or not module_path.is_file():
        raise FileNotFoundError(f'{spec.id}: {directory} needs character.json and illustration.py')
    record = json.loads(record_path.read_text(encoding='utf-8'))
    module_spec = importlib.util.spec_from_file_location(f'illustration_{directory.name}', module_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    if not hasattr(module, 'draw'):
        raise AttributeError(f'{module_path} must define draw(ctx, pal, character)')
    return record, module


def paint(spec):
    """params: character (directory beside batch.json)."""
    if tuple(spec.frame) != BUST:
        raise ValueError(f'{spec.id}: bust illustrations are authored at {BUST}, not {tuple(spec.frame)}')
    record, module = load_character(spec)

    def draw_frame(ctx, _index):
        module.draw(ctx, spec.palette, record)

    frames = sheet.render(spec.frame, draw_frame, 1, lambda image, _i: paper_grain(image, spec.seed, fine=0.03, mottle=0.02, mottle_cell=48))
    return sheet.Work(frames=frames, clips=dict(STILL), vector=draw_frame)


def crop_transform(box, frame):
    """Scale and offset that map a crop box on the bust canvas onto a frame."""
    x, y, width, height = box
    if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > BUST[0] or y + height > BUST[1]:
        raise ValueError(f'Crop box {box} must lie inside the {BUST} bust canvas')
    if abs(width / height - frame[0] / frame[1]) > 1e-3:
        raise ValueError(f'Crop box {box} does not match the frame aspect {frame[0]}:{frame[1]}')
    return frame[0] / width, (-x, -y)


def paint_crop(spec):
    """params: character, crop (key in character.json 'crops')."""
    record, module = load_character(spec)
    name = spec.params['crop']
    if name not in record.get('crops', {}):
        raise KeyError(f'{spec.id}: crop {name!r} not in character.json; has {sorted(record.get("crops", {}))}')
    scale, offset = crop_transform(record['crops'][name], spec.frame)

    def draw_frame(ctx, _index):
        ctx.scale(scale, scale)
        ctx.translate(*offset)
        module.draw(ctx, spec.palette, record)

    frames = sheet.render(spec.frame, draw_frame, 1, lambda image, _i: paper_grain(image, spec.seed, fine=0.03, mottle=0))
    return sheet.Work(frames=frames, clips=dict(STILL), vector=draw_frame)
