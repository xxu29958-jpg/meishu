"""Headless review images from a built batch, for the create/export/inspect loop.

    python authoring/review.py sheet  <manifest> <asset-id> <out.png> [--zoom 2]
    python authoring/review.py scene  <manifest> <scene.json> <out.png> [--ppu 2] [--ms 0]
    python authoring/review.py strip  <manifest> <asset-id> <clip> <out.png> [--zoom 2] [--mirror]

Outputs are review evidence, not deliverables; write them outside the repository.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared.kit import compose  # noqa: E402

PAPER = (233, 224, 204, 255)
FELT = (58, 84, 70, 255)


def checker(size, cell=16, light=(238, 234, 224, 255), dark=(214, 208, 196, 255)):
    image = Image.new('RGBA', size, light)
    pen = ImageDraw.Draw(image)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                pen.rectangle((x, y, x + cell - 1, y + cell - 1), fill=dark)
    return image


def backdrop(name, size):
    return checker(size) if name == 'checker' else Image.new('RGBA', size, {'paper': PAPER, 'felt': FELT}[name])


def mark_anchor(image, asset, origin, zoom):
    x = origin[0] + asset['anchor'][0] * asset['frame_size'][0] * zoom
    y = origin[1] + asset['anchor'][1] * asset['frame_size'][1] * zoom
    pen = ImageDraw.Draw(image)
    pen.line((x - 6, y, x + 6, y), fill=(212, 40, 89, 255), width=1)
    pen.line((x, y - 6, x, y + 6), fill=(212, 40, 89, 255), width=1)


def frames_image(batch, identifier, indices, zoom, background, mirror=False, anchors=True, columns=None):
    asset = batch.asset(identifier)
    width, height = (round(value * zoom) for value in asset['frame_size'])
    columns = columns or min(len(indices), max(1, 1800 // width))
    rows = (len(indices) + columns - 1) // columns
    image = backdrop(background, (columns * width, rows * height))
    for slot, index in enumerate(indices):
        frame = batch.frame(identifier, index)
        if mirror and asset['directions'] == 'mirror-x':
            frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
        frame = compose.resize_rgba(frame, (width, height))
        origin = ((slot % columns) * width, (slot // columns) * height)
        image.alpha_composite(frame, origin)
        if anchors:
            mark_anchor(image, asset, origin, zoom)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('sheet', 'strip', 'scene'):
        sub = commands.add_parser(name)
        sub.add_argument('manifest', type=Path)
        if name == 'scene':
            sub.add_argument('scene', type=Path)
            sub.add_argument('--ppu', type=float, default=2.0, help='output pixels per logical unit')
            sub.add_argument('--ms', type=float, default=0, help='animation time')
        else:
            sub.add_argument('asset')
            if name == 'strip':
                sub.add_argument('clip')
                sub.add_argument('--mirror', action='store_true')
            sub.add_argument('--zoom', type=float, default=2.0)
            sub.add_argument('--bg', choices=('checker', 'paper', 'felt'), default='checker')
            sub.add_argument('--no-anchors', action='store_true')
        sub.add_argument('out', type=Path)
    args = parser.parse_args()
    batch = compose.Batch(args.manifest)
    if args.command == 'scene':
        scene = json.loads(args.scene.read_text(encoding='utf-8'))
        image = compose.render_scene(batch, scene, args.ppu, elapsed_ms=args.ms)
    else:
        asset = batch.asset(args.asset)
        if args.command == 'strip':
            indices = asset['clips'][args.clip]['frames']
        else:
            indices = list(range((asset['size'][0] // asset['frame_size'][0]) * (asset['size'][1] // asset['frame_size'][1])))
        image = frames_image(batch, args.asset, indices, args.zoom, args.bg,
                             mirror=getattr(args, 'mirror', False), anchors=not args.no_anchors)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(f'{args.out}  {image.size[0]}x{image.size[1]}')


if __name__ == '__main__':
    main()
