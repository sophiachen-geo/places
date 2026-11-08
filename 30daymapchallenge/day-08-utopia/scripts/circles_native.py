import numpy as np, json
from PIL import Image
from scipy import ndimage as ndi
im = np.asarray(Image.open('dl/native-000.jpg').convert('RGB')).astype(int)
cut = 6000; im = im[:cut]
r, g, b = im[..., 0], im[..., 1], im[..., 2]
red = (r > 190) & (g < 110) & (b < 110)
red = ndi.binary_closing(red, structure=np.ones((3, 3)), iterations=6)
red = ndi.binary_fill_holes(red)
rad = 64
yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1]; disk = (xx ** 2 + yy ** 2) <= rad ** 2
er = ndi.binary_erosion(red, structure=disk)
lab, n = ndi.label(er)
cs = ndi.center_of_mass(er, lab, range(1, n + 1))
pts = [(float(x), float(y)) for y, x in cs]
# map to the 150-dpi names (earlier detection x2), add the 7 hand-recovered ones
g150 = json.load(open('work/centers_georef.json'))['centers']
out = []
for c in g150:
    X, Y = 2 * c['px'][0], 2 * c['px'][1]
    best = min(pts, key=lambda p: (p[0] - X) ** 2 + (p[1] - Y) ** 2) if pts else None
    d = ((best[0] - X) ** 2 + (best[1] - Y) ** 2) ** .5 if best else 1e9
    out.append({'name': c['name'], 'u': round(best[0], 1) if d < 40 else X, 'v': round(best[1], 1) if d < 40 else Y,
                'auto': d < 40})
print(n, 'native discs;', sum(o['auto'] for o in out), 'matched automatically')
json.dump(out, open('circles_native.json', 'w'), indent=0)
