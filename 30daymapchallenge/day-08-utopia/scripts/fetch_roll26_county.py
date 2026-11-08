"""LA County Assessor Parcel Data, Roll 2026 (County of LA, ArcGIS Online table, edited Oct 2026):
every parcel in the County (RollYear 2026) -> raw2/roll2026_county.csv.
usage: python fetch_roll26_county.py <record count, e.g. 2400000>"""
import json, ssl, urllib.request, urllib.parse, time, csv, sys
from concurrent.futures import ThreadPoolExecutor
ctx = ssl.create_default_context()
U = 'https://services.arcgis.com/RmCCgQtiZLDCtblq/arcgis/rest/services/Assessor%20Parcel%20Data%20Roll%202026/FeatureServer/0/query'
F = ['UseType', 'YearBuilt', 'Units', 'CENTER_LAT', 'CENTER_LON', 'TaxRateArea_CITY']
BASE = dict(where="RollYear='2026'", outFields=','.join(F),
            returnGeometry='false', orderByFields='OBJECTID', f='json')
def page(off):
    p = dict(BASE, resultOffset=off, resultRecordCount=1000)
    for i in range(7):
        try:
            with urllib.request.urlopen(U + '?' + urllib.parse.urlencode(p), context=ctx, timeout=180) as r:
                d = json.load(r)
            if 'features' in d:
                return [f['attributes'] for f in d['features']]
            raise RuntimeError(str(d)[:200])
        except Exception as e:
            time.sleep(2 ** i)
    raise SystemExit(f'failed at {off}')
N = int(sys.argv[1])
rows = []
with ThreadPoolExecutor(14) as ex:
    for i, chunk in enumerate(ex.map(page, range(0, N + 1000, 1000))):
        rows += chunk
        if i % 50 == 0:
            print(i, len(rows), time.strftime('%H:%M:%S'), flush=True)
with open('raw2/roll2026_county.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(F)
    for a in rows:
        w.writerow([a.get(k) for k in F])
print('done', len(rows))
