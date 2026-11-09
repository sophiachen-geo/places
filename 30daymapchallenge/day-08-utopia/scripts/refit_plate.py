"""Refit a historical plate on its interior control points (plate_gcps.py) and cut new tiles.

Models compared on the same control points, by leave-one-out error (each point predicted from all the others) and by
distortion (spread of local scale; worst local stretch between directions):
  affine (no bending) · 2nd- and 3rd-order polynomials (gentle bending) · thin-plate splines (local bending)
Among models whose leave-one-out RMSE is within 10% of the best, the one with the least local stretch is kept.

usage: python refit_plate.py <name>   -> tiles/<name>/ (z9..zmax), img/<name>_registration.json
"""
import sys, os, json, math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import RBFInterpolator

NAME = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
ANCH = {'parks1930': '[[68,853,-118.8065,34.0011],[307,550,-118.6551,34.1771],[107,550,-118.7759,34.1803],[1745,966,-117.7786,33.9330],[1844,830,-117.7230,34.0067],[1781,825,-117.7604,34.0098]]'}
sys.argv = ['register_plate.py', NAME] + ([ANCH[NAME]] if NAME in ANCH else [])
exec(open(os.path.join(HERE, 'register_plate.py')).read().split('# tiles')[0])   # A, C, g2m, w2g, DAY
gj = json.load(open(f'work2/gcps_{NAME}.json'))
mpp = gj['mpp']
pts = [o for o in gj['gcps'] if o.get('inlier')]
G = np.array([[o['x'], o['y']] for o in pts]); P = np.array([[o['u'], o['v']] for o in pts])

def poly(order):
    def fit(G, P):
        mu, sd = G.mean(0), G.std(0)
        def F(X):
            z = (np.asarray(X, float) - mu) / sd; x, y = z[:, :1], z[:, 1:]
            cols = [np.ones_like(x)] + [x ** (i - j) * y ** j for i in range(1, order + 1) for j in range(i + 1)]
            return np.hstack(cols)
        M, *_ = np.linalg.lstsq(F(G), P, rcond=None)
        return lambda X: F(X) @ M
    return fit
def tps(sm):        # in kilometres, so the smoothing term is on the same footing as the bending energy
    def fit(G, P):
        f = RBFInterpolator(np.asarray(G, float) / 1000.0, P, kernel='thin_plate_spline', smoothing=sm)
        return lambda X: f(np.asarray(X, float) / 1000.0)
    return fit
MODELS = {'affine': poly(1), 'poly2': poly(2), 'poly3': poly(3),
          'tps_s1000': tps(1000.0), 'tps_s200': tps(200.0), 'tps_s50': tps(50.0), 'tps_s10': tps(10.0)}

gx, gy = np.meshgrid(np.linspace(G[:, 0].min(), G[:, 0].max(), 60), np.linspace(G[:, 1].min(), G[:, 1].max(), 60))
GG = np.c_[gx.ravel(), gy.ravel()]
def distortion(f):
    e = 100.0; u0 = f(GG); ux = (f(GG + [e, 0]) - u0) / e; uy = (f(GG + [0, e]) - u0) / e
    s = np.linalg.svd(np.stack([ux, uy], -1), compute_uv=False); area = s[:, 0] * s[:, 1]
    return float(np.std(area) / np.mean(area) * 100), float(np.percentile(s[:, 0] / s[:, 1], 95))
rows = {}
for name, fit in MODELS.items():
    f = fit(G, P)
    res = np.hypot(*(f(G) - P).T) * mpp
    loo = []
    for i in range(len(G)):
        k = np.ones(len(G), bool); k[i] = False
        loo.append(math.hypot(*(fit(G[k], P[k])(G[i:i + 1]) - P[i:i + 1])[0]) * mpp)
    loo = np.array(loo); sv, an = distortion(f)
    rows[name] = dict(rmse_m=round(float(np.sqrt((res ** 2).mean()))), loo_rmse_m=round(float(np.sqrt((loo ** 2).mean()))),
                      loo_median_m=round(float(np.median(loo))), loo_p90_m=round(float(np.percentile(loo, 90))),
                      scale_variation_pct=round(sv, 1), stretch_p95=round(an, 3))
    print(name, rows[name], flush=True)
best = min(r['loo_rmse_m'] for r in rows.values())
ok = [n for n in rows if rows[n]['loo_rmse_m'] <= best * 1.10]          # as accurate as the best, within 10%
pick = min(ok, key=lambda n: (rows[n]['stretch_p95'], rows[n]['loo_rmse_m']))   # ...then the one that bends the scan least
model = MODELS[pick](G, P)
print('kept', pick, rows[pick])

# tiles (same grid and window as register_plate.py)
ORIG = math.pi * 6378137.0
def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    return int((lon + 180) / 360 * n), int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
OUTD = f'{DAY}tiles/{NAME}/'
lon0, lat0, lon1, lat1 = C['window']; pad = 0.15; Z = C['zmax']
tx0, ty0 = lonlat_to_tile(lon0 - pad, lat1 + pad, Z); tx1, ty1 = lonlat_to_tile(lon1 + pad, lat0 - pad, Z)
GN = 17; n = 0
for tx in range(tx0, tx1 + 1):
    for ty in range(ty0, ty1 + 1):
        span = 2 * ORIG / 2 ** Z
        bx0, by1 = -ORIG + tx * span, ORIG - ty * span
        gx_ = np.linspace(bx0, bx0 + span, GN); gy_ = np.linspace(by1, by1 - span, GN)
        GX, GY = np.meshgrid(gx_, gy_)
        lon, lat = w2g(GX.ravel(), GY.ravel())
        uv = model(np.c_[g2m(lon, lat)])
        U = ndi.zoom(uv[:, 0].reshape(GN, GN), 256 / GN, order=1)[:256, :256]
        V = ndi.zoom(uv[:, 1].reshape(GN, GN), 256 / GN, order=1)[:256, :256]
        inside = (U >= x0c) & (U < x1c - 1) & (V >= y0c) & (V < y1c - 1)
        if not inside.any(): continue
        t = np.zeros((256, 256, 4), np.uint8)
        for c in range(3):
            t[..., c] = ndi.map_coordinates(A[..., c], [V, U], order=1, mode='nearest')
        t[..., 3] = inside * 255
        os.makedirs(f'{OUTD}{Z}/{tx}', exist_ok=True)
        Image.fromarray(t, 'RGBA').save(f'{OUTD}{Z}/{tx}/{ty}.webp', 'WEBP', quality=85, method=6)
        n += 1
for z in range(Z - 1, 8, -1):
    kids = {}
    for tx in os.listdir(f'{OUTD}{z+1}'):
        for fn in os.listdir(f'{OUTD}{z+1}/{tx}'):
            ty = int(fn.split('.')[0]); kids.setdefault((int(tx) // 2, ty // 2), []).append((int(tx), ty))
    for (px, py), ch in kids.items():
        cv = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        for cx, cy in ch:
            cv.paste(Image.open(f'{OUTD}{z+1}/{cx}/{cy}.webp'), ((cx - 2 * px) * 256, (cy - 2 * py) * 256))
        os.makedirs(f'{OUTD}{z}/{px}', exist_ok=True)
        cv.resize((256, 256), Image.LANCZOS).save(f'{OUTD}{z}/{px}/{py}.webp', 'WEBP', quality=85, method=6)
json.dump({'name': NAME, 'method': 'interior control points by local pattern matching against LA County road and rail centrelines (plate_gcps.py), model chosen by leave-one-out error and distortion',
           'control_points': len(G), 'm_per_px': round(mpp), 'model': pick, 'models': rows, 'zmax': Z},
          open(f'{DAY}img/{NAME}_registration.json', 'w'), indent=1)
print('tiles z', Z, n)
