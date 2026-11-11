"""Check repository payload and optionally compare images with a reference hash set.

No copyrighted inputs are needed. --deny-hashes is for the integrator's private
audit only; it never copies or emits their content or file paths.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from validate import ROOT, ValidationError, require, validate


def check(root, deny_hashes=None):
    root = Path(root).resolve()
    ignored = {'.git', '__pycache__', '.venv'}
    allowed = {'.md', '.json', '.png', '.py', '.js', '.html', '.css', '.txt', '.svg'}
    manifests = [root / 'samples/manifest.json', *sorted((root / 'submissions').glob('*/manifest.json'))]
    images = set()
    for manifest in manifests:
        for asset in validate(manifest)['assets']:
            images.add((manifest.parent / asset['file']).resolve())
    deny = set(deny_hashes or [])
    files = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts):
            continue
        require(not path.is_symlink(), f'Symbolic link in repository: {relative}')
        if not path.is_file():
            continue
        require(path.suffix.lower() in allowed or path.name in ('.gitignore', '.gitattributes'), f'Unexpected repository format: {relative}')
        content = path.read_bytes()
        require(not content.startswith((b'PK\x03\x04', b'\x7fELF', b'dex\n', b'MZ')), f'Executable/archive signature: {relative}')
        digest = hashlib.sha256(content).hexdigest()
        require(digest not in deny, f'Image matches excluded source hash: {relative}')
        if path.suffix.lower() == '.png':
            require(path.resolve() in images, f'Image missing from provenance manifest: {relative}')
        else:
            text = content.decode('utf-8')
            # These identify machine-private dependencies, not ordinary historical words.
            if path.resolve() != (root / 'tools/check_isolation.py').resolve():
                # This checker's literal signatures are detection code, not dependencies.
                require(not re.search(r'(?:[CDE]:[/\\]|file://|com\.easytech\.|def_battlelist|art-reference/|OWNER-CONTRACT)', text),
                        f'Private dependency or original-engine identifier: {relative}')
        files.append({'file': relative.as_posix(), 'sha256': digest})
    return {'status': 'passed', 'file_count': len(files), 'original_image_hashes_compared': len(deny),
            'checks': ['allowed formats plus file signatures', 'no machine/private paths',
                       'all sample images declared with provenance', 'manifest and pixel/frame validation'],
            'limits': 'Hash comparison detects exact reuse. Independent generation and content review support authorship; format checks alone cannot prove it.',
            'files': files}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--deny-hashes', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        deny = json.loads(args.deny_hashes.read_text(encoding='utf-8')) if args.deny_hashes else []
        report = check(args.root, deny)
        if args.report:
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(f'PASS: {report["file_count"]} files inspected; {len(deny)} exclusion hashes compared')
    except (ValueError, OSError) as error:
        parser.exit(1, f'FAIL: {error}\n')
