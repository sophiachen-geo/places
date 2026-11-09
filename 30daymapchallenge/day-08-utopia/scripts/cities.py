"""Incorporated city boundaries for the story map -> data/cities.geojson
Source: Los Angeles County, City and Unincorporated Community Boundaries (raw2/city_comm.geojson, fetch.py places).
Generalised to ~30 m for the web; 'la' flags the City of Los Angeles."""
import json, os
from shapely.geometry import shape, mapping
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
out = []
for f in json.load(open("raw2/city_comm.geojson"))["features"]:
    p = f["properties"]
    if p["JURISDICTION"] != "INCORPORATED CITY" or not f.get("geometry"): continue
    g = shape(f["geometry"]).simplify(0.0003, preserve_topology=True)
    m = mapping(g)
    def r(o): return round(o, 5) if isinstance(o, float) else [r(v) for v in o] if isinstance(o, (list, tuple)) else o
    m["coordinates"] = r(m["coordinates"])
    out.append({"type": "Feature", "properties": {"name": p["CITY_COMM_NAME"].title(), "la": p["CITY_COMM_NAME"] == "LOS ANGELES"}, "geometry": m})
json.dump({"type": "FeatureCollection", "features": out}, open(DAY + "data/cities.geojson", "w"), separators=(",", ":"))
print(len(out), "cities")
