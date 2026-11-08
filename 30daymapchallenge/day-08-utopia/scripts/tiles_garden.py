"""Garden-suburb tiles at parcel precision (z10-14):
  built2026/  every City parcel on the 2026 Assessor roll, a dot at the Assessor's centroid, coloured by
              the Assessor's own UseType (+ use code for 2-4 vs 5+ units)
  zonedsf/    City of LA zoning (live layer, edited 5 Nov 2026): single-family zones (R1/RS/RE/RW1/RZ + RA) filled
"""
import os as _os
DAY = _os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
import os, csv, json, math
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import shape, box
from shapely.strtree import STRtree
from shapely.ops import transform
from pyproj import Transformer

S = ''
T = DAY + 'tiles/'
ORIG = math.pi * 6378137.0
g2w = Transformer.from_crs(4326, 3857, always_xy=True).transform

# ---------------- built 2026 ----------------
CLS = {'sfr': (63, 138, 46), 'adu': (128, 179, 64), 'cnd24': (141, 153, 166), 'apt5': (47, 62, 78), 'oth': (205, 199, 186)}
ORDER = ['oth', 'sfr', 'adu', 'cnd24', 'apt5']          # later classes drawn on top
pts = {k: [] for k in CLS}
with open(S + 'raw2/roll2026_city.csv') as f:
    for a in csv.DictReader(f):
        try:
            lat, lon = float(a['CENTER_LAT']), float(a['CENTER_LON'])
        except ValueError:
            continue
        if not (33.6 < lat < 34.4 and -118.8 < lon < -118.1):
            continue
        ut, code = a['UseType'], a['UseCode'] or ''
        units = int(float(a['Units'] or 0))
        if ut == 'SFR':
            k = 'adu' if units >= 2 else 'sfr'
        elif ut == 'CND' or (ut == 'R-I' and code[:2] in ('02', '03', '04')):
            k = 'cnd24'
        elif ut == 'R-I':
            k = 'apt5'
        elif ut == 'VAC':
            continue
        else:
            k = 'oth'
        pts[k].append((lon, lat))
print({k: len(v) for k, v in pts.items()})
XY = {k: np.array([g2w(lo, la) for lo, la in v]) for k, v in pts.items()}
allxy = np.vstack(list(XY.values()))
minx, miny = allxy.min(0); maxx, maxy = allxy.max(0)

def tiles_for(z):
    span = 2 * ORIG / 2 ** z
    return (int((minx + ORIG) // span), int((ORIG - maxy) // span), int((maxx + ORIG) // span), int((ORIG - miny) // span), span)

SIZE = {10: 1, 11: 1, 12: 2, 13: 2, 14: 3}
ALPHA = {10: 150, 11: 180, 12: 220, 13: 255, 14: 255}
nb = 0
for z in range(10, 15):
    tx0, ty0, tx1, ty1, span = tiles_for(z)
    res = span / 256
    buf = {}
    for k in ORDER:
        P = XY[k]
        if not len(P):
            continue
        gx = ((P[:, 0] + ORIG) / res).astype(np.int64); gy = ((ORIG - P[:, 1]) / res).astype(np.int64)
        tx, ty = gx // 256, gy // 256; px, py = gx % 256, gy % 256
        col = np.array(CLS[k] + (ALPHA[z],), np.uint8)
        key = tx * 100000 + ty
        order = np.argsort(key)
        key, px, py, tx, ty = key[order], px[order], py[order], tx[order], ty[order]
        bounds = np.r_[0, np.nonzero(np.diff(key))[0] + 1, len(key)]
        s = SIZE[z]
        for i in range(len(bounds) - 1):
            a, b = bounds[i], bounds[i + 1]
            t = (int(tx[a]), int(ty[a]))
            if t not in buf:
                buf[t] = np.zeros((256 + s, 256 + s, 4), np.uint8)
            arr = buf[t]
            for dx in range(s):
                for dy in range(s):
                    arr[py[a:b] + dy, px[a:b] + dx] = col
    for (tx, ty), arr in buf.items():
        d = f'{T}built2026/{z}/{tx}'; os.makedirs(d, exist_ok=True)
        Image.fromarray(arr[:256, :256], 'RGBA').save(f'{d}/{ty}.webp', 'WEBP', lossless=True, method=6)
        nb += 1
    print('built z', z, len(buf))

# ---------------- zoned single-family ----------------
z3310 = json.load(open(S + 'raw/zoning_3310.geojson'))
m2w = Transformer.from_crs(3310, 3857, always_xy=True).transform
SFZ = {'Single Family Residential', 'Suburban'}
polys = [transform(m2w, shape(f['geometry'])) for f in z3310['features'] if f['geometry'] and f['properties']['CATEGORY'] in SFZ]
tree = STRtree(polys)
FILL = (63, 138, 46, 120); EDGE = (40, 100, 30, 200)
nz = 0
for z in range(10, 15):
    span = 2 * ORIG / 2 ** z; res = span / 256
    ux0 = min(p.bounds[0] for p in polys); uy0 = min(p.bounds[1] for p in polys)
    ux1 = max(p.bounds[2] for p in polys); uy1 = max(p.bounds[3] for p in polys)
    for tx in range(int((ux0 + ORIG) // span), int((ux1 + ORIG) // span) + 1):
        for ty in range(int((ORIG - uy1) // span), int((ORIG - uy0) // span) + 1):
            bx0 = -ORIG + tx * span; by1 = ORIG - ty * span
            tb = box(bx0, by1 - span, bx0 + span, by1)
            idx = tree.query(tb)
            if not len(idx):
                continue
            im = Image.new('RGBA', (256, 256), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
            for i in idx:
                g = polys[i]
                for pg in getattr(g, 'geoms', [g]):
                    ring = [((x - bx0) / res, (by1 - y) / res) for x, y in pg.exterior.coords]
                    dr.polygon(ring, fill=FILL, outline=EDGE if z >= 13 else None)
                    for h in pg.interiors:
                        dr.polygon([((x - bx0) / res, (by1 - y) / res) for x, y in h.coords], fill=(0, 0, 0, 0))
            if im.getbbox() is None:
                continue
            d = f'{T}zonedsf/{z}/{tx}'; os.makedirs(d, exist_ok=True)
            im.save(f'{d}/{ty}.webp', 'WEBP', lossless=True, method=6)
            nz += 1
    print('zoned z', z, nz)
