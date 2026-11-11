"""The rail network Los Angeles dismantled: the Pacific Electric (Red Car) and Los Angeles Railway (Yellow Car) lines
about 1925, near the networks' peak (the central lines as drawn in 1927).

Sources, in order of precedence (a later source only fills what an earlier one leaves out):
Pacific Electric
  wiki     lines whose Wikipedia article has a route map (Template:Attached KML/<line>, CC BY-SA)
  usgs     Long Beach-San Pedro, San Pedro via Dominguez (on the Wilmington sheet), Hawthorne-El Nido and Westgate, traced on
           USGS 1:24,000 sheets of 1924-25 (usgs/pdf/), each placed by the coordinates printed in its GeoPDF: between waypoints
           set on the printed railway, the cheapest path along the sheet's black linework, snapped to today's centrelines
           within 40 m (not Westgate's private way; west of Westgate station: today's San Vicente Boulevard, in whose median
           it ran); on a sheet where a line is traced, the trace replaces the plate's
  pe1927   every rail line drawn solid red (and the dashed black subway) on the Pacific Electric engineering department's
           map C.E. 8214 (1927), georeferenced by plate_gcps.py + dense_gcps.py + refit_plate.py (img/pe1927_registration.json):
           colour masks (legend swatches: rail #dc7864, motor coach #da765e, subway #7c5748), long strokes only (the motor
           coach dashes, ~25 px long, drop out), skeleton, spurs pruned, mapped through the exact inverse of the chosen model,
           snapped to today's street or rail centrelines within 60 m; named after a named line that runs along it
  plate    the other lines, traced from the 1925 Kelker, De Leuw plate (dl1925/, Plate 1, georeferenced by plate_gcps.py /
           refit_plate.py): the cheapest path along the plate's solid stroke between waypoints, through the exact inverse of
           the plate's thin-plate spline, snapped to a County CAMS rail or road centreline running alongside (120 m, 25 deg,
           100 m or more); dropped where a better source runs within 150 m
  ohm      OpenHistoricalMap Pacific Electric track in service in 1925 (no yards, spurs or sidings), where the plate agrees
Los Angeles Railway
  streets  lines routed along today's street centrelines from the street sequence each line's Wikipedia article documents
           for the 1920s; stretches of 300 m or more on streets where the 1927 map shows no transit line at all are dropped
  pe1927   every other line drawn solid yellow on the 1927 map (rail; the dashed motor coach lines left out)
Flags: last = '1961' on the Long Beach Line (the last Red Car, 9 April 1961); last = '1963' on lines J, P, R, S and V
(the last streetcars, replaced by buses on 31 March 1963).

Inputs (working directory): dl1925/1925-kelker-deleuw-plan.tif; work2/gcps_transit1925.json; dl_maps/1927_pe_lary_engineer.jpg;
work2/gcps_pe1927.json; raw4/roads_major.geojson, raw4/roads_secondary.geojson, raw4/roads_minor_core.geojson,
raw4/roads_minor_edges.geojson (CAMS, eGIS_Addressing_ROAD_LINES); ohm/kml/*.kml; ohm/pe_rel_geom.json (Overpass on
overpass-api.openhistoricalmap.org: rel[type=multilinestring][operator|network = Pacific Electric | PE](33.5,-119.0,34.5,-117.4);
out geom;); usgs/pdf/CA_Wilmington_295813_1925.pdf, CA_Torrance_295502_1924.pdf, CA_Inglewood_291567_1924.pdf,
CA_Sawtelle_295108_1925.pdf (USGS Historical Topographic Map Collection, ..._24000_geo.pdf); projgrids/us_noaa_conus.tif (NADCON)
-> data/old_network.geojson, data/story_stats.json ['old_network']
needs: numpy scipy pillow shapely pyproj scikit-image networkx pypdf; poppler-utils (pdftoppm)
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
ROADS = cams(['raw4/roads_major.geojson', 'raw4/roads_secondary.geojson', 'raw4/roads_minor_core.geojson', 'raw4/roads_minor_edges.geojson'])
SNAPL = [LineString(c) for ty, nm, c in ROADS if ty in ('Railroad', 'Highway', 'Primary', 'Secondary')]
SNAPTREE = STRtree(SNAPL)
SNAPL_ALL = [LineString(c) for ty, nm, c in ROADS if ty not in ('Freeway', 'Ramp')]     # streetcars ran in every class of street
SNAPTREE_ALL = STRtree(SNAPL_ALL)

def snap_line(L, r=120.0, ang=25.0, step=20.0, minrun=5, lines=None, tree=None):
    """move a traced line onto a parallel modern rail or road centreline wherever one runs alongside for 100 m or more"""
    n = max(2, int(L.length / step)); P = [L.interpolate(i / (n - 1), normalized=True) for i in range(n)]
    tang = np.array([[L.interpolate(min(L.length, L.project(p) + 5)).x - L.interpolate(max(0, L.project(p) - 5)).x,
                      L.interpolate(min(L.length, L.project(p) + 5)).y - L.interpolate(max(0, L.project(p) - 5)).y] for p in P])
    out = []; ok = []
    for p, tv in zip(P, tang):
        best = None
        for k in (tree or SNAPTREE).query(p.buffer(r)):
            c = (lines or SNAPL)[k]; d = c.distance(p)
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

# ---------------------------------------------------------------- the 1927 Pacific Electric engineering map (C.E. 8214)
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plates import CUSTOM, PAD27, PE1927_OUT
REG27 = json.load(open(DAY + 'img/pe1927_registration.json'))
_g27 = json.load(open(S + 'work2/gcps_pe1927.json'))
_p27 = [o for o in _g27['gcps'] if o.get('inlier')]
G27 = np.array([[o['x'], o['y']] for o in _p27]); P27 = np.array([[o['u'], o['v']] for o in _p27])
def _poly(order, G, P):
    mu, sd = G.mean(0), G.std(0)
    F = lambda X: (lambda z: np.hstack([np.ones((len(z), 1))] + [z[:, :1] ** (i - j) * z[:, 1:] ** j for i in range(1, order + 1) for j in range(i + 1)]))((np.asarray(X, float) - mu) / sd)
    M, *_ = np.linalg.lstsq(F(G), P, rcond=None); return lambda X: F(X) @ M
if REG27['model'].startswith('tps'):              # the model refit_plate.py chose for the tiles
    _f27 = RBFInterpolator(G27 / 1000.0, P27, kernel='thin_plate_spline', smoothing=float(REG27['model'].split('_s')[1]))
    fwd27 = lambda xy: _f27(np.asarray(xy, float) / 1000.0)
else:
    fwd27 = _poly({'affine': 1, 'poly2': 2, 'poly3': 3}[REG27['model']], G27, P27)
_A27, *_ = np.linalg.lstsq(np.c_[P27, np.ones(len(P27))], G27, rcond=None)
def inv27(uv, it=6):
    uv = np.asarray(uv, float).reshape(-1, 2); x = np.c_[uv, np.ones(len(uv))] @ _A27; e = 5.0
    for _ in range(it):
        f0 = fwd27(x); J = np.stack([(fwd27(x + [e, 0]) - f0) / e, (fwd27(x + [0, e]) - f0) / e], -1)
        x = x + np.linalg.solve(J, (uv - f0)[..., None])[..., 0]
    return x
A27 = np.asarray(Image.open(S + CUSTOM['pe1927']['img']).convert('RGB')).astype(np.int16)    # unpadded; +PAD27 for the model
_R, _G, _B = A27[..., 0], A27[..., 1], A27[..., 2]
CROP27 = (250, 300, 4590, 5540)
_keep27 = np.zeros(_R.shape, bool); _keep27[CROP27[1]:CROP27[3], CROP27[0]:CROP27[2]] = True
for a_, b_, c_, d_ in PE1927_OUT: _keep27[b_:d_, a_:c_] = False
RED27 = ((_R - _G > 60) & (_R - _B > 70)) & _keep27                  # Pacific Electric (rail solid, motor coach dashed)
YEL27 = ((_R - _B > 90) & (_G - _B > 70) & (_R > 170)) & _keep27     # Los Angeles Railway (rail solid, motor coach dashed)
BLK27 = ((A27.sum(-1) < 300) & ((A27.max(-1) - A27.min(-1)) < 45)) & _keep27   # the subway (dashed black) and dark street ink
ANY27 = ndi.binary_dilation(RED27 | YEL27 | ((_G - _R > 45) & (_G - _B > 8)) | ((_B - _G > 18) & (_R - _G > 10) & (_B > 170)), iterations=8)
del A27, _R, _G, _B
def solid27(m, min_len=90):
    """solid lines of one colour: long connected strokes (the motor coach dashes, ~25 px long with ~10 px gaps, drop out)"""
    m = ndi.binary_closing(ndi.binary_opening(m, iterations=1), structure=np.ones((5, 5)))
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    sl = ndi.find_objects(lab); keep = np.zeros(n + 1, bool)
    for i, s_ in enumerate(sl):
        if s_ is None: continue
        ys, xs = np.nonzero(lab[s_] == i + 1)
        if len(xs) < 20: continue
        c = np.cov(np.c_[xs, ys].T); ev = np.linalg.eigvalsh(c)
        if 4 * math.sqrt(max(ev[-1], 0)) >= min_len: keep[i + 1] = True        # major axis length (as skimage's regionprops)
    return keep[lab]
def dashed27(m, dmin=12, dmax=48):
    m = ndi.binary_opening(m, iterations=1); lab, n = ndi.label(m, structure=np.ones((3, 3))); keep = np.zeros(n + 1, bool)
    for i, s_ in enumerate(ndi.find_objects(lab)):
        if s_ is None: continue
        ys, xs = np.nonzero(lab[s_] == i + 1)
        if len(xs) < 8: continue
        ev = np.linalg.eigvalsh(np.cov(np.c_[xs, ys].T)); L_, W_ = 4 * math.sqrt(max(ev[-1], 0)), 4 * math.sqrt(max(ev[0], 0))
        if dmin <= L_ <= dmax and W_ <= 9: keep[i + 1] = True
    return keep[lab]
_NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
def skel_paths(sk, spur=30):
    """skeleton -> polylines between junctions and ends, end spurs shorter than `spur` px pruned"""
    ys, xs = np.nonzero(sk); idx = {(y, x): i for i, (y, x) in enumerate(zip(ys, xs))}
    Gs = nx.Graph()
    for i, (y, x) in enumerate(zip(ys, xs)):
        Gs.add_node(i, p=(x, y))
        for dy, dx in _NB:
            j = idx.get((y + dy, x + dx))
            if j is not None and j > i: Gs.add_edge(i, j)
    for _ in range(4):
        removed = False
        for e in [q for q in Gs if Gs.degree(q) == 1]:
            if e not in Gs: continue
            path = [e]; cur = e; prev = None
            while True:
                nb = [q for q in Gs.neighbors(cur) if q != prev]
                if len(nb) != 1: break
                prev, cur = cur, nb[0]; path.append(cur)
                if Gs.degree(cur) != 2 or len(path) > spur: break
            if len(path) <= spur and Gs.degree(cur) >= 3: Gs.remove_nodes_from(path[:-1]); removed = True
        if not removed: break
    out = []; seen = set()
    for q0 in [q for q in Gs if Gs.degree(q) != 2]:
        for nb in Gs.neighbors(q0):
            if (q0, nb) in seen: continue
            path = [q0, nb]; prev, cur = q0, nb
            while Gs.degree(cur) == 2:
                nxt = [q for q in Gs.neighbors(cur) if q != prev][0]; prev, cur = cur, nxt; path.append(cur)
            seen.add((path[-1], path[-2])); seen.add((q0, nb))
            if len(path) >= 4: out.append(np.array([Gs.nodes[q]['p'] for q in path], float))
    for comp in nx.connected_components(Gs):
        if all(Gs.degree(q) == 2 for q in comp) and len(comp) >= 8:
            q0 = next(iter(comp)); order = list(nx.dfs_preorder_nodes(Gs, q0)); out.append(np.array([Gs.nodes[q]['p'] for q in order + [q0]], float))
    return out
def vec27(mask, spur=30, minlen=12):
    out = []
    for P in skel_paths(skeletonize(mask), spur):
        if len(P) < minlen: continue
        if len(P) >= 15:      # smooth out the teeth where a dashed motor coach line touches a rail line on the same street
            S_ = np.c_[ndi.uniform_filter1d(P[:, 0], 15, mode='nearest'), ndi.uniform_filter1d(P[:, 1], 15, mode='nearest')]; S_[0], S_[-1] = P[0], P[-1]; P = S_
        Q = P[::4] if len(P) > 8 else P
        if not np.array_equal(Q[-1], P[-1]): Q = np.vstack([Q, P[-1]])
        L = LineString(inv27(Q + PAD27))
        out.append(snap_line(L, r=60.0, ang=30.0, step=10.0, minrun=4, lines=SNAPL_ALL, tree=SNAPTREE_ALL).simplify(4.0))
    return out
PE27 = vec27(solid27(RED27)); LARY27 = vec27(solid27(YEL27))
SUB27 = vec27(ndi.binary_closing(ndi.binary_dilation(dashed27(BLK27), iterations=2), structure=np.ones((15, 15))), spur=10)
COVER27 = LineString(inv27(np.array([[CROP27[0], CROP27[1]], [CROP27[2], CROP27[1]], [CROP27[2], CROP27[3]], [CROP27[0], CROP27[3]], [CROP27[0], CROP27[1]]], float) + PAD27)).convex_hull
def on_any27(L, step=25.0):
    """per point along L: True where the 1927 map shows any transit line within ~45 m, None outside the map"""
    d = np.arange(0, L.length + 1e-6, step); P = np.array([L.interpolate(x).coords[0] for x in d])
    inside = np.array([COVER27.contains(Point(p)) for p in P])
    uv = fwd27(P) - PAD27; u = np.clip(np.round(uv[:, 0]).astype(int), 0, ANY27.shape[1] - 1); v = np.clip(np.round(uv[:, 1]).astype(int), 0, ANY27.shape[0] - 1)
    return d, inside, ANY27[v, u]
def prune_by_1927(L, minrun=300.0):
    """drop the parts of a routed line that run, inside the 1927 map, for 300 m or more on streets where the map shows no transit line"""
    d, inside, hit = on_any27(L); bad = inside & ~hit
    dd = np.diff(np.r_[0, bad.astype(int), 0]); st_, en_ = np.where(dd == 1)[0], np.where(dd == -1)[0]
    cut = [(d[a], d[min(b, len(d) - 1)]) for a, b in zip(st_, en_) if d[min(b, len(d) - 1)] - d[a] >= minrun]
    if not cut: return L, 0.0
    keep, pos = [], 0.0
    for a, b in cut:
        if a - pos > 30: keep.append(substring(L, pos, a))
        pos = b
    if L.length - pos > 30: keep.append(substring(L, pos, L.length))
    keep = [k for k in keep if k.geom_type == 'LineString' and k.length > 30]
    return (MultiLineString(keep) if keep else None), sum(b - a for a, b in cut)
print('1927 map:', len(PE27), 'PE pieces,', len(LARY27), 'LARy pieces,', len(SUB27), 'subway pieces', flush=True)

# ---------------------------------------------------------------- USGS 1:24,000 sheets of the 1920s (lines beyond the 1927 map)
import subprocess, tempfile, pyproj, pypdf
from pyproj import CRS
pyproj.datadir.append_data_dir(os.path.abspath(S + 'projgrids'))
def topo(pdf, ppi=300):
    """the map face of a USGS GeoPDF, with its own georeference (LGIDict: CTM to the sheet's NAD27 polyconic, NADCON to WGS84)"""
    page = pypdf.PdfReader(pdf).pages[0]; L = page['/LGIDict']; L = L[0] if isinstance(L, list) else L; P = L['/Projection']
    crs = CRS.from_proj4(f"+proj=poly +lat_0={float(P['/OriginLatitude'])} +lon_0={float(P['/CentralMeridian'])} +x_0=0 +y_0=0 +datum=NAD27 +units=m +no_defs")
    a, b, c, d, e, f = [float(x) for x in L['/CTM']]
    nl = np.array([float(x) for x in L['/Neatline']]).reshape(-1, 2); H = float(page.mediabox[3]); s = ppi / 72.0
    lon, lat = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True).transform(a * nl[:, 0] + c * nl[:, 1] + e, b * nl[:, 0] + d * nl[:, 1] + f)
    err = max(np.abs(lon * 60 - np.round(lon * 60 * 2) / 2).max(), np.abs(lat * 60 - np.round(lat * 60 * 2) / 2).max()) * 1852
    assert err < 2, (pdf, err)                                       # the neatline lands on the survey grid
    x0, x1 = nl[:, 0].min() - 2, nl[:, 0].max() + 2; y0, y1 = H - nl[:, 1].max() - 2, H - nl[:, 1].min() + 2
    X, Y, W_, H_ = int(x0 * s), int(y0 * s), int(math.ceil((x1 - x0) * s)), int(math.ceil((y1 - y0) * s))
    with tempfile.TemporaryDirectory(dir='.') as td:
        subprocess.run(['pdftoppm', '-r', str(ppi), '-x', str(X), '-y', str(Y), '-W', str(W_), '-H', str(H_), '-singlefile', pdf, f'{td}/p'], check=True)
        A_ = np.asarray(Image.open(f'{td}/p.ppm').convert('RGB')).astype(np.int16)
    n2w = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)
    def px2m(col, row):
        px = (np.asarray(col, float) + 0.5 + X) / s; py = H - (np.asarray(row, float) + 0.5 + Y) / s
        lo, la = n2w.transform(a * px + c * py + e, b * px + d * py + f); return np.c_[g2m(lo, la)]
    blk = (A_.sum(-1) < 330) & ((A_.max(-1) - A_.min(-1)) < 70)     # black linework (railways are black, ticked)
    lo4, la4 = Transformer.from_crs(crs.geodetic_crs, CRS.from_epsg(4326), always_xy=True).transform([lon.min(), lon.max(), lon.max(), lon.min()], [lat.min(), lat.min(), lat.max(), lat.max()])
    face = LineString(np.c_[g2m(np.r_[lo4, lo4[:1]], np.r_[la4, la4[:1]])]).convex_hull     # the sheet's map face, EPSG:3310
    return dict(cost=np.where(ndi.binary_dilation(blk), 1.0, 25.0).astype(np.float32), px2m=px2m, face=face)
USGS = {   # waypoints on the printed railway (sheet px at 300 ppi); sheets in usgs/pdf/ (prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/)
 'Long Beach–San Pedro Line': ('CA_Wilmington_295813_1925', [(4262, 1330), (4256, 1200), (4250, 1060), (4215, 1008), (4000, 1003), (3760, 985), (3655, 958),
                                                              (3500, 905), (3300, 912), (3100, 932), (2900, 950), (2700, 963), (2500, 985), (2350, 993), (2215, 1000)]),
 'San Pedro via Dominguez Line': ('CA_Wilmington_295813_1925', [(2805, 30), (2730, 200), (2640, 350), (2560, 480), (2490, 600), (2420, 720), (2350, 840), (2290, 920),
                                                                (2215, 1000), (2050, 1150), (1955, 1250), (1840, 1350), (1790, 1400), (1640, 1560), (1510, 1660), (1460, 1800),
                                                                (1420, 1900), (1380, 2100), (1340, 2300), (1300, 2450), (1240, 2600), (1180, 2750)]),
 'Hawthorne–El Nido Line': ('CA_Inglewood_291567_1924', [(2200, 4400), (2200, 4900), (2201, 5460)]),
 'Hawthorne–El Nido Line (south)': ('CA_Torrance_295502_1924', [(3722, 5), (3722, 400), (3722, 900), (3720, 1390), (3672, 1600), (3600, 1790), (3560, 1880),
                                                                (3440, 2100), (3360, 2200), (3160, 2500), (3000, 2660), (2720, 2780), (2500, 2840)]),
 'Westgate Line': ('CA_Sawtelle_295108_1925', [(2260, 2930), (2210, 2895), (2170, 2845), (2120, 2785), (2070, 2715), (2000, 2655), (1950, 2630), (1880, 2590), (1775, 2525)]),
}
_sheets = {}
NOSNAP = {'Westgate Line'}     # its private way runs diagonally through a diagonal street grid: snapping would pull it onto a street
def trace_topo(sheet, wps, margin=25, snap=True):
    if sheet not in _sheets: _sheets[sheet] = topo(S + f'usgs/pdf/{sheet}.pdf')
    T = _sheets[sheet]; C = T['cost']; Hc, Wc = C.shape; out = []
    for (u0, v0), (u1, v1) in zip(wps[:-1], wps[1:]):
        x0 = int(max(0, min(u0, u1) - margin)); x1 = int(min(Wc, max(u0, u1) + margin)); y0 = int(max(0, min(v0, v1) - margin)); y1 = int(min(Hc, max(v0, v1) + margin))
        m = MCP_Geometric(C[y0:y1, x0:x1]); m.find_costs([(v0 - y0, u0 - x0)], [(v1 - y0, u1 - x0)])
        p = np.array(m.traceback((v1 - y0, u1 - x0))); seg = np.c_[p[:, 1] + x0, p[:, 0] + y0].astype(float)
        out.append(seg if not out else seg[1:])
    P = np.concatenate(out)
    Q = np.c_[ndi.uniform_filter1d(P[:, 0], 9, mode='nearest'), ndi.uniform_filter1d(P[:, 1], 9, mode='nearest')]; Q[0], Q[-1] = P[0], P[-1]
    L = LineString(T['px2m'](Q[:, 0], Q[:, 1]))
    return snap_line(L, r=40.0, step=10.0, minrun=4, lines=SNAPL_ALL, tree=SNAPTREE_ALL) if snap else L.simplify(6.0)
TOPO = {nm: trace_topo(sh, w, snap=nm not in NOSNAP) for nm, (sh, w) in USGS.items()}
FACE = {nm: _sheets[sh]['face'] for nm, (sh, w) in USGS.items()}       # where a line is traced on a sheet, the sheet replaces the plate
# the Westgate Line west of Westgate ran in the middle of San Vicente Boulevard to Santa Monica: today's centreline
_sv = nx.Graph([(a, b, d) for a, b, d in G.edges(data=True) if d['key'] == 'SAN VICENTE'])
_w0 = Point(TOPO['Westgate Line'].coords[-1])
_n0 = min(_sv.nodes, key=lambda q: _w0.distance(Point(q))); _n1 = min(N('SAN VICENTE') & N('OCEAN'), key=lambda q: q[0])
_pth = nx.shortest_path(_sv, _n0, _n1, weight='len'); _c = []
for a, b in zip(_pth[:-1], _pth[1:]):
    c = G[a][b]['coords']
    if (round(c[0][0]), round(c[0][1])) != a: c = c[::-1]
    _c += c if not _c else c[1:]
TOPO['Westgate Line'] = linemerge([TOPO['Westgate Line'], LineString([TOPO['Westgate Line'].coords[-1]] + _c)])
print('USGS sheets:', {k: round(v.length / 1609.34, 1) for k, v in TOPO.items()}, flush=True)

# ---------------------------------------------------------------- merge, flags, miles
feats, meta = [], []
def add(geom, op, name, src, last=None):
    gl = mapping(geom); parts = gl['coordinates'] if gl['type'] == 'MultiLineString' else [gl['coordinates']]
    out = [[[round(x, 5), round(y, 5)] for x, y in (m2g(*q) for q in part)] for part in parts if len(part) >= 2]
    if not out: return
    feats.append({'type': 'Feature', 'geometry': {'type': 'MultiLineString', 'coordinates': out}, 'properties': {'op': op, 'name': name, 'src': src, 'last': last}})
    meta.append((op, geom, last))
def rest(L, cover, buf=60.0, minlen=200.0):
    if not cover:
        parts = [p for p in (L.geoms if hasattr(L, 'geoms') else [L]) if p.length >= minlen]
        return MultiLineString(parts) if parts else None
    d = L.difference(unary_union(cover).buffer(buf))
    parts = [p for p in (d.geoms if hasattr(d, 'geoms') else [d]) if p.geom_type == 'LineString' and p.length >= minlen]
    return MultiLineString(parts) if parts else None
def name_from(L, named, buf=150.0, need=0.6):
    """the name of the named line that runs along most of L (within buf, for at least `need` of L's length)"""
    best = (0.0, None)
    for nm, gm in named.items():
        f = L.intersection(gm.buffer(buf)).length / max(L.length, 1e-9)
        if f > best[0]: best = (f, nm)
    return best[1] if best[0] >= need else None
# Pacific Electric: inside the 1927 map, the map's own lines come first (it is the company's engineering map of its rail
# lines); then the Wikipedia route maps, the USGS traces, the plate and OpenHistoricalMap fill only what is still missing
taken = []; named = {}
for nm, ls in WIKI.items():
    gm = unary_union(ls); named[nm] = gm
    if nm.startswith('Long Beach Line'): add(gm.simplify(4.0), 'PE', nm, 'wiki', last='1961')
for nm, L in TOPO.items():
    nm2 = nm.replace(' (south)', ''); named[nm2] = unary_union([named[nm2], L]) if nm2 in named else L
traced = {nm: snap_line(LineString(inv(trace(wps)))) for nm, wps in PE_TRACE.items() if nm != 'Hawthorne–Redondo Beach'}   # that one: usgs
for L in SUB27:
    add(L, 'PE', 'Hollywood Subway', 'pe1927'); taken.append(L)
for L in PE27:
    r = rest(L, taken, minlen=60.0)
    if r is None: continue
    add(r, 'PE', name_from(r, {**named, **traced}), 'pe1927'); taken.append(r)
for nm, ls in WIKI.items():
    r = rest(named[nm], taken, buf=150.0, minlen=150.0)
    if r is not None: add(r.simplify(4.0), 'PE', nm, 'wiki'); taken.append(r)
for nm, L in TOPO.items():
    r = rest(L, taken, minlen=100.0)
    if r is not None: add(r, 'PE', nm.replace(' (south)', ''), 'usgs'); taken.append(r)
IN27 = COVER27.buffer(-300.0)          # inside the 1927 map its lines are the record: the plate and OpenHistoricalMap only fill outside it
def outside27(L):
    if L is None or L.is_empty: return None
    d = L.difference(IN27); parts = [p for p in (d.geoms if hasattr(d, 'geoms') else [d]) if p.geom_type == 'LineString' and not p.is_empty and p.length > 1]
    return MultiLineString(parts) if parts else None
for nm, L in traced.items():
    if nm in FACE: L = L.difference(FACE[nm])
    L = outside27(L) if not L.is_empty else None
    r = rest(L, taken, buf=150.0) if L is not None else None        # the plate is good to ~150 m: a parallel trace within that is the same line
    if r is not None: add(r, 'PE', nm.replace(' (south)', ''), 'plate'); taken.append(r)
for L in OHM:
    L = outside27(L)
    r = rest(L, taken) if L is not None else None
    if r is not None: add(r, 'PE', None, 'ohm'); taken.append(r)
# Los Angeles Railway: routed lines (pruned where the 1927 map shows no transit line on the street) > 1927 map
routed = {}; pruned = {}
for nm, spec in LARY.items():
    L = route(spec)
    if L is None: print('no route', nm); continue
    L2, cut = prune_by_1927(L)
    pruned[nm] = round(float(cut) / 1000, 2)
    if L2 is None: continue
    routed[nm] = L2; add(L2, 'LARy', nm, 'streets')
    if nm in LAST_1963: add(L2, 'LARy', nm, 'streets', last='1963')
ltaken = list(routed.values())
for L in LARY27:
    r = rest(L, ltaken, minlen=60.0)
    if r is not None: add(r, 'LARy', None, 'pe1927'); ltaken.append(r)
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
_m27 = REG27['models'][REG27['model']]
def miles_cov(op, cov):
    gs = [gm.buffer(25) for o, gm, last in meta if o == op and last is None]
    return round(unary_union(gs).intersection(cov).area / 50 / 1609.34, 1)
st['old_network'] = {
    'period': 'about 1925 (the networks near their peak); the central lines as drawn on the 1927 engineering map',
    'miles_1925': {'PE': miles('PE'), 'LARy': miles('LARy')},
    'miles_1925_plate_window': {'PE': miles_in('PE'), 'LARy': miles_in('LARy')},
    'miles_1927_map_window': {'PE': miles_cov('PE', COVER27), 'LARy': miles_cov('LARy', COVER27)},
    'miles_by_source': {src: round(unary_union([gm.buffer(25) for (o, gm, last), f in zip(meta, feats) if f['properties']['src'] == src and last is None]).area / 50 / 1609.34, 1)
                        for src in ('wiki', 'usgs', 'pe1927', 'plate', 'ohm', 'streets')},
    'accuracy': {'wiki': 'as drawn by Wikipedia editors on modern maps (tens of metres)',
                 'usgs': 'traced on USGS 1:24,000 sheets of 1924-25, placed by the coordinates printed in each GeoPDF (exact to the survey grid; sheet accuracy about 12 m), snapped to today\'s centrelines within 40 m',
                 'pe1927': f"1927 map georeferenced on {REG27['control_points']} control points ({REG27['model']}, leave-one-out error {_m27['loo_rmse_m']} m), lines snapped to today's street or rail centrelines within 60 m",
                 'plate': 'plate georeference 113 m (leave-one-out RMSE) plus tracing 50-80 m; about half the traced length snapped to a surviving rail or road centreline',
                 'streets': "exact street centrelines, following each article's street list; stretches of 300 m or more on streets where the 1927 map shows no transit line are dropped",
                 'ohm': 'OpenHistoricalMap track, kept only where the plate shows a line within 6 px (about 100 m)'},
    'routed_km_dropped_by_1927_map': pruned,
    'gaps': ['Pacific Electric: the Catalina Dock Line\'s own spur at Wilmington (it used the San Pedro via Dominguez Line to Wilmington; its 1925 dock track cannot be told apart on the sheet); '
             'lines closed before 1925 are left out (Santa Ana-Huntington Beach 1922, East Washington 1923); the Inland Empire lines beyond the 1925 plate (Redlands, Highland, Arrowhead, Riverside-Rialto/Arlington, Upland-Ontario)',
             'Los Angeles Railway: outside the 1927 map, only the lines with a Wikipedia route description; the 1932-1955 numbered routes are not drawn separately'],
    'lines': {'PE_wiki': sorted(WIKI), 'PE_usgs': sorted({k.replace(' (south)', '') for k in USGS}), 'PE_plate': sorted(traced), 'LARy_streets': sorted(routed),
              'last_1961': ['Long Beach Line'], 'last_1963': LAST_1963},
    'method': ('Pacific Electric: Wikipedia route maps where a line has one; the Long Beach-San Pedro, Hawthorne-El Nido and Westgate lines, and the San Pedro via Dominguez Line through Wilmington, traced on USGS 1:24,000 sheets of 1924-25; '
               'in central Los Angeles every rail line drawn solid red on the Pacific Electric engineering department\'s 1927 map (C.E. 8214), extracted by colour, its motor coach '
               '(bus) lines left out by their dashes; elsewhere the lines traced from the 1925 Kelker, De Leuw plate and snapped to surviving rail or road centrelines, and OpenHistoricalMap '
               'track where the plate agrees. Los Angeles Railway: each line routed on today\'s streets from the street sequence its Wikipedia article gives for the 1920s, checked against '
               'the 1927 map, plus every other line drawn solid yellow on that map. The layer shows the networks about 1925; the central lines are as of 1927. '
               'Route miles: lines buffered 25 m and unioned, shared track counted once, per company.'),
    'src': 'Wikipedia line articles and route maps (CC BY-SA); Pacific Electric Railway, map C.E. 8214 (1927) and Kelker, De Leuw & Co. 1925, Plate 1 (LA Metro Research Library); '
           'USGS Historical Topographic Map Collection (Wilmington 1925, Torrance 1924, Inglewood 1924, Sawtelle 1925); OpenHistoricalMap (CC0); LA County CAMS centrelines'}
json.dump(st, open(DAY + 'data/story_stats.json', 'w'), indent=1)
print('features', len(feats), 'PE miles', st['old_network']['miles_1925']['PE'], 'LARy miles', st['old_network']['miles_1925']['LARy'])
print('by source', st['old_network']['miles_by_source'], 'pruned km', pruned)
print(os.path.getsize(DAY + 'data/old_network.geojson') // 1024, 'KB')

# ---------------------------------------------------------------------------------------------------------------
# Last step: smooth the jitter of pixel-traced lines (1927 map, 1925 plate, USGS sheets). A traced line with more
# than two sharp turns (over 60 degrees) is resampled every 10 m, moving-averaged over about 120 m (end points kept)
# and lightly simplified; this moves no line more than about 35 m, within the sources' own accuracy.
import math as _m
from shapely.geometry import shape as _shape, mapping as _mapping, LineString as _LS, MultiLineString as _MLS
from shapely.ops import transform as _tf
_m2g = Transformer.from_crs(3310, 4326, always_xy=True).transform
def _turns(ln):
    c = list(ln.coords); t = 0
    for a, b, cc in zip(c, c[1:], c[2:]):
        v1 = (b[0] - a[0], b[1] - a[1]); v2 = (cc[0] - b[0], cc[1] - b[1]); n1 = _m.hypot(*v1); n2 = _m.hypot(*v2)
        if n1 >= 1 and n2 >= 1 and _m.degrees(_m.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2))))) > 60: t += 1
    return t
def _smooth(ln, k=6):
    n = max(3, int(ln.length / 10)); pts = [ln.interpolate(i / n, normalized=True).coords[0] for i in range(n + 1)]
    out = [pts[0]] + [tuple(sum(p[j] for p in pts[max(0, i - k): i + k + 1]) / len(pts[max(0, i - k): i + k + 1]) for j in (0, 1)) for i in range(1, n)] + [pts[-1]]
    return _LS(out).simplify(3)
def _rnd(o): return [_rnd(v) for v in o] if o and isinstance(o[0], (list, tuple)) else [round(o[0], 5), round(o[1], 5)]
_d = json.load(open(DAY + 'data/old_network.geojson')); _n = 0
for _f in _d['features']:
    if _f['properties']['src'] not in ('pe1927', 'plate', 'usgs'): continue
    _g = _tf(g2m, _shape(_f['geometry'])); _parts = list(_g.geoms) if _g.geom_type == 'MultiLineString' else [_g]
    if sum(_turns(p) for p in _parts) <= 2: continue
    _new = [_smooth(p) if _turns(p) > 2 else p for p in _parts]
    _gm = _mapping(_tf(_m2g, _MLS(_new) if _g.geom_type == 'MultiLineString' else _new[0])); _gm['coordinates'] = _rnd(_gm['coordinates'])
    _f['geometry'] = _gm; _n += 1
json.dump(_d, open(DAY + 'data/old_network.geojson', 'w'), separators=(',', ':'))
print('smoothed', _n, 'traced lines')
