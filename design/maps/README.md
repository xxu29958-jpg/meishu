# Region maps

One record per painted regional map. A record is what integration needs to place the map and to turn longitude and latitude into pixels; it holds no art parameters (those are the recipe under `authoring/<batch>/`) and no politics (those are the dated records under `design/global-conquest/`).

| Field | Meaning |
| --- | --- |
| `projection`, `formulas` | The projection and its forward and inverse formulas, written out so they can be implemented without a library |
| `window` | The rectangle of the projection plane the map covers, in km |
| `levels` | One entry per level of detail: scale, pixel size, chunk grid, id pattern, the batch that delivers it |
| `chunks` | How chunks are placed and how levels relate |
| `hex_scale` | The options for laying the hex grid over the map. A proposal until the Owner decides; never baked into an image |
| `check_points` | Places with their km and level-0 pixel positions and whether they are land or sea. `validation/test_atlas.py` checks the delivered chunks against them; an integrator can check a port of the projection the same way |

`authoring/shared/kit/geo.py` implements the projection and reads these records; the map painter takes its frame from them, so the record and the picture cannot drift apart.

Status of `europe.json`: proposal. The projection, window and chunk convention await integration; the hex scale awaits the Owner.
