import json
from pyproj import Geod
geod=Geod(ellps='WGS84')
# Named core of each 1974 Concept center (the district's commercial/civic heart = where the plan put the core + station)
CORE={
'San Fernando':(34.2836,-118.4405,'San Fernando Rd & Maclay Ave'),
'Granada Hills':(34.2657,-118.5236,'Chatsworth St & Zelzah Ave'),
'Chatsworth':(34.2572,-118.6012,'Devonshire St & Topanga Cyn Blvd'),
'Northridge':(34.2355,-118.5363,'Reseda Blvd & Nordhoff St'),
'Panorama City':(34.2222,-118.4489,'Van Nuys Blvd & Roscoe Blvd'),
'Van Nuys':(34.1867,-118.4489,'Van Nuys Blvd & Victory Blvd'),
'Canoga Park–Woodland Hills':(34.1833,-118.6030,'Warner Center (Topanga Cyn & Erwin)'),
'Burbank':(34.1808,-118.3090,'San Fernando Blvd & Olive Ave'),
'Sherman Oaks':(34.1515,-118.4480,'Ventura Blvd & Sepulveda Blvd'),
'Pasadena':(34.1458,-118.1441,'Colorado Blvd & Garfield Ave (Civic Center)'),
'Glendale':(34.1468,-118.2551,'Brand Blvd & Broadway'),
'Highland Park':(34.1112,-118.1925,'Figueroa St & York Blvd'),
'Hollywood (west circle)':(34.1016,-118.3387,'Hollywood Blvd & Highland Ave'),
'Hollywood (east circle)':(34.1016,-118.3267,'Hollywood Blvd & Vine St'),
'East Hollywood':(34.0983,-118.2917,'Sunset Blvd & Vermont Ave'),
'Alhambra':(34.0953,-118.1270,'Main St & Garfield Ave'),
'Sunset Strip':(34.0954,-118.3768,'Sunset Blvd & La Cienega Blvd'),
'Echo Park':(34.0780,-118.2606,'Sunset Blvd & Echo Park Ave'),
'Lincoln Heights':(34.0717,-118.2161,'N Broadway & Daly St'),
'Beverly Hills':(34.0667,-118.3995,'Wilshire Blvd & Beverly Dr'),
'Century City':(34.0590,-118.4170,'Avenue of the Stars & Constellation Blvd'),
'Westwood':(34.0592,-118.4446,'Wilshire Blvd & Westwood Blvd'),
'Miracle Mile (west circle)':(34.0627,-118.3610,'Wilshire Blvd & Fairfax Ave'),
'Miracle Mile (east circle)':(34.0622,-118.3434,'Wilshire Blvd & La Brea Ave'),
'Wilshire Center (west circle)':(34.0617,-118.3089,'Wilshire Blvd & Western Ave'),
'Wilshire Center (east circle)':(34.0625,-118.2910,'Wilshire Blvd & Vermont Ave'),
'Regional Core — unlabelled (Westlake)':(34.0573,-118.2755,'Wilshire Blvd & Alvarado St (MacArthur Park)'),
'Civic Center (west circle)':(34.0530,-118.2500,'Bunker Hill (Grand Ave & 2nd St)'),
'Civic Center (east circle)':(34.0537,-118.2428,'City Hall / Civic Center'),
'Downtown':(34.0485,-118.2550,'Pershing Square / 7th St'),
'General Hospital':(34.0617,-118.2090,'LAC+USC Medical Center'),
'Boyle Heights':(34.0466,-118.2103,'Brooklyn Ave (Cesar Chavez) & Soto St'),
'East Los Angeles':(34.0237,-118.1554,'Whittier Blvd & Atlantic Blvd'),
'Santa Monica':(34.0175,-118.4955,'Wilshire Blvd & 4th St'),
'Exposition Park–USC':(34.0170,-118.2870,'Exposition Park / USC'),
'Culver City':(34.0236,-118.3948,'Culver Blvd & Washington Blvd'),
'Crenshaw':(34.0105,-118.3352,'Crenshaw Blvd & Martin Luther King Jr Blvd'),
'Vernon–Central':(34.0040,-118.2565,'Vernon Ave & Central Ave'),
'Huntington Park':(33.9800,-118.2250,'Pacific Blvd'),
'Vermont–Manchester':(33.9600,-118.2917,'Vermont Ave & Manchester Ave'),
'Avalon–Manchester':(33.9602,-118.2652,'Avalon Blvd & Manchester Ave'),
'Inglewood':(33.9617,-118.3531,'Market St & Manchester Blvd'),
'Watts':(33.9425,-118.2430,'103rd St & Wilmington Ave'),
'Westchester–Airport':(33.9455,-118.3870,'Century Blvd hotel strip'),
'Downey':(33.9401,-118.1332,'Firestone Blvd & Downey Ave'),
'Compton':(33.8958,-118.2201,'Compton Civic Center'),
'South Bay':(33.8728,-118.3524,'Hawthorne Blvd & Artesia Blvd (South Bay Galleria)'),
'Del Amo':(33.8317,-118.3505,'Del Amo Fashion Center'),
'Redondo Beach':(33.8410,-118.3880,'Pacific Coast Hwy & Torrance Blvd'),
'Lakewood':(33.8536,-118.1339,'Lakewood Center'),
'Long Beach':(33.7680,-118.1925,'Pine Ave & Ocean Blvd'),
'San Pedro':(33.7385,-118.2830,'6th St & Pacific Ave'),
'Reseda':(34.2011,-118.5361,'Reseda Blvd & Sherman Way'),
'North Hollywood':(34.1686,-118.3763,'Lankershim Blvd & Chandler Blvd'),
'Universal City':(34.1390,-118.3620,'Universal City'),
'Venice':(33.9910,-118.4700,'Windward Ave & Main St'),
}
RENAME={'Civic Center (west circle)':'Bunker Hill (unlabelled circle)','Civic Center (east circle)':'Civic Center',
 'Regional Core — unlabelled (Westlake)':'Westlake (unlabelled circle)'}
g=json.load(open('work/centers_georef.json'))
out=[]; offs=[]
for c in g['centers']:
    lat,lng,core=CORE[c['name']]
    _,_,d=geod.inv(c['lng'],c['lat'],lng,lat); offs.append(d)
    out.append({'name':RENAME.get(c['name'],c['name']),'core':core,'lat':lat,'lng':lng,'dlat':c['lat'],'dlng':c['lng'],'off_m':round(d)})
    if d>1300: print('CHECK',c['name'],round(d))
import statistics
print('n',len(out),'median offset',round(statistics.median(offs)),'p90',round(sorted(offs)[int(.9*len(offs))]),'max',round(max(offs)))
json.dump({'rmse_affine_m':509,'centers':out},open('work/centers_final.json','w'),indent=1,ensure_ascii=False)
