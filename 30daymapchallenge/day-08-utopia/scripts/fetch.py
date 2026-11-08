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
if L=='shn':
    fetch('https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/SHN_Lines/FeatureServer/0', R+'shn_la.geojson', where="County='LA'")
if L=='aadt':
    fetch('https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Traffic_AADT/FeatureServer/0', R+'aadt_la.geojson', where="CNTY='LA'")
if L=='city':
    fetch('https://services1.arcgis.com/tzwalEyxl2rpamKs/arcgis/rest/services/City_Boundary_5db85/FeatureServer/0', R+'city.geojson')
if L=='fwy':
    fetch('https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/CRS_Functional_Classification/FeatureServer/0', R+'fwy_d7.geojson', where="Caltrans_District=7 AND F_System IN (1,2)", fields='RouteID,F_System,County_label', offset_tol=0.0002)
if L=='bottle':
    fetch('https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Bottlenecks/FeatureServer/0', R+'bottlenecks_d7.geojson', where="District='7'")
if L=='aadt':
    fetch('https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Traffic_AADT/FeatureServer/0', R+'aadt_la.geojson', where="CNTY='LA'")
if L=='city2':
    fetch('https://services1.arcgis.com/tzwalEyxl2rpamKs/arcgis/rest/services/Los_Angeles_City_Boundary/FeatureServer/0', R+'city.geojson', offset_tol=0.0002)
if L=='postmiles':
    fetch('https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/SHN_Postmiles_Tenth/FeatureServer/0', 'raw2/postmiles_la.geojson', where="County='LA' AND Route IN (2,5,10,60,101,105,110,405,605,710)", fields='Route,PMPrefix,PM,PMSuffix,Odometer,Direction,AlignCode')
if L=='hcm':
    fetch('https://services1.arcgis.com/tzwalEyxl2rpamKs/arcgis/rest/services/Historic_Preservation_CPA/FeatureServer/0', 'raw2/hcm.geojson', where="1=1", fields='HIST_TYPE,MNT_TYPE,MNT_NUM,NAME,LOCATION,DATE_ACTIVE,STATUS')
if L=='places':   # story page: outlines of the places named in the essay
    fetch('https://services.arcgis.com/RmCCgQtiZLDCtblq/arcgis/rest/services/admin_dist_SDE_DIST_DRP_CITY_COMM_BDY/FeatureServer/0', 'raw2/city_comm.geojson', where="1=1", fields='*', offset_tol=0.00005)
    fetch('https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/Area_Planning_Commissions/FeatureServer/0', 'raw2/apc.geojson', where="1=1", fields='*', offset_tol=0.00005)
    fetch('https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/Community_Plan_Areas/FeatureServer/0', 'raw2/cpa.geojson', where="1=1", fields='*', offset_tol=0.00005)
    fetch('https://services5.arcgis.com/7nsPwEMP38bSkCjy/ArcGIS/rest/services/Historic_Preservation_Overlay_Zones/FeatureServer/5', 'raw2/hpoz.geojson', where="1=1", fields='NAME', offset_tol=0.00002)
