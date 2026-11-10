"""Where the 1974 planners drew each of the 56 centres, on today's map.

The disc centres detected on the native 300-ppi scan (work2/circles_native.json) are carried through the inverse of the
shape-preserving placement of the diagram (warp1974.py: a similarity fit on the inland centres + the coastline), so a
circle sits exactly where its disc is drawn, and the diagram is not bent to suit anyone's choice of core.
Writes work/centers_plan.json (same shape as work/centers_exact.json, plus the old intersection core for reference).
"""
import os, json, math
import numpy as np
from pyproj import Transformer
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'warp1974.py')
exec(open(SRC).read().split('# ---------- 5. leave-one-out')[0])     # -> G_all (EPSG:3310 m), P_all (scan px), fit_similarity, REN
# pixel -> metres as a similarity in complex form, both frames y-up: x + iy = a (u - iv) + b
zs = P_all[:, 0] - 1j * P_all[:, 1]; zt = G_all[:, 0] + 1j * G_all[:, 1]
M = np.c_[zs, np.ones_like(zs)]; (a_, b_), *_ = np.linalg.lstsq(M, zt, rcond=None)
def inv(UV):
    z = a_ * (UV[:, 0] + 1j * UV[:, 1]) + b_          # UV given as (u, -v)
    return np.c_[z.real, z.imag]
to_ll = Transformer.from_crs(3310, 4326, always_xy=True).transform
fwd_err = np.hypot(*(inv(P_all * [1, -1]) - G_all).T)
print(f'inverse placement on {len(G_all)} control points: median {np.median(fwd_err):.0f} m')
discs = {REN.get(c['name'], c['name']): (c['u'], c['v']) for c in json.load(open('work2/circles_native.json'))}
cores = {c['name']: c for c in json.load(open('work/centers_exact.json'))['centers']}
g2m_ = Transformer.from_crs(4326, 3310, always_xy=True).transform
out = []
for name, (u, v) in discs.items():
    x, y = inv(np.array([[u, -v]]))[0]
    lon, lat = to_ll(x, y)
    c = cores[name]; cx, cy = g2m_(c['lng'], c['lat'])
    out.append({'name': name, 'core': c['core'], 'lat': round(lat, 6), 'lng': round(lon, 6),
                'core_lat': c['lat'], 'core_lng': c['lng'], 'off_m': int(round(math.hypot(x - cx, y - cy), -1))})
json.dump({'source': '1974 Concept Los Angeles disc centres (native scan) through the inverse of the similarity placement',
           'centers': sorted(out, key=lambda d: d['name'])}, open('work/centers_plan.json', 'w'), indent=1)
offs = sorted(d['off_m'] for d in out)
print(len(out), 'centres; shift from the chosen intersections: median', offs[len(offs) // 2], 'm, max', offs[-1], 'm')
for d in sorted(out, key=lambda d: -d['off_m'])[:8]: print(f"  {d['off_m']:5d} m  {d['name']}  (was {d['core']})")
