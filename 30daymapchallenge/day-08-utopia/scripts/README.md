# Day 8 · Utopia — processing (rebuilt Nov 2026 on the newest authoritative sources)

Run everything from one empty working directory `W`, with these scripts copied into it and `DAY` pointing at
this day folder (e.g. `export DAY=/path/to/places/30daymapchallenge/day-08-utopia/`).
Python 3 with numpy, scipy, pillow, shapely, pyproj, pyarrow; poppler-utils for `pdfimages`.

| # | Step | Source (vintage) | Output |
|---|---|---|---|
| 1 | `pdfimages -j 1974-concept-los-angeles-side-1.pdf dl/native` | [1974 adopted diagram](https://libraryarchives.metro.net/dpgtl/lacity/1974-concept-los-angeles-side-1.pdf), native 300-ppi JPEG | `dl/native-000.jpg` |
| 2 | `python fetch.py {bldg,zoning,holc,aadt,fwy,bottle,city,postmiles,hcm}` | County LARIAC6 2020; City zoning (5 Nov 2026); Caltrans AADT 2024, postmiles; City HCMs (Nov 2026) | `raw/`, `raw2/` |
| 3 | `python fetch_roll26.py 805901` | County Assessor roll 2026 (City of LA parcels) | `raw2/roll2026_city.csv` |
| 4 | Metro rail GTFS (`stops/routes/trips/shapes/feed_info.txt`) from <https://gitlab.com/LACMTA/gtfs_rail> | 7 Nov 2026 feed | `raw2/gtfs_*.txt` |
| 5 | Metro GIS: `Metro_Under_Construction_and_Planned_Stations`, `Metro_Busway_Stations_06_2023` (services8.arcgis.com/TNoJFjk1LsD45Juj) | Jun 2026 / Jun 2023 | `raw2/metro_*.geojson` |
| 6 | LADBS: Certificates of Occupancy (`3f9m-afei`, ≥10 storeys since 2019-06) and new-building permits (`pi9x-tg5x`) from data.lacity.org | to Nov 2026 | `raw2/cofo_tall.json`, `raw2/ladbs_new.json` |
| 7 | Mapping Inequality GeoParquet from <https://data.source.coop/cboettig/mappinginequality/> | Jul 2026 | `raw2/holc/mappinginequality.parquet` |
| 8 | County boundary (`County_Boundary`), Dodger Stadium parcels (`ASSR_PARCELS_25_View`, AIN 541501*) | Nov 2025 / 2025 | `raw2/county_boundary.geojson`, `raw2/chavez_parcels.geojson` |
| 9 | `python circles2.py && python georef.py && python cores.py` | 150-dpi render of the diagram (`pdftoppm -r 150`) | first-pass disc detection + drawn positions (`work/`) |
| 10 | `python cores2.py` | County CAMS street centerlines (live) | `work/centers_exact.json` — every core at an exact intersection |
| 11 | `python circles_native.py && python warp1974.py && python tiles1974.py` | native scan + County shoreline | `img/concept1974_warped.json`, `tiles/plan1974/` (z9–13) |
| 12 | `python tiles_garden.py` | 2026 roll + City zoning | `tiles/built2026/`, `tiles/zonedsf/` (z10–14) |
| 13 | `python build2.py $DAY/data` | everything above; `sites_text.json` | `data/*.geojson`, `data/stats.json` |

The Caltrans bottleneck tables (District 7 Mobility Performance Report, 2025 Q2 edition: calendar-2024 top 20 and
2025 Q2 top 10) are transcribed verbatim inside `build2.py` and located on Caltrans tenth-mile postmiles.
Live services change: a re-fetch will move some counts (new towers, new permits, a newer roll).
