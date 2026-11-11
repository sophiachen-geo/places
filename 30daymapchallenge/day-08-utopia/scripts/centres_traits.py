"""What the 56 centres of the 1974 Centers Concept had going for them: traits measured within half a mile (804.7 m) of
each centre as the 1974 map draws it (data/centers.geojson), compared across the four outcomes.

Run from the working directory that holds raw/, raw2/, raw4/ and gif/ (see README); DAY points at the day folder.
-> data/centres_traits.json (one record per centre + group summaries), printed tables

Traits (half-mile disc unless noted)
  km_downtown      straight-line km to Pershing Square
  fwy_m            metres to the nearest freeway centreline (Caltrans D7 LRS, F_System 1-2, state highways)
  fwy_pre74        a freeway segment that had opened by 1974 runs within the disc (opening years: gif/freeways_dated.json)
  tw_pre74 / tw_post74  buildings of 150 ft+ (data/towers.geojson) standing before 1974 / built 1974 or later. Year
                   built: the 2026 Assessor roll parcel nearest the tower (within 60 m, not a house or vacant lot; the
                   largest building there); LADBS certificate-of-occupancy towers are 2020-2026 by definition
  rail_year        opening year of the first Metro rail station within the disc (data/metro_lines.geojson) or None;
                   rail_by1995 = a station there by 1995
  jobs, homes      as on data/centers.geojson (LODES 2023 jobs; 2026 roll housing units)
  income           median household income, ACS 2020-2024 B19001, tracts with an internal point within 1 km pooled
                   (acs_income.py); 1.5 km where none
  ci_pre74         commercial and industrial parcels (roll UseType 'C/I') with a building from before 1974: count,
                   and share of all parcels built before 1974 -- the earliest available stand-in for "already a business
                   centre in 1974" (buildings since demolished are missing, so it undercounts the old stock)
  com_sqft_pre74   City of LA only: floor area of commercial buildings (use codes 1xxx-2xxx) built before 1974, in
                   thousands of sq ft (2026 roll SQFTmain)
  homes_pre74      housing units on parcels whose building predates 1974 (a lower bound on 1974 housing)
  zoned_com_pct    City of LA only: share of zoned land in a commercial category (CATEGORY Commercial, Commercial-Mixed)
                   on today's zoning map (2026), which itself reflects post-1974 plans
  in_city          inside the City of Los Angeles
"""
import csv, json, math, os, sys, collections, statistics as stt
import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import mannwhitneyu
from shapely.geometry import shape, Point
from shapely.ops import unary_union, transform
from shapely import STRtree
from pyproj import Transformer

S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acs_income as ai

tf = Transformer.from_crs(4326, 3310, always_xy=True)
g2m = tf.transform
HALF = 804.7
C = json.load(open(DAY + 'data/centers.geojson'))['features']
cx, cy = tf.transform(np.array([f['geometry']['coordinates'][0] for f in C]), np.array([f['geometry']['coordinates'][1] for f in C]))
DTX, DTY = tf.transform(-118.2527, 34.0484)

# ---- Assessor roll (county): parcels
lon, lat, units, yr, ut = [], [], [], [], []
with open(S + 'raw2/roll2026_county.csv') as f:
    for a in csv.DictReader(f):
        try: la, lo = float(a['CENTER_LAT']), float(a['CENTER_LON'])
        except ValueError: continue
        if not la: continue
        lon.append(lo); lat.append(la); units.append(float(a['Units'] or 0))
        try: yr.append(int(float(a['YearBuilt'] or 0)))
        except ValueError: yr.append(0)
        ut.append(a['UseType'])
X, Y = tf.transform(np.array(lon), np.array(lat))
units, yr, ut = np.array(units), np.array(yr), np.array(ut)
tree = cKDTree(np.c_[X, Y])
# City roll: floor area by use code
clon, clat, csq, cyr, cuc = [], [], [], [], []
with open(S + 'raw2/roll2026_city.csv') as f:
    for a in csv.DictReader(f):
        try: la, lo = float(a['CENTER_LAT']), float(a['CENTER_LON'])
        except ValueError: continue
        if not la: continue
        clon.append(lo); clat.append(la); csq.append(float(a['SQFTmain'] or 0))
        try: cyr.append(int(float(a['YearBuilt'] or 0)))
        except ValueError: cyr.append(0)
        cuc.append(a['UseCode'][:1])
CX_, CY_ = tf.transform(np.array(clon), np.array(clat))
csq, cyr, cuc = np.array(csq), np.array(cyr), np.array(cuc)
ctree = cKDTree(np.c_[CX_, CY_])

# ---- towers and their year built
T = json.load(open(DAY + 'data/towers.geojson'))['features']
tx, ty = tf.transform(np.array([f['geometry']['coordinates'][0] for f in T]), np.array([f['geometry']['coordinates'][1] for f in T]))
tyear, matched = [], 0
for i, f in enumerate(T):
    if f['properties'].get('src') == 'LADBS CofO': tyear.append(2022); matched += 1; continue
    idx = [j for j in tree.query_ball_point([tx[i], ty[i]], 60) if ut[j] not in ('SFR', 'VAC') and yr[j] > 1850]
    if not idx: tyear.append(None); continue
    # the biggest building on the nearest parcels: most units for housing, else the nearest commercial parcel
    idx.sort(key=lambda j: (-(units[j] if ut[j] in ('R-I', 'CND') else 0), math.hypot(X[j] - tx[i], Y[j] - ty[i])))
    tyear.append(int(yr[idx[0]])); matched += 1
tyear = np.array([y if y is not None else -1 for y in tyear])

# ---- freeways (all, and those open by 1974)
fw = [f for f in json.load(open(S + 'raw/fwy_d7.geojson'))['features']
      if f['properties']['RouteID'].startswith('SHS_') and f['properties']['F_System'] in (1, 2)]
fwy = transform(g2m, unary_union([shape(f['geometry']) for f in fw]))
fd = json.load(open(S + 'gif/freeways_dated.json'))
from shapely.geometry import MultiLineString
fwy74 = transform(g2m, MultiLineString([ln for d in fd if d['y0'] and d['y0'] <= 1974 for ln in d['lines']]))

# ---- rail stations with opening years
ST = [f for f in json.load(open(DAY + 'data/metro_lines.geojson'))['features'] if f['properties'].get('kind') == 'station']
sx, sy = tf.transform(np.array([f['geometry']['coordinates'][0] for f in ST]), np.array([f['geometry']['coordinates'][1] for f in ST]))
syear = np.array([f['properties']['year'] for f in ST])

# ---- City zoning (EPSG:3310)
Z = json.load(open(S + 'raw/zoning_3310.geojson'))['features']
zg = [shape(f['geometry']).buffer(0) for f in Z]; zcat = [f['properties']['CATEGORY'] for f in Z]   # buffer(0) repairs a few invalid outlines
ztree = STRtree(zg)
city = transform(g2m, [shape(f['geometry']) for f in json.load(open(S + 'raw2/city_comm.geojson'))['features'] if f['properties']['CITY_COMM_NAME'] == 'LOS ANGELES'][0])

to4326 = Transformer.from_crs(3310, 4326, always_xy=True).transform
recs = []
for k, f in enumerate(C):
    p = f['properties']; x, y = cx[k], cy[k]; pt = Point(x, y); disc = pt.buffer(HALF)
    idx = np.array(tree.query_ball_point([x, y], HALF), dtype=int)
    pre = idx[(yr[idx] > 1850) & (yr[idx] < 1974)]
    ci_pre = int((ut[pre] == 'C/I').sum())
    cidx = np.array(ctree.query_ball_point([x, y], HALF), dtype=int)
    in_city = bool(p['in_city'])                          # as on the page (the plan's disc centre inside the City)
    city_cover = len(cidx) / max(1, len(idx))             # share of the disc's parcels on the City roll
    com_sqft = round(float(csq[cidx][(np.isin(cuc[cidx], ['1', '2'])) & (cyr[cidx] > 1850) & (cyr[cidx] < 1974)].sum()) / 1000) if city_cover >= 0.7 else None
    d_t = np.hypot(tx - x, ty - y) <= HALF
    tw_pre = int((d_t & (tyear > 0) & (tyear < 1974)).sum()); tw_post = int((d_t & (tyear >= 1974)).sum()); tw_unk = int((d_t & (tyear < 0)).sum())
    d_s = np.hypot(sx - x, sy - y) <= HALF
    ry = int(syear[d_s].min()) if d_s.any() else None
    # income: tracts with an internal point within 1 km (1.5 km if none)
    inc = None
    for r_ in (1000, 1500, 2500):
        g = transform(to4326, pt.buffer(r_))
        inc = ai.pooled(g)
        if inc: break
    zarea = com = 0.0
    if city_cover >= 0.7:
        for j in ztree.query(disc):
            a = zg[j].intersection(disc).area
            zarea += a
            if zcat[j] in ('Commercial', 'Commercial-Mixed'): com += a
    recs.append({'name': p['name'], 'oc': p['oc'], 'nb': p.get('nb'), 'in_city': in_city,
                 'km_downtown': round(math.hypot(x - DTX, y - DTY) / 1000, 1),
                 'fwy_m': int(round(fwy.distance(pt), -1)), 'fwy_half': bool(fwy.distance(pt) <= HALF), 'fwy_pre74': bool(fwy74.distance(pt) <= HALF),
                 'tw': p['tw'], 'tw_pre74': tw_pre, 'tw_post74': tw_post, 'tw_unknown_year': tw_unk,
                 'rail_year': ry, 'rail_by1995': bool(ry and ry <= 1995),
                 'jobs': p['jobs'], 'homes': p['homes'], 'income': inc,
                 'ci_pre74': ci_pre, 'ci_pre74_share': round(ci_pre / max(1, len(pre)) * 100, 1),
                 'homes_pre74': int(units[pre].sum()), 'com_ksqft_pre74': com_sqft,
                 'zoned_com_pct': round(com / zarea * 100, 1) if city_cover >= 0.7 and zarea else None})

GROUPS = ['realised', 'towers', 'rail', 'neither']
NUM = ['km_downtown', 'fwy_m', 'tw_pre74', 'tw_post74', 'jobs', 'homes', 'income', 'ci_pre74', 'ci_pre74_share', 'homes_pre74', 'com_ksqft_pre74', 'zoned_com_pct']
BOOL = ['fwy_half', 'fwy_pre74', 'rail_by1995', 'in_city']
summ = {'n': {g: sum(r['oc'] == g for r in recs) for g in GROUPS}, 'median': {}, 'count_true': {}, 'realised_vs_neither': {}}
for t in NUM:
    summ['median'][t] = {}
    for g in GROUPS:
        v = [r[t] for r in recs if r['oc'] == g and r[t] is not None]
        summ['median'][t][g] = round(stt.median(v), 1) if v else None
    a = [r[t] for r in recs if r['oc'] == 'realised' and r[t] is not None]; b = [r[t] for r in recs if r['oc'] == 'neither' and r[t] is not None]
    if len(a) > 2 and len(b) > 2:
        u, pv = mannwhitneyu(a, b, alternative='two-sided')
        summ['realised_vs_neither'][t] = {'auc': round(u / (len(a) * len(b)), 2), 'p': round(float(pv), 4), 'n': [len(a), len(b)]}
# 'got towers' (realised+towers) vs not, and 'got rail' (realised+rail) vs not
for lab, pos in (('towers_any', ('realised', 'towers')), ('rail_any', ('realised', 'rail'))):
    summ[lab] = {}
    for t in NUM:
        a = [r[t] for r in recs if r['oc'] in pos and r[t] is not None]; b = [r[t] for r in recs if r['oc'] not in pos and r[t] is not None]
        if len(a) > 2 and len(b) > 2:
            u, pv = mannwhitneyu(a, b, alternative='two-sided')
            summ[lab][t] = {'auc': round(u / (len(a) * len(b)), 2), 'p': round(float(pv), 4), 'median_yes': round(stt.median(a), 1), 'median_no': round(stt.median(b), 1)}
for t in BOOL + ['tw_pre74_any']:
    summ['count_true'][t] = {g: (sum(1 for r in recs if r['oc'] == g and ((r['tw_pre74'] > 0) if t == 'tw_pre74_any' else r[t])), summ['n'][g]) for g in GROUPS}
summ['towers_matched'] = {'matched': matched, 'of': len(T)}
# one-question rule: did a building of 150 ft+ stand there before 1974?  -> did the centre get towers (5+ today)?
got = lambda r: r['oc'] in ('realised', 'towers')
summ['rule_pre74_tower'] = {'had_and_got': [r['name'] for r in recs if r['tw_pre74'] > 0 and got(r)], 'had_not_got': [r['name'] for r in recs if r['tw_pre74'] > 0 and not got(r)],
                            'none_but_got': [r['name'] for r in recs if r['tw_pre74'] == 0 and got(r)], 'none_none': sum(1 for r in recs if r['tw_pre74'] == 0 and not got(r))}
json.dump({'centres': recs, 'summary': summ,
           'method': __doc__.split('Traits')[1].strip(), 'src': 'Assessor roll 2026; Caltrans D7; LA Metro GTFS; ACS 2020-2024; City zoning 2026; LODES 2023'},
          open(DAY + 'data/centres_traits.json', 'w'), indent=1)
print('towers with a year:', matched, 'of', len(T)); print('rule', {k: (v if isinstance(v, int) else len(v), v) for k, v in summ['rule_pre74_tower'].items()})
print('n', summ['n'])
for t in NUM: print(f"{t:16s}", summ['median'][t], summ['realised_vs_neither'].get(t))
for t in summ['count_true']: print(t, summ['count_true'][t])
for lab in ('towers_any', 'rail_any'):
    print(lab, sorted(((v['auc'], t, v['p'], v['median_yes'], v['median_no']) for t, v in summ[lab].items()), key=lambda z: -abs(z[0] - 0.5))[:6])
