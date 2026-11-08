"""Build the Day 8 (Utopia) datasets for the LA utopia map.

Inputs  : raw downloads in ../raw (ArcGIS REST + Metro GTFS) and the georeferenced
          1974 Concept centers (centers_georef.json).
Outputs : compact GeoJSON + stats.json in the site folder.
All metric work is done in EPSG:3310 (California Albers, metres).
"""
import json, csv, math, collections, os, sys
from shapely.geometry import shape, mapping, Point, Polygon, LineString, MultiLineString
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from pyproj import Transformer

S = ''
RAW = S + 'raw/'
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

to3310 = Transformer.from_crs(4326, 3310, always_xy=True).transform
to4326 = Transformer.from_crs(3310, 4326, always_xy=True).transform
P = lambda g: transform(to3310, g)
G = lambda g: transform(to4326, g)


def rnd(o, nd=5):
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, (list, tuple)):
        return [rnd(x, nd) for x in o]
    if isinstance(o, dict):
        return {k: rnd(v, nd) for k, v in o.items()}
    return o


def write(name, feats):
    fc = {'type': 'FeatureCollection', 'features': feats}
    with open(os.path.join(OUT, name), 'w') as f:
        json.dump(fc, f, separators=(',', ':'))
    print(f'{name:22s} {len(feats):6d} feats {os.path.getsize(os.path.join(OUT, name))/1024:8.1f} KB')


def feat(geom, props):
    g = mapping(geom)
    g['coordinates'] = rnd(g['coordinates'])
    return {'type': 'Feature', 'geometry': g, 'properties': props}


stats = {}

# ---------------------------------------------------------------- city boundary
city_fc = json.load(open(RAW + 'city.geojson'))
city = unary_union([shape(f['geometry']) for f in city_fc['features']]).buffer(0)
city_m = P(city)
stats['city_area_km2'] = round(city_m.area / 1e6, 1)
write('city.geojson', [feat(city.simplify(0.0004), {'name': 'City of Los Angeles'})])

# ---------------------------------------------------------------- zoning -> single-family hexes
z = json.load(open(RAW + 'zoning_3310.geojson'))
SF = {'Single Family Residential', 'Suburban'}            # R1, RS, RE*, RW1, RZ, R1V/H/R + RA
MF = {'Multiple Family Residential', 'Residential', 'Residential-Mixed'}
zg, zc = [], []
area_by_cat = collections.Counter()
for f in z['features']:
    if not f['geometry']:
        continue
    g = shape(f['geometry']).buffer(0)
    cat = f['properties']['CATEGORY']
    zg.append(g); zc.append(cat)
    area_by_cat[cat] += g.area
sf_area = sum(a for c, a in area_by_cat.items() if c in SF)
mf_area = sum(a for c, a in area_by_cat.items() if c in MF)
tot_area = sum(area_by_cat.values())
stats['zoning'] = {
    'sf_share_of_residential': round(sf_area / (sf_area + mf_area) * 100, 1),
    'sf_share_of_all_zoned': round(sf_area / tot_area * 100, 1),
    'sf_km2': round(sf_area / 1e6, 1),
    'mf_km2': round(mf_area / 1e6, 1),
    'zoned_km2': round(tot_area / 1e6, 1),
    'n_polygons': len(zg),
}
tree = STRtree(zg)

# hex grid, ~1 km2 cells (side 620 m)
s = 620.0
w = math.sqrt(3) * s
minx, miny, maxx, maxy = city_m.bounds
hexes = []
row = 0
y = miny - s
while y < maxy + s:
    x0 = minx - w + (w / 2 if row % 2 else 0)
    x = x0
    while x < maxx + w:
        # pointy-top hexagon, circumradius s
        hx = Polygon([(x + s * math.cos(math.radians(30 + 60 * k)),
                       y + s * math.sin(math.radians(30 + 60 * k))) for k in range(6)])
        if hx.intersects(city_m):
            hexes.append(hx)
        x += w
    y += 1.5 * s
    row += 1
hex_feats = []
for hx in hexes:
    idx = tree.query(hx)
    a = collections.Counter()
    for i in idx:
        inter = zg[i].intersection(hx)
        if not inter.is_empty:
            a[zc[i]] += inter.area
    zoned = sum(a.values())
    if zoned < 0.15 * hx.area:
        continue
    sfa = sum(v for k, v in a.items() if k in SF)
    mfa = sum(v for k, v in a.items() if k in MF)
    res = sfa + mfa
    hex_feats.append(feat(G(hx), {
        'sf': round(sfa / zoned, 3),                          # share of zoned land that is single-family
        'sfr': round(sfa / res, 3) if res > 0 else None,      # share of residential land that is single-family
        'os': round((a['Open Space'] + a['Agricultural']) / zoned, 3),
    }))
write('sf_hex.geojson', hex_feats)

# ---------------------------------------------------------------- HOLC 1939 x today's zoning
holc = json.load(open(RAW + 'holc.geojson'))
holc_feats = []
grade_area = collections.Counter()
grade_sf = collections.Counter()
for f in holc['features']:
    g = shape(f['geometry']).buffer(0)
    grade = (f['properties'].get('HOLC_grade') or '').strip()[:1]
    if grade not in 'ABCD' or not grade:
        continue
    gm = P(g)
    holc_feats.append(feat(g.simplify(0.0002), {'grade': grade, 'id': f['properties'].get('HOLC')}))
    gm_city = gm.intersection(city_m)
    if gm_city.is_empty:
        continue
    for i in tree.query(gm_city):
        inter = zg[i].intersection(gm_city)
        if inter.is_empty:
            continue
        grade_area[grade] += inter.area
        if zc[i] in SF:
            grade_sf[grade] += inter.area
write('holc.geojson', holc_feats)
stats['holc_sf_share_today'] = {g: round(grade_sf[g] / grade_area[g] * 100, 1) for g in 'ABCD' if grade_area[g]}
stats['holc_area_km2_in_city'] = {g: round(grade_area[g] / 1e6, 1) for g in 'ABCD'}

# ---------------------------------------------------------------- tall buildings (LARIAC6, 2020, >=150 ft)
tb = json.load(open(RAW + 'tall2020.geojson'))
pts = []
for f in tb['features']:
    g = P(shape(f['geometry']))
    pts.append((g.centroid, f['properties']['HEIGHT'], g.area))
# cluster footprint parts of the same tower (centroids within 35 m)
used = [False] * len(pts)
towers = []
for i, (c, h, a) in enumerate(pts):
    if used[i]:
        continue
    grp = [i]; used[i] = True
    for j in range(i + 1, len(pts)):
        if not used[j] and c.distance(pts[j][0]) < 35:
            grp.append(j); used[j] = True
    k = max(grp, key=lambda q: pts[q][1])
    towers.append((pts[k][0], max(pts[q][1] for q in grp)))
write('towers.geojson', [feat(G(c), {'h': round(h)}) for c, h in towers])
stats['towers_county_2020'] = len(towers)
stats['towers_in_city'] = sum(1 for c, h in towers if city_m.contains(c))

# ---------------------------------------------------------------- Metro rail (GTFS, current)
stops = list(csv.DictReader(open(RAW + 'gtfs_stops.txt', encoding='utf-8-sig')))
stations = {}
for r in stops:
    if r['location_type'] == '1':
        nm = r['stop_name'].replace(' Station', '')
        stations[nm] = (float(r['stop_lon']), float(r['stop_lat']))
routes = {r['route_id']: r for r in csv.DictReader(open(RAW + 'gtfs_routes.txt', encoding='utf-8-sig'))}
trips = list(csv.DictReader(open(RAW + 'gtfs_trips.txt', encoding='utf-8-sig')))
shape_route = {}
for t in trips:
    shape_route[t['shape_id']] = t['route_id']
shp = collections.defaultdict(list)
for r in csv.DictReader(open(RAW + 'gtfs_shapes.txt', encoding='utf-8-sig')):
    shp[r['shape_id']].append((int(r['shape_pt_sequence']), float(r['shape_pt_lon']), float(r['shape_pt_lat'])))
best = {}
for sid, ptsq in shp.items():
    rid = shape_route.get(sid)
    if not rid:
        continue
    ln = LineString([(x, y) for _, x, y in sorted(ptsq)])
    if rid not in best or P(ln).length > P(best[rid]).length:
        best[rid] = ln
rail_feats = []
for rid, ln in best.items():
    r = routes[rid]
    rail_feats.append(feat(ln.simplify(0.00005), {'line': r['route_long_name'].replace('Metro ', ''), 'color': '#' + r['route_color']}))
write('rail.geojson', rail_feats)
# D Line Sections 2-3 (under construction, 2027) -- station sites from Metro project pages
uc_stations = {
    'Wilshire/Rodeo (D Line §2, 2027)': (-118.40180, 34.06686),
    'Century City/Constellation (D Line §2, 2027)': (-118.41505, 34.05930),
    'Westwood/UCLA (D Line §3, 2027)': (-118.44260, 34.06150),
    'Westwood/VA Hospital (D Line §3, 2027)': (-118.45380, 34.05520),
}
st_feats = [feat(Point(xy), {'name': n, 'uc': 0}) for n, xy in stations.items()]
st_feats += [feat(Point(xy), {'name': n, 'uc': 1}) for n, xy in uc_stations.items()]
write('stations.geojson', st_feats)
stats['rail_stations_open'] = len(stations)
st_m = [(n, P(Point(xy)), 0) for n, xy in stations.items()] + [(n, P(Point(xy)), 1) for n, xy in uc_stations.items()]

# ---------------------------------------------------------------- 1974 Concept centers vs reality
cg = json.load(open(S + 'work/centers_final.json'))['centers']
R = 800.0  # 1/4-mile core (~400 m) + ~500 m georeferencing RMSE
ESFV = {'Van Nuys', 'Panorama City'}   # East San Fernando Valley LRT, groundbreaking Oct 2026, ~2031
c_feats = []
catch = []
outcome_n = collections.Counter()
for c in cg:
    p = P(Point(c['lng'], c['lat']))
    catch.append(p.buffer(R))
    tw = [h for t, h in towers if t.distance(p) <= R]
    open_st = sorted(((s.distance(p), n) for n, s, uc in st_m if uc == 0))
    uc_st = sorted(((s.distance(p), n) for n, s, uc in st_m if uc == 1))
    d_open, n_open = open_st[0]
    rail = 'open' if d_open <= R else ('building' if (uc_st and uc_st[0][0] <= R) or c['name'] in ESFV else 'none')
    many = len(tw) >= 5
    if many and rail == 'open':
        oc = 'realised'
    elif many:
        oc = 'towers'
    elif rail == 'open':
        oc = 'rail'
    else:
        oc = 'neither'
    outcome_n[oc] += 1
    c_feats.append(feat(Point(c['lng'], c['lat']), {
        'name': c['name'], 'towers': len(tw), 'hmax': round(max(tw)) if tw else 0,
        'rail': rail, 'near': n_open, 'near_m': round(d_open, -1),
        'uc': uc_st[0][1] if rail == 'building' and uc_st and uc_st[0][0] <= R else ('East San Fernando Valley LRT (≈2031)' if rail == 'building' else ''),
        'oc': oc, 'in_city': bool(city_m.contains(p)), 'core': c['core'], 'off': c['off_m'],
        'drawn': [round(c['dlng'], 5), round(c['dlat'], 5)],
    }))
write('centers.geojson', c_feats)
cu = unary_union(catch)
in_c = sum(1 for t, h in towers if cu.contains(t))
stats['centers'] = {
    'n': len(cg), 'n_in_city': sum(1 for f in c_feats if f['properties']['in_city']),
    'outcomes': dict(outcome_n),
    'rail_open': sum(1 for f in c_feats if f['properties']['rail'] == 'open'),
    'rail_building': sum(1 for f in c_feats if f['properties']['rail'] == 'building'),
    'catchment_km2': round(cu.area / 1e6, 1),
    'towers_in_catchments': in_c,
    'towers_share_in_catchments': round(in_c / len(towers) * 100, 1),
    'catchment_share_of_city': round(cu.intersection(city_m).area / city_m.area * 100, 1),
    'towers_in_city_in_catchments': sum(1 for t, h in towers if city_m.contains(t) and cu.contains(t)),
}
# top centers by towers
stats['centers']['top'] = sorted([(f['properties']['name'], f['properties']['towers']) for f in c_feats], key=lambda r: -r[1])[:10]

# ---------------------------------------------------------------- Autopia: freeways, AADT, bottlenecks
county_box = P(Polygon([(-118.95, 33.70), (-117.64, 33.70), (-117.64, 34.82), (-118.95, 34.82)]))
fw = json.load(open(RAW + 'fwy_d7.geojson'))
lines = []
for f in fw['features']:
    if f['properties'].get('County_label') != 'LOS ANGELES':
        continue
    g = shape(f['geometry'])
    lines.append(g)
fwy = unary_union(lines).simplify(0.0002)
geoms = list(fwy.geoms) if hasattr(fwy, 'geoms') else [fwy]
write('freeways.geojson', [feat(MultiLineString([list(g.coords) for g in geoms if g.length > 0]), {})])
stats['freeway_km_la'] = round(P(unary_union(lines)).length / 1e3)

aadt = json.load(open(RAW + 'aadt_la.geojson'))
fwy_m = P(unary_union(lines))
a_feats = []
best_a = None
for f in aadt['features']:
    p = f['properties']
    vals = []
    for k in ('AHEAD_AADT', 'BACK_AADT'):
        try:
            vals.append(int(float(p[k])))
        except (TypeError, ValueError):
            pass
    if not vals or not f['geometry']:
        continue
    v = max(vals)
    pt = shape(f['geometry'])
    if v < 150000 or fwy_m.distance(P(pt)) > 120:
        continue
    a_feats.append(feat(pt, {'v': v, 'rte': p['RTE'].lstrip('0'), 'at': p['DESCRIPTION'].title()}))
    if not best_a or v > best_a[0]:
        best_a = (v, p['RTE'].lstrip('0'), p['DESCRIPTION'].title())
# thin duplicates (back/ahead points ~20 m apart): keep the max per 400 m
a_feats.sort(key=lambda f: -f['properties']['v'])
kept, kp = [], []
for f in a_feats:
    q = P(shape(f['geometry']))
    if any(q.distance(o) < 400 for o in kp):
        continue
    kept.append(f); kp.append(q)
write('aadt.geojson', kept)
stats['aadt_max'] = best_a
stats['aadt_ge_300k'] = sum(1 for f in kept if f['properties']['v'] >= 300000)
stats['aadt_ge_250k'] = sum(1 for f in kept if f['properties']['v'] >= 250000)

bn = json.load(open(RAW + 'bottlenecks_d7.geojson'))
b_feats = []
for f in bn['features']:
    p = f['properties']
    b_feats.append(feat(shape(f['geometry']).simplify(0.0001), {
        'rank': int(p['Rank']), 'fwy': p['Fwy'], 'at': p['Name'].title(), 'shift': p['Shift'],
        'delay': round(float(p['Total_Delay__veh_hrs_'])), 'mi': float(p['Avg_Extent__Miles_']),
        'days': p.get('Number_Days_Active')}))
write('bottlenecks.geojson', b_feats)
stats['bottleneck_delay_total_veh_hrs'] = sum(f['properties']['delay'] for f in b_feats)

json.dump(stats, open(os.path.join(OUT, 'stats.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(stats, indent=1, ensure_ascii=False))
