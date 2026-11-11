# atlas-europe-01 · Europe and its approaches, continuous map, level 0

One painted map from Iceland to the Caspian and from the North Cape to Cairo, delivered as thirty chunks. No hexes, frontiers, towns or lettering are in the paint: the game lays those over it.

Rebuild: `python authoring/build.py authoring/atlas-europe-01`, then `authoring/scene.py`, seal and validate (`authoring/README.md`).

## Ids

`maps.region.europe.z0.r{row}c{column}`, rows 0-4 from the north, columns 0-5 from the west. `z0` is the level of detail.

## Things an integrator should know

- **Placement.** Each chunk is 516 x 516: a 512 square plus a 2 px skirt that repeats its neighbours' pixels exactly (tested). The anchor is the centre. Draw chunk (row, column) with its centre at `((column + 0.5) * 512, (row + 0.5) * 512)`. `preview.json` does exactly this.
- **Projection.** Lambert azimuthal equal-area on a sphere, centred 50°N 20°E, 1.875 km per pixel at this level. Formulas, the window and sixteen check points (longitude and latitude to pixel, land or sea) are in `design/maps/europe.json`. Equal-area means a hex covers the same ground anywhere on the map.
- **Hex scale is not decided and not baked in.** At one art pixel per logical unit a hex column is 120 km and the map is 48 x 47 hexes. `design/maps/europe.json` gives the alternative and what it costs.
- **This is the overview level.** It is sharp at zoom 1 and below on a 1x display. Closer zoom needs level 1 (four batches of the same painting at twice the scale), which the painter can render from the same recipe. Not built yet.
- **Budget.** 31,950,720 decoded bytes: the whole 32 MiB of one batch. Nothing else can ride in this batch.

## What is geography and what is interpretation

| From Natural Earth 1:50m (public domain) | Interpreted and written in the recipe |
| --- | --- |
| Coastlines, islands, lakes | Land cover of about 1800: 352 hand-placed samples of ground type, blended by distance |
| Rivers and their rank | Ridge lines for ranges the data does not outline (66 lines, placed from general knowledge, approximate to tens of km) |
| Outlines of the major ranges, deserts, deltas | The shape of relief inside every outline: drawn with noise, not surveyed. No elevation data was used |
| | Hydrography as of the period: eight modern reservoirs and four later canals left out; the Zuiderzee open and its polders water |
| | Seven straits cut to a minimum drawn width so crossings stay visible |

## Not in this batch

Levels 1 and above; the Americas; the world map; political overlays; a per-hex terrain table derived from the same data. More rivers (the Niemen, Berezina, Meuse, Main, Sava and others are not in the 1:50m river layer) need the 1:10m file. See `design/COVERAGE.md`.
