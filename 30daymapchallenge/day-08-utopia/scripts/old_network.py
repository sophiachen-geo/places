"""The rail network Los Angeles dismantled: every Pacific Electric (Red Car) and Los Angeles Railway (Yellow Car) line
with a route map on Wikipedia, dated by its opening and final closing year.

  lines    the lines linked from Wikipedia's "List of Pacific Electric lines" and "Los Angeles Railway" articles; each
           line's route is its article's attached KML (Template:Attached KML/<article>, CC BY-SA, traced by Wikipedia
           editors from historical maps); years from the article's infobox ('open' and the LAST year in 'close',
           so a line cut back in stages counts until its last section closed)
  fetch    raw wikitext via index.php?action=raw, one request every 1.5 s; cached in ohm/articles/ and ohm/kml/
-> data/old_network.geojson, data/story_stats.json ['old_network'] (route miles open by year, shared track once)
"""
import json, os, re, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from shapely.geometry import LineString, MultiLineString, mapping
from shapely.ops import transform, unary_union
from pyproj import Transformer

S = 'ohm/'
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
UA = {'User-Agent': 'Mozilla/5.0 (compatible; research-script/1.0)'}
os.makedirs(S + 'articles', exist_ok=True); os.makedirs(S + 'kml', exist_ok=True)
safe = lambda t: re.sub(r'[^A-Za-z0-9]+', '_', t)

def raw(title, cache):
    f = S + cache + '/' + safe(title) + ('.kml' if cache == 'kml' else '.wiki')
    if os.path.exists(f): return open(f).read() or None
    u = 'https://en.wikipedia.org/w/index.php?' + urllib.parse.urlencode({'title': ('Template:Attached KML/' if cache == 'kml' else '') + title, 'action': 'raw'})
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r: t = r.read().decode('utf-8')
    except Exception:
        t = ''
    time.sleep(1.5)
    open(f, 'w').write(t)
    return t or None

def titles(article, rx):
    t = raw(article, 'articles') or ''
    out = []
    for l in re.findall(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]', t):
        l = l.strip()
        if re.search(rx, l) and 'Metro)' not in l and 'Bus' not in l and 'National City' not in l and l not in out: out.append(l)
    return out

def years(field, text):
    m = re.search(r'\|\s*' + field + r'\s*=([^\n]*)', text)
    ys = [int(y) for y in re.findall(r'(1[89]\d\d|20[0-2]\d)', m.group(1))] if m else []
    return ys

def kml_lines(k):
    k = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', k)
    root = ET.fromstring(k.encode('utf-8'))
    out = []
    for c in root.iter('coordinates'):
        pts = [tuple(map(float, p.split(',')[:2])) for p in c.text.split() if p.count(',') >= 1]
        if len(pts) >= 2: out.append(LineString(pts))
    return out

g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
feats, meta = [], []
for op, article, rx in [('PE', 'List of Pacific Electric lines', r'Line|Short Line|Air Line'), ('LARy', 'Los Angeles Railway', r'\(Los Angeles Railway\)')]:
    for title in titles(article, rx):
        art = raw(title, 'articles')
        if art and art.lstrip().upper().startswith('#REDIRECT'):
            title = re.search(r'\[\[([^\]|#]+)', art).group(1).strip(); art = raw(title, 'articles')
        k = raw(title, 'kml')
        o, c = years('open', art or ''), years('close', art or '')
        ok = bool(k and '<kml' in k)
        meta.append({'op': op, 'line': title, 'route': ok, 'open': o[0] if o else None, 'close': c[-1] if c else None})
        if not ok: continue
        ls = [l for l in kml_lines(k) if l.length > 0]
        if not ls: meta[-1]['route'] = False; continue
        g = MultiLineString(ls).simplify(0.00004)
        gm = mapping(g); gm['coordinates'] = [[[round(x, 5), round(y, 5)] for x, y in part] for part in gm['coordinates']]
        name = re.sub(r'\s*\((Los Angeles Railway|Pacific Electric)\)', '', title)
        feats.append({'type': 'Feature', 'geometry': gm, 'properties': {'name': name, 'op': op, 'open': meta[-1]['open'], 'close': meta[-1]['close'], 'wiki': title}})
        meta[-1]['g'] = transform(g2m, g)

# route miles open by year (shared track counted once: each line buffered 25 m and unioned)
def miles(y, op):
    gs = [m['g'].buffer(25) for m in meta if m.get('g') is not None and m['op'] == op and m['open'] and m['open'] <= y and (m['close'] is None or m['close'] >= y)]
    return round(unary_union(gs).area / 50 / 1609.34, 1) if gs else 0.0
by_year = [[y, miles(y, 'PE'), miles(y, 'LARy')] for y in range(1895, 1966)]
ever = {op: round(unary_union([m['g'].buffer(25) for m in meta if m.get('g') is not None and m['op'] == op]).area / 50 / 1609.34, 1) for op in ('PE', 'LARy')}
json.dump({'type': 'FeatureCollection', 'features': feats}, open(DAY + 'data/old_network.geojson', 'w'), separators=(',', ':'))
st = json.load(open(DAY + 'data/story_stats.json'))
st['old_network'] = {'miles_by_year': by_year, 'miles_ever': ever,
                     'lines': [{k: v for k, v in m.items() if k != 'g'} for m in meta],
                     'src': 'Wikipedia line articles and their attached route maps (KML, CC BY-SA); years from each article'}
json.dump(st, open(DAY + 'data/story_stats.json', 'w'), indent=1)
print(len(feats), 'routes of', len(meta), 'lines;', 'ever', ever)
print('peak', max(by_year, key=lambda r: r[1] + r[2]))
print('missing', [(m['op'], m['line']) for m in meta if not m['route']])
print('undated', [(m['op'], m['line'], m['open'], m['close']) for m in meta if m['route'] and (not m['open'] or not m['close'])])
print(os.path.getsize(DAY + 'data/old_network.geojson') // 1024, 'KB')
