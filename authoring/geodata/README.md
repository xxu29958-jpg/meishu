# Geography data

Compact layers the map painters read, derived from public-domain data. Raw downloads never enter the repository.

## natural-earth-50m

Natural Earth 5.1.2 at 1:50m: land, lakes, rivers, physical region outlines, elevation points. Public domain. `SOURCE.json` pins the repository commit and the SHA-256 of each file used; the Owner approved the download on 2026-11-11.

To derive the layers again, fetch the five files named in `SOURCE.json` from its `url_pattern` into an empty directory and run:

```sh
python -I authoring/geodata/import_natural_earth.py <download-directory>
```

The import refuses files whose hash differs. It rounds coordinates to 0.001 degree, keeps name, class and rank, and drops region outlines that only repeat the land outline. It moves and invents nothing. Historical choices (leaving out modern reservoirs, for instance) belong to the map recipe that uses the layers.

| Layer | Holds |
| --- | --- |
| `land.json` | 1,421 land polygons |
| `lakes.json` | 412 lakes with name and rank |
| `rivers.json` | 895 river and lake-centre lines with name and rank |
| `regions.json` | 391 outlines of ranges, plateaus, deserts, plains, deltas, basins, tundra |
| `points.json` | 86 summits and depressions with elevation |

Format: `{"layer", "scale", "features"}`; rings and lines are flat `[lon, lat, lon, lat, ...]` integer lists, degrees times `scale`. `authoring/shared/kit/geo.py` reads them.

Known limits of 1:50m for this project: many rivers that matter to the period are absent (Niemen, Berezina, Meuse, Main, Sava); only the largest ranges are outlined; coasts are generalised to a few km. The 1:10m files would fix the first two and sharpen the third; they have not been downloaded.
