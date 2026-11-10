"""Plates registered without a County outline on them (plate_gcps.py / refit_plate.py read this).

transit1925  Kelker, De Leuw & Co., Report and Recommendations on a Comprehensive Rapid Transit Plan for the City and
             County of Los Angeles (January 1925), Plate 1, "The Complete Plan for the Metropolitan District".
             LA Metro Research Library scan, 7205 x 5385 px at 300 dpi, stored upside down (rotated here).
             https://libraryarchives.metro.net/DPGTL/maps/1925-kelker-deleuw-plan.tif
             First guess: ten towns' station symbols on the plate <-> their present-day centres; the interior control
             points then come from matching today's road and rail network (plate_gcps.py).
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
}
