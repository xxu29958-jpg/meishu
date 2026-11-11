"""Turn a text map layout into a preview scene for a batch.

    python authoring/scene.py authoring/campaign-atlas-01/scenes/channel-coast.json submissions/campaign-atlas-01/preview.json

The layout is display data (terrain codes, legend, placed items). The scene
follows the layered map recipe in shared/kit/maplayout.py and validates against
schemas/preview-scene.schema.json through tools/validate.py like any batch file.

A layout of the form {"region": "<path to a region record>", "level": 0} lays
out that level of a regional map from its chunks instead.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared.kit.maplayout import scene_from_layout, scene_from_region  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('layout', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    try:
        layout = json.loads(args.layout.read_text(encoding='utf-8'))
        if 'region' in layout:
            region = json.loads((args.layout.parent / layout['region']).read_text(encoding='utf-8'))
            scene = scene_from_region(region, layout.get('level', 0))
        else:
            scene = scene_from_layout(layout)
    except (OSError, KeyError, ValueError) as error:
        parser.exit(1, f'SCENE FAILED: {error}\n')
    args.out.write_text(json.dumps(scene, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'{args.out}: {len(scene["tiles"])} cells, {len(scene["items"])} placed pieces')


if __name__ == '__main__':
    main()
