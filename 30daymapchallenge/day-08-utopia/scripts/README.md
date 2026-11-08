# Day 8 · Utopia — processing (rebuilt Nov 2026 on the newest authoritative sources)

Run everything from one empty working directory `W`, with these scripts copied into it and `DAY` pointing at
this day folder (e.g. `export DAY=/path/to/places/30daymapchallenge/day-08-utopia/`).
Python 3 with numpy, scipy, pillow, shapely ≥ 2, pyproj, pyarrow, rasterio; poppler-utils for `pdfimages`.
Steps 14–20 feed the illustrated essay (`../index.html`); `../analysis.html` is the detailed analysis page.

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
| 14 | `python fetch_roll26_county.py 2400000` | County Assessor roll 2026, **all** parcels (year built, units) | `raw2/roll2026_county.csv` |
| 15 | `python fetch.py places` | County city boundaries; City Area Planning Commissions, Community Plan Areas, HPOZs (Nov 2026) | `raw2/{city_comm,apc,cpa,hpoz}.geojson` |
| 16 | `pdfimages -j -png -f 120 -l 120 1930_parks_playgrounds_beaches_los_angeles_region.pdf orig/p1930` and `pdfimages -png -f 11 -l 11 1946_interregional_regional_metropolitan_parkways.pdf orig/p1946` | [1930 Olmsted–Bartholomew report](https://libraryarchives.metro.net/DPGTL/trafficplans/1930_parks_playgrounds_beaches_los_angeles_region.pdf), [1946 RPC parkways report](https://libraryarchives.metro.net/DPGTL/trafficplans/1946_interregional_regional_metropolitan_parkways.pdf) (Metro Research Library) | `orig/p1930-004.jpg`, `orig/p1946-000.png` |
| 17 | `python register_plate.py parkways1946` · `python register_plate.py parks1930 '[[68,853,-118.8065,34.0011],[307,550,-118.6551,34.1771],[107,550,-118.7759,34.1803],[1745,966,-117.7786,33.9330],[1975,318,-117.6467,34.2889],[1945,662,-117.6878,34.1065]]'` | hand anchors on County-boundary vertices, then ICP against the surveyed County outline + thin-plate spline | `tiles/{parkways1946,parks1930}/` (z9–12), `img/*_registration.json` |
| 18 | USGS Historical Topographic Map Collection GeoTIFFs from `https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/` (file names as in `tiles_topo.py`, spaces → `_`), plus `https://cdn.proj.org/us_noaa_conus.tif` in `projgrids/`; then `python tiles_topo.py` | Llano 1930, La Crescenta 1928, Hollywood 1953, Beverly Hills 1950, Los Angeles 1953 (1:24,000) | `tiles/topo_*/` (z12–16), `img/topo_meta.json` |
| 19 | `python build_story.py && python story_stats.py` | roll (step 14), outlines (step 15), Caltrans LRS (`raw/fwy_d7.geojson`) | `img/morph_grid.png`, `data/morph.json`, `data/story_places.geojson`, `data/story_stats.json` |
| 20 | `python fetch.py bldg120`, LODES8 `ca/wac/ca_wac_S000_JT00_2023.csv.gz` + `ca/ca_xwalk.csv.gz` from <https://lehd.ces.census.gov/data/lodes/LODES8/> into `raw3/`, Metrolink GTFS (<https://metrolinktrains.com/globalassets/about/gtfs/gtfs.zip>) unzipped to `raw3/ml/`; then `python centres_more.py` | jobs 2023, roll 2026, Metrolink May 2026, LARIAC 2020 (120–149 ft) | jobs / homes / Metrolink per centre in `data/centers.geojson`; `stats.json → centers.neither_types` |

The Caltrans bottleneck tables (District 7 Mobility Performance Report, 2025 Q2 edition: calendar-2024 top 20 and
2025 Q2 top 10) are transcribed verbatim inside `build2.py` and located on Caltrans tenth-mile postmiles.
Live services change: a re-fetch will move some counts (new towers, new permits, a newer roll).

`morph_grid.png` packs the chronology into one RGBA image: one pixel per 120 m Web-Mercator cell, R = median year built
of the cell's parcels − 1850, G = parcel count (capped at 255), A = occupied. The story page recolours it in the browser
for any year, so the timeline needs no tiles per year.
