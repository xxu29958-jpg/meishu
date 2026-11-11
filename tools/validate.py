"""Validate a standalone artwork batch without any game files or platform tools."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from PIL import Image
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
MAX_BATCH_BYTES = 32 * 1024 * 1024
MAX_ASSET_BYTES = 16 * 1024 * 1024


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def local_file(base, relative):
    require(isinstance(relative, str) and re.fullmatch(r'[A-Za-z0-9_./-]+', relative),
            f'Unsafe path: {relative!r}; use a relative path with /')
    parts = Path(relative).parts
    require(not Path(relative).is_absolute() and '..' not in parts, f'Path escapes batch: {relative}')
    path = base / relative
    require(path.resolve().is_relative_to(base.resolve()), f'Path escapes batch: {relative}')
    cursor = path
    while cursor != base:
        require(not cursor.is_symlink(), f'Symbolic link is not a delivery file: {relative}')
        cursor = cursor.parent
    require(path.is_file(), f'Missing file: {relative}')
    return path


def read_json(path):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'{path.name}: duplicate JSON key {key}')
            result[key] = value
        return result
    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_keys,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValidationError(f'Non-finite JSON: {value}')))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValidationError(f'{path}: {error}') from error


def check_schema(value, name):
    schema = read_json(ROOT / 'schemas' / (name + '.schema.json'))
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: str(list(error.path)))
    if errors:
        error = errors[0]
        location = '.'.join(map(str, error.path)) or '$'
        raise ValidationError(f'{name} at {location}: {error.message}')


def validate(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    base = manifest_path.parent
    manifest = read_json(manifest_path)
    check_schema(manifest, 'asset-manifest')
    theme_path = local_file(base, manifest['theme'])
    source_path = local_file(base, manifest['sources'])
    theme = read_json(theme_path)
    sources = read_json(source_path)
    check_schema(theme, 'visual-theme')
    check_schema(sources, 'sources')
    require(theme['id'] == manifest['theme_id'], 'Theme id does not match manifest.theme_id')
    source_ids = [item['id'] for item in sources['sources']]
    require(len(source_ids) == len(set(source_ids)), 'Duplicate source id')
    declared = {manifest_path, theme_path.resolve(), source_path.resolve()}
    for item in sources['sources']:
        for relative in item['editable_files']:
            path = local_file(base, relative)
            require(path.suffix.lower() in ('.svg', '.kra', '.ora', '.psd', '.blend'),
                    f'Unsupported editable format: {relative}')
            if path.suffix.lower() == '.svg':
                content = path.read_text(encoding='utf-8').lower()
                require(not re.search(r'<script|<!entity|<!doctype|(?:href|src)\s*=\s*[\"\'](?:https?:|file:|//)|\bon\w+\s*=', content),
                        f'SVG contains active or external content: {relative}')
            declared.add(path.resolve())
    identifiers = set()
    decoded_bytes = 0
    inventory = []
    for asset in manifest['assets']:
        identifier = asset['id']
        require(identifier not in identifiers, f'Duplicate asset id: {identifier}')
        identifiers.add(identifier)
        require(asset['source_id'] in source_ids, f'{identifier}: unknown source_id')
        path = local_file(base, asset['file'])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest == asset['sha256'], f'{identifier}: SHA-256 mismatch; run seal after authoring')
        width, height = asset['size']
        frame_width, frame_height = asset['frame_size']
        require(width % frame_width == 0 and height % frame_height == 0,
                f'{identifier}: sheet dimensions are not a complete frame grid')
        require(width * height * 4 <= MAX_ASSET_BYTES, f'{identifier}: decoded texture exceeds 16 MiB')
        with Image.open(path) as image:
            require(image.format == 'PNG' and image.mode == 'RGBA', f'{identifier}: expected 8-bit RGBA PNG')
            require(image.size == (width, height), f'{identifier}: actual PNG size does not match manifest')
            image.load()
            require(image.getchannel('A').getbbox() is not None, f'{identifier}: completely invisible image')
            pixels = image.tobytes()
            require(all(pixels[i+3] != 0 or pixels[i:i+3] == b'\x00\x00\x00' for i in range(0, len(pixels), 4)),
                    f'{identifier}: fully transparent pixels must have zero RGB')
        display_width, display_height = asset['display_size']
        require(abs(display_width / display_height - frame_width / frame_height) < .0001,
                f'{identifier}: display_size distorts frame aspect ratio')
        frame_count = (width // frame_width) * (height // frame_height)
        for name, clip in asset['clips'].items():
            require(max(clip['frames']) < frame_count, f'{identifier}/{name}: frame index outside sheet')
        required_clips = {'ui': {'normal', 'pressed', 'selected', 'disabled'},
                          'units': {'idle', 'move', 'attack', 'recover', 'finish'},
                          'effects': {'play'}, 'buildings': {'still', 'damaged'}}
        required = required_clips.get(asset['category'], {'still'})
        require(required <= set(asset['clips']), f'{identifier}: missing clips {sorted(required - set(asset["clips"]))}')
        require(asset['blend'] == 'normal' or asset['category'] == 'effects', f'{identifier}: additive blending is effects-only')
        if asset['category'] == 'effects':
            require(not asset['clips']['play']['loop'], f'{identifier}: play must terminate')
        if asset['category'] == 'ui':
            require('stretch' in asset, f'{identifier}: UI requires stretch insets')
        if 'stretch' in asset:
            left, top, right, bottom = asset['stretch']
            require(left + right < frame_width and top + bottom < frame_height,
                    f'{identifier}: stretch borders leave no center')
        if path.resolve() not in declared:
            decoded_bytes += width * height * 4
        declared.add(path.resolve())
        inventory.append({'id': identifier, 'file': asset['file'], 'sha256': digest})
    require(decoded_bytes <= MAX_BATCH_BYTES, 'Batch decoded textures exceed 32 MiB')
    global_visual = theme.get('global_visual')
    if global_visual:
        entity_ids = set()
        assets_by_id = {asset['id']: asset for asset in manifest['assets']}
        for entity in global_visual['entities']:
            require(entity['id'] not in entity_ids, 'Duplicate global visual entity')
            entity_ids.add(entity['id'])
            links = [(entity['flag_asset'], 'identity')]
            for key, category in [('specialty_units', 'units'), ('historical_portraits', 'portraits'), ('building_assets', 'buildings')]:
                links.extend((identifier, category) for identifier in entity[key])
            for identifier, category in links:
                require(identifier in identifiers, f'Global visual references missing asset: {identifier}')
                require(assets_by_id[identifier]['category'] == category, f'Global visual category mismatch: {identifier}')
    if 'preview' in manifest:
        preview_path = local_file(base, manifest['preview'])
        preview = read_json(preview_path)
        check_schema(preview, 'preview-scene')
        declared.add(preview_path.resolve())
        assets_by_id = {asset['id']: asset for asset in manifest['assets']}
        occupied = set()
        for tile in preview['tiles']:
            coordinate = (tile['row'], tile['column'])
            require(coordinate not in occupied, f'Duplicate preview tile coordinate: {coordinate}')
            occupied.add(coordinate)
        for item in preview['tiles'] + preview['items']:
            identifier = item['asset']
            require(identifier in identifiers, f'Preview references missing asset: {identifier}')
            require(item['clip'] in assets_by_id[identifier]['clips'],
                    f'Preview references missing clip: {identifier}/{item["clip"]}')
    for path in base.rglob('*'):
        require(not path.is_symlink(), f'Symbolic link in batch: {path.relative_to(base)}')
        if not path.is_file() or path.resolve() in declared:
            continue
        require(path.suffix.lower() == '.md', f'Undeclared file in batch: {path.relative_to(base)}')
    return {'status': 'passed', 'contract_version': 1, 'theme_id': manifest['theme_id'],
            'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'asset_count': len(inventory), 'decoded_bytes': decoded_bytes, 'assets': inventory,
            'source_review': 'Structured provenance checked; final art authorship still requires content review.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', nargs='?', type=Path, default=ROOT / 'samples/manifest.json')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.manifest)
    except (ValidationError, OSError, ValueError) as error:
        parser.exit(1, f'FAIL: {error}\n')
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'PASS: {report["asset_count"]} assets; {report["decoded_bytes"]:,} decoded bytes; {report["theme_id"]}')


if __name__ == '__main__':
    main()
