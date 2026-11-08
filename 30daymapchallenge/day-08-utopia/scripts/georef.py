import json, numpy as np
from pyproj import Transformer
p=json.load(open('work/circles2.json'))
drop={21,47,48}
pts={i:(x,y) for i,(x,y,s) in enumerate(p) if i not in drop}
# manually added (missed by detector): display coords -> full res
extra={'reseda':(757,653),'north_hollywood':(1358,842),'universal_city':(1388,923),'east_la':(2130,1443),
       'venice':(983,1581),'redondo':(1267,2204),'san_pedro':(1663,2681)}
names={0:'San Fernando',1:'Granada Hills',2:'Chatsworth',3:'Northridge',4:'Panorama City',5:'Van Nuys',6:'Canoga Park–Woodland Hills',
7:'Burbank',8:'Sherman Oaks',9:'Pasadena',10:'Glendale',11:'Highland Park',12:'Hollywood (east circle)',13:'Hollywood (west circle)',
14:'East Hollywood',15:'Alhambra',16:'Sunset Strip',17:'Echo Park',18:'Lincoln Heights',19:'Beverly Hills',20:'Miracle Mile (west circle)',
22:'Wilshire Center (west circle)',23:'Century City',24:'Miracle Mile (east circle)',25:'Wilshire Center (east circle)',26:'Civic Center (east circle)',
27:'Westwood',28:'General Hospital',29:'Regional Core — unlabelled (Westlake)',30:'Civic Center (west circle)',31:'Downtown',32:'Boyle Heights',
33:'Santa Monica',34:'Exposition Park–USC',35:'Culver City',36:'Crenshaw',37:'Vernon–Central',38:'Huntington Park',39:'Vermont–Manchester',
40:'Avalon–Manchester',41:'Inglewood',42:'Watts',43:'Westchester–Airport',44:'Downey',45:'Compton',46:'South Bay',49:'Lakewood',50:'Del Amo',51:'Long Beach'}
xname={'reseda':'Reseda','north_hollywood':'North Hollywood','universal_city':'Universal City','east_la':'East Los Angeles','venice':'Venice','redondo':'Redondo Beach','san_pedro':'San Pedro'}
C=[(names[i],x,y) for i,(x,y) in pts.items()]+[(xname[k],x,y) for k,(x,y) in extra.items()]
print(len(C))
ctrl={'Santa Monica':(34.0165,-118.4957),'Long Beach':(33.7701,-118.1937),'San Pedro':(33.7375,-118.2810),'Pasadena':(34.1456,-118.1500),
'San Fernando':(34.2819,-118.4390),'Chatsworth':(34.2572,-118.6012),'Downey':(33.9401,-118.1332),'Burbank':(34.1808,-118.3090),
'Glendale':(34.1468,-118.2551),'Westwood':(34.0592,-118.4446),'Inglewood':(33.9617,-118.3531),'Compton':(33.8958,-118.2201),
'Redondo Beach':(33.8422,-118.3929),'Lakewood':(33.8536,-118.1339),'Downtown':(34.0485,-118.2529),'Van Nuys':(34.1867,-118.4490),
'Canoga Park–Woodland Hills':(34.1840,-118.6010),'Alhambra':(34.0950,-118.1270)}
tr=Transformer.from_crs(4326,3310,always_xy=True); inv=Transformer.from_crs(3310,4326,always_xy=True)
A=[];B=[]
for n,x,y in C:
    if n in ctrl:
        lat,lng=ctrl[n]; X,Y=tr.transform(lng,lat); A.append([x,y,1]); B.append([X,Y])
A=np.array(A);B=np.array(B)
M,res,_,_=np.linalg.lstsq(A,B,rcond=None)
pred=A@M; err=np.hypot(*(pred-B).T)
print('affine RMSE m',np.sqrt((err**2).mean()).round(0),'max',err.max().round(0))
for (n,x,y) in C:
    if n in ctrl:
        k=[c for c in C if c[0]==n][0]
for n,e in zip([n for n,x,y in C if n in ctrl],err): print(f'{n:30s} {e:7.0f}')
out=[]
for n,x,y in C:
    X,Y=np.array([x,y,1])@M; lng,lat=inv.transform(X,Y); out.append({'name':n,'px':[x,y],'lat':round(lat,5),'lng':round(lng,5)})
json.dump({'M':M.tolist(),'centers':out},open('work/centers_georef.json','w'),indent=1)
