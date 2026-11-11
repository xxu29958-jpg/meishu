import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from check_isolation import check
from validate import ValidationError


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='meishu-isolation-')
        self.root = Path(self.temp.name) / 'production'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('.git', '__pycache__', '.venv'))

    def tearDown(self):
        self.temp.cleanup()

    def test_independent_repository(self):
        self.assertEqual(check(self.root)['status'], 'passed')

    def test_binary_disguised_as_text(self):
        (self.root / 'unexpected.txt').write_bytes(b'MZ\x00\x01')
        with self.assertRaisesRegex(ValidationError, 'signature'):
            check(self.root)

    def test_actual_exclusion_hash(self):
        import hashlib
        image = self.root / 'samples/maps/maps.terrain.plain.png'
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValidationError, 'excluded source hash'):
            check(self.root, [digest])


if __name__ == '__main__':
    unittest.main()
