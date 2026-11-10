"""Chapter IV (the transit metropolis): today's Metro network by opening year, and the votes that paid for it.

  lines    Metro rail and busway sections dated by the year they opened (gif/transit_segments.json, built by
           gif_prep_transit.py from LA Metro GTFS rail + bus, Nov 2026) -> data/metro_lines.geojson
  miles    route miles open by year, shared track counted once (sections buffered 25 m and unioned)
  stations open rail stations (data/stations.geojson, k = 'open'), each dated by the earliest section it stands on
           (sections within 60 m, else the nearest; a name ending '<X>-Line' looks only at line X) and added to metro_lines.geojson as points (kind 'station')
  ballots  LA Metro Research Library, "Los Angeles County Mass Transit Ballot Initiatives" (2017 history spreadsheet,
           raw4/ballots.json transcribed from libraryarchives.metro.net/DPGTL/histories/2017-History-BallotInitiatives.xls)
-> data/story_stats.json ['transit']
"""
import json, os
from shapely.geometry import LineString, mapping
from shapely.ops import transform, unary_union
from pyproj import Transformer

S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
SEG = json.load(open(S + 'gif/transit_segments.json'))
for s in SEG: s['g'] = transform(g2m, LineString(s['coords']))
def miles(y, kind):
    gs = [s['g'].buffer(25) for s in SEG if s['year'] <= y and s['kind'] == kind]
    return round(unary_union(gs).area / 50 / 1609.34, 1) if gs else 0.0
years = sorted({s['year'] for s in SEG} | {2026})
by_year = [[y, miles(y, 'rail'), miles(y, 'bus')] for y in range(1990, 2027) if y in years or y == 1990]
def r(o):
    if isinstance(o, float): return round(o, 5)
    if isinstance(o, (list, tuple)): return [r(v) for v in o]
    return o
feats = []
for s in SEG:
    g = LineString(s['coords']).simplify(0.00004)
    gm = mapping(g); gm['coordinates'] = r(gm['coordinates'])
    feats.append({'type': 'Feature', 'geometry': gm, 'properties': {'line': s['line'], 'color': s['color'], 'year': s['year'], 'kind': s['kind']}})
from shapely.geometry import Point
for f in json.load(open(DAY + 'data/stations.geojson'))['features']:
    if f['properties']['k'] != 'open': continue
    q = transform(g2m, Point(f['geometry']['coordinates']))
    nm = f['properties']['name']; ln = nm[-6] if nm.endswith('-Line') else None    # 'Expo / Crenshaw K-Line': that line's platform
    d = sorted((s['g'].distance(q), s['year']) for s in SEG if s['kind'] == 'rail' and (ln is None or s['line'] == ln))
    yr = min([y for dd, y in d if dd <= 60] or [d[0][1]])
    feats.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': r(f['geometry']['coordinates'])},
                  'properties': {'name': f['properties']['name'], 'year': yr, 'kind': 'station'}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(DAY + 'data/metro_lines.geojson', 'w'), separators=(',', ':'))
stations = sum(1 for f in json.load(open(DAY + 'data/stations.geojson'))['features'] if f['properties']['k'] == 'open')
ballots = json.load(open(S + 'raw4/ballots.json'))
st = json.load(open(DAY + 'data/story_stats.json'))
st['transit'] = {'miles_by_year': by_year, 'rail_miles_2026': miles(2026, 'rail'), 'busway_miles_2026': miles(2026, 'bus'),
                 'stations_open': stations, 'ballots': ballots,
                 'src': 'LA Metro GTFS (rail and bus, Nov 2026), sections dated by opening year; LA Metro Research Library ballot history (2017)'}
json.dump(st, open(DAY + 'data/story_stats.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in st['transit'].items() if k not in ('ballots',)}))
print(os.path.getsize(DAY + 'data/metro_lines.geojson') // 1024, 'KB')
