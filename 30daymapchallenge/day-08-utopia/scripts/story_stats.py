"""Extra figures for the story page -> data/story_stats.json, plus the Boyle Heights 500-ft freeway band
appended to data/story_places.geojson (run after build_story.py).

  boyle      homes (Assessor 'Units', 2026 roll) whose parcel centroid lies within 500 ft (152.4 m) of a freeway
             centreline (Caltrans D7 LRS, F_System 1-2, SHS routes only), Boyle Heights CPA vs City vs County,
             and the same share for every place: the City's 35 Community Plan Areas and the County's other
             cities and unincorporated communities (DRP City & Community boundaries).
             500 ft is CARB's siting distance for sensitive land uses near freeways (Air Quality and Land Use
             Handbook, 2005).
  parkways1946  mileage + cost table, 'Interregional, Regional and Metropolitan Parkways' (LA County RPC, 1946).
"""
import csv, json, os
import numpy as np
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform
from shapely import contains_xy
from pyproj import Transformer

S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
m2g = Transformer.from_crs(3310, 4326, always_xy=True).transform
fw = [f for f in json.load(open(S + 'raw/fwy_d7.geojson'))['features']
      if f['properties']['RouteID'].startswith('SHS_') and f['properties']['F_System'] in (1, 2)]
lines = transform(g2m, unary_union([shape(f['geometry']) for f in fw]))
band = lines.buffer(152.4)
cpa = {f['properties']['NAME_ALF']: shape(f['geometry']) for f in json.load(open(S + 'raw2/cpa.geojson'))['features']}
bh = cpa['Boyle Heights']; bhm = transform(g2m, bh)
routes = {}
for f in fw:
    routes.setdefault(f['properties']['RouteID'][4:7], []).append(shape(f['geometry']))
crossing = sorted(int(r) for r, gs in routes.items() if transform(g2m, unary_union(gs)).intersection(bhm).length > 500)

lon, lat, units, city = [], [], [], []
with open(S + 'raw2/roll2026_county.csv') as f:
    for a in csv.DictReader(f):
        try:
            la = float(a['CENTER_LAT']); lo = float(a['CENTER_LON']); u = int(float(a['Units'] or 0))
        except ValueError:
            continue
        if u <= 0: continue
        lon.append(lo); lat.append(la); units.append(u); city.append(a['TaxRateArea_CITY'] == 'LOS ANGELES')
lon, lat, units, city = map(np.array, (lon, lat, units, city))
x, y = g2m(lon, lat)
near = contains_xy(band, x, y)
inbh = contains_xy(bh, lon, lat)
def share(m):
    return {'homes': int(units[m].sum()), 'within_500ft_pct': round(float(units[m & near].sum() / units[m].sum() * 100), 1)}
# every place: the City's plan areas, the other cities, the unincorporated communities
PLACES = [(n, 'la', g) for n, g in cpa.items()]
for f in json.load(open(S + 'raw2/city_comm.geojson'))['features']:
    pr = f['properties']
    if not f.get('geometry') or pr['CITY_COMM_NAME'] == 'LOS ANGELES': continue
    kind = 'city' if pr['JURISDICTION'] == 'INCORPORATED CITY' else 'unincorporated'
    PLACES.append((pr['CITY_COMM_NAME'], kind, shape(f['geometry'])))
places = []
for name, kind, g in PLACES:
    x0, y0, x1, y1 = g.bounds
    pre = (lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1)
    m = np.zeros_like(pre); m[pre] = contains_xy(g, lon[pre], lat[pre])
    if units[m].sum() < 5000: continue            # too few homes for a share to mean much
    places.append({'name': name, 'kind': kind, **share(m)})
places.sort(key=lambda d: -d['within_500ft_pct'])
out = {
    'boyle': {'routes': crossing, 'land_within_500ft_pct': round(band.intersection(bhm).area / bhm.area * 100, 1),
              'bh': share(inbh), 'city': share(city), 'county': share(np.ones_like(city, bool)), 'places': places},
    'parkways1946': {'miles': {'interregional': 118.3, 'regional': 205.1, 'metropolitan': 289.9, 'total': 613.3},
                     'cost_usd_1946': 939599000, 'src': 'LA County Regional Planning Commission 1946, table of length and estimated cost'},
}
json.dump(out, open(DAY + 'data/story_stats.json', 'w'), indent=1)
sp = json.load(open(DAY + 'data/story_places.geojson'))
sp['features'] = [f for f in sp['features'] if f['properties']['id'] != 'bh500']
g = transform(m2g, band.intersection(bhm)).simplify(0.00005)
def r(o):
    if isinstance(o, float): return round(o, 5)
    if isinstance(o, (list, tuple)): return [r(v) for v in o]
    return o
gm = mapping(g); gm['coordinates'] = r(gm['coordinates'])
sp['features'].append({'type': 'Feature', 'geometry': gm, 'properties': {'id': 'bh500', 'name': 'Within 500 ft of a freeway', 'ch': 'autopia',
                       'src': 'Caltrans D7 LRS centrelines, 152.4 m buffer, clipped to the Boyle Heights CPA'}})
json.dump(sp, open(DAY + 'data/story_places.geojson', 'w'), separators=(',', ':'))
# the same band across the whole County, for the map
cbd = shape(json.load(open(S + 'raw2/county_boundary.geojson'))['features'][0]['geometry'])
gc = transform(m2g, band.intersection(transform(g2m, cbd))).simplify(0.00006)
gm = mapping(gc); gm['coordinates'] = r(gm['coordinates'])
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': gm, 'properties': {
    'name': 'Within 500 ft of a freeway', 'src': 'Caltrans D7 LRS centrelines (F_System 1-2, state highways), 152.4 m buffer, LA County'}}]},
    open(DAY + 'data/fwy500.geojson', 'w'), separators=(',', ':'))
print(json.dumps({k: v for k, v in out['boyle'].items() if k != 'places'}, indent=1))
for d in places[:25]: print(d)
print(len(places), 'places')
