"""Frames -> row-major sprite sheet, optional vector export, manifest facts."""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import cairo
from PIL import Image

from .raster import Canvas

MAX_TEXTURE = 2048


@dataclass
class Work:
    """What a painter hands back for one asset."""
    frames: list                       # straight-alpha RGBA images, all frame_size
    clips: dict                        # manifest clip records
    vector: object = None              # optional draw(ctx, frame_index) for the editable SVG
    notes: dict = field(default_factory=dict)


def render(frame_size, draw_frame, count, finish=None):
    """Rasterise `count` frames with draw_frame(ctx, index); `finish` post-processes each image."""
    frames = []
    for index in range(count):
        canvas = Canvas(*frame_size)
        draw_frame(canvas.ctx, index)
        image = canvas.image()
        frames.append(finish(image, index) if finish else image)
    return frames


def columns_for(count, frame_width, requested=None):
    limit = max(1, MAX_TEXTURE // frame_width)
    if requested:
        if requested > limit:
            raise ValueError(f'{requested} columns of {frame_width}px exceed the {MAX_TEXTURE}px texture limit')
        return requested
    return min(count, limit, 8)


def pack(frames, columns=None):
    width, height = frames[0].size
    for index, frame in enumerate(frames):
        if frame.size != (width, height) or frame.mode != 'RGBA':
            raise ValueError(f'Frame {index} is {frame.mode} {frame.size}; expected RGBA {(width, height)}')
    columns = columns_for(len(frames), width, columns)
    rows = (len(frames) + columns - 1) // columns
    if rows * height > MAX_TEXTURE:
        raise ValueError(f'{len(frames)} frames of {width}x{height} do not fit a {MAX_TEXTURE}px sheet')
    sheet = Image.new('RGBA', (columns * width, rows * height), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        sheet.paste(frame, ((index % columns) * width, (index // columns) * height))
    return sheet


def frame_origin(index, columns, frame_size):
    return ((index % columns) * frame_size[0], (index // columns) * frame_size[1])


def save_png(sheet, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, format='PNG', optimize=False, compress_level=9)
    return {'size': list(sheet.size), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def save_svg(path, frame_size, count, draw_frame, columns=None):
    """Vector master of the line and wash layers, laid out like the sheet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = columns_for(count, frame_size[0], columns)
    rows = (count + columns - 1) // columns
    surface = cairo.SVGSurface(str(path), columns * frame_size[0], rows * frame_size[1])
    surface.set_document_unit(cairo.SVGUnit.PX)
    ctx = cairo.Context(surface)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for index in range(count):
        x, y = frame_origin(index, columns, frame_size)
        ctx.save()
        ctx.translate(x, y)
        ctx.rectangle(0, 0, *frame_size)
        ctx.clip()
        draw_frame(ctx, index)
        ctx.restore()
    surface.finish()
    # Cairo writes platform line endings and no trailing newline; normalise for review.
    text = path.read_text(encoding='utf-8').replace('\r\n', '\n')
    path.write_text(text if text.endswith('\n') else text + '\n', encoding='utf-8', newline='\n')
