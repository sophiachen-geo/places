"""USGS Historical Topographic Map Collection (public domain) -> XYZ WebP tiles for each cooperative site.
NAD27 polyconic GeoTIFFs are resampled onto Web Mercator with the NADCON CONUS grid (us_noaa_conus.tif),
so the ~85 m NAD27->WGS84 shift in Los Angeles is corrected."""
import os, math, json
import numpy as np
import rasterio
import pyproj
from pyproj import Transformer, CRS
from PIL import Image
from scipy import ndimage as ndi

S = ''   # run from the working directory that holds raw/, raw2/, orig/, projgrids/
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
pyproj.datadir.append_data_dir(S + 'projgrids')
ORIG = math.pi * 6378137.0
w2g = Transformer.from_crs(3857, 4326, always_xy=True).transform
SITES = {   # id: (file, lon, lat, half-width km, zmin, zmax)
    'llano':     ('CA_Llano_292412_1930_24000_geo.tif',          -117.8271, 34.5065, 2.6, 12, 16),
    'landers':   ('CA_La_Crescenta_291958_1928_24000_geo.tif',   -118.2883, 34.2526, 1.8, 12, 16),
    'village':   ('CA_Hollywood_291374_1953_24000_geo.tif',      -118.3608, 34.0197, 1.5, 12, 16),
    'crestwood': ('CA_Beverly_Hills_288350_1950_24000_geo.tif',  -118.4891, 34.0766, 1.6, 12, 16),
    'elysian':   ('CA_Los_Angeles_292551_1953_24000_geo.tif',    -118.2400, 34.0739, 1.8, 12, 16),
}
def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    return int((lon + 180) / 360 * n), int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
meta = {}
for sid, (fn, lon, lat, hw, zmin, zmax) in SITES.items():
    with rasterio.open(S + 'orig/topo/' + fn) as r:
        A = r.read()                      # (3, H, W)
        inv = ~r.transform
        g2n = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_wkt(r.crs.to_wkt()), always_xy=True)
        year = fn.split('_')[-3]
    dlat = hw / 111.0; dlon = hw / (111.0 * math.cos(math.radians(lat)))
    W0, S0, E0, N0 = lon - dlon, lat - dlat, lon + dlon, lat + dlat
    out = f'{DAY}tiles/topo_{sid}/'
    n = 0
    tx0, ty0 = lonlat_to_tile(W0, N0, zmax); tx1, ty1 = lonlat_to_tile(E0, S0, zmax)
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            span = 2 * ORIG / 2 ** zmax; bx0, by1 = -ORIG + tx * span, ORIG - ty * span
            G = 17
            gx = np.linspace(bx0 + span / 512, bx0 + span - span / 512, G); gy = np.linspace(by1 - span / 512, by1 - span + span / 512, G)
            GX, GY = np.meshgrid(gx, gy)
            lo, la = w2g(GX.ravel(), GY.ravel())
            X, Y = g2n.transform(lo, la)
            col, row = inv * (np.asarray(X), np.asarray(Y))
            C = ndi.zoom(np.asarray(col).reshape(G, G), 256 / G, order=1)[:256, :256]
            R = ndi.zoom(np.asarray(row).reshape(G, G), 256 / G, order=1)[:256, :256]
            LO = ndi.zoom(np.asarray(lo).reshape(G, G), 256 / G, order=1)[:256, :256]
            LA = ndi.zoom(np.asarray(la).reshape(G, G), 256 / G, order=1)[:256, :256]
            inside = (LO >= W0) & (LO <= E0) & (LA >= S0) & (LA <= N0) & (C >= 0) & (R >= 0) & (C < A.shape[2] - 1) & (R < A.shape[1] - 1)
            if not inside.any(): continue
            t = np.zeros((256, 256, 4), np.uint8)
            for c in range(3):
                t[..., c] = ndi.map_coordinates(A[c], [R, C], order=1, mode='nearest')
            t[..., 3] = inside * 255
            os.makedirs(f'{out}{zmax}/{tx}', exist_ok=True)
            Image.fromarray(t, 'RGBA').save(f'{out}{zmax}/{tx}/{ty}.webp', 'WEBP', quality=80, method=6)
            n += 1
    for z in range(zmax - 1, zmin - 1, -1):
        kids = {}
        for tx in os.listdir(f'{out}{z+1}'):
            for f in os.listdir(f'{out}{z+1}/{tx}'):
                ty = int(f.split('.')[0]); kids.setdefault((int(tx) // 2, ty // 2), []).append((int(tx), ty))
        for (px, py), ch in kids.items():
            cv = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
            for cx, cy in ch:
                cv.paste(Image.open(f'{out}{z+1}/{cx}/{cy}.webp'), ((cx - 2 * px) * 256, (cy - 2 * py) * 256))
            os.makedirs(f'{out}{z}/{px}', exist_ok=True)
            cv.resize((256, 256), Image.LANCZOS).save(f'{out}{z}/{px}/{py}.webp', 'WEBP', quality=80, method=6)
    meta[sid] = {'file': fn, 'year': int(year), 'bounds': [[S0, W0], [N0, E0]], 'zmin': zmin, 'zmax': zmax, 'tiles_zmax': n}
    print(sid, year, n)
json.dump(meta, open(DAY + 'img/topo_meta.json', 'w'), indent=1)
