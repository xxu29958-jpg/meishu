"""Create original interface fixtures from geometric primitives, with no external inputs.

These are technical test images, not a proposed art direction or finished historical art.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def make_batch(output):
    output.mkdir(parents=True, exist_ok=True)
    assets = []

    def add(identifier, category, frames, display, anchor, clips, mirror=False, stretch=None, source='project.geometry'):
        width, height = frames[0].size
        columns = min(4, len(frames))
        rows = (len(frames) + columns - 1) // columns
        sheet = Image.new('RGBA', (columns * width, rows * height))
        for index, frame in enumerate(frames):
            sheet.paste(frame, ((index % columns) * width, (index // columns) * height))
        relative = category + '/' + identifier + '.png'
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(path, optimize=False)
        entry = {
            'id': identifier, 'category': category, 'file': relative,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'size': list(sheet.size), 'frame_size': [width, height],
            'display_size': list(display), 'anchor': list(anchor),
            'directions': 'mirror-x' if mirror else 'fixed', 'blend': 'normal',
            'clips': clips, 'source_id': source
        }
        if stretch is not None:
            entry['stretch'] = stretch
        assets.append(entry)

    def single(name='still'):
        return {name: {'frames': [0], 'fps': 1, 'loop': False}}

    for identifier, size in [('ui.panel.command', (480, 280)), ('ui.button.primary', (240, 72))]:
        frames = []
        for index, color in enumerate(['#355766', '#203943', '#56794d', '#666666']):
            frame = Image.new('RGBA', size)
            draw = ImageDraw.Draw(frame)
            draw.rounded_rectangle((2, 2, size[0]-3, size[1]-3), radius=16, fill=color, outline='#d9e4df', width=3)
            draw.line((20, 16 + index * 2, size[0]-20, 16 + index * 2), fill='#b7cccf', width=2)
            if index == 2:
                draw.rectangle((8, 22, 13, size[1]-22), fill='#f4e8ad')
            if index == 3:
                draw.line((10, size[1]-10, 28, size[1]-28), fill='#aaaaaa', width=3)
            frames.append(frame)
        clips = {name: {'frames': [index], 'fps': 1, 'loop': False}
                 for index, name in enumerate(['normal', 'pressed', 'selected', 'disabled'])}
        add(identifier, 'ui', frames, size, (0, 0), clips, stretch=[20, 20, 20, 20])

    for terrain, color in [('plain', '#8ba779'), ('forest', '#6c966d'), ('mountain', '#a3a8a3'),
                           ('water', '#629fb8'), ('coast', '#9bbfa8'), ('river', '#8ba779'),
                           ('snow', '#e4e9e6'), ('desert', '#d1bd8c'), ('wetland', '#82a6a1'), ('road', '#aab58a')]:
        frame = Image.new('RGBA', (128, 144))
        draw = ImageDraw.Draw(frame)
        points = [(64, 1), (127, 36), (127, 108), (64, 143), (0, 108), (0, 36)]
        draw.polygon(points, fill=color, outline='#435b54', width=2)
        if terrain == 'forest':
            for x, y in [(32, 75), (64, 56), (91, 90)]:
                draw.rectangle((x-2, y, x+2, y+15), fill='#5e5445')
                draw.polygon([(x, y-32), (x-17, y+3), (x+17, y+3)], fill='#3c7458')
        elif terrain == 'mountain':
            draw.polygon([(25, 105), (65, 31), (105, 105)], fill='#737d80')
            draw.polygon([(65, 31), (48, 62), (79, 62)], fill='#f0f0e5')
        elif terrain in ('river', 'coast', 'water', 'wetland'):
            draw.line([(20, 65), (52, 75), (76, 64), (109, 76)], fill='#c3e5eb', width=6)
        elif terrain == 'road':
            draw.line([(7, 98), (60, 74), (120, 44)], fill='#ded7bc', width=8)
        else:
            for x, y in [(29, 72), (80, 50), (73, 105)]:
                draw.line((x, y, x+9, y-3), fill='#617b62', width=2)
        add('maps.terrain.' + terrain, 'maps', [frame], (64, 72), (.5, .5), single())

    for kind, identifier in [('infantry', 'units.infantry.line'), ('cavalry', 'units.cavalry.light'),
                             ('grenadier', 'units.france.grenadier')]:
        frames = []
        for action in range(5):
            for step in range(4):
                frame = Image.new('RGBA', (128, 128))
                draw = ImageDraw.Draw(frame)
                bob = (0, -2, 0, 2)[step]
                shift = (0, 3, 7, 1)[step] if action == 2 else 0
                draw.ellipse((30, 108, 100, 116), fill=(0, 0, 0, 45))
                if kind == 'cavalry':
                    draw.ellipse((25, 72, 94, 99), fill='#916448')
                    draw.polygon([(80, 82), (85, 50+bob), (106, 55+bob), (100, 84)], fill='#916448')
                    for x in [36, 74]:
                        draw.line((x, 90, x + (step % 2)*7, 112), fill='#573e30', width=5)
                    body_y = 47 + bob
                else:
                    body_y = 58 + bob
                    for x in [55, 71]:
                        draw.line((x, 85+bob, x + (step % 2)*6 - 3, 112), fill='#ddd7ba', width=8)
                draw.rectangle((49+shift, body_y, 79+shift, body_y+28), fill='#45648b')
                draw.line((50+shift, body_y+2, 77+shift, body_y+26), fill='#eee5cb', width=4)
                draw.ellipse((53+shift, body_y-23, 76+shift, body_y), fill='#d7ae80')
                hat_height = 16 if kind == 'grenadier' else 9
                draw.rectangle((51+shift, body_y-23-hat_height, 79+shift, body_y-19), fill='#2c3542')
                draw.line((78+shift, body_y+12, 102+shift, body_y-10-step*2), fill='#b9c9cb', width=4)
                frames.append(frame)
        clips = {}
        for action, name in enumerate(['idle', 'move', 'attack', 'recover', 'finish']):
            clips[name] = {'frames': list(range(action*4, action*4+4)),
                           'fps': 8 if name == 'idle' else 12, 'loop': name in ('idle', 'move')}
        add(identifier, 'units', frames, (64, 64), (.5, .875), clips, mirror=True)

    portrait = Image.new('RGBA', (512, 640))
    draw = ImageDraw.Draw(portrait)
    draw.polygon([(44, 630), (75, 410), (208, 345), (304, 345), (440, 410), (468, 630)], fill='#425d79')
    draw.ellipse((164, 151, 348, 383), fill='#dbb28a')
    draw.polygon([(72, 202), (166, 115), (346, 115), (440, 202)], fill='#263440')
    draw.line((89, 199, 423, 199), fill='#d9be83', width=8)
    draw.polygon([(192, 378), (256, 510), (320, 378)], fill='#e8e4d5')
    draw.ellipse((204, 236, 214, 246), fill='#4b4440')
    draw.ellipse((294, 236, 304, 246), fill='#4b4440')
    draw.line((228, 318, 280, 318), fill='#986c56', width=4)
    add('portraits.napoleon.bust', 'portraits', [portrait], (256, 320), (.5, 1), single())
    avatar = portrait.crop((96, 100, 416, 420)).resize((192, 192), Image.Resampling.LANCZOS)
    # Fully transparent pixels have zero RGB in every runtime file.
    pixels = bytearray(avatar.tobytes())
    for offset in range(0, len(pixels), 4):
        if pixels[offset + 3] == 0:
            pixels[offset:offset + 3] = b'\x00\x00\x00'
    avatar = Image.frombytes('RGBA', avatar.size, bytes(pixels))
    add('portraits.napoleon.avatar', 'portraits', [avatar], (96, 96), (.5, .5), single())

    buildings = ['city', 'capital', 'farm', 'barracks', 'factory', 'port', 'fort', 'regional']
    for number, kind in enumerate(buildings):
        frames = []
        for damaged in (False, True):
            frame = Image.new('RGBA', (128, 144))
            draw = ImageDraw.Draw(frame)
            draw.ellipse((13, 111, 115, 137), fill=(55, 55, 45, 60))
            draw.rectangle((24, 68, 104, 125), fill='#bca77e' if not damaged else '#968c7b')
            draw.polygon([(18, 70), (64, 38-number*2), (110, 70)], fill='#735e55')
            for x in [36, 57, 80]:
                draw.rectangle((x, 82, x+11, 98), fill='#435560')
            draw.rectangle((57, 104, 73, 126), fill='#655442')
            if kind in ('capital', 'fort'):
                draw.rectangle((50, 22, 78, 58), fill='#cbb991')
                draw.rectangle((48, 20, 80, 28), fill='#81715a')
            if kind == 'factory':
                draw.rectangle((86, 27, 99, 70), fill='#8b6655')
            if kind == 'port':
                draw.line((15, 131, 114, 131), fill='#75b6ca', width=5)
            if kind == 'farm':
                for y in [110, 118, 126]:
                    draw.line((8, y, 31, y), fill='#899a58', width=3)
            if damaged:
                draw.line([(84, 71), (76, 88), (85, 100), (75, 119)], fill='#443c38', width=3)
            frames.append(frame)
        add('buildings.' + kind + '.l1', 'buildings', frames, (64, 72), (.5, .875),
            {'still': {'frames': [0], 'fps': 1, 'loop': False}, 'damaged': {'frames': [1], 'fps': 1, 'loop': False}})

    frames = []
    for index in range(8):
        frame = Image.new('RGBA', (128, 128))
        draw = ImageDraw.Draw(frame)
        radius = 5 + index * 6
        alpha = 255 - index * 30
        draw.ellipse((64-radius, 64-radius, 64+radius, 64+radius), outline=(244, 190, 83, alpha), width=5)
        draw.line((64-radius, 64, 64+radius, 64), fill=(255, 239, 192, alpha), width=3)
        draw.line((64, 64-radius, 64, 64+radius), fill=(255, 239, 192, alpha), width=3)
        frames.append(frame)
    add('effects.hit.spark', 'effects', frames, (64, 64), (.5, .5),
        {'play': {'frames': list(range(8)), 'fps': 12, 'loop': False}})

    flag = Image.new('RGBA', (96, 64))
    draw = ImageDraw.Draw(flag)
    for index, color in enumerate(['#244b86', '#f4f4ed', '#b74c49']):
        draw.rectangle((index*32, 0, (index+1)*32-1, 63), fill=color)
    add('identity.france.flag', 'identity', [flag], (48, 32), (.5, .5), single(), source='project.tricolour')

    write_json(output / 'manifest.json', {'contract_version': 1, 'theme_id': 'sample.geometry.v1',
        'theme': 'theme.json', 'sources': 'sources.json', 'assets': assets})
    write_json(output / 'theme.json', {'contract_version': 1, 'id': 'sample.geometry.v1',
        'title': '原创几何接口样例（非美术方向）', 'era': '拿破仑时代',
        'art_direction': '技术占位；成品风格由 Claude 自主创作', 'light_direction': '测试图无统一光照资格',
        'partial': True, 'map_regions': ['europe', 'americas', 'global'],
        'global_visual': {'id': 'global-visual.v1', 'start_year': 1805, 'projection': 'equirectangular',
            'entities': [{'id': 'historical.france', 'label': 'France · 1805 · visual sample',
                'flag_asset': 'identity.france.flag', 'map_color': '#5577aa',
                'specialty_units': ['units.france.grenadier'],
                'historical_portraits': ['portraits.napoleon.bust'],
                'building_assets': ['buildings.regional.l1'], 'faction_visual': '独立标签与轮廓，最终由美术定义'}],
            'relation_styles': {'self': '实线', 'ally': '双线', 'neutral': '点线', 'opponent': '斜线', 'unknown': '问号'},
            'territory_style': '透明覆盖；不烘焙政治边界'}})
    sources = []
    for identifier, description, references in [
        ('project.geometry', '本仓库 generate_samples.py 从空白 RGBA 画布和几何原语原创绘制。人像/制服仅为接口占位，非考证成品。', []),
        ('project.tricolour', '程序独立绘制三条色带；参考仅用于旗帜史实，不复制网页图像。', ['https://www.elysee.fr/en/french-presidency/the-french-flag'])]:
        sources.append({'id': identifier, 'author': '项目自研 / Codex', 'method': 'procedural-original',
            'license': '项目自有测试内容，供本项目制作、修改与集成使用',
            'description': description, 'references': references, 'editable_files': []})
    write_json(output / 'sources.json', {'contract_version': 1, 'sources': sources})
    return len(assets)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'samples')
    args = parser.parse_args()
    print(f'Generated {make_batch(args.output)} original test assets in {args.output}')
