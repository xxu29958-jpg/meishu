"""Exercise real valid and broken submissions, including the publishing boundary."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from validate import ValidationError, validate
from fixture_source import make_batch


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='meishu-test-')
        self.root = Path(self.temp.name) / 'batch'
        shutil.copytree(ROOT / 'samples', self.root)
        self.path = self.root / 'manifest.json'
        self.data = json.loads(self.path.read_text(encoding='utf-8'))

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.path.write_text(json.dumps(self.data), encoding='utf-8')

    def rejected(self, message):
        self.save()
        with self.assertRaisesRegex(ValidationError, message):
            validate(self.path)

    def test_complete_original_batch(self):
        report = validate(self.path)
        self.assertEqual(report['asset_count'], 27)
        self.assertEqual({item['category'] for item in self.data['assets']},
                         {'ui', 'maps', 'units', 'portraits', 'buildings', 'effects', 'identity'})

    def test_reproducible_without_game(self):
        # Compare decoded pixels, not file hashes: PNG bytes depend on the platform's zlib build.
        fresh = Path(self.temp.name) / 'fresh'
        make_batch(fresh)
        regenerated, committed = validate(fresh / 'manifest.json')['assets'], validate(self.path)['assets']
        self.assertEqual([item['id'] for item in regenerated], [item['id'] for item in committed])
        for item in committed:
            with Image.open(fresh / item['file']) as new, Image.open(self.root / item['file']) as old:
                self.assertEqual(new.convert('RGBA').tobytes(), old.convert('RGBA').tobytes(), item['id'])

    def test_missing_file(self):
        (self.root / self.data['assets'][0]['file']).unlink()
        self.rejected('Missing file')

    def test_directory_escape(self):
        self.data['assets'][0]['file'] = '../outside.png'
        self.rejected('escapes batch')

    def test_tampered_image(self):
        self.data['assets'][0]['sha256'] = '0' * 64
        self.rejected('SHA-256 mismatch')

    def test_duplicate_id(self):
        self.data['assets'].append(copy.deepcopy(self.data['assets'][0]))
        self.rejected('Duplicate asset id')

    def test_frame_outside_sheet(self):
        self.data['assets'][0]['clips']['normal']['frames'] = [999]
        self.rejected('outside sheet')

    def test_missing_state(self):
        del self.data['assets'][0]['clips']['disabled']
        self.rejected('missing clips')

    def test_unknown_rules(self):
        self.data['assets'][0]['damage'] = 100
        self.rejected('Additional properties')

    def test_undeclared_payload(self):
        (self.root / 'hidden.dat').write_bytes(b'not-art')
        self.rejected('Undeclared file')

    def test_unknown_provenance(self):
        self.data['assets'][0]['source_id'] = 'missing.source'
        self.rejected('unknown source_id')

    def test_anchor_out_of_bounds(self):
        self.data['assets'][0]['anchor'] = [1.5, 0]
        self.rejected('maximum')

    def test_global_reference(self):
        theme_path = self.root / 'theme.json'
        theme = json.loads(theme_path.read_text(encoding='utf-8'))
        theme['global_visual']['entities'][0]['flag_asset'] = 'identity.missing.flag'
        theme_path.write_text(json.dumps(theme), encoding='utf-8')
        self.rejected('missing asset')

    def test_unrelated_batch_without_sample_identifiers(self):
        report = validate(ROOT / 'submissions/interface-test-b/manifest.json')
        self.assertEqual(report['theme_id'], 'test.batch-b')
        self.assertEqual({asset['id'] for asset in report['assets']},
                         {'batch-b.command.one', 'batch-b.signal.two'})

    def test_bad_preview_reference(self):
        preview_path = self.root / self.data['preview']
        preview = json.loads(preview_path.read_text(encoding='utf-8'))
        preview['items'][0]['asset'] = 'unknown.asset'
        preview_path.write_text(json.dumps(preview), encoding='utf-8')
        self.rejected('Preview references missing asset')


if __name__ == '__main__':
    unittest.main()
