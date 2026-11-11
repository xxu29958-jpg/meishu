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

## Strategic maps: Europe, the Americas, the world

Not yet made. Plan:

- **Paint from geography, not from hexes.** Coastlines, rivers and lakes from Natural Earth (public domain; named in `references/SOURCES.json` as the data route). Relief as engraved hachure and wash. The same palette, ink and sea lining as the terrain kit.
- **World:** equirectangular, 4096×2048 design canvas per ASSET-SPEC (`u = (lon + 180) / 360`, `v = (90 - lat) / 180`), split at the date line.
- **Europe and the Americas:** their own canvases at higher detail, same projection unless integration prefers another.
- **Delivery:** 512×512 chunks with a 2 px skirt (516×516), as ASSET-SPEC describes. Proposed ids `maps.region.<region>.r<row>c<column>`, anchor `[0, 0]`, placed at `(column * 512 - 2, row * 512 - 2)`.
- **Nothing political in the paint.** Frontiers, territory washes, cities and names are overlays keyed to the dated records in `design/global-conquest/`.
- **Hexes are derived, not drawn.** The gameplay hex grid is laid over the painted map; a terrain-type grid for rules can be sampled from the same geographic data and delivered as design data.

Blocked on one decision: downloading the Natural Earth files (asked of the Owner).

## Not done

Snow, desert, wetland, mountain, river and road; edge variety (two or three outlines per coast layer so long shores do not repeat); the three strategic maps; territory and frontier overlay styles as assets.
