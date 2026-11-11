# Authoring

How the art is made and how to make it again. Runtime deliverables are in `submissions/<batch>/`; this directory is everything that produces them.

## Environment

Python 3.12 with Pillow and jsonschema (`requirements.txt`) plus numpy and pycairo (`authoring/requirements.txt`). Built with Pillow 12.3.0, numpy 2.5.4, pycairo 1.25.1 on cairo 1.18.0.

```sh
python -m venv --system-site-packages .venv     # system site packages if pycairo comes from the OS
.venv/bin/python -m pip install -r requirements.txt -r authoring/requirements.txt
```

## Build a batch

```sh
python authoring/build.py authoring/campaign-atlas-01
python authoring/scene.py authoring/campaign-atlas-01/scenes/channel-coast.json submissions/campaign-atlas-01/preview.json
python tools/seal.py submissions/campaign-atlas-01/manifest.json
python tools/validate.py submissions/campaign-atlas-01/manifest.json
python -m unittest discover -s validation
```

The Europe map is a batch like any other; its preview scene comes from the region record:

```sh
python authoring/build.py authoring/atlas-europe-01
python authoring/scene.py authoring/atlas-europe-01/scenes/europe.json submissions/atlas-europe-01/preview.json
```

`--only <id-prefix>` rebuilds part of a batch. The build writes PNGs, the vector masters in `sources/` and `manifest.json`. It never writes `theme.json` or `sources.json`: those are declarations, kept by hand.

Rebuilding gives the same pixels on the same library versions. PNG bytes, and so hashes, can differ between zlib builds; `seal.py` records the bytes actually committed.

## Look at the result

```sh
python tools/preview.py                      # then /previews/ and /previews/screens.html
python authoring/review.py sheet <manifest> <asset-id> out.png --zoom 3
python authoring/review.py strip <manifest> <asset-id> attack out.png --mirror
python authoring/review.py scene <manifest> <scene.json> out.png --ppu 2
```

`review.py` writes outside the repository on purpose: every PNG in the tree must be a declared asset.

## Layout

```
authoring/
  build.py            batch.json -> PNGs, SVGs, manifest
  scene.py            map layout -> preview scene
  review.py           headless contact sheets and scenes
  shared/
    formats.json      canvas formats from ASSET-SPEC
    kit/              raster, draw, palette, sheet, anim, rig, hexgrid, compose, maplayout, geo, field
    painters/         terrain, buildings, figure, infantry, cavalry, effects, flags, ui, illustration, atlas
  geodata/            public-domain geography layers and the tool that derives them (see its README)
  <batch>/
    batch.json        the asset list: id, painter, format, parameters, source
    palette.json      every colour, by role
    ...               painter data: unit looks and drills, building plans, effect recipes, flags, scenes, characters
```

## Where a change goes

| To change | Edit |
| --- | --- |
| A colour, everywhere | `<batch>/palette.json` |
| A uniform, or add a regiment | `<batch>/units/<nation>.json` |
| Animation timing or a pose | `<batch>/units/*-drill.json` |
| How many men stand in a unit | `formation` on the asset in `batch.json` |
| A town's layout or its damage | `<batch>/buildings/*.json` |
| An effect's timing or layers | `<batch>/effects.json` |
| An avatar's crop | `<batch>/portraits/<name>/character.json` |
| A screen's layout or its sample text | `design/ui/flows/`, `design/ui/data/` |
| What a regional map shows: ranges, land cover, period hydrography, straits, every stroke | `<batch>/<region>.json` (the recipe) |
| A regional map's projection, window, levels | `design/maps/<region>.json` |
| Add a commander | New `portraits/<name>/` with `illustration.py` and `character.json`, two asset entries |
| Add a kind of artwork | New module in `shared/painters/`, one line in `shared/painters/__init__.py` |

Shared code never names an asset, a nation, a person or a place. If a change seems to need that, it belongs in data.

## Painted maps

`shared/painters/atlas.py` paints a regional map for a `Frame` (a pixel window on a projection, `shared/kit/geo.py`). A batch entry with `"parts": true` returns many pieces from one painting; each becomes its own asset, `<id>.r<row>c<column>`. To look at part of a map without building the batch, call `atlas.render(frame.window(left, top, width, height), recipe, palette)`: any window paints the same ground it would in the whole picture. A palette may `extend` another so maps share ink, paper and sea with the terrain kit.
