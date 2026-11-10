"""Does living near a freeway go with commuting by transit less? A test across Los Angeles County's block groups.

  exposure   share of a block group's homes (Assessor 'Units', 2026 roll, parcel centroids) within 500 ft (152.4 m) of a
             freeway centreline (Caltrans D7 LRS, F_System 1-2, state highways) -- the same band as story_stats.py
  outcome    workers 16+ commuting by public transportation (excl. taxicab), ACS 2020-2024 5-year, B08301 E010 / E001
  controls   median household income (B19013), homes per km2 of land, homes within 800 m of a Metro rail station,
             Metro bus stops per km2 (bus GTFS 2026), distance to Downtown (Pershing Square)
  units      2020 block groups (TIGER cartographic boundaries, cb_2024_06_bg_500k), County 037; kept if 200+ workers,
             100+ homes on the roll and a published median income
  models     Spearman (raw); OLS on transit share with cluster-robust errors by census tract, raw and controlled;
             the same comparison within income quintiles (freeway-side block groups, 25%+ of homes within 500 ft,
             against those with none)
-> data/story_stats.json ['fwy_transit'] and a printed summary
"""
import csv, json, os, math
import numpy as np
import shapefile
import shapely
from shapely.geometry import shape
from shapely.ops import unary_union, transform
from pyproj import Transformer
from scipy.stats import spearmanr
import statsmodels.api as sm

S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
tf = Transformer.from_crs(4326, 3310, always_xy=True)

# freeway band, as in story_stats.py
fw = [f for f in json.load(open(S + 'raw/fwy_d7.geojson'))['features']
      if f['properties']['RouteID'].startswith('SHS_') and f['properties']['F_System'] in (1, 2)]
band = transform(g2m, unary_union([shape(f['geometry']) for f in fw])).buffer(152.4)
shapely.prepare(band)

# homes
lon, lat, units = [], [], []
with open(S + 'raw2/roll2026_county.csv') as f:
    for a in csv.DictReader(f):
        try:
            la, lo, u = float(a['CENTER_LAT']), float(a['CENTER_LON']), int(float(a['Units'] or 0))
        except ValueError:
            continue
        if u > 0 and la and lo: lon.append(lo); lat.append(la); units.append(u)
units = np.array(units, float)
X, Y = tf.transform(np.array(lon), np.array(lat))
pts = shapely.points(X, Y)
near = shapely.contains_xy(band, X, Y)

# rail stations (open) and bus stops
st = [f['geometry']['coordinates'] for f in json.load(open(DAY + 'data/stations.geojson'))['features'] if f['properties']['k'] == 'open']
sx, sy = tf.transform(*np.array(st).T)
rail = unary_union(shapely.points(sx, sy).tolist()).buffer(800); shapely.prepare(rail)
near_rail = shapely.contains_xy(rail, X, Y)
bs = []
with open(S + 'raw3/bus/stops.txt') as f:
    for a in csv.DictReader(f): bs.append((float(a['stop_lon']), float(a['stop_lat'])))
bx, by = tf.transform(*np.array(bs).T)
DTX, DTY = tf.transform(-118.2527, 34.0484)

# block groups
sf = shapefile.Reader(S + 'raw4/bg/cb_2024_06_bg_500k')
flds = [f[0] for f in sf.fields[1:]]
geoms, ids, aland = [], [], []
for sr in sf.iterShapeRecords():
    r = dict(zip(flds, sr.record))
    if r['COUNTYFP'] != '037': continue
    g = transform(g2m, shape(sr.shape.__geo_interface__))
    geoms.append(g); ids.append(r['GEOID']); aland.append(r['ALAND'] / 1e6)
tree = shapely.STRtree(geoms)
pi, gi = tree.query(pts, predicate='within')
hom = np.bincount(gi, weights=units[pi], minlength=len(geoms))
hnear = np.bincount(gi, weights=(units * near)[pi], minlength=len(geoms))
hrail = np.bincount(gi, weights=(units * near_rail)[pi], minlength=len(geoms))
bi, bgi = tree.query(shapely.points(bx, by), predicate='within')
nbus = np.bincount(bgi, minlength=len(geoms))
cen = shapely.centroid(geoms)

def acs(table, cols):
    out = {}
    with open(S + f'raw4/acs/acsdt5y2024-{table}.dat') as f:
        rd = csv.reader(f, delimiter='|'); hdr = next(rd); ix = [hdr.index(c) for c in cols]
        for row in rd:
            if row[0].startswith('1500000US06037'):
                try: out[row[0][9:]] = [float(row[i]) for i in ix]
                except ValueError: pass
    return out
mode = acs('b08301', ['B08301_E001', 'B08301_E010', 'B08301_E003'])
inc = acs('b19013', ['B19013_E001'])

rows = []
for k, gid in enumerate(ids):
    if gid not in mode or gid not in inc or hom[k] < 100 or aland[k] <= 0: continue
    w, t, da = mode[gid]
    if w < 200 or inc[gid][0] <= 0: continue
    rows.append(dict(id=gid, tract=gid[:11], workers=w, transit=t / w * 100, drive_alone=da / w * 100, near=hnear[k] / hom[k] * 100,
                     income=inc[gid][0], density=hom[k] / aland[k], rail=hrail[k] / hom[k] * 100, bus=nbus[k] / aland[k],
                     dist=math.hypot(cen[k].x - DTX, cen[k].y - DTY) / 1000))
n = len(rows)
v = lambda k: np.array([r[k] for r in rows])
T, NR, INC, DEN = v('transit'), v('near'), v('income'), v('density')
rho, p = spearmanr(NR, T)
rho_da, _ = spearmanr(NR, v('drive_alone'))

def ols(cols, y=T):
    Xm = sm.add_constant(np.column_stack(cols))
    groups = np.unique(v('tract'), return_inverse=True)[1]
    return sm.OLS(y, Xm).fit(cov_type='cluster', cov_kwds={'groups': groups})
raw = ols([NR / 10])
ctrl = ols([NR / 10, np.log(INC), np.log(DEN), v('rail') / 10, np.log1p(v('bus')), v('dist')])
ctrl_da = ols([NR / 10, np.log(INC), np.log(DEN), v('rail') / 10, np.log1p(v('bus')), v('dist')], y=v('drive_alone'))
def coef(m, i=1): return dict(b=round(float(m.params[i]), 2), lo=round(float(m.conf_int()[i][0]), 2), hi=round(float(m.conf_int()[i][1]), 2), p=float(m.pvalues[i]))

# within income quintiles: freeway-side (25%+ of homes within 500 ft) vs none, worker-weighted transit share
q = np.quantile(INC, [0.2, 0.4, 0.6, 0.8]); qi = np.searchsorted(q, INC, side='right')
W, TR = v('workers'), T * v('workers') / 100
quint = []
for j in range(5):
    m = qi == j
    a, b = m & (NR >= 25), m & (NR == 0)
    quint.append(dict(q=j + 1, inc_lo=int(INC[m].min()), inc_hi=int(INC[m].max()),
                      near_n=int(a.sum()), near_pct=round(float(TR[a].sum() / W[a].sum() * 100), 1) if a.any() else None,
                      none_n=int(b.sum()), none_pct=round(float(TR[b].sum() / W[b].sum() * 100), 1) if b.any() else None))
res = {'n_block_groups': n, 'spearman_near_transit': round(float(rho), 3), 'spearman_p': float(p), 'spearman_near_drive_alone': round(float(rho_da), 3),
       'ols_raw_per10pts': coef(raw), 'ols_controlled_per10pts': coef(ctrl), 'ols_controlled_drive_alone_per10pts': coef(ctrl_da),
       'r2_raw': round(float(raw.rsquared), 3), 'r2_controlled': round(float(ctrl.rsquared), 3),
       'controls': ['log median household income', 'log homes per km2', 'share of homes within 800 m of a rail station', 'log(1 + bus stops per km2)', 'km to Downtown'],
       'control_coefs': {nm: coef(ctrl, i + 2) for i, nm in enumerate(['log_income', 'log_density', 'rail_per10pts', 'log_bus', 'km_downtown'])},
       'by_income_quintile': quint,
       'src': 'Block groups (2020): ACS 2020-2024 B08301, B19013; homes and the 500 ft band as in the 500 ft ranking; Metro rail stations and bus stops (GTFS 2026). Cluster-robust errors by tract.'}
print(json.dumps(res, indent=1))
st_ = json.load(open(DAY + 'data/story_stats.json'))
st_['fwy_transit'] = res
json.dump(st_, open(DAY + 'data/story_stats.json', 'w'), indent=1)
