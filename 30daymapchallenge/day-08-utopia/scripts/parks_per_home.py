"""Public park land per 1,000 homes, for the chapter on the pastoral metropolis -> data/story_stats.json ['parks'].

  parks   open-access land in the California Protected Areas Database (CPAD holdings, GreenInfo Network, current
          release; fetched to raw4/cpad_county.geojson), federal land (national forest / recreation area) excluded
  homes   housing units on the 2026 Assessor roll ('Units'), counted by parcel centroid
  places  the City of Los Angeles's 35 Community Plan Areas (raw2/cpa.geojson) with 5,000+ homes, plus the whole City
          and the whole County for reference
  income  median household income, American Community Survey 5-year 2020-2024 (the most recent release), from the Census
          Bureau's keyless table-based summary files (raw4/acs/acsdt5y2024-b19001.dat, -b19013.dat) and tract internal
          points (raw4/acs/gaz_tracts_06.txt, 2024 Gazetteer). For a plan area, its tracts (by internal point) are pooled
          and the median is interpolated from the 16 income brackets of table B19001; City and County use the published
          B19013 medians.

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
# --- income: ACS 2020-2024 ---
import csv as _csv
BR = [0, 10e3, 15e3, 20e3, 25e3, 30e3, 35e3, 40e3, 45e3, 50e3, 60e3, 75e3, 100e3, 125e3, 150e3, 200e3, None]
tr_hh = {}
with open(S + 'raw4/acs/acsdt5y2024-b19001.dat') as f:
    rd = _csv.reader(f, delimiter='|'); hdr = next(rd); ix = [hdr.index(f'B19001_E{i:03d}') for i in range(2, 18)]
    for row in rd:
        if row[0].startswith('1400000US06037'):
            tr_hh[row[0][9:]] = np.array([float(row[i] or 0) for i in ix])
pub = {}
with open(S + 'raw4/acs/acsdt5y2024-b19013.dat') as f:
    rd = _csv.reader(f, delimiter='|'); hdr = next(rd); k = hdr.index('B19013_E001')
    for row in rd:
        if row[0] in ('0500000US06037', '1600000US0644000'): pub[row[0]] = int(row[k])
tlon, tlat, tid = [], [], []
with open(S + 'raw4/acs/gaz_tracts_06.txt') as f:
    rd = _csv.reader(f, delimiter='\t'); hdr = [h.strip() for h in next(rd)]
    for row in rd:
        gid = row[hdr.index('GEOID')].strip()
        if gid in tr_hh: tid.append(gid); tlat.append(float(row[hdr.index('INTPTLAT')])); tlon.append(float(row[hdr.index('INTPTLONG')]))
tlon, tlat = np.array(tlon), np.array(tlat)
def median_income(g):
    m = contains_xy(g, tlon, tlat)
    if not m.any(): return None, 0
    c = sum(tr_hh[tid[i]] for i in np.nonzero(m)[0]); n = c.sum(); half = n / 2; cum = 0.0
    for j, cnt in enumerate(c):
        if cum + cnt >= half:
            if BR[j + 1] is None: return 200000, int(n)          # top bracket: $200,000 or more
            return int(round(BR[j] + (half - cum) / cnt * (BR[j + 1] - BR[j]), -2)), int(n)
        cum += cnt
la = []
for f in json.load(open(S + 'raw2/cpa.geojson'))['features']:
    g = shape(f['geometry']); r = measure(g)
    if r['homes'] >= 5000:
        mi, hh = median_income(g)
        la.append({'name': f['properties']['NAME_ALF'], **r, 'median_income': mi, 'households_acs': hh})
la.sort(key=lambda d: d['per_1000_homes'])
cityg = [shape(f['geometry']) for f in json.load(open(S + 'raw2/city_comm.geojson'))['features'] if f['properties']['CITY_COMM_NAME'] == 'LOS ANGELES'][0]
cnty = shape(json.load(open(S + 'raw2/county_boundary.geojson'))['features'][0]['geometry'])
st = json.load(open(DAY + 'data/story_stats.json'))
st['parks'] = {'la': la, 'city': {**measure(cityg), 'median_income': pub['1600000US0644000']},
               'county': {**measure(cnty), 'median_income': pub['0500000US06037']},
               'src': 'CPAD holdings (GreenInfo Network, current release), open-access land excluding federal; 2026 Assessor roll units',
               'income_src': 'U.S. Census Bureau, American Community Survey 5-year estimates 2020-2024, tables B19001 and B19013'}
json.dump(st, open(DAY + 'data/story_stats.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in st['parks'].items() if k != 'la'}))
for d in la: print(f"{d['per_1000_homes']:8.2f}  ${d['median_income']:>7,}  {d['name']}")
