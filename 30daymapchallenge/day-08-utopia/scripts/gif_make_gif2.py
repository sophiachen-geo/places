"""Los Angeles, built year by year — atlas / riso edition.
Buildings: LA County Assessor 2026 roll (year built, 120 m cells). Parks & forest: CPAD (GreenInfo, 2026 release).
Water: USGS NHD + basemap ocean. Freeways: Caltrans geometry, opening years LA Almanac (+ Wikipedia/AARoads for 3 routes).
Metro: GTFS 2026, sections dated by opening year, coloured as they were at the time."""
import json, math, os, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape, LineString

G = 'gif/'
S = ''
DAY = os.environ.get('DAY', '../places/30daymapchallenge/day-08-utopia/')
def ff(prefix, style):
    for f in glob.glob(G + 'fonts/' + prefix + '_*.ttf'):
        if os.popen(f"fc-scan --format '%{{style[0]}}' '{f}'").read().strip() == style: return f
    raise SystemExit(f'missing {prefix} {style}')
F_TITLE, F_ITAL = ff('fraunces', 'SemiBold'), ff('fraunces', 'Italic')
F_UI, F_UIB, F_NUM = ff('worksans', 'Regular'), ff('worksans', 'SemiBold'), ff('worksans', 'SemiBold')
TITLE, ITAL = ImageFont.truetype(F_TITLE, 28), ImageFont.truetype(F_ITAL, 14)
UI, UIB, NUM = ImageFont.truetype(F_UI, 12), ImageFont.truetype(F_UIB, 12), ImageFont.truetype(F_NUM, 56)
TINY, SRC, LBL = ImageFont.truetype(F_UI, 10), ImageFont.truetype(F_UI, 10), ImageFont.truetype(F_UIB, 11)

hex2 = lambda c: tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
PAPER, INK, INK2, INK3, HAIR = (255, 255, 255), (17, 17, 17), (85, 85, 85), (128, 128, 128), (214, 214, 214)
COL = {'pastoral': hex2('#00A95C'), 'autopia': hex2('#F0A202'), 'centers': hex2('#3255A4'), 'coop': hex2('#FF48B0')}
WATER, RIVER, OPEN, CASE = hex2('#B4D2EE'), hex2('#5E9BD6'), hex2('#C9E8CF'), (70, 70, 70)

R = 6378137.0; ORIG = math.pi * R
mx = lambda lon: math.radians(lon) * R
my = lambda lat: R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
M = json.load(open(DAY + 'data/morph.json'))
NX, NY = M['size']; CS = M['cell_m_webmerc']
GX0 = round(mx(M['bounds'][0][1]) / CS) * CS; GY1 = round(my(M['bounds'][1][0]) / CS) * CS
grid = np.asarray(Image.open(DAY + 'img/morph_grid.png').convert('RGBA'))
YR = np.where(grid[..., 3] > 0, grid[..., 0].astype(int) + 1850, 0)
W_, E_, S_, N_ = -118.70, -117.90, 33.70, 34.33
# ---------- projection: NAD83 / California State Plane Zone 5 (EPSG:2229, US feet), the County's own mapping projection ----------
from pyproj import Transformer
from scipy import ndimage as ndi
T = Transformer.from_crs(4326, 2229, always_xy=True); TI = Transformer.from_crs(2229, 4326, always_xy=True)
_bl = np.linspace(0, 1, 60)
_lo = np.r_[W_ + (E_ - W_) * _bl, np.full(60, E_), E_ - (E_ - W_) * _bl, np.full(60, W_)]
_la = np.r_[np.full(60, S_), S_ + (N_ - S_) * _bl, np.full(60, N_), N_ - (N_ - S_) * _bl]
_x, _y = T.transform(_lo, _la)
PXMIN, PXMAX, PYMIN, PYMAX = _x.min(), _x.max(), _y.min(), _y.max()
W = 742; PRES = (PXMAX - PXMIN) / W; H = int(round((PYMAX - PYMIN) / PRES))
def P(coords):
    a = np.asarray(coords, float)
    if a.ndim == 1: a = a[None, :]
    X, Y = T.transform(a[:, 0], a[:, 1])
    return list(zip(((X - PXMIN) / PRES).tolist(), ((PYMAX - Y) / PRES).tolist()))
topx = lambda lo, la: P([(lo, la)])[0]
# every output pixel back to lon/lat, then into the Web-Mercator sources (year grid, basemap tiles)
_gx, _gy = np.meshgrid(PXMIN + (np.arange(W) + 0.5) * PRES, PYMAX - (np.arange(H) + 0.5) * PRES)
LON, LAT = TI.transform(_gx, _gy)
MX = np.radians(LON) * R; MY = R * np.log(np.tan(np.pi / 4 + np.radians(LAT) / 2))
gi = np.floor((MX - GX0) / CS).astype(int); gj = np.floor((GY1 - MY) / CS).astype(int)
ok = (gi >= 0) & (gi < NX) & (gj >= 0) & (gj < NY)
yr = np.where(ok, YR[np.clip(gj, 0, NY - 1), np.clip(gi, 0, NX - 1)], 0)
print('map', W, H, 'ft/px', round(PRES, 1))

# ---------- base: Esri light gray, lightened toward white paper; ocean from its own tint ----------
z = 11; span = 2 * ORIG / 2 ** z
tx = sorted({int(f.split('_')[1]) for f in os.listdir(G + 'tiles')}); ty = sorted({int(f.split('_')[2].split('.')[0]) for f in os.listdir(G + 'tiles')})
mos = Image.new('RGB', (256 * len(tx), 256 * len(ty)))
for a, x in enumerate(tx):
    for b, y in enumerate(ty): mos.paste(Image.open(f'{G}tiles/{z}_{x}_{y}.png').convert('RGB'), (256 * a, 256 * b))
mX, mY, res = -ORIG + tx[0] * span, ORIG - ty[0] * span, span / 256
MA = np.asarray(mos).astype(float)
U = np.clip((MX - mX) / res - 0.5, 0, MA.shape[1] - 1); V = np.clip((mY - MY) / res - 0.5, 0, MA.shape[0] - 1)
raw = MA[np.round(V).astype(int), np.round(U).astype(int)].astype(int)
ocean = (raw[..., 2] - raw[..., 0] >= 3) & (raw[..., 0] < 222)
smooth = np.dstack([ndi.map_coordinates(MA[..., c], [V, U], order=1) for c in range(3)])
base = smooth * 0.5 + 255 * 0.5

def raster(polys, holes=True):
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    for pg in polys:
        for p in (pg.geoms if pg.geom_type == 'MultiPolygon' else [pg]):
            if p.is_empty or p.geom_type != 'Polygon': continue
            d.polygon(P(list(p.exterior.coords)), fill=255)
            if holes:
                for r_ in p.interiors: d.polygon(P(list(r_.coords)), fill=0)
    return np.asarray(im) > 0
cb = shape(json.load(open(S + 'raw2/county_boundary.geojson'))['features'][0]['geometry'])
inside = raster([cb], holes=False)
nhd = json.load(open(S + 'raw3/nhd_view.json'))
up = lambda f, k: f['properties'].get(k, f['properties'].get(k.lower()))
water_polys = [shape(f['geometry']) for f in nhd['wb'] if f.get('geometry')] + \
              [shape(f['geometry']) for f in nhd['area'] if f.get('geometry') and up(f, 'FTYPE') in (445, 460, 336)]
cpad = json.load(open(S + 'raw3/cpad_view.geojson'))
water_polys += [shape(f['geometry']) for f in cpad['features'] if f.get('geometry') and f['properties']['LAND_WATER'] == 'Water']
water = ocean | raster(water_polys)
openm = raster([shape(f['geometry']) for f in cpad['features'] if f.get('geometry') and f['properties']['LAND_WATER'] == 'Land']) & ~water
land_out = ~inside & ~water
base = np.where(land_out[..., None], base * 0.35 + 255 * 0.65, base)              # beyond the County line: no building data
base = np.where(openm[..., None], np.where(inside[..., None], np.array(OPEN), np.array(OPEN) * 0.55 + 255 * 0.45), base)
base = np.where(water[..., None], np.array(WATER), base)
rivers = []
for f in nhd['flow']:
    g = shape(f['geometry'])
    for l in (g.geoms if g.geom_type == 'MultiLineString' else [g]): rivers.append(P(list(l.coords)))
county_line = [P(list(p.exterior.coords)) for p in (cb.geoms if cb.geom_type == 'MultiPolygon' else [cb])]
# incorporated city boundaries (LA County, City & Unincorporated Community Boundaries)
CITY_LA, CITY_OTHER = [], []
for f in json.load(open(S + 'raw2/city_comm.geojson'))['features']:
    if f['properties']['JURISDICTION'] != 'INCORPORATED CITY' or not f.get('geometry'): continue
    g = shape(f['geometry'])
    for p in (g.geoms if g.geom_type == 'MultiPolygon' else [g]):
        ring = P(list(p.exterior.coords))
        (CITY_LA if f['properties']['CITY_COMM_NAME'] == 'LOS ANGELES' else CITY_OTHER).append(ring)

# ---------- buildings ----------
STOPS = [(1890, (66, 66, 66)), (1950, (138, 138, 138)), (2015, (204, 204, 204))]
def ramp(y):
    if y <= STOPS[0][0]: return STOPS[0][1]
    if y >= STOPS[2][0]: return STOPS[2][1]
    a, b = (STOPS[0], STOPS[1]) if y < STOPS[1][0] else (STOPS[1], STOPS[2])
    t = (y - a[0]) / (b[0] - a[0]); return tuple(a[1][k] + (b[1][k] - a[1][k]) * t for k in range(3))
LUT = np.array([ramp(y) for y in range(0, 2030)], float); FRONT = 5

# ---------- freeways and Metro ----------
FWY = [(o['y0'], o['y1'], [P(l) for l in o['lines']]) for o in json.load(open(G + 'freeways_dated.json'))]
def dashed(d, pts, on=5, off=4, fill=CASE, width=2):
    acc, draw = 0.0, True
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0); pos = 0.0
        while pos < seg:
            step = min((on if draw else off) - acc, seg - pos)
            if draw:
                t0, t1 = pos / seg, (pos + step) / seg
                d.line([(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0), (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)], fill=fill, width=width)
            pos += step; acc += step
            if acc >= (on if draw else off) - 1e-9: acc, draw = 0.0, not draw
from shapely.geometry import LineString as _LS
OFF = {'A': -1.4, 'E': 1.4, 'B': -1.4, 'D': 1.4, 'C': -1.4, 'K': 1.4, 'G': 0, 'J': 0}
segs = []
for sg in json.load(open(G + 'transit_segments.json')):
    pts = P(sg['coords'])
    if OFF[sg['line']]:
        o = _LS(pts).offset_curve(OFF[sg['line']])
        lines = [list(g_.coords) for g_ in (o.geoms if o.geom_type.startswith('Multi') else [o]) if not g_.is_empty]
    else: lines = [pts]
    segs.append((sg['year'], sg['line'], hex2(sg['color']), lines))
AQUA, GOLD, RED, GREEN = hex2('#00AEC7'), hex2('#FDB913'), hex2('#EB131B'), hex2('#58A738')
def look(sg, Y):
    y0, L_ = sg[0], sg[1]
    if L_ == 'A' and y0 in (2003, 2009, 2016, 2025) and Y < 2023: return 'L', GOLD
    if L_ == 'E' and y0 == 2009 and Y < 2023: return 'L', GOLD
    if L_ == 'E' and y0 in (2012, 2016) and Y < 2023: return 'E', AQUA
    if L_ == 'K' and y0 == 1995 and Y < 2024: return 'C', GREEN
    if L_ == 'D' and Y < 2006: return 'B', RED
    return L_, sg[2]
def lname(k, Y):
    if Y < 2020: return {'A': 'Blue Line', 'B': 'Red Line', 'C': 'Green Line', 'D': 'Purple Line', 'E': 'Expo Line', 'L': 'Gold Line', 'G': 'Orange Line', 'J': 'Silver Line'}[k]
    return f'{k} Line'

PLACES = [('San Fernando Valley', -118.47, 34.205), ('Pasadena', -118.144, 34.153), ('Hollywood', -118.33, 34.098), ('Downtown', -118.247, 34.047),
          ('Santa Monica', -118.49, 34.016), ('Long Beach', -118.19, 33.775)]
NATURE = [('Pacific Ocean', -118.63, 33.715, RIVER), ('Angeles National Forest', -118.16, 34.300, (40, 120, 70)), ('Santa Monica Mountains', -118.60, 34.105, (40, 120, 70)),
          ('Griffith Park', -118.29, 34.137, (40, 120, 70)), ('Orange County · no building data', -118.03, 33.80, INK3)]
MIL = [(1904, 'pastoral', 'Residential District Ordinance'), (1913, 'coop', 'Little Landers colony, Tujunga'), (1914, 'coop', 'Llano del Rio founded'),
       (1930, 'pastoral', 'Olmsted–Bartholomew parks plan'), (1940, 'autopia', 'Arroyo Seco Parkway, the first freeway'), (1942, 'coop', 'Baldwin Hills Village completed'),
       (1946, 'autopia', 'County parkways plan'), (1949, 'autopia', 'Four Level Interchange completed'), (1953, 'coop', 'Elysian Park Heights cancelled'),
       (1962, 'coop', 'Dodger Stadium opens in Chávez Ravine'), (1966, 'autopia', 'Santa Monica Freeway completed'), (1971, 'autopia', 'Banham’s “Autopia”'),
       (1974, 'centers', 'Centers Concept adopted'),
       (1990, '#0072BC', 'Blue Line opens: rail returns to LA'), (1993, '#EB131B', 'Red Line subway opens'), (1995, '#58A738', 'Green Line opens'),
       (2000, '#EB131B', 'Red Line reaches North Hollywood'), (2003, '#FDB913', 'Gold Line reaches Pasadena'), (2005, '#FC4C02', 'Orange Line busway opens'),
       (2009, '#ADB8BF', 'Silver Line busway opens'), (2012, '#00AEC7', 'Expo Line opens'), (2016, '#00AEC7', 'Expo Line reaches Santa Monica'),
       (2022, '#E56DB1', 'K Line opens'), (2023, '#0072BC', 'Regional Connector: lines regrouped as A and E'), (2026, '#A05DA5', 'D Line reaches La Cienega')]
hist = {int(k): v for k, v in M['hist'].items()}; N = M['parcels']
cum = np.cumsum([hist.get(y, 0) for y in range(1850, 2027)]) / N
HY0, HY1 = 1880, 2026; hmax = max(hist.get(y, 0) for y in range(HY0, HY1 + 1))
TOP, BOT = 64, 372

def halo_text(d, xy, s, font, fill, halo=(255, 255, 255), sw=3):
    d.text(xy, s, font=font, fill=fill, stroke_width=sw, stroke_fill=halo)

def frame(Y):
    m = (yr > 0) & (yr <= Y)
    col = LUT[np.clip(yr, 0, 2029)]; col[(yr > Y - FRONT) & m] = INK
    a = np.where(m, 0.9, 0.0)[..., None]
    mp = Image.fromarray((base * (1 - a) + col * a).clip(0, 255).astype(np.uint8)); dm = ImageDraw.Draw(mp)
    for line in county_line: dm.line(line, fill=(150, 150, 150), width=1)
    for ln in rivers: dm.line(ln, fill=RIVER, width=2, joint='curve')
    for ring in CITY_OTHER: dm.line(ring, fill=(150, 150, 150), width=1)
    for ring in CITY_LA: dm.line(ring, fill=INK, width=2, joint='curve')
    for y0, y1, lines in FWY:                       # freeways: complete = white road with dark edges; opening in stages = dashed
        if Y < y0: continue
        for ln in lines:
            if Y >= y1:
                dm.line(ln, fill=CASE, width=5, joint='curve')
            else:
                dashed(dm, ln)
    for y0, y1, lines in FWY:
        if Y >= y1:
            for ln in lines: dm.line(ln, fill=(255, 255, 255), width=3, joint='curve')
    on = [(sg, *look(sg, Y)) for sg in segs if sg[0] <= Y]
    for sg, k_, c_ in on:
        for ln in sg[3]: dm.line(ln, fill=(255, 255, 255), width=6, joint='curve')
    for sg, k_, c_ in sorted(on, key=lambda t: 'JGCKBDELA'.index(t[0][1])):
        for ln in sg[3]: dm.line(ln, fill=c_, width=3, joint='curve')
    legend = {}
    for sg, k_, c_ in on: legend.setdefault(k_, c_)

    im = Image.new('RGB', (W, TOP + H + BOT), PAPER); im.paste(mp, (0, TOP)); d = ImageDraw.Draw(im)
    d.text((18, 15), 'Los Angeles, Built Year by Year', font=TITLE, fill=INK)
    d.rectangle([0, TOP - 3, W, TOP - 1], fill=INK); d.rectangle([0, TOP + H, W, TOP + H + 2], fill=INK)
    for name, lo, la in PLACES:
        x, y = topx(lo, la); w = d.textlength(name, font=UIB); halo_text(d, (x - w / 2, TOP + y - 8), name, UIB, INK2)
    for name, lo, la, c in NATURE:
        x, y = topx(lo, la); w = d.textlength(name, font=ITAL); halo_text(d, (x - w / 2, TOP + y - 9), name, ITAL, c, sw=2)
    # year, share, histogram, milestone
    by = TOP + H + 3
    d.text((16, by + 18), str(Y), font=NUM, fill=INK)
    p = cum[min(Y, 2026) - 1850] * 100
    d.text((18, by + 86), f'{p:.0f}% of today’s buildings' if p >= 1 else f'{p:.1f}% of today’s buildings', font=UI, fill=INK2)
    hx0, hx1, hy0, hy1 = 206, W - 16, by + 44, by + 96
    bw = (hx1 - hx0) / (HY1 - HY0 + 1)
    for y in range(HY0, HY1 + 1):
        v = hist.get(y, 0); h = (hy1 - hy0) * v / hmax
        c = (230, 230, 230) if y > Y else (INK if Y - y < FRONT else tuple(int(t) for t in ramp(y)))
        x = hx0 + (y - HY0) * bw
        if h > 0.3: d.rectangle([x, hy1 - h, x + max(bw - 0.6, 0.8), hy1], fill=c)
    d.line([(hx0, hy1 + 0.5), (hx1, hy1 + 0.5)], fill=INK)
    for y in range(1900, 2021, 20):
        x = hx0 + (y - HY0 + 0.5) * bw; tw = d.textlength(str(y), font=TINY); d.text((x - tw / 2, hy1 + 4), str(y), font=TINY, fill=INK3)
    cx = hx0 + (min(Y, HY1) - HY0 + 0.5) * bw; d.line([(cx, hy0 - 4), (cx, hy1 + 2)], fill=INK, width=2)
    ms = [m_ for m_ in MIL if m_[0] <= Y and Y - m_[0] <= 7]
    if ms:
        y_, ch, t = ms[-1]
        d.rectangle([hx0, by + 18, hx0 + 9, by + 27], fill=INK if ch in COL else hex2(ch))   # colour only where it matches a line on the map
        d.text((hx0 + 15, by + 15), f'{y_} · {t}', font=UIB, fill=INK)
    # ---- legend band below the map (nothing drawn over land) ----
    def sw_(kind, sx, sy, col=None):
        if kind == 'water': d.rectangle([sx, sy + 2, sx + 18, sy + 11], fill=WATER)
        elif kind == 'open': d.rectangle([sx, sy + 2, sx + 18, sy + 11], fill=OPEN)
        elif kind == 'fwy': d.line([(sx, sy + 7), (sx + 18, sy + 7)], fill=CASE, width=5); d.line([(sx, sy + 7), (sx + 18, sy + 7)], fill=(255, 255, 255), width=3)
        elif kind == 'fwyb': dashed(d, [(sx, sy + 7), (sx + 18, sy + 7)])
        elif kind == 'new': d.rectangle([sx, sy + 2, sx + 18, sy + 11], fill=INK)
        elif kind == 'cla': d.line([(sx, sy + 7), (sx + 18, sy + 7)], fill=INK, width=2)
        elif kind == 'cot': d.line([(sx, sy + 7), (sx + 18, sy + 7)], fill=(150, 150, 150), width=1)
        elif kind == 'old':
            for q in range(18): d.line([(sx + q, sy + 2), (sx + q, sy + 11)], fill=tuple(int(v) for v in ramp(1890 + q * 7)))
        elif kind == 'metro': d.line([(sx, sy + 7), (sx + 18, sy + 7)], fill=col, width=4)
    ly = by + 124
    d.line([(16, ly), (W - 16, ly)], fill=HAIR)
    d.text((16, ly + 9), 'MAP KEY', font=LBL, fill=INK)
    rows = [('water', 'Water'), ('open', 'Parks, forest, open space'), ('fwy', 'Freeway'),
            ('fwyb', 'Freeway, opening in stages'), ('old', 'Buildings: darker = older'), ('new', f'Built in the last {FRONT} years'),
            ('cla', 'City of Los Angeles'), ('cot', 'Other cities'), ('scale', '')]
    cw = (W - 32) / 3
    for k, (kind, t) in enumerate(rows):
        sx, sy = 16 + (k % 3) * cw, ly + 27 + (k // 3) * 17
        if kind == 'scale':   # true scale in this projection
            ppm = 5280 / PRES; x0_ = sx
            for q in range(2): d.rectangle([x0_ + q * 5 * ppm, sy + 5, x0_ + (q + 1) * 5 * ppm, sy + 9], fill=INK if q == 0 else PAPER, outline=INK)
            d.text((x0_ + 10 * ppm + 6, sy), '10 miles', font=UI, fill=INK2)
            continue
        sw_(kind, sx, sy); d.text((sx + 26, sy), t, font=UI, fill=INK2)
    my_ = ly + 27 + 3 * 17 + 8
    d.text((16, my_), 'METRO LINES', font=LBL, fill=INK)
    opened = [k_ for k_ in 'ABCDELKGJ' if k_ in legend]
    if not opened: d.text((16, my_ + 18), 'No Metro rail yet: the first line opens in 1990.', font=UI, fill=INK3)
    cw2 = (W - 32) / 5
    for k, L_ in enumerate(opened):
        sx, sy = 16 + (k % 5) * cw2, my_ + 18 + (k // 5) * 17
        sw_('metro', sx, sy, legend[L_]); d.text((sx + 26, sy), lname(L_, Y), font=UI, fill=INK2)
    fy = my_ + 18 + 2 * 17 + 14
    d.line([(16, fy - 8), (W - 16, fy - 8)], fill=HAIR)
    for k, t in enumerate(['Buildings: Los Angeles County Assessor, 2026 property roll — year built of 2.2 million parcels (LA County only).',
                           'Metro: LA Metro GTFS 2026, each section from the year it opened. Freeways: Caltrans; opening years: LA Almanac.',
                           'Parks & forest: California Protected Areas Database (GreenInfo Network, 2026). Water: USGS National Hydrography Dataset.',
                           'City boundaries: Los Angeles County, City & Unincorporated Community Boundaries (2026).',
                           'Basemap: Esri, HERE, Garmin, © OpenStreetMap contributors.',
                           'Projection: NAD83 / California State Plane Zone 5 (EPSG:2229), the projection used by Los Angeles County.']):
        d.text((16, fy + k * 14), t, font=SRC, fill=INK2 if k < 4 else INK3)
    return im

if os.environ.get('PREVIEW'):
    for y_ in [int(v) for v in os.environ['PREVIEW'].split(',')]: frame(y_).save(G + f'v2_{y_}.png')
    raise SystemExit(0)
years = list(range(1880, 2027, 2))
if years[-1] != 2026: years.append(2026)
frames = [frame(y) for y in years]
if os.environ.get('FRAMES'):            # full frames for video / full-frame GIF exports
    fd = os.environ['FRAMES']; os.makedirs(fd, exist_ok=True)
    for k, f in enumerate(frames): f.save(f'{fd}/f{k:03d}.png')
    json.dump(years, open(f'{fd}/years.json', 'w'))
    raise SystemExit(0)
sample = Image.new('RGB', (W, (TOP + H + BOT) * 3))
for k, y in enumerate((1925, 1960, 2026)): sample.paste(frame(y), (0, (TOP + H + BOT) * k))
PIN = list(dict.fromkeys([sg[2] for sg in segs] + [AQUA, GOLD, RED, GREEN, WATER, RIVER, OPEN, CASE, INK, (255, 255, 255)] +
                         [hex2(c) for _, c, _ in MIL if isinstance(c, str) and c.startswith('#')]))
NA = 127 - len(PIN)
base_pal = sample.quantize(colors=NA, method=Image.Quantize.MEDIANCUT).getpalette()[:NA * 3]
pal = Image.new('P', (1, 1)); pal.putpalette(base_pal + [v for c in PIN for v in c] + [255, 0, 255] + [0, 0, 0] * 128)
q = [np.asarray(f.quantize(palette=pal, dither=Image.Dither.NONE)) for f in frames]
TR = 127; plt = pal.getpalette()[:127 * 3] + [255, 0, 255]
imgs = []
for k, arr in enumerate(q):
    a2 = arr.copy()
    if k: a2[arr == q[k - 1]] = TR
    im = Image.fromarray(a2.astype(np.uint8), 'P'); im.putpalette(plt + [0, 0, 0] * 128); imgs.append(im)
dur = [1500] + [200] * (len(imgs) - 2) + [4500]
out = G + 'la_built_year_by_year_v2.gif'
imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=dur, loop=0, optimize=False, disposal=1, transparency=TR)
print(out, os.path.getsize(out) // 1024, 'KB', len(imgs), 'frames', 'pinned', len(PIN))
