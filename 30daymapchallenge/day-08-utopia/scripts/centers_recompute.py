"""Re-run the centres' tests at the plan's own disc positions (work/centers_plan.json) -> data/centers.geojson + stats.

Same tests as build2.py, on the same evidence already in data/: buildings of 150 ft and up (towers.geojson) and
rail stations open / under construction / busway (stations.geojson), within 1/2 mile (and the plan's own 1/4 mile).
Then run centres_more.py (jobs, homes, sub-types of 'neither') and today_centres.py.
"""
import json, os, collections
from shapely.geometry import shape, Point
from shapely.ops import unary_union, transform
from pyproj import Transformer

S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
to3310 = Transformer.from_crs(4326, 3310, always_xy=True).transform
P = lambda g: transform(to3310, g)
QUARTER, HALF = 402.3, 804.7
towers = [{'pt': P(shape(f['geometry'])), 'h': f['properties'].get('h'), 'src': f['properties'].get('src')}
          for f in json.load(open(DAY + 'data/towers.geojson'))['features']]
st = json.load(open(DAY + 'data/stations.geojson'))['features']
st_open = [(f['properties']['name'], P(shape(f['geometry']))) for f in st if f['properties']['k'] == 'open']
st_uc = [(f['properties']['name'], P(shape(f['geometry'])), f['properties'].get('line', '')) for f in st if f['properties']['k'] == 'uc']
st_bus = [(f['properties']['name'], P(shape(f['geometry'])), f['properties'].get('line', '')) for f in st if f['properties']['k'] == 'bus']
city_m = P([shape(f['geometry']) for f in json.load(open(S + 'raw2/city_comm.geojson'))['features'] if f['properties']['CITY_COMM_NAME'] == 'LOS ANGELES'][0])
old = {f['properties']['name']: f['properties'] for f in json.load(open(DAY + 'data/centers.geojson'))['features']}

def cls(ntw, near):
    return 'realised' if ntw >= 5 and near else ('towers' if ntw >= 5 else ('rail' if near else 'neither'))
cf = []; oc_n = collections.Counter(); strict_n = collections.Counter()
for c in json.load(open(S + 'work/centers_plan.json'))['centers']:
    p = P(Point(c['lng'], c['lat']))
    tw_h = [t for t in towers if t['pt'].distance(p) <= HALF]
    tw_q = [t for t in towers if t['pt'].distance(p) <= QUARTER]
    d_open, n_open = min((s.distance(p), n) for n, s in st_open)
    uc = min(((s.distance(p), n, l) for n, s, l in st_uc), default=(1e9, '', ''))
    bus = min(((s.distance(p), n, l) for n, s, l in st_bus), default=(1e9, '', ''))
    rail = 'open' if d_open <= HALF else ('building' if uc[0] <= HALF else 'none')
    oc = cls(len(tw_h), d_open <= HALF); strict = cls(len(tw_q), d_open <= QUARTER)
    oc_n[oc] += 1; strict_n[strict] += 1
    hs = [t['h'] for t in tw_h if t['h']]
    pr = {'name': c['name'], 'core': 'as drawn on the 1974 map', 'core_street': c['core'], 'in_city': bool(city_m.contains(p)),
          'tw': len(tw_h), 'twq': len(tw_q), 'twnew': sum(1 for t in tw_h if t['src'] == 'LADBS CofO'), 'hmax': max(hs) if hs else 0,
          'near': n_open, 'near_m': int(round(d_open, -1)), 'rail': rail,
          'uc': f"{uc[1]} ({uc[2]})" if rail == 'building' else '', 'bus': f"{bus[1]} ({bus[2]})" if bus[0] <= HALF else '',
          'oc': oc, 'strict': strict, 'drawn': [c['lng'], c['lat']], 'off': c['off_m'], 'oc_at_street_core': old.get(c['name'], {}).get('oc')}
    cf.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [c['lng'], c['lat']]}, 'properties': pr})
json.dump({'type': 'FeatureCollection', 'features': cf}, open(DAY + 'data/centers.geojson', 'w'), separators=(',', ':'))

cu_h = unary_union([P(Point(f['geometry']['coordinates'])).buffer(HALF) for f in cf])
cu_q = unary_union([P(Point(f['geometry']['coordinates'])).buffer(QUARTER) for f in cf])
ct = [t for t in towers if city_m.contains(t['pt'])]
core4 = unary_union([P(Point(f['geometry']['coordinates'])).buffer(HALF) for f in cf if f['properties']['name'] in
                     ('Downtown', 'Bunker Hill (unlabelled circle)', 'Civic Center', 'Westlake (unlabelled circle)')])
stats = json.load(open(DAY + 'data/stats.json'))
new_t = [t for t in towers if t['src'] == 'LADBS CofO']
stats['centers'].update({
    'n': len(cf), 'n_in_city': sum(f['properties']['in_city'] for f in cf), 'positions': 'as drawn on the 1974 map',
    'outcomes_half_mile': dict(oc_n), 'outcomes_quarter_mile': dict(strict_n),
    'rail_open_half': sum(f['properties']['rail'] == 'open' for f in cf),
    'rail_building_half': sum(f['properties']['rail'] == 'building' for f in cf),
    'city_towers_in_half': sum(cu_h.contains(t['pt']) for t in ct), 'city_towers': len(ct),
    'half_share_of_city_land': round(cu_h.intersection(city_m).area / city_m.area * 100, 1),
    'city_towers_in_quarter': sum(cu_q.contains(t['pt']) for t in ct),
    'quarter_share_of_city_land': round(cu_q.intersection(city_m).area / city_m.area * 100, 1),
    'all_towers_in_half': sum(cu_h.contains(t['pt']) for t in towers),
    'downtown4_towers': sum(core4.contains(t['pt']) for t in towers),
    'new_towers_in_half': sum(cu_h.contains(t['pt']) for t in new_t), 'new_towers': len(new_t),
})
json.dump(stats, open(DAY + 'data/stats.json', 'w'), indent=1)
changed = [(f['properties']['name'], f['properties']['oc_at_street_core'], f['properties']['oc']) for f in cf if f['properties']['oc'] != f['properties']['oc_at_street_core']]
print('outcomes', dict(oc_n), '| quarter mile', dict(strict_n))
print('changed class at the plan position:', changed)
