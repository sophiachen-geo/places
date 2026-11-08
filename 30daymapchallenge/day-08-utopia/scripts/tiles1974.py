"""Cut the rubber-sheeted 1974 diagram into XYZ WebP tiles (z9-13; z13 ~ native 12.7 m/px).
Reuses the control points and spline of warp1974.py; samples the native scan directly per tile."""
import os as _os
DAY = _os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
import os, math, json, numpy as np
from PIL import Image
from scipy import ndimage as ndi
exec(open('warp1974.py').read().split('# ---------- 5. leave-one-out')[0])
OUTD = DAY + 'tiles/plan1974/'
R0 = 6378137.0; ORIG = math.pi * R0
def tile_bounds(z, x, y):
    n = 2 ** z; span = 2 * ORIG / n
    return -ORIG + x * span, ORIG - (y + 1) * span, -ORIG + (x + 1) * span, ORIG - y * span
def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return x, y
meta = json.load(open(DAY + 'img/concept1974_warped.json'))
(s_, w_), (n_, e_) = meta['bounds']
ZMAX = 13
x0, y0 = lonlat_to_tile(w_, n_, ZMAX); x1, y1 = lonlat_to_tile(e_, s_, ZMAX)
G = 17
count = 0
for tx in range(x0, x1 + 1):
    for ty in range(y0, y1 + 1):
        bx0, by0, bx1, by1 = tile_bounds(ZMAX, tx, ty)
        gx = np.linspace(bx0, bx1, G); gy = np.linspace(by1, by0, G)
        GX, GY = np.meshgrid(gx, gy)
        lon, lat = w2g(GX.ravel(), GY.ravel())
        uv = model(np.c_[g2m(lon, lat)])
        U = ndi.zoom(uv[:, 0].reshape(G, G), 256 / G, order=1)[:256, :256]
        V = ndi.zoom(uv[:, 1].reshape(G, G), 256 / G, order=1)[:256, :256]
        inside = (U >= 0) & (U < W - 1) & (V >= 0) & (V < V_MAX)
        if not inside.any():
            continue
        t = np.zeros((256, 256, 4), np.uint8)
        for c in range(3):
            t[..., c] = ndi.map_coordinates(A[..., c], [V, U], order=1, mode='nearest')
        t[..., 3] = inside * 255
        os.makedirs(f'{OUTD}{ZMAX}/{tx}', exist_ok=True)
        Image.fromarray(t, 'RGBA').save(f'{OUTD}{ZMAX}/{tx}/{ty}.webp', 'WEBP', quality=80, method=6)
        count += 1
print('z13 tiles', count)
for z in range(ZMAX - 1, 8, -1):
    kids = {}
    for tx in os.listdir(f'{OUTD}{z+1}'):
        for f in os.listdir(f'{OUTD}{z+1}/{tx}'):
            ty = int(f.split('.')[0]); kids.setdefault((int(tx) // 2, ty // 2), []).append((int(tx), ty))
    for (px, py), ch in kids.items():
        canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        for cx, cy in ch:
            canvas.paste(Image.open(f'{OUTD}{z+1}/{cx}/{cy}.webp'), ((cx - 2 * px) * 256, (cy - 2 * py) * 256))
        os.makedirs(f'{OUTD}{z}/{px}', exist_ok=True)
        canvas.resize((256, 256), Image.LANCZOS).save(f'{OUTD}{z}/{px}/{py}.webp', 'WEBP', quality=80, method=6)
    print('z', z, len(kids))
