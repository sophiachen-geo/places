"""Simplified outlines of every place named in the evidence-card charts -> data/chart_places.geojson, so a chart row
can take the map there. Run after story_stats.py and parks_per_home.py.
  ids: 'la:<plan area>' (City Community Plan Areas, raw2/cpa.geojson) or 'cc:<name>' (DRP City & Community boundaries)."""
import json, os
from shapely.geometry import shape, mapping
S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
st = json.load(open(DAY + 'data/story_stats.json'))
want = {('la' if p['kind'] == 'la' else 'cc') + ':' + p['name'] for p in st['boyle']['places'][:10]}
want |= {'la:' + p['name'] for p in st['parks']['la'][:6] + st['parks']['la'][-4:]}
src = {'la:' + f['properties']['NAME_ALF']: f['geometry'] for f in json.load(open(S + 'raw2/cpa.geojson'))['features']}
src.update({'cc:' + f['properties']['CITY_COMM_NAME']: f['geometry'] for f in json.load(open(S + 'raw2/city_comm.geojson'))['features']
            if f.get('geometry') and f['properties']['CITY_COMM_NAME'] != 'LOS ANGELES'})
def r(o):
    if isinstance(o, float): return round(o, 5)
    if isinstance(o, (list, tuple)): return [r(v) for v in o]
    return o
feats = []
for k in sorted(want):
    g = shape(src[k]).simplify(0.0004, preserve_topology=True)
    gm = mapping(g); gm['coordinates'] = r(gm['coordinates'])
    feats.append({'type': 'Feature', 'geometry': gm, 'properties': {'id': k}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(DAY + 'data/chart_places.geojson', 'w'), separators=(',', ':'))
print(len(feats), 'outlines', os.path.getsize(DAY + 'data/chart_places.geojson') // 1024, 'KB')
