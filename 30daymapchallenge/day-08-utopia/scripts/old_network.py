"""The rail network Los Angeles dismantled: the Pacific Electric (Red Car) and Los Angeles Railway (Yellow Car) lines
as they ran in the mid-1920s, near the networks' peak.

Sources, in order of precedence (a later source only fills what an earlier one leaves out):
  wiki     Pacific Electric lines whose Wikipedia article has a route map (Template:Attached KML/<line>, CC BY-SA)
  plate    the other Pacific Electric lines, traced from the 1925 Kelker, De Leuw plate (dl1925/, Plate 1, georeferenced by
           plate_gcps.py / refit_plate.py): between waypoints set on the printed line, the cheapest path along the plate's
           solid stroke (thick brown, or darkened under the red proposals; ticked steam railroads cost more), mapped to the
           ground through the exact inverse of the plate's thin-plate spline, then snapped to a County CAMS rail or road
           centreline wherever one runs alongside (within 120 m, within 25 degrees, for 100 m or more)
  ohm      OpenHistoricalMap Pacific Electric track (railway = tram / light_rail / rail; no yards, spurs or sidings),
           kept only where the plate shows a printed line within 6 px along at least 60% of it
  streets  Los Angeles Railway lines routed along today's street centrelines from the street sequence each line's
           Wikipedia article documents for the 1920s (renamed streets by today's name)
Flags: last = '1961' on the Long Beach Line (the last Red Car, 9 April 1961); last = '1963' on lines J, P, R, S and V
(the last streetcars, replaced by buses on 31 March 1963).

Inputs (working directory): dl1925/1925-kelker-deleuw-plan.tif; work2/gcps_transit1925.json; raw4/roads_major.geojson,
raw4/roads_secondary.geojson, raw4/roads_minor_core.geojson (CAMS, eGIS_Addressing_ROAD_LINES); ohm/kml/*.kml;
ohm/pe_rel_geom.json (Overpass on overpass-api.openhistoricalmap.org:
  rel[type=multilinestring][operator|network = Pacific Electric | PE](33.5,-119.0,34.5,-117.4); out geom;)
-> data/old_network.geojson, data/story_stats.json ['old_network']
needs: numpy scipy pillow shapely pyproj scikit-image networkx
"""
import os, re, json, glob, math
import numpy as np
import networkx as nx
import xml.etree.ElementTree as ET
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize, remove_small_objects
from skimage.graph import MCP_Geometric
from shapely.geometry import LineString, MultiLineString, mapping, Point
from shapely.ops import unary_union, linemerge, substring
from shapely import STRtree
from pyproj import Transformer

S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
m2g = Transformer.from_crs(3310, 4326, always_xy=True).transform

# ---------------------------------------------------------------- the plate and its georeference
Image.MAX_IMAGE_PIXELS = None
A = np.asarray(Image.open(S + 'dl1925/1925-kelker-deleuw-plan.tif').convert('RGB').rotate(180)).astype(np.float32)
H, W = A.shape[:2]
PAPER = np.array([250, 200, 170], np.float32); BROWN = np.array([144, 77, 14], np.float32) - PAPER
D = A - PAPER; t = (D @ BROWN) / (BROWN @ BROWN); perp = np.linalg.norm(D - t[..., None] * BROWN, axis=-1)
INK = (t > 0.42) & (perp < 22)                     # the plate's brown linework (the red proposals and the paper fall outside)
BLK = A.sum(-1) < 260                              # black (existing rapid transit) and brown darkened under the red proposals
del D, t, perp, A
crop = np.zeros_like(INK); crop[290:5010, 520:6630] = True
INK &= crop; BLK &= crop; INK[2025:2100, :] = False  # outside the map frame; the fold across the sheet
thick = ndi.binary_opening(INK, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool))
SOLID = remove_small_objects(thick | BLK, max_size=150)
SK0 = skeletonize(SOLID)
lab, n = ndi.label(SK0, structure=np.ones((3, 3))); sz = ndi.sum(SK0, lab, range(1, n + 1))
keep = np.zeros(n + 1, bool); keep[1:] = sz >= 40; SK0 = keep[lab]
nb = ndi.convolve(SK0.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - SK0
JD = ndi.uniform_filter((SK0 & (nb >= 3)).astype(np.float32), 31)      # branch density: high on ticked steam railroads
COST = np.where(BLK, 1.0, np.where(ndi.binary_dilation(SK0), 1.0 + np.minimum(600 * JD, 4.0), np.where(INK, 3.5, 30.0))).astype(np.float32)
INK6 = ndi.binary_dilation(INK | BLK, iterations=6)
_sy, _sx = np.nonzero(SK0 | BLK); SNAPT = cKDTree(np.c_[_sx, _sy])

g = json.load(open(S + 'work2/gcps_transit1925.json'))
pts = [o for o in g['gcps'] if o.get('inlier')]
GC = np.array([[o['x'], o['y']] for o in pts]); PC = np.array([[o['u'], o['v']] for o in pts])
_f = RBFInterpolator(GC / 1000.0, PC, kernel='thin_plate_spline', smoothing=200.0)   # as refit_plate.py keeps for transit1925
def fwd(xy): return _f(np.asarray(xy, float) / 1000.0)
_AFF, *_ = np.linalg.lstsq(np.c_[PC, np.ones(len(PC))], GC, rcond=None)
def inv(uv, it=6):
    uv = np.asarray(uv, float).reshape(-1, 2); x = np.c_[uv, np.ones(len(uv))] @ _AFF; e = 5.0
    for _ in range(it):
        f0 = fwd(x); J = np.stack([(fwd(x + [e, 0]) - f0) / e, (fwd(x + [0, e]) - f0) / e], -1)
        x = x + np.linalg.solve(J, (uv - f0)[..., None])[..., 0]
    return x

# ---------------------------------------------------------------- Pacific Electric lines traced from the plate
PE_TRACE = {   # waypoints on the printed line, plate px (x right, y down, sheet turned upright)
 'Redondo Beach via Playa del Rey Line': [(2210, 2650), (2100, 2810), (2000, 2970), (1890, 3130), (1960, 3270), (2030, 3395), (2105, 3575), (2162, 3780), (2218, 3915)],
 'Hawthorne–Redondo Beach': [(2436, 3386), (2436, 3700), (2400, 3760), (2330, 3840), (2270, 3880), (2218, 3915)],
 'Hawthorne–South Los Angeles': [(2436, 3386), (2560, 3345), (2790, 3324), (2880, 3324), (3050, 3270), (3060, 3232)],
 'San Pedro via Gardena Line': [(2880, 3324), (2864, 3510), (2810, 3550), (2780, 3624), (2740, 3680), (2740, 3900), (2745, 4200), (2758, 4500), (2856, 4640)],
 'Redondo Beach via Gardena Line': [(2780, 3624), (2600, 3630), (2500, 3700), (2440, 3760)],
 'Hawthorne–El Segundo Line': [(2140, 3385), (2185, 3372), (2232, 3420), (2268, 3462), (2300, 3430), (2350, 3395), (2436, 3386)],
 'San Pedro via Dominguez Line': [(3216, 3750), (3150, 3900), (3080, 4080), (3000, 4300), (2930, 4460), (2890, 4550), (2856, 4640)],
 'Glendale–Burbank Line': [(2950, 2015), (2995, 1960), (2995, 1830), (2995, 1715), (2900, 1710), (2850, 1700), (2780, 1640), (2700, 1580), (2655, 1575)],
 'Alhambra–San Gabriel Line': [(3540, 2140), (3640, 2190), (3750, 2190), (3850, 2150), (3950, 2120), (4100, 2080)],
 'Upland–San Bernardino Line': [(3300, 2430), (3450, 2380), (3600, 2330), (3900, 2330), (4230, 2324), (4420, 2290), (4700, 2220), (4900, 2230),
                                (5080, 2226), (5260, 2210), (5390, 2130), (5410, 2115), (5600, 2120), (5760, 2145), (5900, 2160), (6015, 2163)],
 'Pomona–La Verne': [(5760, 2145), (5800, 2210), (5822, 2270), (5868, 2292), (5872, 2380), (5876, 2420)],
 'Pomona–Claremont Line': [(5925, 2155), (5895, 2210), (5868, 2292)],
 'Pomona local lines': [(5822, 2270), (5820, 2380), (5876, 2382), (5975, 2382)],
 'Pomona local lines (south)': [(5878, 2425), (5880, 2540), (5910, 2540)],
}
def snap_px(p, r=14):
    d, i = SNAPT.query(p, distance_upper_bound=r)
    return (float(_sx[i]), float(_sy[i])) if np.isfinite(d) else p
def deloop(P, r=2.5, gap=6):
    out = []
    for p in P:
        if len(out) > gap:
            arr = np.array(out[:-gap]); d = np.hypot(*(arr - p).T); k = int(np.argmin(d))
            if d[k] <= r: out = out[:k + 1]; continue
        out.append(p)
    return np.array(out)
def trace(wps, margin=60):
    wps = [snap_px(p) for p in wps]; out = []
    for (u0, v0), (u1, v1) in zip(wps[:-1], wps[1:]):
        x0 = int(max(0, min(u0, u1) - margin)); x1 = int(min(W, max(u0, u1) + margin))
        y0 = int(max(0, min(v0, v1) - margin)); y1 = int(min(H, max(v0, v1) + margin))
        m = MCP_Geometric(COST[y0:y1, x0:x1]); m.find_costs([(int(v0) - y0, int(u0) - x0)], [(int(v1) - y0, int(u1) - x0)])
        p = np.array(m.traceback((int(v1) - y0, int(u1) - x0)))
        seg = np.c_[p[:, 1] + x0, p[:, 0] + y0].astype(float); out.append(seg if not out else seg[1:])
    P = deloop(np.concatenate(out))
    if len(P) >= 7:
        Q = np.c_[ndi.uniform_filter1d(P[:, 0], 7, mode='nearest'), ndi.uniform_filter1d(P[:, 1], 7, mode='nearest')]; Q[0], Q[-1] = P[0], P[-1]; P = Q
    return P

# ---------------------------------------------------------------- today's centrelines (rails and streets)
def cams(files, skip=()):
    out = []
    for fn in files:
        for f in json.load(open(S + fn))['features']:
            p = f['properties']; gg = f.get('geometry')
            if not gg or p['Type'] in skip: continue
            for l in (gg['coordinates'] if gg['type'] == 'MultiLineString' else [gg['coordinates']]):
                if len(l) >= 2: out.append((p['Type'], p.get('FullName'), [g2m(*q[:2]) for q in l]))
    return out
ROADS = cams(['raw4/roads_major.geojson', 'raw4/roads_secondary.geojson', 'raw4/roads_minor_core.geojson'])
SNAPL = [LineString(c) for ty, nm, c in ROADS if ty in ('Railroad', 'Highway', 'Primary', 'Secondary')]
SNAPTREE = STRtree(SNAPL)

def snap_line(L, r=120.0, ang=25.0, step=20.0, minrun=5):
    """move a traced line onto a parallel modern rail or road centreline wherever one runs alongside for 100 m or more"""
    n = max(2, int(L.length / step)); P = [L.interpolate(i / (n - 1), normalized=True) for i in range(n)]
    tang = np.array([[L.interpolate(min(L.length, L.project(p) + 5)).x - L.interpolate(max(0, L.project(p) - 5)).x,
                      L.interpolate(min(L.length, L.project(p) + 5)).y - L.interpolate(max(0, L.project(p) - 5)).y] for p in P])
    out = []; ok = []
    for p, tv in zip(P, tang):
        best = None
        for k in SNAPTREE.query(p.buffer(r)):
            c = SNAPL[k]; d = c.distance(p)
            if d > r: continue
            s = c.project(p); a = c.interpolate(max(0, s - 5)); b = c.interpolate(min(c.length, s + 5))
            cv = np.array([b.x - a.x, b.y - a.y]); cosang = abs(cv @ tv) / (np.linalg.norm(cv) * np.linalg.norm(tv) + 1e-9)
            if cosang < math.cos(math.radians(ang)): continue
            if best is None or d < best[0]: best = (d, c.interpolate(s))
        out.append((best[1].x, best[1].y) if best else (p.x, p.y)); ok.append(best is not None)
    ok = np.array(ok)
    d_ = np.diff(np.r_[0, ok.astype(int), 0]); st = np.where(d_ == 1)[0]; en = np.where(d_ == -1)[0]
    final = [(p.x, p.y) for p in P]
    for a, b in zip(st, en):
        if b - a >= minrun: final[a:b] = out[a:b]
    return LineString(final).simplify(4.0)

# ---------------------------------------------------------------- Los Angeles Railway lines routed on today's streets
LARY = {
 'A': dict(start=('ADAMS', 'ALSACE'), streets=['ADAMS', 'NORMANDIE', '24 ST', 'HOOVER', 'BURLINGTON', 'VENICE', 'HILL', '1 ST', 'SPRING', 'MAIN', 'CESAR E CHAVEZ', 'BROADWAY', 'LINCOLN PARK'], end=('LINCOLN PARK', 'VALLEY')),
 'B': dict(start=('CESAR E CHAVEZ', 'EVERGREEN'), streets=['CESAR E CHAVEZ', 'MAIN', '12 ST', 'HOOPER'], end=('HOOPER', 'VERNON')),
 'D': dict(start=('5 ST', 'CENTRAL'), streets=['5 ST', 'OLIVE', '6 ST', 'WILTON PL', '3 ST', 'LARCHMONT'], end=('LARCHMONT', 'MELROSE')),
 'F': dict(start=('FRESNO', '1 ST'), streets=['FRESNO', '4 ST', 'MAIN', 'JEFFERSON', 'GRAND', 'HOOVER', 'VERMONT'], end=('VERMONT', 'MANCHESTER')),
 'G': dict(start=('VERNON', 'MCKINLEY'), streets=['MCKINLEY', '14 ST', 'STANFORD', '12 ST', 'MAIN', 'CESAR E CHAVEZ', 'SPRING'], end=('SPRING', 'ORD')),
 'I': dict(start=('1 ST', 'BROADWAY'), streets=['1 ST', 'ALVARADO'], end=('ALVARADO', '6 ST')),
 'J': dict(start=('JEFFERSON', '10 AVE'), streets=['JEFFERSON', 'GRAND', '7 ST', 'MATEO', 'OLYMPIC', 'SANTA FE', 'PACIFIC', 'FLORENCE', 'SEVILLE'], end=('SEVILLE', 'SANTA ANA')),
 'K': dict(start=('MAIN', 'JEFFERSON'), streets=['JEFFERSON', 'CENTRAL', '38 ST'], end=('38 ST', 'ASCOT')),
 'L': dict(start=('OLYMPIC', 'MULLEN'), streets=['OLYMPIC', 'COUNTRY CLUB', 'VICTORIA', 'HOOVER', '11 ST', 'MAIN', 'SPRING'], end=('SPRING', 'TEMPLE')),
 'N': dict(start=('8 ST', 'HARVARD'), streets=['8 ST', 'VERMONT', '9 ST', 'SPRING', '2 ST', 'TRACTION', '3 ST', 'SANTA FE'], end=('SANTA FE', '2 ST')),
 'O': dict(start=('MAIN', 'TEMPLE'), streets=['MAIN', '8 ST', 'VIRGIL'], end=('VIRGIL', '1 ST')),
 'P': dict(start=('CESAR E CHAVEZ', 'ROWAN'), streets=['ROWAN', '1 ST', 'BROADWAY', 'PICO'], end=('PICO', 'RIMPAU')),
 'R': dict(start=('3 ST', 'LA BREA'), streets=['3 ST', 'VERMONT', '7 ST', 'BOYLE', 'WHITTIER'], end=('WHITTIER', 'EASTERN')),
 'S': dict(start=('WESTERN', 'SANTA MONICA'), streets=['WESTERN', '3 ST', 'VERMONT', '7 ST', 'SAN PEDRO', 'VERNON', 'CENTRAL'], end=('CENTRAL', 'FIRESTONE')),
 'V': dict(start=('VERMONT', 'BEVERLY'), streets=['VERMONT', 'VERNON', 'PACIFIC', 'LEONIS'], end=('LEONIS', 'DOWNEY')),
 'W': dict(start=('MARMION WAY', 'AVENUE 64'), streets=['MARMION WAY', 'FIGUEROA', 'PASADENA', 'BROADWAY', '11 ST', 'FLOWER', 'WASHINGTON'], end=('WASHINGTON', 'RIMPAU')),
 '3': dict(start=('ADAMS', 'ALSACE'), streets=['ADAMS', 'NORMANDIE', '24 ST', 'HOOVER', 'BURLINGTON', 'VENICE', 'HILL', '1 ST', 'BROADWAY', 'LINCOLN PARK'], end=('LINCOLN PARK', 'VALLEY')),
 '5 (Eagle Rock)': dict(start=('COLORADO', 'TOWNSEND'), streets=['COLORADO', 'EAGLE ROCK', 'AVENUE 28', 'FIGUEROA', 'AVENUE 20', 'MAIN'], end=('MAIN', '2 ST')),
 '5 (Hawthorne)': dict(start=('SPRING', '2 ST'), streets=['2 ST', 'BROADWAY', '7 ST', 'GRAND', 'MARTIN LUTHER KING JR', 'LEIMERT', 'CRENSHAW', 'REDONDO', 'FLORENCE', 'MARKET', 'LA BREA', 'HAWTHORNE'], end=('HAWTHORNE', 'BROADWAY')),
 'M (later 8)': dict(start=('SPRING', 'TEMPLE'), streets=['SPRING', 'MAIN', 'BROADWAY', '54 ST'], end=('54 ST', 'CRENSHAW')),
}
LAST_1963 = ['J', 'P', 'R', 'S', 'V']
DIRS = {'N', 'S', 'E', 'W'}
def norm(name):
    if not name: return None
    t = re.sub(r'[^A-Z0-9 ]', ' ', name.upper()).split()
    if t and t[0] in DIRS and len(t) > 1: t = t[1:]
    if len(t) > 1 and t[-1] == 'WY': t[-1] = 'WAY'
    typ = None
    if len(t) > 1 and t[-1] in {'ST', 'AVE', 'AV', 'BLVD', 'RD', 'DR', 'HWY', 'PKWY', 'PL', 'WAY', 'CT', 'TER', 'LN'}: typ = t[-1]; t = t[:-1]
    t = [re.sub(r'^(\d+)(ST|ND|RD|TH)$', r'\1', w) for w in t]; base = ' '.join(t)
    if re.fullmatch(r'\d+', base): return f"{base} {'AVE' if typ in ('AVE', 'AV') else 'ST' if typ in (None, 'ST') else typ}"
    return f'{base} {typ}' if typ in {'PL', 'WAY', 'CT', 'TER', 'LN'} else base
ALIAS = {'9 ST': {'9 ST', 'JAMES M WOOD'}, 'CESAR E CHAVEZ': {'CESAR E CHAVEZ', 'CESAR CHAVEZ'}, 'MARTIN LUTHER KING JR': {'MARTIN LUTHER KING JR', 'MARTIN LUTHER KING'}}
G = nx.Graph()
for ty, nm, c in ROADS:
    if ty in ('Railroad', 'Freeway', 'Ramp'): continue
    a = (round(c[0][0]), round(c[0][1])); b = (round(c[-1][0]), round(c[-1][1]))
    if a == b: continue
    L = LineString(c).length
    if G.has_edge(a, b) and G[a][b]['len'] <= L: continue
    G.add_edge(a, b, key=norm(nm), len=L, coords=c)
_IDX = {}
def N(k):
    if k not in _IDX:
        ks = ALIAS.get(k, {k}); _IDX[k] = {q for u, v, d in G.edges(data=True) if d['key'] in ks for q in (u, v)}
    return _IDX[k]
DT = g2m(-118.2437, 34.0522)
def route(spec):
    st, c0 = spec['start']; en, c1 = spec['end']; seq = spec['streets']
    s0 = N(st) & N(c0)
    if not s0: return None
    cur = min(s0, key=lambda q: (q[0] - DT[0]) ** 2 + (q[1] - DT[1]) ** 2); path = [cur]
    for i, k in enumerate(seq):
        ks = ALIAS.get(k, {k})
        dist, paths = nx.single_source_dijkstra(G, cur, weight=lambda u, v, d, ks=ks: d['len'] * (1.0 if d['key'] in ks else 12.0), cutoff=60000)
        T = (N(seq[i + 1]) & N(k) or N(seq[i + 1])) if i + 1 < len(seq) else (N(k) & N(c1) or N(c1))
        T = [q for q in T if q in dist and q != cur]
        if not T: return None
        tq = min(T, key=lambda q: dist[q]); path += paths[tq][1:]; cur = tq
    coords = []
    for a, b in zip(path[:-1], path[1:]):
        c = G[a][b]['coords']
        if (round(c[0][0]), round(c[0][1])) != a: c = c[::-1]
        coords += c if not coords else c[1:]
    return LineString(coords).simplify(3.0)

# ---------------------------------------------------------------- Wikipedia route maps and OpenHistoricalMap track
def kml_lines(fn):
    tx = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', open(fn).read()); out = []
    for c in ET.fromstring(tx.encode()).iter('coordinates'):
        p = [tuple(map(float, q.split(',')[:2])) for q in c.text.split() if q.count(',') >= 1]
        if len(p) >= 2: out.append(LineString([g2m(*q) for q in p]))
    return out
DASH = {'La Habra Yorba Linda': 'La Habra–Yorba Linda', 'Santa Ana Orange': 'Santa Ana–Orange', 'Monrovia Glendora': 'Monrovia–Glendora',
        'Venice Inglewood': 'Venice–Inglewood', 'San Bernardino Riverside': 'San Bernardino–Riverside'}
def kname(fn):
    nm = os.path.basename(fn)[:-4].replace('_', ' ').strip()
    for a, b in DASH.items(): nm = nm.replace(a, b)
    return nm
WIKI = {kname(fn): kml_lines(fn) for fn in sorted(glob.glob(S + 'ohm/kml/*.kml'))}
def on_plate(L, need=0.6):
    uv = fwd(np.array([L.interpolate(d).coords[0] for d in np.arange(0, L.length, 16.0)] or [L.coords[0]]))
    u = np.clip(np.round(uv[:, 0]).astype(int), 0, W - 1); v = np.clip(np.round(uv[:, 1]).astype(int), 0, H - 1)
    inside = (uv[:, 0] > 520) & (uv[:, 0] < 6630) & (uv[:, 1] > 290) & (uv[:, 1] < 5010)
    return inside.mean() > 0.9 and INK6[v, u].mean() >= need
OHM = []
def year(v):
    m = re.match(r'(\d{4})', v or ''); return int(m.group(1)) if m else None
for e in json.load(open(S + 'ohm/pe_rel_geom.json'))['elements']:      # PE track relations (type=multilinestring), members with geometry
    tg = e.get('tags', {})
    if tg.get('railway') not in ('tram', 'light_rail', 'rail') or tg.get('service'): continue
    if re.search(r'Yard|Shop|Garage|transfer|substation|Spur|Siding|Packing', tg.get('name') or '', re.I): continue
    y0, y1 = year(tg.get('start_date')), year(tg.get('end_date'))
    if (y0 and y0 > 1925) or (y1 and y1 < 1925): continue                 # in service in 1925
    for m in e.get('members', []):
        gm = m.get('geometry')
        if m.get('type') == 'way' and gm and len(gm) >= 2:
            L = LineString([g2m(p['lon'], p['lat']) for p in gm])
            if L.length >= 150 and on_plate(L): OHM.append(L)

# ---------------------------------------------------------------- merge, flags, miles
feats, meta = [], []
def add(geom, op, name, src, last=None):
    gl = mapping(geom); parts = gl['coordinates'] if gl['type'] == 'MultiLineString' else [gl['coordinates']]
    out = [[[round(x, 5), round(y, 5)] for x, y in (m2g(*q) for q in part)] for part in parts if len(part) >= 2]
    if not out: return
    feats.append({'type': 'Feature', 'geometry': {'type': 'MultiLineString', 'coordinates': out}, 'properties': {'op': op, 'name': name, 'src': src, 'last': last}})
    meta.append((op, geom, last))
taken = []
for nm, ls in WIKI.items():
    gm = unary_union(ls); add(gm.simplify(4.0), 'PE', nm, 'wiki'); taken.append(gm)
    if nm.startswith('Long Beach Line'): add(gm.simplify(4.0), 'PE', nm, 'wiki', last='1961')
def rest(L, buf=60.0, minlen=200.0):
    cover = unary_union(taken).buffer(buf); d = L.difference(cover)
    parts = [p for p in (d.geoms if hasattr(d, 'geoms') else [d]) if p.geom_type == 'LineString' and p.length >= minlen]
    return MultiLineString(parts) if parts else None
traced = {}
for nm, wps in PE_TRACE.items():
    L = snap_line(LineString(inv(trace(wps))))
    traced[nm] = L
    r = rest(L)
    if r is not None: add(r, 'PE', nm.replace(' (south)', ''), 'plate'); taken.append(r)
for L in OHM:
    r = rest(L)
    if r is not None: add(r, 'PE', None, 'ohm'); taken.append(r)
routed = {}
for nm, spec in LARY.items():
    L = route(spec)
    if L is None: print('no route', nm); continue
    routed[nm] = L; add(L, 'LARy', nm, 'streets')
    if nm in LAST_1963: add(L, 'LARy', nm, 'streets', last='1963')
def miles(op):
    gs = [gm.buffer(25) for o, gm, last in meta if o == op and last is None]
    return round(unary_union(gs).area / 50 / 1609.34, 1)
from shapely.geometry import box
from shapely.ops import transform as _tf
WIN = _tf(g2m, box(-118.72, 33.68, -117.60, 34.36))      # the plate's own window (tiles/transit1925)
def miles_in(op):
    gs = [gm.buffer(25) for o, gm, last in meta if o == op and last is None]
    return round(unary_union(gs).intersection(WIN).area / 50 / 1609.34, 1)
json.dump({'type': 'FeatureCollection', 'features': feats}, open(DAY + 'data/old_network.geojson', 'w'), separators=(',', ':'))
st = json.load(open(DAY + 'data/story_stats.json'))
st['old_network'] = {
    'miles_1925': {'PE': miles('PE'), 'LARy': miles('LARy')},
    'miles_1925_plate_window': {'PE': miles_in('PE'), 'LARy': miles_in('LARy')},
    'accuracy': {'wiki': 'as drawn by Wikipedia editors on modern maps (tens of metres)',
                 'plate': 'plate georeference 113 m (leave-one-out RMSE) plus tracing 50-80 m; about half the traced length snapped to a surviving rail or road centreline',
                 'streets': 'exact street centrelines; the route follows each article\'s street list (plate agrees within ~65 m along 65-94% of each line)',
                 'ohm': 'OpenHistoricalMap track, kept only where the plate shows a line within 6 px (about 100 m)'},
    'gaps': ['Pacific Electric: Long Beach-San Pedro (harbour belt too tangled on the plate to trace); Annandale, Westgate, Hawthorne-El Nido, Catalina Dock and East Washington locals; the Santa Ana-Huntington Beach line and the Inland Empire lines beyond the plate (Redlands, Highland, Arrowhead, Riverside-Rialto/Arlington, Upland-Ontario)',
             'Los Angeles Railway: lines without a Wikipedia route description (C, E before it became 5, H, Q, U and branches) and short-lived 1920s variants; the 1932-1955 numbered routes (2, 7, 8, 9, 10) are not drawn separately'],
    'lines': {'PE_wiki': sorted(WIKI), 'PE_plate': sorted(PE_TRACE), 'LARy_streets': sorted(routed), 'last_1961': ['Long Beach Line'], 'last_1963': LAST_1963},
    'method': ('Pacific Electric: Wikipedia route maps where a line has one; the other lines traced from the 1925 Kelker, De Leuw plate '
               '(georeferenced, leave-one-out error 113 m) and snapped to surviving rail or road centrelines; OpenHistoricalMap track where the plate agrees. '
               'Los Angeles Railway: each line routed on today\'s streets from the street sequence its Wikipedia article gives for the 1920s. '
               'Route miles: lines buffered 25 m and unioned, shared track counted once, per company.'),
    'src': 'Wikipedia line articles and route maps (CC BY-SA); OpenHistoricalMap (CC0); Kelker, De Leuw & Co. 1925, Plate 1 (LA Metro Research Library); LA County CAMS centrelines'}
json.dump(st, open(DAY + 'data/story_stats.json', 'w'), indent=1)
print('features', len(feats), 'PE miles', st['old_network']['miles_1925']['PE'], 'LARy miles', st['old_network']['miles_1925']['LARy'])
print('ohm pieces kept', sum(1 for f in feats if f['properties']['src'] == 'ohm'))
print(os.path.getsize(DAY + 'data/old_network.geojson') // 1024, 'KB')
