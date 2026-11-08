"""Exact center cores: intersect the two named street centerlines (LA County eGIS CAMS address
lines, live service) and keep the crossing nearest the provisional core. -> work/centers_exact.json"""
import json, ssl, urllib.request, urllib.parse, time, sys
from shapely.geometry import shape, Point, MultiPoint
from shapely.ops import unary_union, transform
from pyproj import Transformer, Geod

ctx = ssl.create_default_context()
U = 'https://services.arcgis.com/RmCCgQtiZLDCtblq/arcgis/rest/services/eGIS_Addressing_ROAD_LINES/FeatureServer/0/query'
geod = Geod(ellps='WGS84')

# center -> ((StName, StPostType), (StName, StPostType))   [StPostType None = any]
X = {
 'San Fernando': (('San Fernando', 'Rd'), ('Maclay', 'Ave')),
 'Granada Hills': (('Chatsworth', 'St'), ('Zelzah', 'Ave')),
 'Chatsworth': (('Devonshire', 'St'), ('Topanga Canyon', 'Blvd')),
 'Northridge': (('Reseda', 'Blvd'), ('Nordhoff', 'St')),
 'Panorama City': (('Van Nuys', 'Blvd'), ('Roscoe', 'Blvd')),
 'Van Nuys': (('Van Nuys', 'Blvd'), ('Victory', 'Blvd')),
 'Canoga Park–Woodland Hills': (('Topanga Canyon', 'Blvd'), ('Erwin', 'St')),
 'Burbank': (('San Fernando', 'Blvd'), ('Olive', 'Ave')),
 'Sherman Oaks': (('Ventura', 'Blvd'), ('Sepulveda', 'Blvd')),
 'Pasadena': (('Colorado', 'Blvd'), ('Garfield', 'Ave')),
 'Glendale': (('Brand', 'Blvd'), ('Broadway', None)),
 'Highland Park': (('Figueroa', 'St'), ('York', 'Blvd')),
 'Hollywood (west circle)': (('Hollywood', 'Blvd'), ('Highland', 'Ave')),
 'Hollywood (east circle)': (('Hollywood', 'Blvd'), ('Vine', 'St')),
 'East Hollywood': (('Sunset', 'Blvd'), ('Vermont', 'Ave')),
 'Alhambra': (('Main', 'St'), ('Garfield', 'Ave')),
 'Sunset Strip': (('Sunset', 'Blvd'), ('La Cienega', 'Blvd')),
 'Echo Park': (('Sunset', 'Blvd'), ('Echo Park', 'Ave')),
 'Lincoln Heights': (('Broadway', None), ('Daly', 'St')),
 'Beverly Hills': (('Wilshire', 'Blvd'), ('Beverly', 'Dr')),
 'Century City': (('Avenue of the Stars', None), ('Constellation', 'Blvd')),
 'Westwood': (('Wilshire', 'Blvd'), ('Westwood', 'Blvd')),
 'Miracle Mile (west circle)': (('Wilshire', 'Blvd'), ('Fairfax', 'Ave')),
 'Miracle Mile (east circle)': (('Wilshire', 'Blvd'), ('La Brea', 'Ave')),
 'Wilshire Center (west circle)': (('Wilshire', 'Blvd'), ('Western', 'Ave')),
 'Wilshire Center (east circle)': (('Wilshire', 'Blvd'), ('Vermont', 'Ave')),
 'Westlake (unlabelled circle)': (('Wilshire', 'Blvd'), ('Alvarado', 'St')),
 'Bunker Hill (unlabelled circle)': (('Grand', 'Ave'), ('2nd', 'St')),
 'Civic Center': (('1st', 'St'), ('Spring', 'St')),
 'Downtown': (('6th', 'St'), ('Olive', 'St')),
 'General Hospital': (('State', 'St'), ('Marengo', 'St')),
 'Boyle Heights': (('Cesar E Chavez', 'Ave'), ('Soto', 'St')),
 'East Los Angeles': (('Whittier', 'Blvd'), ('Atlantic', 'Blvd')),
 'Santa Monica': (('Wilshire', 'Blvd'), ('4th', 'Ave')),   # CAMS codes SM's 4th St as '4th Ave'
 'Exposition Park–USC': (('Figueroa', 'St'), ('Exposition', 'Blvd')),
 'Culver City': (('Culver', 'Blvd'), ('Washington', 'Blvd')),
 'Crenshaw': (('Crenshaw', 'Blvd'), ('Martin Luther King Jr', 'Blvd')),
 'Vernon–Central': (('Vernon', 'Ave'), ('Central', 'Ave')),
 'Huntington Park': (('Pacific', 'Blvd'), ('Gage', 'Ave')),
 'Vermont–Manchester': (('Vermont', 'Ave'), ('Manchester', 'Ave')),
 'Avalon–Manchester': (('Avalon', 'Blvd'), ('Manchester', 'Ave')),
 'Inglewood': (('Market', 'St'), ('Manchester', 'Blvd')),
 'Watts': (('103rd', 'St'), ('Wilmington', 'Ave')),
 'Westchester–Airport': (('Century', 'Blvd'), ('Airport', 'Blvd')),
 'Downey': (('Firestone', 'Blvd'), ('Downey', 'Ave')),
 'Compton': (('Compton', 'Blvd'), ('Willowbrook', 'Ave')),
 'South Bay': (('Hawthorne', 'Blvd'), ('Artesia', 'Blvd')),
 'Del Amo': (('Hawthorne', 'Blvd'), ('Carson', 'St')),
 'Redondo Beach': (('Pacific Coast', 'Hwy'), ('Torrance', 'Blvd')),
 'Lakewood': (('Lakewood', 'Blvd'), ('Candlewood', 'St')),
 'Long Beach': (('Pine', 'Ave'), ('Ocean', 'Blvd')),
 'San Pedro': (('6th', 'St'), ('Pacific', 'Ave')),
 'Reseda': (('Reseda', 'Blvd'), ('Sherman', 'Wy')),
 'North Hollywood': (('Lankershim', 'Blvd'), ('Chandler', 'Blvd')),
 'Universal City': (('Lankershim', 'Blvd'), ('Universal Hollywood', 'Dr')),
 'Venice': (('Windward', 'Ave'), ('Main', 'St')),
}
ALIAS = {'La Cienega': ['La La Cienega', 'La Cienega'], 'La Brea': ['La La Brea', 'La Brea'],
         'Avenue of the Stars': ['of the of the Stars'], 'Martin Luther King Jr': ['Martin Luther King Jr', 'Martin Luther King'],
         'Cesar E Chavez': ['Cesar E Chavez', 'Cesar Chavez'],
         'Pacific Coast': ['Pacific Coast', 'Pacific Coast Highway']}


def q(name, ptype, lon, lat, d=0.03):
    names = ALIAS.get(name, [name])
    w = '(' + ' OR '.join(f"StName='{n}'" for n in names) + ')'
    if ptype:
        w += f" AND StPostType='{ptype}'"
    p = dict(where=w, geometry=f'{lon-d},{lat-d},{lon+d},{lat+d}', geometryType='esriGeometryEnvelope', inSR=4326,
             outSR=4326, outFields='FullName', returnGeometry='true', f='geojson')
    for i in range(5):
        try:
            with urllib.request.urlopen(U + '?' + urllib.parse.urlencode(p), context=ctx, timeout=90) as r:
                return json.load(r)['features']
        except Exception as e:
            time.sleep(2 ** i)
    raise SystemExit('fail ' + name)


prev = {c['name']: c for c in json.load(open('work/centers_final.json'))['centers']}
RENAME = {'Civic Center (west circle)': 'Bunker Hill (unlabelled circle)', 'Civic Center (east circle)': 'Civic Center',
          'Regional Core — unlabelled (Westlake)': 'Westlake (unlabelled circle)'}
out = []
for name, (a, b) in X.items():
    c = prev[name]
    fa, fb = q(*a, c['lng'], c['lat']), q(*b, c['lng'], c['lat'])
    if not fa or not fb:
        print('NO LINES', name, len(fa), len(fb)); continue
    ga = unary_union([shape(f['geometry']) for f in fa]); gb = unary_union([shape(f['geometry']) for f in fb])
    ix = ga.intersection(gb)
    pts = [p for p in getattr(ix, 'geoms', [ix]) if p.geom_type == 'Point'] if not ix.is_empty else []
    if not pts:   # streets meet within a few metres but don't share a vertex: take the closest approach
        from shapely.ops import nearest_points
        pa, pb = nearest_points(ga, gb)
        gap = geod.inv(pa.x, pa.y, pb.x, pb.y)[2]
        pts = [Point((pa.x + pb.x) / 2, (pa.y + pb.y) / 2)] if gap < 40 else []
        if not pts:
            print('NO X', name, round(gap)); continue
    p = min(pts, key=lambda p: geod.inv(p.x, p.y, c['lng'], c['lat'])[2])
    shift = geod.inv(p.x, p.y, c['lng'], c['lat'])[2]
    names = sorted({f['properties']['FullName'] for f in fa}) [:2] + sorted({f['properties']['FullName'] for f in fb})[:2]
    out.append({**c, 'lat': round(p.y, 6), 'lng': round(p.x, 6), 'core': f"{fa[0]['properties']['FullName']} & {fb[0]['properties']['FullName']}",
                'shift_from_v1_m': round(shift), 'off_m': round(geod.inv(p.x, p.y, c['dlng'], c['dlat'])[2])})
    print(f'{name:34s} {out[-1]["core"]:45s} moved {shift:6.0f} m')
json.dump({'source': 'LA County eGIS CAMS address lines (live)', 'centers': out}, open('work/centers_exact.json', 'w'), indent=1, ensure_ascii=False)
print(len(out))
