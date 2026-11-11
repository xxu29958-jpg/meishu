import json
import sys
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from preview import Workbench


class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Workbench, directory=str(ROOT)))
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.address = f'http://127.0.0.1:{cls.server.server_port}/api/validate?manifest='

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def test_two_batches_share_exactly_the_same_endpoint(self):
        for path, count in [('samples/manifest.json', 27), ('submissions/interface-test-b/manifest.json', 2)]:
            with urlopen(self.address + path) as response:
                result = json.load(response)
            self.assertEqual(result['report']['asset_count'], count)
            self.assertEqual(result['manifest']['theme_id'], result['theme']['id'])
            self.assertTrue(result['sources']['sources'])

    def test_error_is_explicit_and_never_success(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.address + 'samples/absent.json')
        self.assertEqual(caught.exception.code, 422)
        self.assertIn('Missing file', json.load(caught.exception)['error'])


if __name__ == '__main__':
    unittest.main()
