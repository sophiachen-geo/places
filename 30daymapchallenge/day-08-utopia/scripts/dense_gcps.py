"""Dense interior control points for a street-map plate (plates.py entries with a 'streets' image), after plate_gcps.py.

plate_gcps.py gives a first model from a few dozen points matched on the plate's major linework. Here:
  1. sites: today's street intersections (County CAMS centrelines, every street class but railroads and freeways),
     one per `dense_cell_m` cell, nearest the cell's centre;
  2. at each site today's streets within `dense_half_m` are drawn into the plate's pixel space with the current model
     and slid (normalised cross-correlation) over the plate's own street centrelines within `dense_search_m`;
  3. a point is kept when its peak is clear of the next one (ratio >= 1.05) and agrees with its neighbours: a local
     affine fitted to the 10 nearest other points must predict it within max(6 px, 3 robust sigma);
  4. every cell of a `grid_cells` grid over the plate that has streets but no point is searched again with all its
     intersections (up to 8 sites);
  5. the whole is run twice, the second time with the model refitted on the first round's points;
  6. where the leave-one-out residuals cluster (a point off by more than 25 m: folds, paper stretch, the sheet's edges),
     every intersection within 1.2 km on a 150 m cell is matched as well, and empty cells are searched with all of their
     intersections (up to 20, clear-peak ratio 1.03); the consensus is then rerun on everything.
Validation: 20% of the points (seeded) are held out, the models are fitted on the rest, and the held-out residuals are
reported next to the leave-one-out figures; refit_plate.py then fits on all points and selects the model.

usage: python dense_gcps.py <name>  (in plate_gcps.py's working directory)
  -> work2/gcps_<name>.json (dense; the plate_gcps.py points kept as 'seed'), work2/gcps_<name>_validation.json,
     work2/gcps_<name>_coverage.jpg (points coloured by leave-one-out residual, residual vectors x20, the grid)
"""
import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree
from shapely.geometry import shape, LineString, box
from shapely import STRtree
from pyproj import Transformer
from collections import Counter

NAME = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from plates import CUSTOM
cfg = CUSTOM[NAME]
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
m2g = Transformer.from_crs(3310, 4326, always_xy=True).transform
A = cfg['load'](cfg['img'])
x0c, y0c, x1c, y1c = cfg['crop']
seed = json.load(open(f'work2/gcps_{NAME}.json'))
mpp = seed['mpp']
if 'seed' in seed: seed['gcps'] = seed['seed']               # rerun: start again from plate_gcps.py's points
seed_pts = [o for o in seed['gcps'] if o.get('inlier')]
S = cfg['streets'](A).astype(np.float32)
I = ndi.gaussian_filter(S, 1.2)
del S

def tps(G, P, sm):
    f = RBFInterpolator(np.asarray(G, float) / 1000.0, np.asarray(P, float), kernel='thin_plate_spline', smoothing=sm)
    return lambda X: f(np.asarray(X, float) / 1000.0)

# today's streets, densified to <= 60 m so a curved model bends them correctly
lines_m = []
for f in json.load(open(cfg['centrelines']))['features']:
    g = f.get('geometry'); ty = f['properties']['Type']
    if not g or ty in ('Railroad', 'Freeway', 'Ramp'): continue
    for l in (g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]):
        if len(l) < 2: continue
        L = LineString([g2m(*q[:2]) for q in l])
        n = max(2, int(math.ceil(L.length / 60.0)) + 1)
        lines_m.append(np.array([L.interpolate(i / (n - 1), normalized=True).coords[0] for i in range(n)]))
tree = STRtree([LineString(c) for c in lines_m])
ends = Counter()
for c in lines_m:
    for p in (c[0], c[-1]): ends[(round(p[0], -1), round(p[1], -1))] += 1
J = np.array([k for k, v in ends.items() if v >= 3], float)
print('streets', len(lines_m), 'intersections', len(J), flush=True)

OUT = [(a + 1400, b + 1400, c + 1400, d + 1400) for a, b, c, d in __import__('plates').PE1927_OUT] if NAME == 'pe1927' else []
def usable(u, v, m=40):
    if not (x0c + m < u < x1c - m and y0c + m < v < y1c - m): return False
    return not any(a - m < u < c + m and b - m < v < d + m for a, b, c, d in OUT)

HALF_M, SEARCH_M = cfg['dense_half_m'], cfg['dense_search_m']
half = int(HALF_M / mpp); Sx = int(round(SEARCH_M / mpp))
def match(model, site):
    cu, cv = model(site[None])[0]
    if not usable(cu, cv, half // 2): return None
    W = 2 * half + 1
    im = Image.new('L', (W, W), 0); d = ImageDraw.Draw(im)
    clip = box(site[0] - HALF_M * 1.2, site[1] - HALF_M * 1.2, site[0] + HALF_M * 1.2, site[1] + HALF_M * 1.2)
    idx = tree.query(clip)
    if len(idx) < 6: return None
    pts = np.concatenate([lines_m[i] for i in idx]); cut = np.cumsum([len(lines_m[i]) for i in idx])[:-1]
    uv = model(pts) - [cu, cv] + half
    for seg in np.split(uv, cut): d.line([tuple(p) for p in seg], fill=255, width=2)
    T = ndi.gaussian_filter(np.asarray(im, np.float32) / 255, 1.2)
    if T.sum() < 80: return None
    u0, v0 = int(round(cu)) - half - Sx, int(round(cv)) - half - Sx
    Iw = I[v0:v0 + W + 2 * Sx, u0:u0 + W + 2 * Sx]
    if Iw.shape != (W + 2 * Sx, W + 2 * Sx) or Iw.sum() < 40: return None
    num = fftconvolve(Iw, T[::-1, ::-1], mode='valid')
    en = fftconvolve(Iw ** 2, np.ones_like(T), mode='valid')
    sc = num / np.sqrt(en * (T ** 2).sum() + 1e-9)
    j = np.unravel_index(np.argmax(sc), sc.shape); best = sc[j]
    yy, xx = np.mgrid[:sc.shape[0], :sc.shape[1]]
    far = np.hypot(yy - j[0], xx - j[1]) > 5
    second = sc[far].max() if far.any() else 0
    dv, du = j[0] - Sx, j[1] - Sx
    # sub-pixel peak (parabola in each direction)
    if 0 < j[0] < sc.shape[0] - 1:
        a, b, c = sc[j[0] - 1, j[1]], best, sc[j[0] + 1, j[1]]; dv += 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    if 0 < j[1] < sc.shape[1] - 1:
        a, b, c = sc[j[0], j[1] - 1], best, sc[j[0], j[1] + 1]; du += 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    lo, la = m2g(*site)
    return dict(lon=float(lo), lat=float(la), x=float(site[0]), y=float(site[1]), u=float(cu + du), v=float(cv + dv),
                du=round(float(du), 2), dv=round(float(dv), 2), score=round(float(best), 3), ratio=round(float(best / max(second, 1e-6)), 3),
                edge=bool(abs(j[0] - Sx) >= Sx - 1 or abs(j[1] - Sx) >= Sx - 1))

def consensus(pts, k=10, it=6):
    """local-affine agreement: each point predicted from its k nearest others"""
    G = np.array([[o['x'], o['y']] for o in pts]); P = np.array([[o['u'], o['v']] for o in pts]); ok = np.ones(len(G), bool)
    for _ in range(it):
        tr = cKDTree(G[ok]); gi = np.nonzero(ok)[0]; e = np.zeros(len(G))
        for i in range(len(G)):
            _, nn = tr.query(G[i], k + 1); nn = [gi[q] for q in np.atleast_1d(nn) if gi[q] != i][:k]
            X = np.c_[G[nn], np.ones(len(nn))]; M, *_ = np.linalg.lstsq(X, P[nn], rcond=None)
            e[i] = np.hypot(*(np.r_[G[i], 1] @ M - P[i]))
        sig = 1.4826 * np.median(e[ok]); thr = max(6.0, 3 * sig)
        new = e <= thr
        if (new == ok).all(): break
        ok = new
    return ok, e

def cell_of(u, v, nx, ny):
    return (min(nx - 1, int((u - x0c) / (x1c - x0c) * nx)), min(ny - 1, int((v - y0c) / (y1c - y0c) * ny)))

NX, NY = cfg['grid_cells']
model = tps([[o['x'], o['y']] for o in seed_pts], [[o['u'], o['v']] for o in seed_pts], 50.0)
for rnd in range(2):
    CELL = cfg['dense_cell_m']
    best = {}
    for p in J:
        key = (int(p[0] // CELL), int(p[1] // CELL)); c = (np.array(key) + 0.5) * CELL; d = np.hypot(*(p - c))
        if key not in best or d < best[key][0]: best[key] = (d, p)
    sites = [p for _, p in best.values()]
    res = [m for m in (match(model, s) for s in sites) if m]
    cand = [o for o in res if not o['edge'] and o['ratio'] >= 1.05 and o['score'] >= 0.15]
    ok, e = consensus(cand)
    pts = [o for o, k in zip(cand, ok) if k]
    # fill empty grid cells that have streets
    have = Counter(cell_of(o['u'], o['v'], NX, NY) for o in pts)
    JP = model(J); cellJ = {}
    for p, (u, v) in zip(J, JP):
        if usable(u, v, half // 2): cellJ.setdefault(cell_of(u, v, NX, NY), []).append(p)
    extra = []
    for c, ps in cellJ.items():
        if have.get(c): continue
        ctr = np.mean(ps, 0); ps = sorted(ps, key=lambda q: np.hypot(*(q - ctr)))[:8]
        extra += [m for m in (match(model, s) for s in ps) if m]
    cand2 = cand + [o for o in extra if not o['edge'] and o['ratio'] >= 1.05 and o['score'] >= 0.15]
    ok, e = consensus(cand2)
    for o, k, ee in zip(cand2, ok, e): o['inlier'] = bool(k); o['local_px'] = round(float(ee), 2)
    pts = [o for o in cand2 if o['inlier']]
    print(f'round {rnd}: sites {len(sites)} + {len(extra)} cell fills, candidates {len(cand2)}, inliers {len(pts)}', flush=True)
    model = tps([[o['x'], o['y']] for o in pts], [[o['u'], o['v']] for o in pts], 50.0)
# 6. densify where the residuals cluster
Gq = np.array([[o['x'], o['y']] for o in pts]); Pq = np.array([[o['u'], o['v']] for o in pts])
looq = np.zeros(len(Gq))
for i in range(len(Gq)):
    k = np.ones(len(Gq), bool); k[i] = False; looq[i] = np.hypot(*(tps(Gq[k], Pq[k], 50.0)(Gq[i:i + 1]) - Pq[i:i + 1])[0]) * mpp
hot = Gq[looq > 25.0]
print('points off by more than 25 m:', len(hot), flush=True)
done = {(round(o['x'], -1), round(o['y'], -1)) for o in cand2}
near = cKDTree(hot).query(J, distance_upper_bound=1200)[0] < 1200 if len(hot) else np.zeros(len(J), bool)
best = {}
for p in J[near]:
    key = (int(p[0] // 150), int(p[1] // 150)); c = (np.array(key) + 0.5) * 150; d = np.hypot(*(p - c))
    if key not in best or d < best[key][0]: best[key] = (d, p)
more = [m for m in (match(model, p) for _, p in best.values() if (round(p[0], -1), round(p[1], -1)) not in done) if m]
have = Counter(cell_of(o['u'], o['v'], NX, NY) for o in pts)
JP = model(J); cellJ = {}
for p, (u, v) in zip(J, JP):
    if usable(u, v, half // 2): cellJ.setdefault(cell_of(u, v, NX, NY), []).append(p)
fill = []
for c, ps in cellJ.items():
    if have.get(c): continue
    ctr = np.mean(ps, 0); ps = sorted(ps, key=lambda q: np.hypot(*(q - ctr)))[:20]
    fill += [m for m in (match(model, p) for p in ps) if m]
cand3 = cand2 + [o for o in more if not o['edge'] and o['ratio'] >= 1.05 and o['score'] >= 0.15] \
              + [o for o in fill if not o['edge'] and o['ratio'] >= 1.03 and o['score'] >= 0.15]
ok, e = consensus(cand3)
for o, k, ee in zip(cand3, ok, e): o['inlier'] = bool(k); o['local_px'] = round(float(ee), 2)
pts = [o for o in cand3 if o['inlier']]
print(f'round 2 (residual clusters): +{len(more)} sites near {len(hot)} points, +{len(fill)} in empty cells; candidates {len(cand3)}, inliers {len(pts)}', flush=True)
model = tps([[o['x'], o['y']] for o in pts], [[o['u'], o['v']] for o in pts], 50.0)
allc = cand3

# coverage of the grid
have = Counter(cell_of(o['u'], o['v'], NX, NY) for o in pts)
JP = model(J); streetcells = {cell_of(u, v, NX, NY) for u, v in JP if usable(u, v, 10)}
empty = sorted(c for c in streetcells if not have.get(c))
print(f'grid {NX}x{NY}: {len(streetcells)} cells with streets, {len(empty)} without a point: {empty}')

# validation: 20% held out; LOO for reference
G = np.array([[o['x'], o['y']] for o in pts]); P = np.array([[o['u'], o['v']] for o in pts])
rng = np.random.default_rng(0); hold = np.zeros(len(G), bool); hold[rng.choice(len(G), int(round(0.2 * len(G))), replace=False)] = True
def poly(order):
    def fit(G, P):
        mu, sd = G.mean(0), G.std(0)
        F = lambda X: (lambda z: np.hstack([np.ones((len(z), 1))] + [z[:, :1] ** (i - j) * z[:, 1:] ** j for i in range(1, order + 1) for j in range(i + 1)]))((np.asarray(X, float) - mu) / sd)
        M, *_ = np.linalg.lstsq(F(G), P, rcond=None); return lambda X: F(X) @ M
    return fit
MODELS = {'affine': poly(1), 'poly2': poly(2), 'poly3': poly(3), 'tps_s1000': lambda G, P: tps(G, P, 1000.0), 'tps_s200': lambda G, P: tps(G, P, 200.0),
          'tps_s50': lambda G, P: tps(G, P, 50.0), 'tps_s10': lambda G, P: tps(G, P, 10.0)}
val = {}
for nm, fit in MODELS.items():
    f = fit(G[~hold], P[~hold]); r = np.hypot(*(f(G[hold]) - P[hold]).T) * mpp
    loo = []
    for i in range(len(G)):
        k = np.ones(len(G), bool); k[i] = False; loo.append(np.hypot(*(fit(G[k], P[k])(G[i:i + 1]) - P[i:i + 1])[0]) * mpp)
    loo = np.array(loo)
    val[nm] = dict(check_rmse_m=round(float(np.sqrt((r ** 2).mean())), 1), check_median_m=round(float(np.median(r)), 1), check_p90_m=round(float(np.percentile(r, 90)), 1),
                   loo_rmse_m=round(float(np.sqrt((loo ** 2).mean())), 1), loo_median_m=round(float(np.median(loo)), 1), loo_p90_m=round(float(np.percentile(loo, 90)), 1))
    print(nm, val[nm], flush=True)
    if nm == 'tps_s50': LOO50 = loo
json.dump({'name': NAME, 'n': int(len(G)), 'n_checkpoints': int(hold.sum()), 'grid': [NX, NY], 'cells_with_streets': len(streetcells),
           'cells_without_point': [list(c) for c in empty], 'models': val}, open(f'work2/gcps_{NAME}_validation.json', 'w'), indent=1)
json.dump({'name': NAME, 'mpp': mpp, 'gcps': allc, 'seed': seed['gcps']}, open(f'work2/gcps_{NAME}.json', 'w'), indent=1)

# coverage image: points coloured by leave-one-out residual (tps_s50), residual vectors x20, the grid
sc = 4
prev = Image.fromarray(A[y0c:y1c:sc, x0c:x1c:sc]).convert('RGB')
prev = Image.blend(prev, Image.new('RGB', prev.size, 'white'), 0.45); d = ImageDraw.Draw(prev)
for i in range(1, NX): xx = (x1c - x0c) / NX * i / sc; d.line([(xx, 0), (xx, prev.size[1])], fill=(120, 120, 120))
for j in range(1, NY): yy = (y1c - y0c) / NY * j / sc; d.line([(0, yy), (prev.size[0], yy)], fill=(120, 120, 120))
f50 = MODELS['tps_s50']
for i, (g, p) in enumerate(zip(G, P)):
    k = np.ones(len(G), bool); k[i] = False
    q = f50(G[k], P[k])(G[i:i + 1])[0]
    r = LOO50[i]; col = (0, 150, 0) if r < 20 else (230, 160, 0) if r < 40 else (220, 0, 0)
    u, v = (p[0] - x0c) / sc, (p[1] - y0c) / sc
    d.line([(u, v), (u + (p[0] - q[0]) * 20 / sc, v + (p[1] - q[1]) * 20 / sc)], fill=col, width=2)
    d.ellipse((u - 5, v - 5, u + 5, v + 5), fill=col, outline=(0, 0, 0) if hold[i] else None, width=2)
for c in empty:
    cx = (c[0] + 0.5) * (x1c - x0c) / NX / sc; cy = (c[1] + 0.5) * (y1c - y0c) / NY / sc
    d.rectangle((cx - 8, cy - 8, cx + 8, cy + 8), outline=(0, 0, 255), width=2)
d.rectangle((0, 0, 560, 40), fill=(255, 255, 255))
d.text((6, 4), f'{NAME}: {len(G)} control points (black ring = checkpoint); colour = leave-one-out residual of tps_s50:', fill=(0, 0, 0))
d.text((6, 20), 'green < 20 m, orange 20-40 m, red > 40 m; lines = residual x20; blue box = grid cell with streets but no point', fill=(0, 0, 0))
prev.save(f'work2/gcps_{NAME}_coverage.jpg', quality=88)
