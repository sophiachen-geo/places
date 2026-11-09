"""USGS Historical Topographic Map Collection (public domain) -> XYZ WebP tiles, one set per sheet group.

Source: the GeoPDF of each sheet, whose scan (~650 ppi, ~0.95 m per pixel) is about twice as sharp as
the 300 dpi GeoTIFF. Each PDF carries its own georeference (LGIDict): a CTM from page points to the
sheet's polyconic NAD27 coordinates, and the neatline. The whole map face inside the neatline is tiled,
z12 to z17; the collar (title, legend, margins) is left out because it is not geography.

NAD27 is shifted to WGS84 with the NADCON CONUS grid (us_noaa_conus.tif in projgrids/), about 85 m in
Los Angeles. The CRS comes from the matching GeoTIFF (same projection as the PDF), and each neatline is
checked to land on its survey grid before tiling.

Run from the working directory that holds orig/topo/ (GeoTIFFs), orig/topo_pdf/<id>.pdf and projgrids/:
    DAY=../places/30daymapchallenge/day-08-utopia/ python tiles_topo.py
"""
import os, math, json, subprocess, tempfile
import numpy as np
import rasterio
import pyproj
import pypdf
from pyproj import Transformer, CRS
from PIL import Image
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
pyproj.datadir.append_data_dir('projgrids')
ORIG = math.pi * 6378137.0
w2g = Transformer.from_crs(3857, 4326, always_xy=True).transform
ZMIN, ZMAX, Q = 12, 17, 82

# sheet id: (GeoTIFF for the CRS, year)
SHEETS = {
    'llano':       ('CA_Llano_292412_1930_24000_geo.tif', 1930),
    'lacrescenta': ('CA_La_Crescenta_291958_1928_24000_geo.tif', 1928),
    'hollywood':   ('CA_Hollywood_291374_1953_24000_geo.tif', 1953),
    'beverly':     ('CA_Beverly_Hills_288350_1950_24000_geo.tif', 1950),
    'losangeles':  ('CA_Los_Angeles_292551_1953_24000_geo.tif', 1953),
}
# tile set: sheets mosaicked into it (adjacent sheets of the same year share one seamless set)
SETS = {'llano': ['llano'], 'lacrescenta': ['lacrescenta'], 'beverly': ['beverly'], 'la1953': ['hollywood', 'losangeles']}
# cooperative site: (tile set, its own sheet, lon, lat, half-width km of the framing window)
SITES = {
    'llano':     ('llano', 'llano', -117.8271, 34.5065, 2.6),
    'landers':   ('lacrescenta', 'lacrescenta', -118.2883, 34.2526, 1.8),
    'village':   ('la1953', 'hollywood', -118.3608, 34.0197, 1.5),
    'crestwood': ('beverly', 'beverly', -118.4891, 34.0766, 1.6),
    'elysian':   ('la1953', 'losangeles', -118.2400, 34.0739, 1.8),
}
PDF_ID = {'llano': 'llano', 'lacrescenta': 'landers', 'hollywood': 'village', 'beverly': 'crestwood', 'losangeles': 'elysian'}


def in_poly(poly, x, y):
    """vectorised even-odd point-in-polygon"""
    inside = np.zeros(x.shape, bool)
    xs, ys = poly[:, 0], poly[:, 1]
    for i in range(len(poly)):
        x1, y1, x2, y2 = xs[i - 1], ys[i - 1], xs[i], ys[i]
        crosses = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1)
        inside ^= crosses
    return inside


def load_sheet(sid):
    tif, year = SHEETS[sid]
    with rasterio.open('orig/topo/' + tif) as r:
        crs = CRS.from_wkt(r.crs.to_wkt())
    page = pypdf.PdfReader(f'orig/topo_pdf/{PDF_ID[sid]}.pdf').pages[0]
    L = page['/LGIDict']; L = L[0] if isinstance(L, list) else L
    a, b, c, d, e, f = [float(x) for x in L['/CTM']]
    nl = np.array([float(x) for x in L['/Neatline']]).reshape(-1, 2)          # page points, y up
    H = float(page.mediabox[3])
    # neatline must land on the survey grid (minutes) in the sheet's own NAD27 polyconic
    to_ll = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
    lon, lat = to_ll.transform(a * nl[:, 0] + c * nl[:, 1] + e, b * nl[:, 0] + d * nl[:, 1] + f)
    err = max(np.abs(lon * 60 - np.round(lon * 60 * 2) / 2).max(), np.abs(lat * 60 - np.round(lat * 60 * 2) / 2).max()) * 1852
    assert err < 2, (sid, err)
    # render the neatline box at the scan's own resolution
    ppi = max(int(l.split()[12]) for l in subprocess.run(['pdfimages', '-list', f'orig/topo_pdf/{PDF_ID[sid]}.pdf'],
              capture_output=True, text=True).stdout.splitlines()[2:])
    s = ppi / 72.0
    x0, x1 = nl[:, 0].min() - 2, nl[:, 0].max() + 2
    y0, y1 = H - nl[:, 1].max() - 2, H - nl[:, 1].min() + 2                  # y down
    X, Y, W, Hh = int(x0 * s), int(y0 * s), int(math.ceil((x1 - x0) * s)), int(math.ceil((y1 - y0) * s))
    with tempfile.TemporaryDirectory(dir='.') as td:
        subprocess.run(['pdftoppm', '-r', str(ppi), '-x', str(X), '-y', str(Y), '-W', str(W), '-H', str(Hh),
                        '-singlefile', f'orig/topo_pdf/{PDF_ID[sid]}.pdf', f'{td}/p'], check=True)
        A = np.asarray(Image.open(f'{td}/p.ppm').convert('RGB'))
    return dict(sid=sid, year=year, crs=crs, ctm=(a, b, c, d, e, f), H=H, s=s, X=X, Y=Y, A=A,
                poly=nl, g2n=Transformer.from_crs(CRS.from_epsg(4326), crs, always_xy=True),
                lonlat=(float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max())), err_m=float(err), ppi=ppi)


def wgs_bounds(sh):
    """neatline box in WGS84 (via the datum grid)"""
    n2g = Transformer.from_crs(sh['crs'].geodetic_crs, CRS.from_epsg(4326), always_xy=True)
    W, S, E, N = sh['lonlat']
    lo, la = n2g.transform([W, E, E, W], [S, S, N, N])
    return min(lo), min(la), max(lo), max(la)


def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    return int((lon + 180) / 360 * n), int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)


def sample(sh, lo, la):
    """WGS84 lon/lat grid (256x256) -> RGB + inside-neatline mask from one sheet"""
    a, b, c, d, e, f = sh['ctm']
    E, N = sh['g2n'].transform(lo.ravel(), la.ravel())
    E, N = np.asarray(E).reshape(lo.shape), np.asarray(N).reshape(lo.shape)
    det = a * d - b * c
    px = (d * (E - e) - c * (N - f)) / det                               # page points, y up
    py = (-b * (E - e) + a * (N - f)) / det
    inside = in_poly(sh['poly'], px, py)
    col = px * sh['s'] - sh['X'] - 0.5
    row = (sh['H'] - py) * sh['s'] - sh['Y'] - 0.5
    rgb = np.stack([ndi.map_coordinates(sh['A'][..., k], [row, col], order=1, mode='nearest') for k in range(3)], -1)
    return rgb, inside


meta, sheets = {}, {}
for set_id, members in SETS.items():
    shs = [load_sheet(m) for m in members]
    for sh in shs:
        sheets[sh['sid']] = sh
        print(sh['sid'], 'ppi', sh['ppi'], 'raster', sh['A'].shape, 'neatline grid error m', round(sh['err_m'], 2))
    bb = [wgs_bounds(sh) for sh in shs]
    W0, S0, E0, N0 = min(x[0] for x in bb), min(x[1] for x in bb), max(x[2] for x in bb), max(x[3] for x in bb)
    out = f'{DAY}tiles/topo_{set_id}/'
    n = 0
    tx0, ty0 = lonlat_to_tile(W0, N0, ZMAX); tx1, ty1 = lonlat_to_tile(E0, S0, ZMAX)
    span = 2 * ORIG / 2 ** ZMAX
    G = 17
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            bx0, by1 = -ORIG + tx * span, ORIG - ty * span
            gx = np.linspace(bx0 + span / 512, bx0 + span - span / 512, G); gy = np.linspace(by1 - span / 512, by1 - span + span / 512, G)
            GX, GY = np.meshgrid(gx, gy)
            lo, la = w2g(GX.ravel(), GY.ravel())
            LO = ndi.zoom(np.asarray(lo).reshape(G, G), 256 / G, order=1)[:256, :256]
            LA = ndi.zoom(np.asarray(la).reshape(G, G), 256 / G, order=1)[:256, :256]
            t = np.zeros((256, 256, 4), np.uint8)
            for sh in shs:
                rgb, inside = sample(sh, LO, LA)
                put = inside & (t[..., 3] == 0)
                t[put, :3] = rgb[put]; t[put, 3] = 255
            if not t[..., 3].any():
                continue
            os.makedirs(f'{out}{ZMAX}/{tx}', exist_ok=True)
            Image.fromarray(t, 'RGBA').save(f'{out}{ZMAX}/{tx}/{ty}.webp', 'WEBP', quality=Q, method=6)
            n += 1
    for z in range(ZMAX - 1, ZMIN - 1, -1):
        kids = {}
        for tx in os.listdir(f'{out}{z+1}'):
            for fn in os.listdir(f'{out}{z+1}/{tx}'):
                ty = int(fn.split('.')[0]); kids.setdefault((int(tx) // 2, ty // 2), []).append((int(tx), ty))
        for (px, py), ch in kids.items():
            cv = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
            for cx, cy in ch:
                cv.paste(Image.open(f'{out}{z+1}/{cx}/{cy}.webp'), ((cx - 2 * px) * 256, (cy - 2 * py) * 256))
            os.makedirs(f'{out}{z}/{px}', exist_ok=True)
            cv.resize((256, 256), Image.LANCZOS).save(f'{out}{z}/{px}/{py}.webp', 'WEBP', quality=Q, method=6)
    print(set_id, 'tiles at z%d:' % ZMAX, n)
    for sh in shs:
        sh['A'] = None
    for site, (sset, sheet, lon, lat, hw) in SITES.items():
        if sset != set_id:
            continue
        dlat = hw / 111.0; dlon = hw / (111.0 * math.cos(math.radians(lat)))
        meta[site] = {'file': SHEETS[sheet][0], 'year': SHEETS[sheet][1], 'tiles': set_id,
                      'sheets': [SHEETS[m][0] for m in members],
                      'bounds': [[S0, W0], [N0, E0]],
                      'focus': [[lat - dlat, lon - dlon], [lat + dlat, lon + dlon]],
                      'zmin': ZMIN, 'zmax': ZMAX, 'tiles_zmax': n}
order = ['llano', 'landers', 'village', 'crestwood', 'elysian']
json.dump({k: meta[k] for k in order}, open(DAY + 'img/topo_meta.json', 'w'), indent=1)
