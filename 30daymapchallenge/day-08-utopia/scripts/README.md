# Day 8 · Utopia — processing

Run from an empty working directory `W` (not committed). Python 3 with numpy, scipy, pillow, shapely, pyproj.

| Step | Command (from `W`) | Output |
|---|---|---|
| 1 | `pdftoppm -r 150 -png 1974-concept-los-angeles-side-1.pdf dl/map74_hi` ([PDF](https://libraryarchives.metro.net/dpgtl/lacity/1974-concept-los-angeles-side-1.pdf)) | `dl/map74_hi-1.png` |
| 2 | `python fetch.py {bldg,zoning,holc,aadt,fwy,bottle,city}` (one call per layer) | `raw/*.geojson` |
| 3 | Metro rail GTFS `stops/routes/trips/shapes.txt` from <https://gitlab.com/LACMTA/gtfs_rail> → `raw/gtfs_*.txt` | `raw/gtfs_*.txt` |
| 4 | `python circles2.py` — detect the red center discs (49; 7 overlapping ones are added in `georef.py`) | `work/circles2.json` |
| 5 | `python georef.py` — name the 56 discs, affine-georeference (RMSE 509 m) | `work/centers_georef.json` |
| 6 | `python cores.py` — attach each center's named core; reports drawn-vs-core offsets | `work/centers_final.json` |
| 7 | `python build.py <day-folder>/data` — every derived layer + `stats.json` | `data/*.geojson`, `data/stats.json` |
| 8 | `python scripts/sites.py` (from the day folder) — the five social-utopia sites | `data/utopias.geojson` |

Steps 4–7 reproduce the committed `data/` byte-for-byte from the same raw downloads (checked 8 Nov 2026).
Live services change; a re-fetch will shift counts slightly (new towers, new counts).
