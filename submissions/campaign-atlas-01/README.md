# campaign-atlas-01 · Campaign Atlas, first collection

France, September 1805. Thirty assets in one art direction: the Campaign Atlas identity recorded in `design/ART-DECISIONS.md`.

Rebuild: `python authoring/build.py authoring/campaign-atlas-01`, then seal and validate (`authoring/README.md`).

## Replaces sample ids

`ui.panel.command`, `ui.button.primary`, `maps.terrain.plain`, `maps.terrain.forest`, `maps.terrain.water`, `maps.terrain.coast`, `units.infantry.line`, `units.cavalry.light`, `units.france.grenadier`, `portraits.napoleon.bust`, `portraits.napoleon.avatar`, `buildings.city.l1`, `buildings.capital.l1`, `buildings.port.l1`, `effects.hit.spark`, `identity.france.flag`.

## New ids

`ui.button.secondary`, `ui.tab.folio`, `ui.list.row`, `ui.chip.resource`, `ui.rule.section`, `ui.icon.gold`, `ui.icon.men`, `ui.icon.guns`, `ui.backdrop.desk`, `maps.terrain.plain.tilled`, `maps.coast.shallows`, `maps.coast.surf`, `maps.coast.sand`, `maps.grid.hex`.

## Things an integrator should know

- **Land pieces are larger than a hex** (176×198 shown at 88×99) and coast layers larger still (240×270 at 120×135). They are meant to overlap. Draw order is in `design/art/maps.md`; `preview.json` follows it.
- **Unit sheets are 8 columns** with clips of unequal length (infantry 37 frames, cavalry 34). Read frames from `clips`, not from a fixed grid.
- **Muzzle flash and first smoke are in the infantry attack frames.**
- **`ui.rule.section` and `ui.backdrop.desk` have one frame**; their four state clips all point to it.
- **Editable SVGs** in `sources/` are vector exports of line and wash. The authoritative source is the code and data under `authoring/`. Units, the avatar and the raster-masked land and coast pieces have no SVG.

## Not in this batch

Every other nation, arm, terrain, building type, effect and screen. See `design/COVERAGE.md`.
