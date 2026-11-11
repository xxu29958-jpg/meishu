"""Build a batch's runtime PNGs, editable SVGs and manifest from its authoring inputs.

    python authoring/build.py authoring/campaign-atlas-01
    python authoring/build.py authoring/campaign-atlas-01 --only units. --only maps.terrain.forest

The batch directory supplies batch.json (asset list), a palette and painter data.
Painters are looked up by name; nothing here knows a particular asset. theme.json,
sources.json and preview.json in the output directory are hand-written records
and are never generated. Afterwards run tools/seal.py and tools/validate.py.
"""
import argparse
import json
import sys
import time
import zlib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.kit import sheet  # noqa: E402
from shared.kit.palette import Palette  # noqa: E402
from shared.painters import find_painter  # noqa: E402

FORMAT_KEYS = ('frame', 'display', 'anchor', 'directions', 'blend')


class BuildError(ValueError):
    pass


@dataclass
class Spec:
    """Everything a painter may read for one asset."""
    id: str
    category: str
    params: dict
    palette: Palette
    frame: tuple
    seed: int
    batch_dir: Path

    def data(self, relative):
        """Load a JSON input that lives beside batch.json."""
        path = self.batch_dir / relative
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            raise BuildError(f'{self.id}: cannot read {path}: {error}') from error


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise BuildError(f'Cannot read {path}: {error}') from error


def resolve_format(asset, formats):
    """Merge the named canvas format with per-asset overrides."""
    name = asset.get('format')
    if name is not None and name not in formats:
        raise BuildError(f'{asset["id"]}: unknown format {name!r}; known: {sorted(formats)}')
    merged = dict(formats.get(name, {}))
    merged.update({key: asset[key] for key in FORMAT_KEYS if key in asset})
    missing = [key for key in ('frame', 'display', 'anchor') if key not in merged]
    if missing:
        raise BuildError(f'{asset["id"]}: missing {missing}; set a format or give them on the asset')
    merged.setdefault('directions', 'fixed')
    merged.setdefault('blend', 'normal')
    return merged


def build_asset(asset, batch, formats, palette, batch_dir, output):
    """Paint one batch entry and return its manifest entries.

    Most painters return one Work. A painter may return {suffix: Work} instead,
    for artwork delivered in pieces (the chunks of a regional map); each piece
    becomes its own asset, `<id>.<suffix>`, sharing the entry's format and source.
    """
    identifier = asset['id']
    fmt = resolve_format(asset, formats)
    spec = Spec(id=identifier, category=asset['category'], params=asset.get('params', {}), palette=palette,
                frame=tuple(fmt['frame']), seed=zlib.crc32(identifier.encode()) ^ batch.get('seed', 0),
                batch_dir=batch_dir)
    result = find_painter(asset['painter'])(spec)
    if isinstance(result, dict) != bool(asset.get('parts', False)):
        raise BuildError(f'{identifier}: painter {asset["painter"]!r} returns {"parts" if isinstance(result, dict) else "one work"}; '
                         f'set "parts": {str(isinstance(result, dict)).lower()} on the batch entry')
    works = {f'{identifier}.{suffix}': work for suffix, work in result.items()} if isinstance(result, dict) else {identifier: result}
    return [build_work(name, work, asset, fmt, spec, output) for name, work in works.items()]


def build_work(identifier, work, asset, fmt, spec, output):
    if not work.frames:
        raise BuildError(f'{identifier}: painter {asset["painter"]!r} returned no frames')
    for index, frame in enumerate(work.frames):
        if frame.size != spec.frame:
            raise BuildError(f'{identifier}: frame {index} is {frame.size}, format says {spec.frame}')
    used = {index for clip in work.clips.values() for index in clip['frames']}
    if used and max(used) >= len(work.frames):
        raise BuildError(f'{identifier}: clips reference frame {max(used)} but only {len(work.frames)} were painted')
    columns = asset.get('columns')
    relative = f'{asset["category"]}/{identifier}.png'
    facts = sheet.save_png(sheet.pack(work.frames, columns), output / relative)
    if work.vector is not None and asset.get('editable', True):
        sheet.save_svg(output / 'sources' / f'{identifier}.svg', spec.frame, len(work.frames), work.vector, columns)
    entry = {'id': identifier, 'category': asset['category'], 'file': relative,
             'frame_size': list(fmt['frame']), 'display_size': list(fmt['display']), 'anchor': list(fmt['anchor']),
             'directions': fmt['directions'], 'blend': fmt['blend'], 'clips': work.clips,
             'source_id': asset['source_id']}
    if 'stretch' in asset:
        entry['stretch'] = list(asset['stretch'])
    entry.update(facts)
    return entry


def entry_ids(asset, entries):
    """Manifest entries that belong to a batch entry (its own id, or `<id>.<suffix>` for parts)."""
    if asset.get('parts', False):
        return [entry for entry in entries if entry['id'].startswith(asset['id'] + '.')]
    return [entry for entry in entries if entry['id'] == asset['id']]


def build(batch_dir, only=()):
    batch_dir = Path(batch_dir).resolve()
    batch = load_json(batch_dir / 'batch.json')
    formats = load_json(Path(__file__).resolve().parent / 'shared' / 'formats.json')['formats']
    palette = Palette.load(batch_dir / batch['palette'])
    output = (ROOT / batch['output']).resolve()
    if not output.is_relative_to(ROOT / 'submissions'):
        raise BuildError(f'Output must be inside submissions/: {batch["output"]}')
    identifiers = [asset['id'] for asset in batch['assets']]
    duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
    if duplicates:
        raise BuildError(f'Duplicate asset ids in batch.json: {duplicates}')
    for asset in batch['assets']:
        if asset.get('parts', False):
            clash = [other for other in identifiers if other.startswith(asset['id'] + '.')]
            if clash:
                raise BuildError(f'{asset["id"]} is built in parts; ids under it are reserved: {clash}')
    manifest_path = output / 'manifest.json'
    previous = []
    if only and manifest_path.is_file():
        previous = load_json(manifest_path)['assets']
    entries = []
    for asset in batch['assets']:
        selected = not only or any(asset['id'].startswith(prefix) for prefix in only)
        if not selected:
            kept = entry_ids(asset, previous)
            if not kept:
                raise BuildError(f'{asset["id"]} has never been built; run without --only first')
            entries.extend(kept)
            continue
        started = time.perf_counter()
        built = build_asset(asset, batch, formats, palette, batch_dir, output)
        entries.extend(built)
        label = asset['id'] + (f' ({len(built)} parts)' if asset.get('parts', False) else '')
        print(f'  {label:<34} {built[0]["size"][0]}x{built[0]["size"][1]}'
              f'  {time.perf_counter() - started:5.1f}s', flush=True)
    manifest = {'contract_version': 1, 'theme_id': batch['theme_id'], 'theme': batch['theme'],
                'sources': batch['sources'], 'assets': entries}
    if 'preview' in batch:
        manifest['preview'] = batch['preview']
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('batch', type=Path, help='authoring batch directory containing batch.json')
    parser.add_argument('--only', action='append', default=[], metavar='ID_PREFIX',
                        help='rebuild only assets whose id starts with this prefix (repeatable)')
    args = parser.parse_args()
    try:
        manifest = build(args.batch, tuple(args.only))
    except (BuildError, KeyError, ValueError) as error:
        parser.exit(1, f'BUILD FAILED: {error}\n')
    print(f'Wrote {len(manifest["assets"])} manifest entries. Next: tools/seal.py then tools/validate.py.')


if __name__ == '__main__':
    main()
