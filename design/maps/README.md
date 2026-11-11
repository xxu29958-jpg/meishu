# Region maps

One record per painted regional map. A record is what integration needs to place the map and to turn longitude and latitude into pixels; it holds no art parameters (those are the recipe under `authoring/<batch>/`) and no politics (those are the dated records under `design/global-conquest/`).

| Field | Meaning |
| --- | --- |
| `projection`, `formulas` | The projection and its forward and inverse formulas, written out so they can be implemented without a library |
| `window` | The rectangle of the projection plane the map covers, in km |
| `levels` | One entry per level of detail: scale, pixel size, chunk grid, id pattern, the batch that delivers it |
| `chunks` | How chunks are placed and how levels relate |
| `hex_scale` | The scale the Owner chose and what was set aside |
| `hex_grid` | The grid at that scale: columns, rows, origin, step. Never baked into an image |
| `check_points` | Places with their km and level-0 pixel positions and whether they are land or sea. `validation/test_atlas.py` checks the delivered chunks against them; an integrator can check a port of the projection the same way |

`authoring/shared/kit/geo.py` implements the projection and reads these records; the map painter takes its frame from them, so the record and the picture cannot drift apart.

Status of `europe.json`: the hex scale is decided (120 km per hex column, Owner, 2026-11-11). The projection, window, chunk convention and grid origin await integration.

## Hex tables

`europe-hexes.json` gives one physical terrain word per hex, derived by `python authoring/hexes.py authoring/atlas-europe-01/hexes.json design/maps/europe-hexes.json`. Each hex is measured over its own pixels with the fields that painted the map, so table and picture agree; a test re-derives the table and compares.

| Field | Meaning |
| --- | --- |
| `grid` | Copied from the region record |
| `legend`, `terrain` | One character per hex, one string per row from the north: sea, lake, plain, forest, hills, mountain, steppe, desert, marsh, tundra |
| `kept_as_land` | Places that matter but fill less than the 40% of their hex the rule asks (Malta, Corfu, Naples and others), with the reason. A proposal to prune |
| `sea_basins` | Sea hexes joined edge to edge, with the named waters each basin holds. At 120 km the Baltic, the Mediterranean and the Black Sea are each cut off from the next |
| `passages` | Named straits: the hex each falls in, whether that hex is sea, and which basins it touches. Where the hex is land, ships need a rule to pass |
| `rivers` | Named rivers as the hexes they run through |
| `check_points` | The region record's check points as hexes |

The table is physical only: no ownership, no movement costs, no cities. Classes and thresholds live in `authoring/atlas-europe-01/hexes.json` and are meant to be tuned with integration.
