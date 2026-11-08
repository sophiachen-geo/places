"""Register a historical regional plate (1930 Olmsted-Bartholomew, 1946 RPC parkways) to the County's surveyed
boundary + shoreline, then cut XYZ WebP tiles.

  1. 3-4 hand-identified anchors -> affine (pixel <-> EPSG:3310)
  2. iterative closest point: samples every 500 m along the surveyed county outline (coast + county lines)
     are matched to the nearest dark line pixel on the plate, radius shrinking 70 -> 25 px, outliers rejected
  3. thin-plate spline (smallest fold-free smoothing) on the final correspondences
  4. tiles z9..zmax over the plate's map area

usage: python register_plate.py <name>   (config below)
"""
import sys, os, json, math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree
from shapely.geometry import shape, LineString, Polygon, box
from pyproj import Transformer

S = ''   # run from the working directory that holds raw/, raw2/, orig/, projgrids/
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
w2g = Transformer.from_crs(3857, 4326, always_xy=True).transform

CFG = {
  'parkways1946': dict(img=S + 'orig/p1946-000.png', crop=(500, 140, 1860, 930), zmax=12,
      dark=lambda r, g, b: (r + g + b < 330) & (r < 140),
      anchors=[  # (u, v) on the plate  ->  (lon, lat)
          ((541, 512), (-118.9445, 34.0427)),    # LA/Ventura county line at the coast (Leo Carrillo)
          ((1140, 898), (-118.2935, 33.7055)),   # Point Fermin
          ((1743.5, 519), (-117.7230, 34.0067)), # LA/San Bernardino line turns west (County boundary vertex)
          ((1706, 519), (-117.7604, 34.0098)),   # ...and turns south
          ((1687, 610), (-117.7786, 33.9330)),   # LA/Orange line begins (vertex)
          ((1502.5, 612.5), (-117.9719, 33.9377)), # LA/Orange line turns south (vertex)
          ((1500, 660), (-117.9735, 33.8943)),   # next vertex south
      ],
      window=(-118.95, 33.70, -117.65, 34.42)),
  'parks1930': dict(img=S + 'orig/p1930-004.jpg', crop=(230, 20, 2100, 1283), zmax=12,
      dark=lambda r, g, b: (r + g + b < 300),
      anchors=[],   # filled from CLI json if given
      window=(-118.81, 33.80, -117.60, 34.45)),
}
name = sys.argv[1]
C = CFG[name]
if len(sys.argv) > 2:
    C['anchors'] = [((a[0], a[1]), (a[2], a[3])) for a in json.loads(sys.argv[2])]
A = np.asarray(Image.open(C['img']).convert('RGB'))
H, W = A.shape[:2]
x0c, y0c, x1c, y1c = C['crop']
r, g, b = (A[..., i].astype(int) for i in range(3))
dark = C['dark'](r, g, b)
mask = np.zeros_like(dark); mask[y0c:y1c, x0c:x1c] = True
dark &= mask
dv, du = np.nonzero(dark)
tree = cKDTree(np.c_[du, dv].astype(float))
print('dark px', len(du))

# surveyed outline: mainland exterior ring of the County boundary, inside the window
cb = shape(json.load(open(S + 'raw2/county_boundary.geojson'))['features'][0]['geometry'])
main = max(cb.geoms, key=lambda p: p.area)
ring = LineString(main.exterior.coords).intersection(box(*C['window']))
G_s = []
for seg in getattr(ring, 'geoms', [ring]):
    sm = LineString([g2m(x, y) for x, y in seg.coords])
    n = max(int(sm.length // 500), 1)
    G_s += [sm.interpolate(i * sm.length / n).coords[0] for i in range(n + 1)]
G_s = np.array(G_s)

Pa = np.array([a[0] for a in C['anchors']], float)
Ga = np.array([g2m(*a[1]) for a in C['anchors']], float)
def affine(src, dst):
    M, *_ = np.linalg.lstsq(np.c_[src, np.ones(len(src))], dst, rcond=None)
    return lambda xy: np.c_[xy, np.ones(len(xy))] @ M
model = affine(Ga, Pa)
inv_scale = np.sqrt(abs(np.linalg.det(np.linalg.lstsq(np.c_[Pa, np.ones(len(Pa))], Ga, rcond=None)[0][:2])))
print(f'~{inv_scale:.0f} m per plate pixel')

def folds(m):
    gx, gy = np.meshgrid(np.linspace(G_s[:, 0].min(), G_s[:, 0].max(), 120), np.linspace(G_s[:, 1].min(), G_s[:, 1].max(), 120))
    uv = m(np.c_[gx.ravel(), gy.ravel()]); U = uv[:, 0].reshape(gx.shape); V = uv[:, 1].reshape(gx.shape)
    det = np.gradient(U, axis=1) * np.gradient(V, axis=0) - np.gradient(U, axis=0) * np.gradient(V, axis=1)
    return int((np.sign(det) != np.sign(np.median(det))).sum())

ok = None
for it, (rad, kind) in enumerate([(70, 'aff'), (50, 'aff'), (40, 'poly'), (30, 'poly'), (25, 'tps'), (25, 'tps')]):
    guess = model(G_s)
    d, idx = tree.query(guess)
    ok = d < rad
    if ok.sum() > 12:
        res = d[ok]; ok &= d < max(3 * np.median(res), 4)
    Gm, Pm = np.r_[Ga, G_s[ok]], np.r_[Pa, tree.data[idx[ok]]]
    if kind == 'aff':
        model = affine(Gm, Pm)
    elif kind == 'poly':
        def feats(xy, mu=Gm.mean(0), sd=Gm.std(0)):
            z = (xy - mu) / sd
            return np.c_[np.ones(len(z)), z, z ** 2, z[:, :1] * z[:, 1:]]
        Mq, *_ = np.linalg.lstsq(feats(Gm), Pm, rcond=None)
        model = (lambda F, M: (lambda xy: F(xy) @ M))(feats, Mq)
    else:
        for sm in (300, 1000, 3000, 10000):
            cand = RBFInterpolator(Gm, Pm, kernel='thin_plate_spline', smoothing=sm)
            if folds(cand) == 0: break
        model = cand
    print(f'iter {it} [{kind}] r={rad}: {ok.sum()} outline matches, median residual {np.median(d[ok]) * inv_scale:.0f} m')

# residual on the outline (px -> m)
d, idx = tree.query(model(G_s))
res_m = d[ok] * inv_scale
print(f'final: {ok.sum()} control points on the surveyed outline; median {np.median(res_m):.0f} m, p90 {np.percentile(res_m, 90):.0f} m')

# tiles
ORIG = math.pi * 6378137.0
def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    return int((lon + 180) / 360 * n), int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
OUTD = f'{DAY}tiles/{name}/'
lon0, lat0, lon1, lat1 = C['window']
pad = 0.15
tx0, ty0 = lonlat_to_tile(lon0 - pad, lat1 + pad, C['zmax']); tx1, ty1 = lonlat_to_tile(lon1 + pad, lat0 - pad, C['zmax'])
GN = 17; n = 0
for tx in range(tx0, tx1 + 1):
    for ty in range(ty0, ty1 + 1):
        span = 2 * ORIG / 2 ** C['zmax']
        bx0, by1 = -ORIG + tx * span, ORIG - ty * span
        gx = np.linspace(bx0, bx0 + span, GN); gy = np.linspace(by1, by1 - span, GN)
        GX, GY = np.meshgrid(gx, gy)
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
        os.makedirs(f'{OUTD}{C["zmax"]}/{tx}', exist_ok=True)
        Image.fromarray(t, 'RGBA').save(f'{OUTD}{C["zmax"]}/{tx}/{ty}.webp', 'WEBP', quality=82, method=6)
        n += 1
print('tiles z', C['zmax'], n)
for z in range(C['zmax'] - 1, 8, -1):
    kids = {}
    for tx in os.listdir(f'{OUTD}{z+1}'):
        for f in os.listdir(f'{OUTD}{z+1}/{tx}'):
            ty = int(f.split('.')[0]); kids.setdefault((int(tx) // 2, ty // 2), []).append((int(tx), ty))
    for (px, py), ch in kids.items():
        cv = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        for cx, cy in ch:
            cv.paste(Image.open(f'{OUTD}{z+1}/{cx}/{cy}.webp'), ((cx - 2 * px) * 256, (cy - 2 * py) * 256))
        os.makedirs(f'{OUTD}{z}/{px}', exist_ok=True)
        cv.resize((256, 256), Image.LANCZOS).save(f'{OUTD}{z}/{px}/{py}.webp', 'WEBP', quality=82, method=6)
json.dump({'name': name, 'control_points': int(ok.sum()) + len(Pa), 'median_m': round(float(np.median(res_m))),
           'p90_m': round(float(np.percentile(res_m, 90))), 'm_per_px': round(float(inv_scale)), 'zmax': C['zmax']},
          open(f'{DAY}img/{name}_registration.json', 'w'), indent=1)
# QA overlay: surveyed outline drawn on the plate
from PIL import ImageDraw
qa = Image.fromarray(A).convert('RGB'); dq = ImageDraw.Draw(qa)
pts = model(G_s)
for (u, v), k in zip(pts, ok):
    dq.ellipse((u - 3, v - 3, u + 3, v + 3), outline=(0, 0, 255) if k else (255, 0, 0), width=2)
qa.crop(C['crop']).save(f'qa_{name}.jpg', quality=85)
