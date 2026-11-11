# Maps

Direction: one continuous historical map. The hex grid is underneath, never on show. Decision record: `design/ART-DECISIONS.md`.

## The terrain kit (delivered in `campaign-atlas-01`)

| Asset | Frame / display | What it is |
| --- | --- | --- |
| `maps.terrain.water`, `maps.terrain.coast` | 128×144 / 64×72 | Open sea and shallows. Fill the hex exactly, with a pixel of bleed on the slanted edges. Repeat on the lattice. |
| `maps.terrain.plain`, `.plain.tilled`, `maps.terrain.forest` | 176×198 / 88×99 | Land pieces. The hex sits in the centre; the ground runs past it and feathers out along a wandering edge. Forest crowns may overhang. |
| `maps.coast.shallows`, `.surf`, `.sand` | 240×270 / 120×135 | Coast under-layers: a pale shelf of shallow water, a rim of surf, a beach. All three share one outline. |
| `maps.grid.hex` | 128×144 / 64×72 | Optional dotted hex outline for the game to show on demand. |

All anchors are the centre `[0.5, 0.5]`; every piece is placed on its hex centre.

### Why pieces overlap

Each ground texture is painted so that it repeats when shifted by one hex in any of the six directions. A plain piece that spills onto its neighbour therefore lays down exactly the paint the neighbour would have. Overlap costs nothing and removes every straight edge.

### Drawing order

Bottom to top, each pass covering the whole visible map before the next begins:

1. Sea (`maps.terrain.water` or `.coast`) on **every** cell, land cells included.
2. `maps.coast.shallows` on every land cell.
3. `maps.coast.surf` on every land cell.
4. `maps.coast.sand` on every land cell.
5. Land pieces, row by row from the top.
6. Territory overlays, buildings, units, markers, effects, as in ASSET-SPEC.

Passes 2-4 must each finish before the next starts. Drawn that way, the surf of one hex is covered by the sand of its neighbour, and the shoreline is the outline of the union, whatever the arrangement of hexes. Drawn per hex, surf lines would cut across beaches.

`authoring/shared/kit/maplayout.py` implements this recipe for previews; `submissions/campaign-atlas-01/preview.json` is a scene made with it.

### Adding terrain

A new ground (snow, desert, marsh) is a function in `authoring/shared/painters/terrain.py` plus a batch entry. A new relief feature (mountains, hills) should be a canopy drawn over a ground, as forest is. Rivers and roads will be centre-to-edge segments on the 176×198 piece canvas, six directions each, drawn after land.

## Strategic maps

### Europe and its approaches (level 0 delivered in `atlas-europe-01`)

One continuous painting, 3072 x 2560 at 1.875 km per pixel, from Iceland to the Caspian and from the North Cape to Cairo. Delivered as thirty 516 x 516 chunks, `maps.region.europe.z0.r{row}c{column}`. The integration record (projection, formulas, window, chunk placement, check points, hex-scale options) is `design/maps/europe.json`.

**How it is painted** (`authoring/shared/painters/atlas.py`, recipe `authoring/atlas-europe-01/europe.json`):

1. *Sea.* Colour deepens with distance from land; a pale shelf hugs the coast. Nine coast-parallel lines open out to sea, as engravers lined water; beyond them a broken horizontal ruling. Faint meridians and parallels every five degrees, on water only.
2. *Ground.* Colour by climate belt from interpreted samples (tundra, taiga, mixed and broadleaf forest, open farmed lowland, forest-steppe, steppe, semi-desert, Mediterranean, highland, desert, delta, marsh), blended by distance and then washed with slow tonal pooling. Dry-country rivers carry a green ribbon: the Nile, the Tigris and Euphrates.
3. *Relief.* An envelope from range outlines and ridge lines, broken into crests by ridged noise, cut by river valleys, shaded from the upper left and hachured down the slope. Tree, rock and snow lines fall with latitude, so the Scandinavian fells are bare where the Alps are wooded.
4. *Woods.* Each ground has a wooded share; noise gathers that share into forests with ragged edges, drawn as massed tree marks (round for broadleaf, pointed for conifer) over a dark floor wash.
5. *Open-country marks.* Stipple on tilled land, grass ticks on steppe, dots and dune crests on sand, reed strokes on marsh.
6. *Water on land.* Rivers by rank, thinning inland, the broad ones with a pale channel inside the line; lakes with a darker centre and an inked shore.
7. *Coast line*, heavier on shores facing away from the light. Water too narrow to hold two coast lines (an estuary) is drawn as a channel instead of filling with ink.
8. *Paper.* Grain and slow mottle over everything; one overall tone adjustment.

**What is data and what is interpretation.** Coastlines, lakes, rivers and the outlines of the major ranges, deserts and deltas are Natural Earth 1:50m (`authoring/geodata/`). Everything else is the author's reading, written in the recipe so it can be corrected: 374 land-cover samples for about 1800; 66 ridge lines for ranges the data does not outline, placed from general knowledge and approximate to tens of km; the form of relief inside every outline, which is drawn and not surveyed (no elevation data was used); hydrography as of the period (8 modern reservoirs and 4 later canals left out, the Zuiderzee open and its polders water); and 7 straits cut to a minimum drawn width so crossings stay visible.

**Nothing political is in the paint.** No frontiers, towns, roads or names. Those are overlays keyed to the dated records in `design/global-conquest/`.

**Seamless by construction.** Slow fields (far distances, relief envelope, ground cover) are surveyed once for the whole picture at a quarter of its resolution. Detail is painted in windows of at most 1024 px; every placement is in km and every random choice is hashed from map position, so a window paints the same ground whichever window it is. Tests hold overlapping windows to within two colour levels and chunk skirts to exact equality. Peak memory for the whole map is about 600 MB.

**Levels of detail.** Level 0 is the overview. Level n has 2^n times the pixels per km; the painter renders any level from the same recipe (stroke sizes stay in pixels, placement stays in km). One batch holds 30 chunks under the 32 MiB budget, so level 1 is four batches. Not built yet.

**Hexes are derived, not drawn.** The Owner chose 120 km per hex column (2026-11-11). The grid is 47 x 47 cells lying wholly inside the map, origin (48, 38), in `design/maps/europe.json`. `design/maps/europe-hexes.json` gives each hex one terrain word, measured from the same fields that painted the map: 1403 land hexes (490 plain, 277 forest, 217 desert, 171 hills, 106 steppe, 82 mountain, 48 tundra, 12 marsh) and 806 sea.

Three things a 120 km hex cannot show by itself, each listed in the table for integration to rule on:

- *Small places that matter.* Malta is a fiftieth of a hex. Twelve places (Malta, Corfu, Minorca, Corsica, Palermo, Crete, Cyprus, Gotland, Naples, Amsterdam, Cádiz, Acre) are kept as land with a stated reason.
- *Straits.* The Sound, the Bosporus and Gibraltar are narrower than a hex. Sea hexes fall into separate basins: the Atlantic with the North Sea; the Baltic; the Mediterranean; the Black Sea; the Caspian; the White Sea. Ten named passages say which hex each strait falls in and which basins it touches.
- *River valleys in desert.* The Nile's green ribbon is a sixth of a hex wide, so Cairo's hex reads as desert. The river list says which hexes a river runs through.

### The Americas and the world

Not started. The same painter and layers serve both. The world map is equirectangular per ASSET-SPEC, 4096 x 2048, split at the date line; the Americas get their own equal-area record. Each needs its own recipe: land-cover samples, ridge lines, period hydrography.

### Limits to know about

- The 1:50m river layer lacks rivers that matter to the period: the Niemen, Berezina, Meuse, Main, Weser, Sava and others. The 1:10m layer has them; it has not been downloaded.
- Only the largest ranges are outlined in the data. The rest stand on hand-placed ridge lines.
- Real elevation data would replace drawn relief with surveyed relief. It is a large raster download and has not been asked for.

## Not done

Snow, desert, wetland, mountain, river and road pieces for the terrain kit; edge variety for coast layers; Europe at level 1; the Americas; the world; territory and frontier overlay styles as assets.
