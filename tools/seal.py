"""Update image sizes and digests after authoring; never modifies provenance claims."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from validate import local_file, read_json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    path = args.manifest.resolve()
    data = read_json(path)
    for asset in data['assets']:
        file = local_file(path.parent, asset['file'])
        with Image.open(file) as image:
            asset['size'] = list(image.size)
        asset['sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Updated image facts. Run validate.py to check the complete batch.')
