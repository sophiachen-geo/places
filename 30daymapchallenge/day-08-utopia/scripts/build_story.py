"""Data for the Day 8 story page:
  img/morph_grid.png   ~100 m Web-Mercator cells; R = median year built (minus 1850) of the parcels' main buildings
                       on the 2026 Assessor roll (county-wide), G = parcel count (capped 255), A = occupied
  data/morph.json      grid bounds + histogram by year + cumulative shares
  data/story_places.geojson  places named in the essay (official boundaries / Caltrans geometry)
"""
import csv, json, math, collections, os
import numpy as np
from PIL import Image
from shapely.geometry import shape, mapping, Point, LineString, MultiLineString, box
from shapely.ops import unary_union, linemerge, transform
from pyproj import Transformer

S = ''   # run from the working directory that holds raw/, raw2/, orig/, projgrids/
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
g2w = Transformer.from_crs(4326, 3857, always_xy=True).transform
w2g = Transformer.from_crs(3857, 4326, always_xy=True).transform
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
Y0, Y1 = 1850, 2026

# ---------------- morphogenesis grid ----------------
lon, lat, yr, city = [], [], [], []
with open(S + 'raw2/roll2026_county.csv') as f:
    for a in csv.DictReader(f):
        try:
            y = int(float(a['YearBuilt'] or 0)); la = float(a['CENTER_LAT']); lo = float(a['CENTER_LON'])
        except ValueError:
            continue
        if not (Y0 < y <= Y1) or not (33.0 < la < 35.0 and -119.0 < lo < -117.5):
            continue
        lon.append(lo); lat.append(la); yr.append(y); city.append(a['TaxRateArea_CITY'] == 'LOS ANGELES')
lon = np.array(lon); lat = np.array(lat); yr = np.array(yr, np.int16); city = np.array(city)
x, y = g2w(lon, lat)
CS = 120.0
x0, y0 = math.floor(x.min() / CS) * CS, math.floor(y.min() / CS) * CS
x1, y1 = math.ceil(x.max() / CS) * CS, math.ceil(y.max() / CS) * CS
nx, ny = int((x1 - x0) / CS), int((y1 - y0) / CS)
cx = ((x - x0) // CS).astype(np.int64); cy = ((y1 - y) // CS).astype(np.int64)
cell = cy * nx + cx
order = np.lexsort((yr, cell)); cs, ys = cell[order], yr[order]
starts = np.r_[0, np.nonzero(np.diff(cs))[0] + 1]; ends = np.r_[starts[1:], len(cs)]
med = ys[(starts + ends - 1) // 2]
cnt = ends - starts
R = np.zeros(nx * ny, np.uint8); Gc = np.zeros(nx * ny, np.uint8); Al = np.zeros(nx * ny, np.uint8)
R[cs[starts]] = (med - Y0).astype(np.uint8); Gc[cs[starts]] = np.minimum(cnt, 255); Al[cs[starts]] = 255
img = np.dstack([R.reshape(ny, nx), Gc.reshape(ny, nx), np.zeros((ny, nx), np.uint8), Al.reshape(ny, nx)])
Image.fromarray(img, 'RGBA').save(DAY + 'img/morph_grid.png', optimize=True)
sw = w2g(x0, y0); ne = w2g(x1, y1)
hist = collections.Counter(yr.tolist()); hist_city = collections.Counter(yr[city].tolist())
N = len(yr)
def share_by(year, mask=None):
    v = yr if mask is None else yr[mask]
    return round(float((v <= year).mean() * 100), 1)
morph = {
    'source': 'LA County Assessor roll 2026 (county-wide): year the main building on each parcel was built',
    'bounds': [[round(sw[1], 6), round(sw[0], 6)], [round(ne[1], 6), round(ne[0], 6)]], 'size': [nx, ny], 'cell_m_webmerc': CS,
    'year0': Y0, 'parcels': int(N), 'cells': int(len(starts)),
    'hist': {str(k): hist[k] for k in sorted(hist)}, 'hist_city': {str(k): hist_city[k] for k in sorted(hist_city)},
    'standing_by': {str(yy): share_by(yy) for yy in (1904, 1914, 1930, 1939, 1946, 1962, 1971, 1974, 1990, 2000)},
    'built_1946_1971_pct': round(float(((yr >= 1946) & (yr <= 1971)).mean() * 100), 1),
    'built_since_1974_pct': round(float((yr > 1974).mean() * 100), 1),
    'median_year': int(np.median(yr)),
}
print('grid', nx, ny, 'cells', len(starts), 'parcels', N, os.path.getsize(DAY + 'img/morph_grid.png') // 1024, 'KB')

# ---------------- places named in the essay ----------------
def feat(geom, props, nd=5):
    g = mapping(geom)
    def r(o):
        if isinstance(o, float): return round(o, nd)
        if isinstance(o, (list, tuple)): return [r(v) for v in o]
        return o
    g['coordinates'] = r(g['coordinates'])
    return {'type': 'Feature', 'geometry': g, 'properties': props}
places = []
hp = {f['properties']['NAME']: shape(f['geometry']) for f in json.load(open(S + 'raw2/hpoz.geojson'))['features']}
cpa = {f['properties']['NAME_ALF']: shape(f['geometry']) for f in json.load(open(S + 'raw2/cpa.geojson'))['features']}
apc = {f['properties']['APC']: shape(f['geometry']) for f in json.load(open(S + 'raw2/apc.geojson'))['features']}
cc = json.load(open(S + 'raw2/city_comm.geojson'))['features']
pas = [shape(f['geometry']) for f in cc if any(isinstance(v, str) and v.strip().lower() in ('pasadena', 'city of pasadena') for v in f['properties'].values())]
valley = unary_union([apc['North Valley APC'], apc['South Valley APC']])
P = [('hancock', 'Hancock Park', 'pastoral', hp['Hancock Park'], 'Hancock Park HPOZ (City of LA)'),
     ('windsor', 'Windsor Square', 'pastoral', hp['Windsor Square'], 'Windsor Square HPOZ (City of LA)'),
     ('valley', 'San Fernando Valley', 'pastoral', valley, 'City of LA North + South Valley Area Planning Commissions'),
     ('hollywood', 'Hollywood', 'pastoral', cpa['Hollywood'], 'Hollywood Community Plan Area'),
     ('boyle', 'Boyle Heights', 'autopia', cpa['Boyle Heights'], 'Boyle Heights Community Plan Area')]
if pas: P.append(('pasadena', 'Pasadena', 'pastoral', unary_union(pas), 'City of Pasadena (County boundary layer)'))
else: print('Pasadena not found')
# year-built profile inside each polygon
from shapely import contains_xy
for pid, name, ch, g, src in P:
    m = contains_xy(g, lon, lat)
    v = yr[m]
    prof = {'parcels': int(m.sum()), 'median_year': int(np.median(v)) if len(v) else None,
            'pre1930_pct': round(float((v < 1930).mean() * 100), 1) if len(v) else None,
            'b1946_1970_pct': round(float(((v >= 1946) & (v <= 1970)).mean() * 100), 1) if len(v) else None}
    places.append(feat(g.simplify(0.00005), {'id': pid, 'name': name, 'ch': ch, 'src': src, **prof}))
    print(pid, prof)
# Caltrans geometry: interchanges & named freeways
fw = json.load(open(S + 'raw/fwy_d7.geojson'))['features']
def route(num):
    return unary_union([shape(f['geometry']) for f in fw if f['properties']['RouteID'] in (f'SHS_{num:03d}._P', f'SHS_{num:03d}._S')])
R10, R5, R101, R110, R405 = route(10), route(5), route(101), route(110), route(405)
def junction(a, b, near):
    ix = a.intersection(b)
    pts = [p for p in getattr(ix, 'geoms', [ix]) if p.geom_type == 'Point']
    if not pts:   # grade-separated lines may not share a vertex: closest approach
        from shapely.ops import nearest_points
        pa, pb = nearest_points(a.intersection(Point(near).buffer(0.03)), b.intersection(Point(near).buffer(0.03)))
        return Point((pa.x + pb.x) / 2, (pa.y + pb.y) / 2)
    return min(pts, key=lambda p: p.distance(Point(near)))
four = junction(R101, R110, (-118.248, 34.061))
ela = junction(R5, R10, (-118.215, 34.030))
smsd = junction(R10, R405, (-118.43, 34.025))
places.append(feat(four, {'id': 'fourlevel', 'name': 'Four Level Interchange', 'ch': 'autopia', 'src': 'US-101 x SR-110, Caltrans LRS'}))
places.append(feat(ela, {'id': 'ela', 'name': 'East Los Angeles Interchange', 'ch': 'autopia', 'src': 'I-5 x I-10, Caltrans LRS'}))
places.append(feat(smsd, {'id': 'smsd', 'name': 'Santa Monica / San Diego freeways', 'ch': 'autopia', 'src': 'I-10 x I-405, Caltrans LRS'}))
smf = R10.intersection(box(-118.50, 33.98, ela.x + 0.002, 34.06))
places.append(feat(linemerge(smf).simplify(0.0001) if smf.geom_type != 'Point' else smf, {'id': 'smfwy', 'name': 'Santa Monica Freeway', 'ch': 'autopia', 'src': 'I-10, Santa Monica to the East LA Interchange (Caltrans LRS)'}))
saf = R5.intersection(cpa['Boyle Heights'].buffer(0.004))
places.append(feat(linemerge(saf).simplify(0.0001), {'id': 'santaana', 'name': 'Santa Ana Freeway', 'ch': 'autopia', 'src': 'I-5 through Boyle Heights (Caltrans LRS)'}))
with open(DAY + 'data/story_places.geojson', 'w') as f:
    json.dump({'type': 'FeatureCollection', 'features': places}, f, separators=(',', ':'))
json.dump(morph, open(DAY + 'data/morph.json', 'w'), separators=(',', ':'))
print(json.dumps({k: v for k, v in morph.items() if k not in ('hist', 'hist_city')}, indent=1))
print('four', four, 'ela', ela, 'smsd', smsd)
