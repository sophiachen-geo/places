"""Where Los Angeles County's job centres are today, and which of the 1974 plan's centres they match.

Definition (Giuliano & Small, "Subcenters in the Los Angeles region", 1991): a contiguous area where employment density is
at least 10 jobs per acre and that holds at least 10,000 jobs in all.
  jobs     LEHD LODES8 Workplace Area Characteristics 2023, all jobs, by 2020 census block (internal points), LA County
  surface  jobs on a 200 m grid (EPSG:3310), smoothed with a 300 m Gaussian, density in jobs per acre
  centres  connected cells >= 10 jobs/acre whose unsmoothed jobs sum to >= 10,000, outlined and lightly smoothed
Each planned centre (data/centers.geojson, at the plan's own positions) is matched to the job centre containing it or
within 800 m of it. Writes data/today_centres.geojson, adds 'today_*' fields to data/centers.geojson, stats['today'].
"""
import csv, gzip, json, os, math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import shape, Point, mapping
from shapely.ops import unary_union, transform
from pyproj import Transformer
import rasterio.features
from affine import Affine

S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
m2g = Transformer.from_crs(3310, 4326, always_xy=True).transform
CELL, SIGMA, ACRE = 200.0, 300.0, 4046.86
pts = {}
with gzip.open("raw3/ca_xwalk.csv.gz", "rt") as f:
    r = csv.reader(f); h = next(r)
    ib, ic, ila, ilo = h.index("tabblk2020"), h.index("cty"), h.index("blklatdd"), h.index("blklondd")
    for row in r:
        if row[ic] == "06037": pts[row[ib]] = (float(row[ilo]), float(row[ila]))
wac = "raw3/ca_wac_S000_JT00_2023.csv.gz" if os.path.exists("raw3/ca_wac_S000_JT00_2023.csv.gz") else "raw3/ca_wac_2023.csv.gz"
lo, la, jn = [], [], []
with gzip.open(wac, "rt") as f:
    r = csv.reader(f); next(r)
    for row in r:
        p = pts.get(row[0])
        if p: lo.append(p[0]); la.append(p[1]); jn.append(int(row[1]))
x, y = g2m(np.array(lo), np.array(la)); jn = np.array(jn, float)
x0, y1 = x.min() - 5000, y.max() + 5000
nx, ny = int((x.max() + 5000 - x0) / CELL) + 1, int((y1 - (y.min() - 5000)) / CELL) + 1
ci, cj = ((x - x0) / CELL).astype(int), ((y1 - y) / CELL).astype(int)
J = np.zeros((ny, nx)); np.add.at(J, (cj, ci), jn)
dens = ndi.gaussian_filter(J, SIGMA / CELL) / (CELL * CELL / ACRE)      # jobs per acre
mask = dens >= 10
lab, n = ndi.label(mask, structure=np.ones((3, 3)))
tot = ndi.sum(J, lab, range(1, n + 1))
keep = [k + 1 for k in range(n) if tot[k] >= 10000]
tf = Affine(CELL, 0, x0, 0, -CELL, y1)
centres = []
for k in keep:
    polys = [shape(g) for g, v in rasterio.features.shapes(lab.astype(np.int32), mask=(lab == k), transform=tf) if v == k]
    g = unary_union(polys).buffer(120).buffer(-120).simplify(40)
    jj = J * (lab == k); yy, xx = np.nonzero(jj)
    w = jj[yy, xx]; cx, cy = x0 + (xx + 0.5) @ w / w.sum() * CELL, y1 - (yy + 0.5) @ w / w.sum() * CELL
    pk = np.unravel_index(np.argmax(dens * (lab == k)), dens.shape)
    centres.append({'k': int(k), 'geom': g, 'jobs': int(tot[k - 1]), 'km2': round(g.area / 1e6, 1),
                    'cx': float(cx), 'cy': float(cy), 'peak': float(dens[pk])})
centres.sort(key=lambda c: -c['jobs'])
C = json.load(open(DAY + 'data/centers.geojson'))
for c in centres: c['planned'] = []
for f in C['features']:
    p = Point(g2m(*f['geometry']['coordinates']))
    best = min(centres, key=lambda c: c['geom'].distance(p))
    d = best['geom'].distance(p)
    pr = f['properties']
    if d <= 800:
        best['planned'].append(pr['name'])
        pr.update({'today_id': best['k'], 'today_jobs': best['jobs'], 'today_km2': best['km2'],
                   'today_off_m': int(round(math.hypot(p.x - best['cx'], p.y - best['cy']), -1)), 'today_in': d == 0})
    else:
        pr.update({'today_id': None, 'today_jobs': 0, 'today_km2': 0, 'today_off_m': None, 'today_in': False, 'today_nearest_m': int(round(d, -1))})
json.dump(C, open(DAY + 'data/centers.geojson', 'w'), separators=(',', ':'))
# names for centres the plan never drew: the City plan area / city / community at the job-weighted centre
places = [(f['properties']['NAME_ALF'], transform(g2m, shape(f['geometry']))) for f in json.load(open(S + 'raw2/cpa.geojson'))['features']]
places += [(f['properties']['CITY_COMM_NAME'].title().replace(' - ', '–'), transform(g2m, shape(f['geometry'])))
           for f in json.load(open(S + 'raw2/city_comm.geojson'))['features'] if f.get('geometry') and f['properties']['CITY_COMM_NAME'] != 'LOS ANGELES']
def where(c):
    if 'Downtown' in c['planned'] and len(c['planned']) >= 5:
        return 'Regional core, Downtown to ' + ('Santa Monica' if 'Santa Monica' in c['planned'] else 'the Westside')
    p = Point(c['cx'], c['cy'])
    for nm, g in places:
        if g.contains(p): return nm.split(' - ')[0]
    return 'Los Angeles County'
def r(o):
    if isinstance(o, float): return round(o, 5)
    if isinstance(o, (list, tuple)): return [r(v) for v in o]
    return o
feats = []
for c in centres:
    gm = mapping(transform(m2g, c['geom'])); gm['coordinates'] = r(gm['coordinates'])
    feats.append({'type': 'Feature', 'geometry': gm, 'properties': {
        'id': c['k'], 'name': where(c), 'jobs': c['jobs'], 'km2': c['km2'], 'planned': c['planned'],
        'peak_jobs_per_acre': round(c['peak']), 'centre': [round(v, 5) for v in m2g(c['cx'], c['cy'])]}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(DAY + 'data/today_centres.geojson', 'w'), separators=(',', ':'))
stats = json.load(open(DAY + 'data/stats.json'))
matched = [f for f in C['features'] if f['properties']['today_id']]
stats['today'] = {'n': len(centres), 'jobs': int(sum(c['jobs'] for c in centres)), 'county_jobs': int(J.sum()),
                  'with_planned': sum(1 for c in centres if c['planned']), 'unplanned': [where(c) for c in centres if not c['planned']],
                  'unplanned_jobs': int(sum(c['jobs'] for c in centres if not c['planned'])),
                  'planned_matched': len(matched), 'planned_n': len(C['features']),
                  'def': 'Giuliano & Small (1991): contiguous area with at least 10 jobs per acre and 10,000 jobs in all; LODES 2023'}
json.dump(stats, open(DAY + 'data/stats.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in stats['today'].items() if k != 'def'}, indent=0))
for c in centres[:14]: print(f"{c['jobs']:8,} jobs {c['km2']:6.1f} km2  {where(c)}  planned: {c['planned']}")
print(os.path.getsize(DAY + 'data/today_centres.geojson') // 1024, 'KB')
