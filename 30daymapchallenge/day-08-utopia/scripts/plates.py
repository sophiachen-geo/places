"""Plates registered without a County outline on them (plate_gcps.py / refit_plate.py read this).

transit1925  Kelker, De Leuw & Co., Report and Recommendations on a Comprehensive Rapid Transit Plan for the City and
             County of Los Angeles (January 1925), Plate 1, "The Complete Plan for the Metropolitan District".
             LA Metro Research Library scan, 7205 x 5385 px at 300 dpi, stored upside down (rotated here).
             https://libraryarchives.metro.net/DPGTL/maps/1925-kelker-deleuw-plan.tif
             First guess: ten towns' station symbols on the plate <-> their present-day centres; the interior control
             points then come from matching today's road and rail network (plate_gcps.py).
pe1927       Pacific Electric Railway, Office of Chief Engineer, map C.E. 8214 (1927): central Los Angeles street map with the
             Pacific Electric and Los Angeles Railway rail and motor coach lines. LA Metro Research Library scan, 4806 x 5673 px.
             https://libraryarchives.metro.net/DPGTL/maps/1927_pe_lary_engineer.jpg
             The matcher sees the coloured transit lines (they run down the middle of the streets, and their network is
             irregular where the block grid repeats) against County CAMS centrelines of the Highway, Primary and Secondary
             roads and railroads: run plate_gcps.py pe1927 in a working directory whose raw4/roads_major.geojson holds those
             classes over the map (33.86-34.26 N, 118.52-118.05 W). First guess: eight street intersections.
             Then dense_gcps.py pe1927 adds control points at street intersections all over the sheet: the street spaces of
             the blue map (the paper connected between block outlines) reduced to their centrelines, matched locally against
             every County CAMS street centreline (raw4/roads_all_pe1927.geojson: Highway, Primary, Secondary and Minor).
             The sheet is padded with 1400 px of plain paper on every side (all pixel positions below include the pad), so that
             the matcher's first-round templates (4.5 km, searched over 3 km) also fit at sites near the edges of the map.
"""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

def _strokes(m, min_px, min_ext):
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1)); sl = ndi.find_objects(lab)
    ext = np.array([max(a.stop - a.start, b.stop - b.start) for a, b in sl])
    keep = np.zeros(n + 1, bool); keep[1:] = (sizes >= min_px) & (ext >= min_ext)
    return keep[lab]

def _lines_1925(A):
    A = A.astype(int); s = A.sum(-1); red = (A[..., 0] - A[..., 1]) > 70
    m = (s < 520) & ~red                       # brown railways, streetcar lines and town plans; not the red proposals
    m[2025:2100, :] = False                    # the fold across the sheet
    return _strokes(m, 150, 60)

def _load_1925(path):
    Image.MAX_IMAGE_PIXELS = None
    return np.asarray(Image.open(path).convert('RGB').rotate(180))

PAD27 = 1400
def _load_1927(path):
    Image.MAX_IMAGE_PIXELS = None
    A = np.asarray(Image.open(path).convert('RGB'))
    out = np.empty((A.shape[0] + 2 * PAD27, A.shape[1] + 2 * PAD27, 3), np.uint8); out[:] = (220, 206, 196)   # the paper's colour
    out[PAD27:PAD27 + A.shape[0], PAD27:PAD27 + A.shape[1]] = A
    return out

PE1927_OUT = [(100, 150, 450, 470), (4280, 150, 4806, 470), (3600, 4980, 4806, 5673), (0, 5480, 4806, 5673)]   # corner ornaments, legend, title (unpadded px)
def _lines_1927(A):
    """the coloured transit lines (Pacific Electric red, Los Angeles Railway yellow, LA Motor Coach green, Motor Transit
    lavender, the black subway): they run in the middle of the streets and form an irregular network, where the block
    grid of the blue street map repeats itself every few hundred metres and cannot pin a match"""
    A = A.astype(np.int16); R, G, B = A[..., 0], A[..., 1], A[..., 2]
    col = ((R - G > 60) & (R - B > 70)) | ((R - B > 90) & (G - B > 70) & (R > 170)) | ((G - R > 45) & (G - B > 8)) | ((B - G > 18) & (R - G > 10) & (B > 170))
    for x0, y0, x1, y1 in PE1927_OUT: col[y0 + PAD27:y1 + PAD27, x0 + PAD27:x1 + PAD27] = False
    return ndi.binary_opening(col, iterations=1)

def _streets_1927(A):
    """street centrelines of the blue street map: paper (not ink) connected over large areas -- the street spaces, since
    each block is closed by its own outline -- thinned to its medial axis where it is street-wide (<= 9 px to the ink)"""
    from skimage.morphology import skeletonize
    x0, y0, x1, y1 = 250 + PAD27, 300 + PAD27, 4590 + PAD27, 5540 + PAD27
    a = A[y0:y1, x0:x1].astype(np.int16); s = a.sum(-1); R, G, B = a[..., 0], a[..., 1], a[..., 2]
    bg = ndi.maximum_filter(ndi.median_filter(s[::2, ::2], 5), 5)
    bg = np.kron(bg, np.ones((2, 2), np.int16))[:s.shape[0], :s.shape[1]]
    col = ((R - G > 60) & (R - B > 70)) | ((R - B > 90) & (G - B > 70) & (R > 170)) | ((G - R > 45) & (G - B > 8))
    dark = ((bg - s) > 40) & ~ndi.binary_dilation(col, iterations=2)    # the coloured transit lines run in the streets
    del a, s, R, G, B, bg, col
    paper = ~dark
    lab, n = ndi.label(paper); sz = ndi.sum(paper, lab, range(1, n + 1))
    big = np.zeros(n + 1, bool); big[1:] = sz >= 15000
    street = big[lab]; del lab
    edt = ndi.distance_transform_edt(street)
    st = skeletonize(street) & (edt <= 9)
    for a0, b0, c0, d0 in PE1927_OUT:
        st[max(0, b0 + PAD27 - y0):max(0, d0 + PAD27 - y0), max(0, a0 + PAD27 - x0):max(0, c0 + PAD27 - x0)] = False
    out = np.zeros(A.shape[:2], bool); out[y0:y1, x0:x1] = st
    return out

CUSTOM = {
    'transit1925': dict(
        img='dl1925/1925-kelker-deleuw-plan.tif', load=_load_1925, lines=_lines_1925,
        crop=(520, 290, 6630, 5010), zmax=13, window=(-118.72, 33.68, -117.60, 34.36),
        anchors=[((1925, 885), (-118.4390, 34.2819)),    # San Fernando
                 ((977, 1451), (-118.5980, 34.2011)),    # Owensmouth (Canoga Park)
                 ((2225, 3928), (-118.3936, 33.8445)),   # Redondo Beach
                 ((2840, 4635), (-118.2808, 33.7395)),   # San Pedro
                 ((3370, 4436), (-118.1920, 33.7686)),   # Long Beach
                 ((5249, 1878), (-117.8653, 34.1361)),   # Glendora
                 ((3588, 1826), (-118.1497, 34.1456)),   # Pasadena
                 ((4215, 2966), (-118.0328, 33.9792)),   # Whittier
                 ((2697, 1570), (-118.3090, 34.1808)),   # Burbank
                 ((6244, 2750), (-117.6889, 34.0122))],  # Chino
        thr_px=12.0),
    'pe1927': dict(
        img='dl_maps/1927_pe_lary_engineer.jpg', load=_load_1927, lines=_lines_1927, streets=_streets_1927,
        centrelines='raw4/roads_all_pe1927.geojson', dense_cell_m=350, dense_half_m=650, dense_search_m=80, grid_cells=(12, 14), dense_keep=1500,
        crop=(250 + PAD27, 300 + PAD27, 4590 + PAD27, 5540 + PAD27), zmax=15, window=(-118.50, 33.92, -118.08, 34.24),
        anchors=[((2270 + PAD27, 3780 + PAD27), (-118.29154, 34.01838)),   # Vermont Av and Exposition Bl
                 ((2125 + PAD27, 3780 + PAD27), (-118.30018, 34.01818)),   # Normandie Av and Exposition Bl
                 ((2270 + PAD27, 3925 + PAD27), (-118.29156, 34.01087)),   # Vermont Av and Santa Barbara Av (Martin Luther King Jr Bl)
                 ((2920 + PAD27, 1290 + PAD27), (-118.25507, 34.14627)),   # Brand Bl and Broadway, Glendale
                 ((1745 + PAD27, 2180 + PAD27), (-118.32669, 34.10163)),   # Hollywood Bl and Vine St
                 ((1265 + PAD27, 4920 + PAD27), (-118.35334, 33.96178)),   # La Brea Av and Manchester Bl, Inglewood
                 ((3420 + PAD27, 4632 + PAD27), (-118.22523, 33.97421)),   # Pacific Bl and Florence Av
                 ((3540 + PAD27, 1462 + PAD27), (-118.21407, 34.13911))],  # Colorado Bl and Eagle Rock Bl
        thr_px=10.0),
}
