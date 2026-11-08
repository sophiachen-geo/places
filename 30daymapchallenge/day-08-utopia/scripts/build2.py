"""Day 8 · Utopia — rebuild on the most recent authoritative sources (Nov 2026).

Sources (vintage):
  centers       1974 Concept LA diagram (adopted 3 Apr 1974); cores = County CAMS street centerlines (live, Nov 2026)
  heights       LARIAC6 building outlines, flown 2020 (County)  +  LADBS Certificates of Occupancy 2020-Nov 2026 (City)
  rail          LA Metro GTFS rail (7 Nov 2026); Metro under-construction/planned stations (Metro GIS, Jun 2026);
                Metro busway stations (Metro GIS, Jun 2023)
  zoning        City of LA zoning (live, edited 5 Nov 2026)
  built form    LA County Assessor roll 2026 (805,901 City parcels)
  HOLC          Mapping Inequality v3 (Univ. of Richmond DSL; Source Cooperative mirror, Jul 2026)
  traffic       Caltrans AADT 2024 (count points); Caltrans D7 Mobility Performance Report (pub. 2025):
                top-20 bottlenecks calendar-year 2024 + top-10 2025 Q2, located on Caltrans tenth-mile postmiles
  sites         LA City Historic-Cultural Monuments (Nov 2026); Assessor parcels (2025); CHL No. 933
"""
import json, csv, math, collections, os, sys
import numpy as np
from shapely.geometry import shape, mapping, Point, LineString, MultiLineString, Polygon
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from shapely import wkb
from pyproj import Transformer
import pyarrow.parquet as pq

S = ''
R1, R2 = S + 'raw/', S + 'raw2/'
OUT = sys.argv[1]
to3310 = Transformer.from_crs(4326, 3310, always_xy=True).transform
P = lambda g: transform(to3310, g)
QUARTER, HALF = 402.3, 804.7   # ¼ mile (the plan's own core radius) and ½ mile (standard transit walkshed)


def rnd(o, nd=6):
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, (list, tuple)): return [rnd(x, nd) for x in o]
    return o


def feat(geom, props, nd=6):
    g = mapping(geom); g['coordinates'] = rnd(g['coordinates'], nd)
    return {'type': 'Feature', 'geometry': g, 'properties': props}


def write(name, feats):
    with open(os.path.join(OUT, name), 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': feats}, f, separators=(',', ':'), ensure_ascii=False)
    print(f'{name:24s} {len(feats):6d} {os.path.getsize(os.path.join(OUT, name))/1024:8.1f} KB')


stats = {'built': '2026-11-08'}
city = unary_union([shape(f['geometry']) for f in json.load(open(R1 + 'city.geojson'))['features']]).buffer(0)
city_m = P(city)

# ============================================================ HEIGHTS
tb = json.load(open(R1 + 'tall2020.geojson'))
parts = [(P(shape(f['geometry'])).centroid, f['properties']['HEIGHT']) for f in tb['features']]
used = [False] * len(parts); towers = []
for i, (c, h) in enumerate(parts):
    if used[i]: continue
    grp = [i]; used[i] = True
    for j in range(i + 1, len(parts)):
        if not used[j] and c.distance(parts[j][0]) < 35:
            grp.append(j); used[j] = True
    k = max(grp, key=lambda q: parts[q][1])
    towers.append({'pt': parts[k][0], 'h': round(max(parts[q][1] for q in grp)), 'src': 'LARIAC 2020'})
n_lariac = len(towers)
# LADBS certificates of occupancy, new buildings >= 12 storeys, completed 2020-01-01 .. today
roll_pt = {}
with open(R2 + 'roll2026_city.csv') as f:
    for a in csv.DictReader(f):
        try: roll_pt[a['AIN']] = (float(a['CENTER_LON']), float(a['CENTER_LAT']))
        except ValueError: pass
permit_h = {}
for r in json.load(open(R2 + 'ladbs_new.json')):
    try: permit_h[r['permit_nbr']] = float(r['height'])
    except (TypeError, ValueError, KeyError): pass
# CofO records without coordinates whose original AIN was re-mapped after construction
FALLBACK = {
    '16010-10000-04211': (-118.372392, 34.028307),      # 3311 S La Cienega: County CAMS address point (AIN 4205033017)
    '17010-10000-03046': (-118.25888287, 34.0406262),   # 230 W Olympic: LADBS permit record coordinates
    '18010-10000-05907': (-118.23217638, 34.04088425),  # 525 S Santa Fe: Assessor 2026 parcels 5164-003-022..027 (built 2024)
}
added = []
seen = set()
for r in json.load(open(R2 + 'cofo_tall.json')):
    if not (r.get('permit_type') or '').startswith('Bldg-New'): continue
    if r.get('permit_sub_type') not in ('Apartment', 'Commercial'): continue
    st = float(r.get('of_stories') or 0); fa = float(r.get('floor_area_l_a_building_code_definition') or 0)
    if st < 12 or fa < 100000 or r['cofo_issue_date'] < '2020-01-01': continue
    if r['pcis_permit'] in seen: continue
    seen.add(r['pcis_permit'])
    ll = r.get('latitude_longitude')
    if isinstance(ll, dict) and ll.get('latitude'):
        lon, lat = float(ll['longitude']), float(ll['latitude'])
    else:
        ain = f"{r.get('assessor_book','')}{r.get('assessor_page','')}{r.get('assessor_parcel','')}"
        if ain in roll_pt:
            lon, lat = roll_pt[ain]
        elif r['pcis_permit'] in FALLBACK:
            lon, lat = FALLBACK[r['pcis_permit']]
        else:
            print('no location', r.get('address_start'), r.get('street_name')); continue
    pt = P(Point(lon, lat))
    addr = ' '.join(filter(None, [r.get('address_start'), r.get('street_direction'), r.get('street_name'), r.get('street_suffix')]))
    h = permit_h.get(r['pcis_permit'])
    dup = any(t['pt'].distance(pt) < 40 for t in towers)
    added.append({'pt': pt, 'h': round(h) if h and 120 < h < 1200 else None, 'st': int(st), 'addr': addr.title(),
                  'cofo': r['cofo_issue_date'][:10], 'src': 'LADBS CofO', 'dup': dup})
new_t = [t for t in added if not t['dup']]
towers += new_t
to4326 = Transformer.from_crs(3310, 4326, always_xy=True).transform
tf = []
for t in towers:
    pr = {'h': t['h'], 'src': t['src']}
    if t['src'] == 'LADBS CofO':
        pr.update({'st': t['st'], 'addr': t['addr'], 'cofo': t['cofo']})
    tf.append(feat(transform(to4326, t['pt']), pr))
write('towers.geojson', tf)
stats['towers'] = {'lariac2020_ge150ft': n_lariac, 'cofo_2020_2026_ge12st': len(added), 'cofo_new_not_in_lariac': len(new_t),
                   'total': len(towers), 'in_city': sum(1 for t in towers if city_m.contains(t['pt']))}

# ============================================================ RAIL
stops = list(csv.DictReader(open(R2 + 'gtfs_stops.txt', encoding='utf-8-sig')))
stations = {r['stop_name'].replace(' Station', ''): (float(r['stop_lon']), float(r['stop_lat'])) for r in stops if r['location_type'] == '1'}
routes = {r['route_id']: r for r in csv.DictReader(open(R2 + 'gtfs_routes.txt', encoding='utf-8-sig'))}
shape_route = {t['shape_id']: t['route_id'] for t in csv.DictReader(open(R2 + 'gtfs_trips.txt', encoding='utf-8-sig'))}
shp = collections.defaultdict(list)
for r in csv.DictReader(open(R2 + 'gtfs_shapes.txt', encoding='utf-8-sig')):
    shp[r['shape_id']].append((int(r['shape_pt_sequence']), float(r['shape_pt_lon']), float(r['shape_pt_lat'])))
best = {}
for sid, q in shp.items():
    rid = shape_route.get(sid)
    if not rid: continue
    ln = LineString([(x, y) for _, x, y in sorted(q)])
    if rid not in best or P(ln).length > P(best[rid]).length: best[rid] = ln
write('rail.geojson', [feat(ln.simplify(0.00003), {'line': routes[r]['route_long_name'].replace('Metro ', ''), 'color': '#' + routes[r]['route_color']}, 5) for r, ln in best.items()])
upc = json.load(open(R2 + 'metro_uc_planned.geojson'))['features']
ESFV_NOTE = 'East San Fernando Valley LRT — groundbreaking 19 Oct 2026, opening ~2031'
future = []
for f in upc:
    p = f['properties']; line = p.get('LINE2') or ''; status = p.get('Status') or ''
    if status == 'Existing' or 'BRT' in line: continue
    if line.startswith('East San Fernando Valley'): status, line = 'Under Construction', ESFV_NOTE
    future.append((p['STOPNAME'], tuple(f['geometry']['coordinates']), status, line))
busway = [(f['properties']['STOPNAME'], (f['properties']['LONG'], f['properties']['LAT']), f['properties']['LINE'])
          for f in json.load(open(R2 + 'metro_busway.geojson'))['features']
          if f['properties']['LINE'] == 901 or (f['properties']['LINE'] == 910 and any(k in f['properties']['STOPNAME'] for k in ('Transitway', 'Busway', 'Station')))]   # J Line: dedicated busway stations only
busway = list({(n, xy): (n, xy, l) for n, xy, l in busway}.values())
sf = [feat(Point(xy), {'name': n, 'k': 'open'}) for n, xy in stations.items()]
sf += [feat(Point(xy), {'name': n, 'k': 'uc' if s == 'Under Construction' else 'plan', 'line': l}) for n, xy, s, l in future]
sf += [feat(Point(xy), {'name': n, 'k': 'bus', 'line': 'G Line' if l == 901 else 'J Line'}) for n, xy, l in busway]
write('stations.geojson', sf)
st_open = [(n, P(Point(xy))) for n, xy in stations.items()]
st_uc = [(n, P(Point(xy)), l) for n, xy, s, l in future if s == 'Under Construction']
st_bus = [(n, P(Point(xy)), l) for n, xy, l in busway]

# ============================================================ CENTERS
cores = json.load(open(S + 'work/centers_exact.json'))['centers']
drawn = {c['name']: c for c in json.load(open(S + 'work/centers_final.json'))['centers']}
cf = []; oc_n = collections.Counter(); strict_n = collections.Counter()
for c in cores:
    p = P(Point(c['lng'], c['lat']))
    tw_h = [t for t in towers if t['pt'].distance(p) <= HALF]
    tw_q = [t for t in towers if t['pt'].distance(p) <= QUARTER]
    d_open, n_open = min((s.distance(p), n) for n, s in st_open)
    uc = min(((s.distance(p), n, l) for n, s, l in st_uc), default=(1e9, '', ''))
    bus = min(((s.distance(p), n, l) for n, s, l in st_bus), default=(1e9, '', ''))
    rail = 'open' if d_open <= HALF else ('building' if uc[0] <= HALF else 'none')

    def cls(ntw, near):
        return 'realised' if ntw >= 5 and near else ('towers' if ntw >= 5 else ('rail' if near else 'neither'))
    oc = cls(len(tw_h), d_open <= HALF); strict = cls(len(tw_q), d_open <= QUARTER)
    oc_n[oc] += 1; strict_n[strict] += 1
    hs = [t['h'] for t in tw_h if t['h']]
    cf.append(feat(Point(c['lng'], c['lat']), {
        'name': c['name'], 'core': c['core'], 'in_city': bool(city_m.contains(p)),
        'tw': len(tw_h), 'twq': len(tw_q), 'twnew': sum(1 for t in tw_h if t['src'] == 'LADBS CofO'), 'hmax': max(hs) if hs else 0,
        'near': n_open, 'near_m': int(round(d_open, -1)), 'rail': rail,
        'uc': f"{uc[1]} ({uc[2]})" if rail == 'building' else '', 'bus': f"{bus[1]} ({bus[2]})" if bus[0] <= HALF else '',
        'oc': oc, 'strict': strict, 'drawn': [round(drawn[c['name']]['dlng'], 6), round(drawn[c['name']]['dlat'], 6)],
        'off': c['off_m']}))
write('centers.geojson', cf)
cu_h = unary_union([P(Point(f['geometry']['coordinates'])).buffer(HALF) for f in cf])
cu_q = unary_union([P(Point(f['geometry']['coordinates'])).buffer(QUARTER) for f in cf])
ct = [t for t in towers if city_m.contains(t['pt'])]
core4 = unary_union([P(Point(f['geometry']['coordinates'])).buffer(HALF) for f in cf if f['properties']['name'] in
                     ('Downtown', 'Bunker Hill (unlabelled circle)', 'Civic Center', 'Westlake (unlabelled circle)')])
stats['centers'] = {
    'n': len(cf), 'n_in_city': sum(f['properties']['in_city'] for f in cf),
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
}

# ============================================================ GARDEN SUBURB: zoning + 2026 roll + HOLC
z = json.load(open(R1 + 'zoning_3310.geojson'))
SFZ = {'Single Family Residential', 'Suburban'}; MFZ = {'Multiple Family Residential', 'Residential', 'Residential-Mixed'}
zg, zc = [], []
area = collections.Counter()
for f in z['features']:
    if not f['geometry']: continue
    g = shape(f['geometry']).buffer(0); zg.append(g); zc.append(f['properties']['CATEGORY']); area[f['properties']['CATEGORY']] += g.area
sfa = sum(v for k, v in area.items() if k in SFZ); mfa = sum(v for k, v in area.items() if k in MFZ)
ztree = STRtree(zg)
roll = collections.Counter(); runits = collections.Counter(); roll_pts = []
with open(R2 + 'roll2026_city.csv') as f:
    for a in csv.DictReader(f):
        ut = a['UseType']; code = a['UseCode'] or ''; u = int(float(a['Units'] or 0))
        k = ('adu' if u >= 2 else 'sfr') if ut == 'SFR' else ('cnd' if ut == 'CND' else ('ri24' if ut == 'R-I' and code[:2] in ('02', '03', '04') else ('ri5' if ut == 'R-I' else ut.lower())))
        roll[k] += 1; runits[k] += u
        try: roll_pts.append((float(a['CENTER_LON']), float(a['CENTER_LAT']), k, u))
        except ValueError: pass
res_parcels = roll['sfr'] + roll['adu'] + roll['cnd'] + roll['ri24'] + roll['ri5']
all_units = sum(runits.values())
stats['garden'] = {
    'zoning_edited': '2026-11-05', 'sf_share_of_residential_zoned_land': round(sfa / (sfa + mfa) * 100, 1),
    'sf_zoned_km2': round(sfa / 1e6, 1), 'mf_zoned_km2': round(mfa / 1e6, 1),
    'roll2026_parcels': sum(roll.values()), 'parcels_by_class': dict(roll), 'units_by_class': dict(runits),
    'sfr_share_of_residential_parcels': round((roll['sfr'] + roll['adu']) / res_parcels * 100, 1),
    'sfr_share_of_all_units': round((runits['sfr'] + runits['adu']) / all_units * 100, 1),
    'units_total': all_units, 'sfr_parcels_with_2plus_units': roll['adu'],
}
# HOLC (Mapping Inequality v3)
t = pq.read_table(R2 + 'holc/mappinginequality.parquet').to_pylist()
holc = [(wkb.loads(r['geom']).buffer(0), r['grade'], r['label']) for r in t if r['state'] == 'CA' and r['city'] == 'Los Angeles' and r['grade'] in ('A', 'B', 'C', 'D')]
write('holc.geojson', [feat(g.simplify(0.00003), {'grade': gr, 'id': lb}, 5) for g, gr, lb in holc])
ga = collections.Counter(); gsf = collections.Counter()
rp_tree_pts = [P(Point(lo, la)) for lo, la, k, u in roll_pts]
rp_tree = STRtree(rp_tree_pts)
gp = collections.Counter(); gps = collections.Counter(); gu = collections.Counter(); gus = collections.Counter()
for g, gr, lb in holc:
    gm = P(g).intersection(city_m)
    if gm.is_empty: continue
    for i in ztree.query(gm):
        it = zg[i].intersection(gm)
        if it.is_empty: continue
        ga[gr] += it.area
        if zc[i] in SFZ: gsf[gr] += it.area
    for i in rp_tree.query(gm, predicate='contains'):
        lo, la, k, u = roll_pts[i]
        if k in ('sfr', 'adu', 'cnd', 'ri24', 'ri5'):
            gp[gr] += 1; gu[gr] += u
            if k in ('sfr', 'adu'): gps[gr] += 1; gus[gr] += u
stats['holc'] = {g: {'zoned_sf_pct': round(gsf[g] / ga[g] * 100, 1), 'built_sfr_parcel_pct': round(gps[g] / gp[g] * 100, 1),
                     'sfr_units_pct': round(gus[g] / gu[g] * 100, 1), 'km2_in_city': round(ga[g] / 1e6, 1)} for g in 'ABCD' if ga[g]}

# ============================================================ AUTOPIA
fw = json.load(open(R1 + 'fwy_d7.geojson'))
lines = [shape(f['geometry']) for f in fw['features'] if f['properties'].get('County_label') == 'LOS ANGELES']
fwy = unary_union(lines)
write('freeways.geojson', [feat(MultiLineString([list(g.coords) for g in getattr(fwy.simplify(0.0002), 'geoms', [fwy.simplify(0.0002)])]), {}, 5)])
fwy_m = P(fwy)
af = []
for f in json.load(open(R1 + 'aadt_la.geojson'))['features']:
    p = f['properties']
    if not f['geometry']: continue
    vals = {}
    for k in ('BACK_AADT', 'AHEAD_AADT'):
        try: vals[k] = int(float(p[k]))
        except (TypeError, ValueError): pass
    if not vals: continue
    pt = shape(f['geometry'])
    if fwy_m.distance(P(pt)) > 120: continue
    af.append(feat(pt, {'v': max(vals.values()), 'b': vals.get('BACK_AADT'), 'a': vals.get('AHEAD_AADT'), 'rte': p['RTE'].lstrip('0'),
                        'pm': f"{p.get('PM_PFX') or ''}{p.get('PM')}", 'at': p['DESCRIPTION'].title()}, 6))
af.sort(key=lambda f: f['properties']['v'])
write('aadt.geojson', af)
top = max(af, key=lambda f: f['properties']['v'])['properties']
stats['aadt'] = {'year': 2024, 'points': len(af), 'max': top, 'ge_300k': sum(f['properties']['v'] >= 300000 for f in af)}

# bottlenecks: Caltrans D7 Mobility Performance Report, 2025 Q2 edition (pub. 2025) — tables transcribed verbatim
BN_2024 = [  # rank, fwy, name, shift, abs_pm, ca_pm, days, extent_mi, delay_veh_hrs
 (1, 'I110-N', 'Solano Ave', 'PM', 25.010, '25.08', 251, 3.70, 779806.4), (2, 'I405-S', 'Howard Hughes Pkwy', 'PM', 48.672, '24.9', 237, 4.68, 714598.7),
 (3, 'I405-S', 'Bel Air Cr', 'AM', 59.572, '35.8', 242, 5.34, 647772.0), (4, 'I110-N', 'Adams', 'AM', 20.530, '20.6', 251, 4.26, 616044.0),
 (5, 'I405-N', 'National', 'AM', 52.932, '29.16', 207, 5.10, 602088.2), (6, 'I5-N', 'Pasadena', 'PM', 136.633, '20', 251, 3.10, 572637.1),
 (7, 'I10-W', 'Robertson', 'AM', 5.655, 'R7.81', 251, 3.90, 554655.3), (8, 'I605-S', 'Florence', 'PM', 11.216, 'R9.164', 176, 6.33, 529271.8),
 (9, 'I110-S', 'Vernon', 'PM', 18.820, '18.89', 251, 3.30, 526862.0), (10, 'I5-S', 'Downey', 'PM', 130.910, '14.34', 222, 2.11, 505076.9),
 (11, 'US101-N', 'White Oak', 'PM', 21.699, '20.34', 192, 8.24, 457591.9), (12, 'I405-N', 'Stagg St', 'PM', 66.972, '43.2', 104, 7.91, 451764.1),
 (13, 'I10-E', 'Cattaraugus', 'PM', 6.205, 'R8.36', 251, 1.60, 427286.4), (14, 'I10-E', 'Los Angeles', 'PM', 13.625, '15.78', 251, 2.69, 388313.0),
 (15, 'I710-S', 'Atlantic 2', 'PM', 16.887, '21.88', 240, 2.75, 386864.0), (16, 'SR60-E', '57 SB to 60 WB', 'PM', 25.141, 'R25', 228, 4.26, 380857.1),
 (17, 'I10-E', 'Mountain', 'PM', 45.740, '47.24', 180, 4.15, 379438.0), (18, 'US101-N', 'Glendale', 'AM', 3.768, '2.42', 251, 2.83, 341044.3),
 (19, 'I105-E', 'Facade', 'PM', 14.400, 'R14.4', 251, 1.10, 339441.2), (20, 'I710-S', 'Atlantic 1', 'PM', 16.687, '21.68', 209, 7.30, 337864.4)]
Q2_2025 = {('I110-N', 'Solano Ave'): 1, ('SR60-E', 'Garfield'): 2, ('I405-N', 'North of 101'): 3, ('I110-N', 'Adams'): 4, ('I405-N', 'National'): 5,
           ('US101-S', 'Woodley'): 6, ('I605-S', 'Florence'): 7, ('I10-W', 'Robertson'): 8, ('I110-S', 'Vernon'): 9, ('US101-S', 'Whitsett Ave'): 10}
pm = collections.defaultdict(list)
for f in json.load(open(R2 + 'postmiles_la.geojson'))['features']:
    p = f['properties']
    pm[(int(p['Route']), p['Direction'])].append((float(p['Odometer']), tuple(f['geometry']['coordinates']), (p['PMPrefix'] or '').strip(), round(float(p['PM']), 3)))
for k in pm: pm[k] = sorted(set(pm[k]))
DIR = {'N': 'NB', 'S': 'SB', 'E': 'EB', 'W': 'WB'}
bf = []
for rank, fwy_, name, shift, absm, capm, days, ext, delay in BN_2024:
    route = int(''.join(ch for ch in fwy_.split('-')[0] if ch.isdigit())); d = DIR[fwy_[-1]]
    lo, hi = (absm - ext, absm) if d in ('NB', 'EB') else (absm, absm + ext)
    # head = the exact county postmile printed in the report (prefix + value); queue = odometer range, kept within
    # reach of the head (some routes repeat odometer values on separate alignments)
    pfx = ''.join(ch for ch in capm if ch.isalpha()); val = float(''.join(ch for ch in capm if ch.isdigit() or ch == '.'))
    cand = [q for q in pm[(route, d)] if q[2] == pfx] or pm[(route, d)]
    hq = min(cand, key=lambda q: abs(q[3] - val)); head = hq[1]
    hm = P(Point(head)); reach = ext * 1609.34 * 1.4 + 400
    seq = [xy for o, xy, _, _ in pm[(route, d)] if lo - 0.05 <= o <= hi + 0.05 and P(Point(xy)).distance(hm) <= reach]
    # keep only the contiguous run containing the head (e.g. I-710's queue would otherwise jump the unbuilt gap)
    runs, cur = [], [seq[0]]
    for a_, b_ in zip(seq, seq[1:]):
        if P(Point(a_)).distance(P(Point(b_))) > 600: runs.append(cur); cur = [b_]
        else: cur.append(b_)
    runs.append(cur)
    seq = min(runs, key=lambda r: min(P(Point(xy)).distance(hm) for xy in r))
    clipped = len(runs) > 1
    if len(seq) < 2: print('no postmiles for', fwy_, name); continue
    bf.append(feat(LineString(seq), {'rank': rank, 'fwy': fwy_, 'at': name, 'shift': shift, 'pm': capm, 'days': days, 'mi': ext,
                                      'delay': round(delay), 'q2_2025': Q2_2025.get((fwy_, name)), 'head': [round(head[0], 6), round(head[1], 6)], 'clipped': clipped}, 6))
write('bottlenecks.geojson', bf)
stats['bottlenecks'] = {'source': 'Caltrans D7 MPR, calendar 2024 top-20 + 2025 Q2 top-10', 'n': len(bf),
                        'delay_2024_top20_veh_hrs': round(sum(b[8] for b in BN_2024)), 'top': BN_2024[0][1:3],
                        'q2_2025_top': 'I110-N Solano Ave', 'loop_detectors_offline_q4_2024_pct': 77.7}

# ============================================================ SOCIAL SITES (authoritative footprints)
hcm = json.load(open(R2 + 'hcm.geojson'))['features']
def hcm_geom(num):
    gs = [shape(f['geometry']) for f in hcm if f['properties']['MNT_TYPE'] == 'LA' and f['properties']['MNT_NUM'] == num and f['geometry']]
    return unary_union(gs) if gs else None
dodger = unary_union([shape(f['geometry']) for f in json.load(open(R2 + 'chavez_parcels.geojson'))['features']
                      if f['properties']['AIN'] in ('5415018015', '5415018016', '5415018010')])
SITES = json.load(open(S + 'work2/sites_text.json'))
sitef = []
for s_ in SITES:
    g = {'hcm2': hcm_geom('2'), 'hcm174': hcm_geom('174'), 'hcm680': hcm_geom('680'), 'dodger': dodger, 'chl933': None}[s_['geomsrc']]
    pt = g.representative_point() if g is not None else Point(s_['lng'], s_['lat'])
    props = {k: v for k, v in s_.items() if k not in ('lng', 'lat')}
    sitef.append(feat(pt, props))
    if g is not None:
        sitef.append(feat(g.simplify(0.000005), {'id': s_['id'], 'shape': 1}))
write('utopias.geojson', sitef)
stats['dodger_site_acres'] = round(P(dodger).area / 4046.86, 1)

json.dump(stats, open(os.path.join(OUT, 'stats.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(stats, indent=1, ensure_ascii=False))
