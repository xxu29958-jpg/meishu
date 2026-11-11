"""Place manifest assets the way the runtime contract says, for headless review.

Mirrors ASSET-SPEC: frame = floor(elapsed_ms * fps / 1000); the screen rectangle's
top-left is world point - anchor * display_size * scale; mirror-x flips about the
anchor so the ground contact point does not move.
"""
import json
from pathlib import Path

from PIL import Image


class Batch:
    """A manifest with lazily opened sheets."""

    def __init__(self, manifest_path):
        self.path = Path(manifest_path).resolve()
        self.manifest = json.loads(self.path.read_text(encoding='utf-8'))
        self.assets = {asset['id']: asset for asset in self.manifest['assets']}
        self._sheets = {}

    def asset(self, identifier):
        if identifier not in self.assets:
            raise KeyError(f'{self.path.parent.name}: no asset {identifier!r}')
        return self.assets[identifier]

    def sheet(self, identifier):
        if identifier not in self._sheets:
            self._sheets[identifier] = Image.open(self.path.parent / self.asset(identifier)['file']).convert('RGBA')
        return self._sheets[identifier]

    def frame(self, identifier, index):
        asset = self.asset(identifier)
        return self.sheet(identifier).crop(frame_box(asset, index))


def frame_at(clip, elapsed_ms):
    """Sheet frame index shown by a clip after elapsed_ms of unpaused time."""
    step = int(elapsed_ms * clip['fps'] // 1000)
    frames = clip['frames']
    return frames[step % len(frames)] if clip['loop'] else frames[min(step, len(frames) - 1)]


def frame_box(asset, index):
    """Pixel box of a frame in the row-major sheet."""
    frame_width, frame_height = asset['frame_size']
    columns = asset['size'][0] // frame_width
    count = columns * (asset['size'][1] // frame_height)
    if not 0 <= index < count:
        raise IndexError(f'{asset["id"]}: frame {index} outside sheet of {count}')
    x, y = (index % columns) * frame_width, (index // columns) * frame_height
    return (x, y, x + frame_width, y + frame_height)


def screen_rect(asset, position, scale=1.0, mirror=False):
    """(left, top, width, height) of the drawn frame; mirroring keeps the anchor point fixed."""
    width, height = asset['display_size'][0] * scale, asset['display_size'][1] * scale
    anchor_x = asset['anchor'][0]
    if mirror and asset['directions'] == 'mirror-x':
        anchor_x = 1.0 - anchor_x
    return (position[0] - anchor_x * width, position[1] - asset['anchor'][1] * height, width, height)


def resize_rgba(image, size):
    """Resize in premultiplied space so transparent edges do not fringe."""
    if image.size == tuple(size):
        return image
    return image.convert('RGBa').resize(size, Image.LANCZOS).convert('RGBA')


def place(canvas, batch, identifier, clip_name, position, scale=1.0, mirror=False, elapsed_ms=0, pixels_per_unit=2.0):
    """Composite one asset onto an RGBA canvas. `position` is in logical units."""
    asset = batch.asset(identifier)
    if clip_name not in asset['clips']:
        raise KeyError(f'{identifier}: no clip {clip_name!r}; has {sorted(asset["clips"])}')
    frame = batch.frame(identifier, frame_at(asset['clips'][clip_name], elapsed_ms))
    flipped = mirror and asset['directions'] == 'mirror-x'
    if flipped:
        frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
    left, top, width, height = screen_rect(asset, position, scale, mirror)
    target = (max(1, round(width * pixels_per_unit)), max(1, round(height * pixels_per_unit)))
    frame = resize_rgba(frame, target)
    layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    layer.paste(frame, (round(left * pixels_per_unit), round(top * pixels_per_unit)))
    canvas.alpha_composite(layer)


def hex_center(scene, row, column):
    step_x, step_y = scene['hex']['step']
    return (scene['origin'][0] + column * step_x + (row % 2) * scene['hex']['odd_row_offset'],
            scene['origin'][1] + row * step_y)


def render_scene(batch, scene, pixels_per_unit=2.0, background=(226, 232, 234, 255), elapsed_ms=0):
    """Draw a preview-scene: tiles in row order, then items in listed order."""
    size = (round(scene['canvas_size'][0] * pixels_per_unit), round(scene['canvas_size'][1] * pixels_per_unit))
    canvas = Image.new('RGBA', size, background)
    for tile in sorted(scene['tiles'], key=lambda tile: (tile['row'], tile['column'])):
        place(canvas, batch, tile['asset'], tile['clip'], hex_center(scene, tile['row'], tile['column']),
              pixels_per_unit=pixels_per_unit, elapsed_ms=elapsed_ms)
    for item in scene['items']:
        position = (scene['origin'][0] + item['position'][0], scene['origin'][1] + item['position'][1])
        place(canvas, batch, item['asset'], item['clip'], position, item['scale'],
              pixels_per_unit=pixels_per_unit, elapsed_ms=elapsed_ms)
    return canvas
