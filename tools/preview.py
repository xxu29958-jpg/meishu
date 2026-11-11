"""Serve the production workbench with the same validator used for delivery."""
import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from validate import ROOT, ValidationError, local_file, read_json, validate


class Workbench(SimpleHTTPRequestHandler):
    def do_GET(self):
        request = urlparse(self.path)
        if request.path != '/api/validate':
            return super().do_GET()
        try:
            values = parse_qs(request.query)
            paths = values.get('manifest', [])
            if len(paths) != 1:
                raise ValidationError('Provide one relative manifest path')
            manifest_path = local_file(Path(self.directory), paths[0])
            report = validate(manifest_path)
            manifest = read_json(manifest_path)
            data = {'report': report, 'manifest': manifest,
                    'theme': read_json(local_file(manifest_path.parent, manifest['theme'])),
                    'sources': read_json(local_file(manifest_path.parent, manifest['sources'])),
                    'preview': read_json(local_file(manifest_path.parent, manifest['preview'])) if 'preview' in manifest else None}
            status = 200
        except (ValidationError, OSError, ValueError) as error:
            data = {'error': str(error)}
            status = 422
        content = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(content)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Workbench, directory=str(ROOT)))
    print(f'Open http://127.0.0.1:{args.port}/previews/', flush=True)
    server.serve_forever()
