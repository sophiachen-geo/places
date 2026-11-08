"""What the 56 centres of the 1974 Concept became beyond 'high-rises + Metro rail' (run after build2.py).

Adds to every centre in data/centers.geojson, within 1/2 mile (804.7 m) of its core:
  jobs     all jobs, LEHD LODES8 Workplace Area Characteristics 2023 (block internal points)
  homes    housing units on the 2026 Assessor roll ('Units'), and sfr_pct = share of them in single-family houses
  post74   share of built parcels whose main building dates from after 1974
  mid      buildings of 120-149 ft (LARIAC 2020), i.e. just under the 150-ft high-rise test
  ml, ml_m nearest Metrolink station (GTFS, May 2026) and its distance
and, for the 28 'neither' centres, a sub-type `nb` (first rule that applies):
  jobs      >= 10,000 jobs within 1/2 mile                       -> an employment centre that was built low
  transit   Metro rail under construction within 1/2 mile, an open Metro station within 1 mile,
            or a busway / Metrolink station within 1/2 mile        -> transit close or coming
  urban     >= 4,000 homes within 1/2 mile (~8 per acre; the City averages ~5) -> dense low-rise neighbourhood
  suburban  everything else
Writes the counts to data/stats.json -> centers.neither_types.

inputs (working directory): raw3/ca_wac_S000_JT00_2023.csv.gz, raw3/ca_xwalk.csv.gz (lehd.ces.census.gov/data/lodes/LODES8/ca/),
raw3/ml/stops.txt (metrolinktrains.com/globalassets/about/gtfs/gtfs.zip), raw2/roll2026_county.csv, raw/mid2020.geojson,
raw/tall2020.geojson (fetch.py bldg / bldg120).
"""
import csv, gzip, json, os, statistics as st
import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import shape

DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
g2m = Transformer.from_crs(4326, 3310, always_xy=True).transform
R = 804.7
C = json.load(open(DAY + "data/centers.geojson"))
xy = np.array([f["geometry"]["coordinates"] for f in C["features"]])
cores = np.c_[g2m(xy[:, 0], xy[:, 1])]

# jobs (LODES block internal points)
pts = {}
with gzip.open("raw3/ca_xwalk.csv.gz", "rt") as f:
    r = csv.reader(f); h = next(r)
    ib, ic, ila, ilo = h.index("tabblk2020"), h.index("cty"), h.index("blklatdd"), h.index("blklondd")
    for row in r:
        if row[ic] in ("06037", "06059", "06111", "06071", "06065"):
            pts[row[ib]] = (float(row[ilo]), float(row[ila]))
jp, jn = [], []
wac = "raw3/ca_wac_S000_JT00_2023.csv.gz" if os.path.exists("raw3/ca_wac_S000_JT00_2023.csv.gz") else "raw3/ca_wac_2023.csv.gz"
with gzip.open(wac, "rt") as f:
    r = csv.reader(f); next(r)
    for row in r:
        p = pts.get(row[0])
        if p: jp.append(p); jn.append(int(row[1]))
jp = np.array(jp); jn = np.array(jn)
jt = cKDTree(np.c_[g2m(jp[:, 0], jp[:, 1])])

# homes, single-family share, build years (2026 roll, county)
lo, la, un, sfr, yr = [], [], [], [], []
with open("raw2/roll2026_county.csv") as f:
    for a in csv.DictReader(f):
        try:
            x, y = float(a["CENTER_LON"]), float(a["CENTER_LAT"])
        except ValueError:
            continue
        lo.append(x); la.append(y); un.append(int(float(a["Units"] or 0))); sfr.append(a["UseType"] == "SFR")
        try: yr.append(int(float(a["YearBuilt"] or 0)))
        except ValueError: yr.append(0)
un, sfr, yr = np.array(un), np.array(sfr), np.array(yr)
pt = cKDTree(np.c_[g2m(np.array(lo), np.array(la))])

# 120-149 ft buildings: merge parts within 30 m, drop parts of >=150 ft towers
def cents(path):
    return np.array([g2m(*shape(f["geometry"]).centroid.coords[0]) for f in json.load(open(path))["features"]])
tall, mid = cents("raw/tall2020.geojson"), cents("raw/mid2020.geojson")
mid = mid[cKDTree(tall).query(mid)[0] > 40]
keep = []
for p in mid:
    if all(np.hypot(*(p - q)) > 30 for q in keep): keep.append(p)
mt_ = cKDTree(np.array(keep))

ml = list(csv.DictReader(open("raw3/ml/stops.txt")))
mlt = cKDTree(np.c_[g2m(np.array([float(s["stop_lon"]) for s in ml]), np.array([float(s["stop_lat"]) for s in ml]))])

types = {"jobs": [], "transit": [], "urban": [], "suburban": []}
for k, f in enumerate(C["features"]):
    p = f["properties"]
    idx = np.array(pt.query_ball_point(cores[k], R), int)
    u = un[idx]; built = yr[idx] > 1850
    d, j = mlt.query(cores[k])
    p.update(jobs=int(jn[jt.query_ball_point(cores[k], R)].sum()), homes=int(u.sum()),
             sfr_pct=round(float(u[sfr[idx]].sum() / max(1, u.sum()) * 100), 1),
             post74=round(float((yr[idx][built] > 1974).mean() * 100), 1) if built.any() else None,
             mid=len(mt_.query_ball_point(cores[k], R)), ml=ml[j]["stop_name"], ml_m=int(d))
    if p["oc"] == "neither":
        if p["jobs"] >= 10000: t = "jobs"
        elif p["rail"] == "building" or p["near_m"] <= 1609.3 or p["bus"] or p["ml_m"] <= R: t = "transit"
        elif p["homes"] >= 4000: t = "urban"
        else: t = "suburban"
        p["nb"] = t; types[t].append(p["name"])
json.dump(C, open(DAY + "data/centers.geojson", "w"), separators=(",", ":"))

S = json.load(open(DAY + "data/stats.json"))
S["centers"]["neither_types"] = {t: {"n": len(v), "names": v} for t, v in types.items()}
S["centers"]["median_by_outcome"] = {
    oc: {k: round(st.median(f["properties"][k] for f in C["features"] if f["properties"]["oc"] == oc), 1) for k in ("jobs", "homes", "sfr_pct", "mid")}
    for oc in ("realised", "towers", "rail", "neither")}
S["centers"]["jobs_src"] = "LEHD LODES8 WAC 2023 (all jobs)"
json.dump(S, open(DAY + "data/stats.json", "w"), indent=1)
for t, v in types.items(): print(t, len(v), v)
print(json.dumps(S["centers"]["median_by_outcome"]))
