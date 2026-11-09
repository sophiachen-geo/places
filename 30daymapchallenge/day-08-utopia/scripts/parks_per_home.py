"""Public park land per 1,000 homes, for the chapter on the pastoral metropolis -> data/story_stats.json ['parks'].

  parks   open-access land in the California Protected Areas Database (CPAD holdings, GreenInfo Network, current
          release; fetched to raw4/cpad_county.geojson), federal land (national forest / recreation area) excluded
  homes   housing units on the 2026 Assessor roll ('Units'), counted by parcel centroid
  places  the City of Los Angeles's 35 Community Plan Areas (raw2/cpa.geojson) with 5,000+ homes, plus the whole City
          and the whole County for reference

Run after story_stats.py.
"""
import csv, json, os, warnings
import numpy as np
from shapely.geometry import shape
from shapely import STRtree, contains_xy, intersection, area, make_valid
from shapely.ops import transform
from pyproj import Transformer
warnings.filterwarnings('ignore')
S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
P = [(f['properties'], make_valid(transform(g2m, shape(f['geometry'])))) for f in json.load(open(S + 'raw4/cpad_county.geojson'))['features'] if f.get('geometry')]
geoms = np.array([g for _, g in P]); fed = np.array([p['AGNCY_LEV'] == 'Federal' for p, _ in P])
tree = STRtree(geoms)
lon, lat, units = [], [], []
with open(S + 'raw2/roll2026_county.csv') as f:
    for a in csv.DictReader(f):
        try: la = float(a['CENTER_LAT']); lo = float(a['CENTER_LON']); u = int(float(a['Units'] or 0))
        except ValueError: continue
        if u > 0: lon.append(lo); lat.append(la); units.append(u)
lon, lat, units = map(np.array, (lon, lat, units))
def measure(g):
    x0, y0, x1, y1 = g.bounds
    pre = (lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1)
    m = np.zeros_like(pre); m[pre] = contains_xy(g, lon[pre], lat[pre]); h = int(units[m].sum())
    gm = make_valid(transform(g2m, g)); idx = tree.query(gm, predicate='intersects')
    a = float((area(intersection(geoms[idx], gm)) / 4046.86)[~fed[idx]].sum())
    return {'homes': h, 'acres': round(a), 'per_1000_homes': round(a / h * 1000, 2) if h else None}
la = []
for f in json.load(open(S + 'raw2/cpa.geojson'))['features']:
    r = measure(shape(f['geometry']))
    if r['homes'] >= 5000: la.append({'name': f['properties']['NAME_ALF'], **r})
la.sort(key=lambda d: d['per_1000_homes'])
cityg = [shape(f['geometry']) for f in json.load(open(S + 'raw2/city_comm.geojson'))['features'] if f['properties']['CITY_COMM_NAME'] == 'LOS ANGELES'][0]
cnty = shape(json.load(open(S + 'raw2/county_boundary.geojson'))['features'][0]['geometry'])
st = json.load(open(DAY + 'data/story_stats.json'))
st['parks'] = {'la': la, 'city': measure(cityg), 'county': measure(cnty),
               'src': 'CPAD holdings (GreenInfo Network, current release), open-access land excluding federal; 2026 Assessor roll units'}
json.dump(st, open(DAY + 'data/story_stats.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in st['parks'].items() if k != 'la'}), [(d['name'], d['per_1000_homes']) for d in la[:6]], [(d['name'], d['per_1000_homes']) for d in la[-4:]])
