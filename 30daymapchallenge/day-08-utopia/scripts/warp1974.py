"""Rubber-sheet the 1974 Concept Los Angeles diagram (native 300-ppi scan) onto Web Mercator.

Control points
  * 56 centers: disc centres detected on the scan  <->  exact street-centerline intersections of each
    center's named core (LA County CAMS address lines, live).
  * Coastline: the drawn shoreline (dark line bounding the white sea, found by flood fill)  <->  the
    LA County boundary shoreline (County of LA, edited Nov 2025), matched by nearest neighbour after
    pre-alignment, iterated twice. Port/harbour excluded (drawn schematically).
Model: thin-plate spline geo(EPSG:3310) -> scan pixel; the five centers drawn on the shoreline are excluded and the
smallest smoothing with no fold is chosen. Writes img/concept1974_warped.json (bounds, control points, leave-one-out error).
"""
import os as _os
DAY = _os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
import json, math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree
from shapely.geometry import shape, LineString, Polygon
from pyproj import Transformer

Image.MAX_IMAGE_PIXELS = None
S = ''
OUT = DAY + 'img/'
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
m2g = Transformer.from_crs(3310, 4326, always_xy=True).transform
g2w = Transformer.from_crs(4326, 3857, always_xy=True).transform
w2g = Transformer.from_crs(3857, 4326, always_xy=True).transform

src = Image.open(S + 'dl/native-000.jpg').convert('RGB')
A = np.asarray(src)
V_MAX = 5850                         # below this the sheet is title/legend text, not map
H, W = A.shape[:2]

# ---------- 1. centers ----------
REN = {'Civic Center (west circle)': 'Bunker Hill (unlabelled circle)', 'Civic Center (east circle)': 'Civic Center',
       'Regional Core — unlabelled (Westlake)': 'Westlake (unlabelled circle)'}
disc = {REN.get(c['name'], c['name']): (c['u'], c['v']) for c in json.load(open(S + 'work2/circles_native.json'))}
core = {c['name']: (c['lng'], c['lat']) for c in json.load(open(S + 'work/centers_exact.json'))['centers']}
names = sorted(disc)
assert set(names) == set(core), set(names) ^ set(core)
COASTAL = {'Santa Monica', 'Venice', 'Redondo Beach', 'San Pedro', 'Long Beach'}   # drawn on the shoreline itself
names = [n for n in names if n not in COASTAL]
P_c = np.array([disc[n] for n in names], float)                       # pixel (u, v)
G_c = np.array([g2m(*core[n]) for n in names], float)                # metres (3310)

def affine(src_xy, dst_xy):
    M, *_ = np.linalg.lstsq(np.c_[src_xy, np.ones(len(src_xy))], dst_xy, rcond=None)
    return lambda xy: np.c_[xy, np.ones(len(xy))] @ M
aff_g2p = affine(G_c, P_c)
aff_p2g = affine(P_c, G_c)
res_aff = np.hypot(*(aff_p2g(P_c) - G_c).T)
print(f'affine on {len(names)} inland centers: RMSE {np.sqrt((res_aff**2).mean()):.0f} m, max {res_aff.max():.0f} m')

# ---------- 2. drawn shoreline ----------
# Suburbs are bare paper (same white as the sea), so colour cannot separate land from sea. The drawn
# shoreline (dark line) and beach strip (green) form a barrier; the sea is the white region connected
# to the open ocean inside the map frame. Shore = dark line pixels touching that region (south of the
# Santa Monica Mountains, where the surveyed coast is sampled).
r, g, b = (A[:V_MAX, :, i].astype(int) for i in range(3))
dark = (r + g + b) < 450
green = (g > r + 15) & (g > b + 40)
barrier = ndi.binary_dilation(dark | green, iterations=6)
frame = np.zeros_like(barrier); frame[:, :40] = 1; frame[:, 4780:] = 1; frame[:140] = 1
lab, _ = ndi.label(~(barrier | frame))
sea = lab == lab[5200, 600]
shore = dark & ndi.binary_dilation(sea, iterations=10)
shore[:2700] = False; shore[:, 4700:] = False
sv, su = np.nonzero(shore)
shore_px = np.c_[su, sv].astype(float)
print('shoreline pixels', len(shore_px))
tree = cKDTree(shore_px)

# ---------- 3. surveyed shoreline ----------
cb = json.load(open(S + 'raw2/county_boundary.geojson'))['features'][0]['geometry']
main = max(shape(cb).geoms, key=lambda p: p.area)
ring = LineString(main.exterior.coords)
win = Polygon([(-118.57, 33.69), (-118.30, 33.69), (-118.30, 34.06), (-118.57, 34.06)])   # Palisades -> Pt Fermin; LB shore is drawn behind breakwaters
port = Polygon([(-118.295, 33.69), (-118.16, 33.69), (-118.16, 33.785), (-118.295, 33.785)])
coast = ring.intersection(win).difference(port.buffer(0))
samples = []
for seg in getattr(coast, 'geoms', [coast]):
    sm = LineString([g2m(x, y) for x, y in seg.coords])
    n = max(int(sm.length // 900), 1)
    samples += [sm.interpolate(i * sm.length / n).coords[0] for i in range(n + 1)]
G_s = np.array(samples, float)

# ---------- 4. iterate correspondences ----------
def fit(smooth):
    model = lambda Gxy: aff_g2p(Gxy)
    for it, tol in enumerate((110, 70, 45, 45)):                    # search radius in sheet px (~1.4 km -> 0.6 km)
        d, idx = tree.query(model(G_s))
        ok = d < tol
        G_all = np.r_[G_c, G_s[ok]]; P_all = np.r_[P_c, shore_px[idx[ok]]]
        model = RBFInterpolator(G_all, P_all, kernel='thin_plate_spline', smoothing=smooth)
    return model, G_all, P_all, ok, idx

def folds(model):
    gx, gy = np.meshgrid(np.linspace(G_c[:, 0].min() - 8e3, G_c[:, 0].max() + 8e3, 160),
                         np.linspace(G_c[:, 1].min() - 8e3, G_c[:, 1].max() + 8e3, 200))
    uv = model(np.c_[gx.ravel(), gy.ravel()]); U = uv[:, 0].reshape(gx.shape); V = uv[:, 1].reshape(gx.shape)
    du_dx = np.gradient(U, axis=1); du_dy = np.gradient(U, axis=0); dv_dx = np.gradient(V, axis=1); dv_dy = np.gradient(V, axis=0)
    det = du_dx * dv_dy - du_dy * dv_dx
    return int((np.sign(det) != np.sign(np.median(det))).sum())

for SMOOTH in (40, 150, 500, 1500, 5000, 15000):
    model, G_all, P_all, ok, idx = fit(SMOOTH)
    nf = folds(model)
    print(f'smoothing {SMOOTH}: {ok.sum()} shoreline GCPs, folded cells {nf}')
    if nf == 0:
        break

# ---------- 5. leave-one-out residuals on the centers ----------
loo = []
for i in range(len(G_c)):
    keep = np.ones(len(G_all), bool); keep[i] = False
    f = RBFInterpolator(G_all[keep], P_all[keep], kernel='thin_plate_spline', smoothing=SMOOTH)
    du, dv = (f(G_c[i:i + 1]) - P_c[i:i + 1])[0]
    loo.append(math.hypot(du, dv))
px_m = np.sqrt(abs(np.linalg.det(np.linalg.lstsq(np.c_[P_c, np.ones(len(P_c))], G_c, rcond=None)[0][:2])))
loo_m = np.array(loo) * px_m
print(f'scale ≈ {px_m:.1f} m/px; leave-one-out center error: median {np.median(loo_m):.0f} m, p90 {np.percentile(loo_m, 90):.0f} m')

# ---------- 6. warp onto a regular EPSG:3857 grid ----------
corners_px = np.array([[0, 0], [W, 0], [W, V_MAX], [0, V_MAX]], float)
cg = [m2g(*xy) for xy in aff_p2g(corners_px)]
lon0, lon1 = min(c[0] for c in cg) - 0.03, max(c[0] for c in cg) + 0.03
lat0, lat1 = min(c[1] for c in cg) - 0.03, max(c[1] for c in cg) + 0.03
x0, y0 = g2w(lon0, lat0); x1, y1 = g2w(lon1, lat1)
RES = 22.0                                                          # web-mercator m/px (~18 m on the ground)
nx, ny = int((x1 - x0) / RES), int((y1 - y0) / RES)
STEP = 8
gx = np.linspace(x0, x1, nx // STEP + 2); gy = np.linspace(y1, y0, ny // STEP + 2)
GX, GY = np.meshgrid(gx, gy)
lon, lat = w2g(GX.ravel(), GY.ravel())
mx, my = g2m(lon, lat)
uv = model(np.c_[mx, my])
U = uv[:, 0].reshape(GX.shape); Vv = uv[:, 1].reshape(GX.shape)
U = ndi.zoom(U, (ny / U.shape[0], nx / U.shape[1]), order=1)
Vv = ndi.zoom(Vv, (ny / Vv.shape[0], nx / Vv.shape[1]), order=1)
out = np.zeros((ny, nx, 4), np.uint8)
for c in range(3):
    out[..., c] = ndi.map_coordinates(A[..., c], [Vv, U], order=1, mode='constant', cval=255)
inside = (U >= 0) & (U < W - 1) & (Vv >= 0) & (Vv < V_MAX)
out[..., 3] = np.where(inside, 255, 0)
img = Image.fromarray(out, 'RGBA')
img.save('work2/concept1974_warped_preview.webp', 'WEBP', quality=82, method=6)   # QA preview only; the site uses tiles1974.py
sw = w2g(x0, y0); ne = w2g(x1, y1)
meta = {
    'bounds': [[round(sw[1], 6), round(sw[0], 6)], [round(ne[1], 6), round(ne[0], 6)]],
    'size_px': [nx, ny], 'res_webmerc_m': RES,
    'gcps': {'inland_centers': len(G_c), 'shoreline': int(ok.sum()), 'tps_smoothing': SMOOTH},
    'affine_rmse_m': round(float(np.sqrt((res_aff ** 2).mean()))),
    'loo_center_error_m': {'median': round(float(np.median(loo_m))), 'p90': round(float(np.percentile(loo_m, 90))), 'max': round(float(loo_m.max()))},
    'source': 'Los Angeles City Planning Dept., Concept Los Angeles diagram, adopted 3 Apr 1974 (LA Metro Research Library scan, 300 ppi)',
}
json.dump(meta, open(OUT + 'concept1974_warped.json', 'w'), indent=1)
print(json.dumps(meta, indent=1), img.size)
