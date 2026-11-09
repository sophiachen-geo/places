"""Metro rail + busway lines cut into sections dated by the year each section opened (today's official line colours).
Geometry: Metro rail GTFS (Nov 2026) and bus GTFS (G Line 901, J Line 910; May 2026). Opening years: Metro history."""
import csv, json, collections
from shapely.geometry import LineString, Point
from shapely.ops import substring
from pyproj import Transformer
S = ''
g2w = Transformer.from_crs(4326, 3857, always_xy=True).transform
w2g = Transformer.from_crs(3857, 4326, always_xy=True).transform

def longest_shape(trips, shapes_txt, route_prefix):
    sids = {t['shape_id'] for t in trips if t['route_id'].split('-')[0] == route_prefix}
    pts = collections.defaultdict(list)
    with open(shapes_txt) as f:
        for r in csv.DictReader(f):
            if r['shape_id'] in sids: pts[r['shape_id']].append((int(r['shape_pt_sequence']), float(r['shape_pt_lon']), float(r['shape_pt_lat'])))
    sid = max(pts, key=lambda k: len(pts[k]))
    return LineString([g2w(x, y) for _, x, y in sorted(pts[sid])]), sid

rail_trips = list(csv.DictReader(open(S + 'raw2/gtfs_trips.txt')))
bus_trips = list(csv.DictReader(open(S + 'raw3/bus/trips.txt')))
stations = {}
for s in csv.DictReader(open(S + 'raw2/gtfs_stops.txt')):
    if s['location_type'] == '1': stations[s['stop_name'].replace(' Station', '')] = Point(g2w(float(s['stop_lon']), float(s['stop_lat'])))

LINES = {  # route, letter, colour, [(from station, to station, year opened)]
  '801': ('A', '#0072BC', [('Downtown Long Beach', 'Pico', 1990), ('Pico', '7th Street / Metro Center', 1991), ('7th Street / Metro Center', 'Little Tokyo / Arts District', 2023),
                          ('Little Tokyo / Arts District', 'Union', 2009), ('Union', 'Sierra Madre Villa', 2003), ('Sierra Madre Villa', 'APU / Citrus College', 2016), ('APU / Citrus College', 'Pomona North', 2025)]),
  '802': ('B', '#EB131B', [('Union', 'Westlake / MacArthur Park', 1993), ('Westlake / MacArthur Park', 'Wilshire / Vermont', 1996), ('Wilshire / Vermont', 'Hollywood / Vine', 1999), ('Hollywood / Vine', 'North Hollywood', 2000)]),
  '805': ('D', '#A05DA5', [('Union', 'Westlake / MacArthur Park', 1993), ('Westlake / MacArthur Park', 'Wilshire / Western', 1996), ('Wilshire / Western', 'Wilshire / La Cienega', 2026)]),
  '804': ('E', '#FDB913', [('Downtown Santa Monica', 'Culver City', 2016), ('Culver City', '7th Street / Metro Center', 2012), ('7th Street / Metro Center', 'Little Tokyo / Arts District', 2023), ('Little Tokyo / Arts District', 'Atlantic', 2009)]),
  '803': ('C', '#58A738', [('Norwalk', 'Aviation / Imperial', 1995), ('Aviation / Imperial', 'Aviation / Century', 2024), ('Aviation / Century', 'LAX / Metro Transit Center', 2025)]),
  '807': ('K', '#E56DB1', [('Expo / Crenshaw K-Line', 'Westchester / Veterans', 2022), ('Westchester / Veterans', 'Aviation / Century', 2025), ('Aviation / Century', 'Aviation / Imperial', 2024), ('Aviation / Imperial', 'Redondo Beach', 1995)]),
}
out = []
for rid, (letter, col, rules) in LINES.items():
    line, sid = longest_shape(rail_trips, S + 'raw2/gtfs_shapes.txt', rid)
    cuts = []
    for a, b, yr in rules:
        da, db = line.project(stations[a]), line.project(stations[b])
        cuts.append((min(da, db), max(da, db), yr))
    cuts.sort()
    # close tiny gaps at the ends and between rules so the whole line is covered
    cuts[0] = (0.0, cuts[0][1], cuts[0][2]); cuts[-1] = (cuts[-1][0], line.length, cuts[-1][2])
    for k in range(1, len(cuts)): cuts[k] = (cuts[k - 1][1], cuts[k][1], cuts[k][2])
    for d0, d1, yr in cuts:
        seg = substring(line, d0, d1)
        out.append({'line': letter, 'color': col, 'year': yr, 'kind': 'rail', 'coords': [[round(c, 5) for c in w2g(*p)] for p in seg.coords]})
    print(letter, sid, [(round(d0), round(d1), yr) for d0, d1, yr in cuts])
# busways: G (2005; Canoga -> Chatsworth 2012), J (2009)
g, gid = longest_shape(bus_trips, S + 'raw3/bus/shapes.txt', '901')
canoga = Point(g2w(-118.5973, 34.1917))      # Canoga station, G Line
dc = g.project(canoga)
parts = [(0, dc, None), (dc, g.length, None)]
# the Chatsworth branch is the part north of Canoga
p0, p1 = substring(g, 0, dc), substring(g, dc, g.length)
north = p0 if w2g(*p0.coords[len(p0.coords) // 2])[1] > 34.20 else p1
for seg in (p0, p1):
    out.append({'line': 'G', 'color': '#FC4C02', 'year': 2012 if seg is north else 2005, 'kind': 'bus', 'coords': [[round(c, 5) for c in w2g(*p)] for p in seg.coords]})
j, jid = longest_shape(bus_trips, S + 'raw3/bus/shapes.txt', '910')
out.append({'line': 'J', 'color': '#ADB8BF', 'year': 2009, 'kind': 'bus', 'coords': [[round(c, 5) for c in w2g(*p)] for p in j.coords]})
print('G', gid, 'J', jid)
json.dump(out, open(S + 'gif/transit_segments.json', 'w'))
print(len(out), 'sections')
