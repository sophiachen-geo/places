"""Interior control points for a historical regional plate (1930 parks plan, 1946 parkways plan) by local pattern matching.

The first registration (register_plate.py) was fitted to the County outline only, so the interior drifted (e.g. the
San Gabriel Valley on the 1930 plate, Pasadena on the 1946 plate). Here, in two rounds (coarse, then fine):
  1. sites on a regular grid over the plate, each a junction of today's major roads / railways
     (LA County CAMS centrelines: Highway, Primary, Railroad) plus the County outline and coast;
  2. today's lines around a site are drawn into the plate's pixel space with the current model;
  3. that pattern is slid over the plate's own linework (roads/railways isolated by colour and by keeping only long
     connected strokes, so lettering and terrain stipple drop out) by normalised cross-correlation;
  4. the best offset gives a control point (site lon/lat <-> plate pixel) when the peak is strong and unambiguous;
  5. a RANSAC fit (2nd-order polynomial) keeps the consistent ones and becomes the model for the next round.

usage: python plate_gcps.py <name>   -> work2/gcps_<name>.json, work2/gcps_<name>_sheet*.jpg (QA: today's lines in magenta)
"""
import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
from shapely.geometry import shape, LineString, box
from shapely import STRtree
from pyproj import Transformer
from collections import Counter

NAME = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'register_plate.py')
sys.path.insert(0, HERE)
from plates import CUSTOM
ANCH = {'parks1930': '[[68,853,-118.8065,34.0011],[307,550,-118.6551,34.1771],[107,550,-118.7759,34.1803],[1745,966,-117.7786,33.9330],[1844,830,-117.7230,34.0067],[1781,825,-117.7604,34.0098]]'}
if NAME in CUSTOM:                             # a plate with no County outline: first guess from its anchors
    from shapely.geometry import shape as _shape
    cfg = CUSTOM[NAME]
    A = cfg['load'](cfg['img'])
    g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
    Ga = np.array([g2m(*ll) for _, ll in cfg['anchors']]); Pa = np.array([uv for uv, _ in cfg['anchors']], float)
    _M, *_ = np.linalg.lstsq(np.c_[Ga, np.ones(len(Ga))], Pa, rcond=None)
    model = lambda xy: np.c_[np.asarray(xy, float), np.ones(len(xy))] @ _M
    inv_scale = 1 / math.sqrt(abs(np.linalg.det(_M[:2])))
    print('anchor residuals px', np.round(np.hypot(*(model(Ga) - Pa).T)).astype(int).tolist(), f'~{inv_scale:.1f} m per px')
    C = {'crop': cfg['crop'], 'zmax': cfg['zmax']}
    cb = _shape(json.load(open('raw2/county_boundary.geojson'))['features'][0]['geometry'])
    main = max(cb.geoms, key=lambda p: p.area) if cb.geom_type == 'MultiPolygon' else cb
else:
    sys.argv = ['register_plate.py', NAME] + ([ANCH[NAME]] if NAME in ANCH else [])
    exec(open(SRC).read().split('# tiles')[0])     # -> A (plate RGB), C (config), model (EPSG:3310 m -> plate px), inv_scale, main, g2m
mpp = float(inv_scale)
m2g_ = Transformer.from_crs(3310, 4326, always_xy=True).transform
x0c, y0c, x1c, y1c = C['crop']

def strokes(m, min_px, min_ext):
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1)); sl = ndi.find_objects(lab)
    ext = np.array([max(a.stop - a.start, b.stop - b.start) for a, b in sl])
    keep = np.zeros(n + 1, bool); keep[1:] = (sizes >= min_px) & (ext >= min_ext)
    return keep[lab]
Ai = A.astype(int); s_ = Ai.sum(-1); sat = Ai.max(-1) - Ai.min(-1)
LINES = (lambda: CUSTOM[NAME]['lines'](A)) if NAME in CUSTOM else {
         'parks1930': lambda: strokes((s_ < 230) & (sat < 60), 120, 40),          # thick black roads and railways
         'parkways1946': lambda: strokes((s_ > 200) & (s_ < 560) & (sat < 40), 60, 30)}[NAME]   # grey existing roads
LINES = LINES()
I = ndi.gaussian_filter(LINES.astype(float), 1.0)
crop = np.zeros_like(LINES); crop[y0c:y1c, x0c:x1c] = True
I[~crop] = 0

roads = [shape(f['geometry']) for f in json.load(open('raw4/roads_major.geojson'))['features'] if f.get('geometry')]
lines_m = []
for g in roads:
    for l in (g.geoms if g.geom_type.startswith('Multi') else [g]):
        lines_m.append(LineString([g2m(x, y) for x, y in l.coords]))
lines_m.append(LineString([g2m(x, y) for x, y in main.exterior.coords]))
tree = STRtree(lines_m)
ends = Counter()
for l in lines_m[:-1]:
    for p in (l.coords[0], l.coords[-1]): ends[(round(p[0], -1), round(p[1], -1))] += 1
J = np.array([k for k, v in ends.items() if v >= 3], float)

def render(model, center_m, R_m, half_px):
    cu, cv = model(center_m[None])[0]
    W = 2 * half_px + 1
    im = Image.new('L', (W, W), 0); d = ImageDraw.Draw(im)
    clip = box(center_m[0] - R_m, center_m[1] - R_m, center_m[0] + R_m, center_m[1] + R_m)
    for i in tree.query(clip):
        seg = lines_m[i].intersection(clip)
        for s in (seg.geoms if hasattr(seg, 'geoms') else [seg]):
            if s.is_empty or s.length < 1: continue
            n = max(2, int(s.length / (mpp / 2)))
            pts = np.array([s.interpolate(t * s.length / (n - 1)).coords[0] for t in range(n)])
            d.line([tuple(p) for p in model(pts) - [cu, cv] + half_px], fill=255, width=2)
    return np.asarray(im, float) / 255, cu, cv

def match(model, R_m, search_m, step_m):
    S = int(round(search_m / mpp)); half = int(R_m / mpp)
    JP = model(J)
    ok = (JP[:, 0] > x0c + 10) & (JP[:, 0] < x1c - 10) & (JP[:, 1] > y0c + 10) & (JP[:, 1] < y1c - 10)
    Jk, JPk = J[ok], JP[ok]
    cells = {}
    for k, (u, v) in enumerate(JPk):
        key = (int(u * mpp // step_m), int(v * mpp // step_m))
        cu, cv = (key[0] + 0.5) * step_m / mpp, (key[1] + 0.5) * step_m / mpp
        dd = math.hypot(u - cu, v - cv)
        if key not in cells or dd < cells[key][0]: cells[key] = (dd, k)
    out = []
    for _, k in cells.values():
        T, cu, cv = render(model, Jk[k], R_m, half)
        if T.sum() < 60: continue
        T = ndi.gaussian_filter(T, 1.0)
        u0, v0 = int(round(cu)) - half - S, int(round(cv)) - half - S
        if u0 < 0 or v0 < 0 or u0 + T.shape[1] + 2 * S > A.shape[1] or v0 + T.shape[0] + 2 * S > A.shape[0]: continue
        Iw = I[v0:v0 + T.shape[0] + 2 * S, u0:u0 + T.shape[1] + 2 * S]
        if Iw.sum() < 30: continue
        num = fftconvolve(Iw, T[::-1, ::-1], mode='valid')
        en = fftconvolve(Iw ** 2, np.ones_like(T), mode='valid')
        score = num / np.sqrt(en * (T ** 2).sum() + 1e-9)
        j = np.unravel_index(np.argmax(score), score.shape); best = score[j]
        yy, xx = np.mgrid[:score.shape[0], :score.shape[1]]
        far = np.hypot(yy - j[0], xx - j[1]) > max(4, 600 / mpp)
        second = score[far].max() if far.any() else 0
        dv, du = j[0] - S, j[1] - S
        lo, la = m2g_(*Jk[k])
        out.append({'lon': float(lo), 'lat': float(la), 'x': float(Jk[k][0]), 'y': float(Jk[k][1]), 'u': float(cu + du), 'v': float(cv + dv),
                    'du': int(du), 'dv': int(dv), 'score': round(float(best), 3), 'ratio': round(float(best / max(second, 1e-6)), 3),
                    'edge': bool(abs(du) >= S - 1 or abs(dv) >= S - 1)})
    return out

def poly2(G, P):
    mu, sd = G.mean(0), G.std(0)
    F = lambda X: (lambda z: np.c_[np.ones(len(z)), z, z ** 2, z[:, :1] * z[:, 1:]])((np.asarray(X, float) - mu) / sd)
    M, *_ = np.linalg.lstsq(F(G), P, rcond=None)
    return lambda X: F(X) @ M

def ransac(gc, thr_px, iters=3000, seed=0):
    rng = np.random.default_rng(seed)
    G = np.array([[o['x'], o['y']] for o in gc]); P = np.array([[o['u'], o['v']] for o in gc])
    best = None
    for _ in range(iters):
        idx = rng.choice(len(G), 8, replace=False)
        try: f = poly2(G[idx], P[idx])
        except np.linalg.LinAlgError: continue
        inl = np.hypot(*(f(G) - P).T) < thr_px
        if best is None or inl.sum() > best.sum(): best = inl
    f = poly2(G[best], P[best])
    for _ in range(3):                                   # refine on the consensus set
        inl = np.hypot(*(f(G) - P).T) < thr_px; f = poly2(G[inl], P[inl])
    return f, inl

THR = CUSTOM[NAME]['thr_px'] if NAME in CUSTOM else {'parks1930': 4.0, 'parkways1946': 3.0}[NAME]       # ~240 m / ~280 m / ~190 m
rounds = []
cur = model
for rnd, (R_m, search_m, step_m) in enumerate([(4500, 3000, 6000), (2500, 1100, 3500)]):
    gc = match(cur, R_m, search_m, step_m)
    cand = [o for o in gc if not o['edge'] and o['ratio'] >= 1.04 and o['score'] >= 0.2]
    f, inl = ransac(cand, THR * (1.6 if rnd == 0 else 1.0))
    for o, k in zip(cand, inl): o['inlier'] = bool(k)
    print(f'round {rnd}: sites {len(gc)}, candidates {len(cand)}, inliers {int(inl.sum())}')
    rounds.append(cand); cur = f

final = [o for o in rounds[-1] if o['inlier']]
json.dump({'name': NAME, 'mpp': mpp, 'gcps': rounds[-1]}, open(f'work2/gcps_{NAME}.json', 'w'), indent=1)
G = np.array([[o['x'], o['y']] for o in final]); P = np.array([[o['u'], o['v']] for o in final])
res = np.hypot(*(cur(G) - P).T) * mpp
print(f'final {len(final)} control points; poly2 residual median {np.median(res):.0f} m, RMSE {np.sqrt((res ** 2).mean()):.0f} m')

def tile(o, sz=140):
    u, v = o['u'], o['v']
    cr = Image.fromarray(A).crop((int(u - sz / 2), int(v - sz / 2), int(u + sz / 2), int(v + sz / 2))).convert('RGB').resize((sz * 2, sz * 2), Image.LANCZOS)
    dq = ImageDraw.Draw(cr)
    T, cu, cv = render(lambda X: cur(X) + [o['u'] - cur(np.array([[o['x'], o['y']]]))[0][0], o['v'] - cur(np.array([[o['x'], o['y']]]))[0][1]],
                       np.array([o['x'], o['y']]), 2500, int(2500 / mpp))
    half = int(2500 / mpp)
    ys, xs = np.nonzero(T > 0.5)
    for X_, Y_ in zip(xs[::2], ys[::2]):
        pu = (X_ - half + cu - (u - sz / 2)) * 2; pv = (Y_ - half + cv - (v - sz / 2)) * 2
        if 0 <= pu < sz * 2 and 0 <= pv < sz * 2: dq.point((pu, pv), fill=(255, 0, 200))
    dq.ellipse((sz - 6, sz - 6, sz + 6, sz + 6), outline=(0, 140, 255), width=2)
    dq.rectangle((0, 0, sz * 2, 14), fill=(255, 255, 255)); dq.text((3, 2), f"{o['lat']:.3f},{o['lon']:.3f} s{o['score']} r{o['ratio']} {'IN' if o.get('inlier') else 'out'}", fill=(0, 0, 0))
    return cr
for si in range(0, len(final), 24):
    chunk = final[si:si + 24]; W6 = 6
    sheet = Image.new('RGB', (W6 * 280, ((len(chunk) + W6 - 1) // W6) * 280), 'white')
    for i, o in enumerate(chunk): sheet.paste(tile(o), ((i % W6) * 280, (i // W6) * 280))
    sheet.save(f'work2/gcps_{NAME}_sheet{si // 24}.jpg', quality=85)
# where the control points are, over the plate
ov = Image.fromarray(A).convert('RGB'); do = ImageDraw.Draw(ov)
for o in rounds[-1]:
    c = (0, 170, 0) if o['inlier'] else (230, 0, 0)
    do.ellipse((o['u'] - 6, o['v'] - 6, o['u'] + 6, o['v'] + 6), outline=c, width=3)
ov.crop(C['crop']).save(f'work2/gcps_{NAME}_spread.jpg', quality=80)
