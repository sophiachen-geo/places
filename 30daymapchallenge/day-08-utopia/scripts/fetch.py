"""Download every source layer into raw/ (run from the working directory).
Usage: python fetch.py {bldg|zoning|holc|fwy|bottle|aadt|city}
"""
import json, ssl, urllib.request, urllib.parse, sys, time
ctx=ssl.create_default_context()
def get(url, params):
    q=urllib.parse.urlencode(params)
    for i in range(4):
        try:
            with urllib.request.urlopen(url+'?'+q, context=ctx, timeout=120) as r: return json.load(r)
        except Exception as e:
            print('retry',e,file=sys.stderr); time.sleep(2**i)
    raise SystemExit('failed '+url)
def fetch(layer, out, where='1=1', fields='*', outSR=4326, offset_tol=None, page=2000):
    feats=[]; off=0
    while True:
        p={'where':where,'outFields':fields,'outSR':outSR,'f':'geojson','resultOffset':off,'resultRecordCount':page}
        if offset_tol: p['maxAllowableOffset']=offset_tol
        d=get(layer+'/query',p)
        fs=d.get('features',[]); feats+=fs
        print(out,len(feats),file=sys.stderr)
        if len(fs)<page and not d.get('properties',{}).get('exceededTransferLimit') and not d.get('exceededTransferLimit'): break
        off+=len(fs)
        if not fs: break
    json.dump({'type':'FeatureCollection','features':feats},open(out,'w'))
L=sys.argv[1]
R='raw/'
if L=='bldg':
    fetch('https://services.arcgis.com/RmCCgQtiZLDCtblq/ArcGIS/rest/services/Countywide_Building_Outlines_(2020)/FeatureServer/0', R+'tall2020.geojson', where='HEIGHT>=150', fields='HEIGHT,ELEV,AREA,BLD_ID')
if L=='zoning':
    fetch('https://services5.arcgis.com/7nsPwEMP38bSkCjy/ArcGIS/rest/services/Zoning/FeatureServer/15', R+'zoning_3310.geojson', fields='Zoning,CATEGORY', outSR=3310, offset_tol=4)
if L=='holc':
    fetch('https://services.arcgis.com/RmCCgQtiZLDCtblq/arcgis/rest/services/LA_County_HOLC/FeatureServer/0', R+'holc.geojson')
if L=='aadt':
    fetch('https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Traffic_AADT/FeatureServer/0', R+'aadt_la.geojson', where="CNTY='LA'")
if L=='fwy':
    fetch('https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/CRS_Functional_Classification/FeatureServer/0', R+'fwy_d7.geojson', where="Caltrans_District=7 AND F_System IN (1,2)", fields='RouteID,F_System,County_label', offset_tol=0.0002)
if L=='bottle':
    fetch('https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Bottlenecks/FeatureServer/0', R+'bottlenecks_d7.geojson', where="District='7'")
if L=='city':
    fetch('https://services1.arcgis.com/tzwalEyxl2rpamKs/arcgis/rest/services/Los_Angeles_City_Boundary/FeatureServer/0', R+'city.geojson', offset_tol=0.0002)
