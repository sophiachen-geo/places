"""Freeways in the GIF view, dated by route: (first section opened, route complete).
Years: LA Almanac 'Freeways and Highways in Los Angeles County' (laalmanac.com/transport/tr26.php), except
Hollywood Fwy south of Cahuenga 1940-1954 (Wikipedia, completed 1954), SR-170 1962-1968 (AARoads/Gribblenation),
SR-103 1948 (Wikipedia). Geometry: Caltrans LRS, District 7 (F_System 1-2)."""
import json
from shapely.geometry import shape, box, mapping, LineString, MultiLineString
from shapely.ops import unary_union, linemerge
S = ''
V = box(-118.75, 33.66, -117.85, 34.38)
fw = [f for f in json.load(open(S + 'raw/fwy_d7.geojson'))['features'] if f['properties']['RouteID'].startswith('SHS_') and f['properties']['F_System'] in (1, 2)]
by = {}
for f in fw:
    r = f['properties']['RouteID'][4:7]; g = shape(f['geometry']).intersection(V)
    if not g.is_empty: by.setdefault(r, []).append(g)
WHOLE = {'002': (1958, 1978), '014': (1963, 1974), '022': (1964, 1967), '047': (1947, 1947), '060': (1965, 1971), '090': (1968, 1972),
         '091': (1968, 1975), '103': (1948, 1948), '105': (1993, 1993), '118': (1968, 1977), '134': (1955, 1977), '170': (1962, 1968),
         '210': (1955, 2003), '405': (1957, 1969), '605': (1964, 1971), '710': (1952, 1965)}
SPLIT = {  # route: (test on a vertex (lon, lat) -> True for the first part, part A years, part B years, names)
  '005': (lambda x, y: y < 34.045, (1945, 1958), (1956, 1975), ('Santa Ana', 'Golden State')),
  '010': (lambda x, y: x < -118.221, (1961, 1966), (1943, 1957), ('Santa Monica', 'San Bernardino')),
  '101': (lambda x, y: y < 34.125 and x > -118.365, (1940, 1954), (1955, 1974), ('Hollywood', 'Ventura')),
  '110': (lambda x, y: y > 34.062, (1940, 1953), (1952, 1970), ('Arroyo Seco', 'Harbor')),
}
def lines(g):
    return [g] if g.geom_type == 'LineString' else [p for p in getattr(g, 'geoms', []) if p.geom_type == 'LineString']
out = []
for r, gs in by.items():
    ls = [l for g in gs for l in lines(g)]
    if r in SPLIT:
        test, a, b, nm = SPLIT[r]
        A, B = [], []
        for l in ls:   # split each line at the boundary by vertex test (fine at this scale)
            cur, side = [l.coords[0]], test(*l.coords[0])
            for c in l.coords[1:]:
                s_ = test(*c)
                if s_ != side:
                    cur.append(c); (A if side else B).append(cur); cur, side = [c], s_
                else: cur.append(c)
            (A if side else B).append(cur)
        for part, yrs, n in ((A, a, nm[0]), (B, b, nm[1])):
            out.append({'route': r, 'name': n, 'y0': yrs[0], 'y1': yrs[1], 'lines': [[list(c) for c in p] for p in part if len(p) > 1]})
    elif r in WHOLE:
        out.append({'route': r, 'name': '', 'y0': WHOLE[r][0], 'y1': WHOLE[r][1], 'lines': [[list(c) for c in l.coords] for l in ls]})
    else:
        print('no dates for route', r)
json.dump(out, open(S + 'gif/freeways_dated.json', 'w'))
print(sorted((o['route'], o['name'], o['y0'], o['y1'], len(o['lines'])) for o in out))
