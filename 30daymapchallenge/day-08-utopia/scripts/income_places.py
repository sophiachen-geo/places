"""Add median household income (acs_income.py) to every place in the 500-ft freeway ranking of data/story_stats.json.
Run after story_stats.py."""
import json, os, sys
from shapely.geometry import shape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acs_income as ai

S = ''
DAY = os.environ.get("DAY", "../places/30daymapchallenge/day-08-utopia/")
geo = {('la', f['properties']['NAME_ALF']): shape(f['geometry']) for f in json.load(open(S + 'raw2/cpa.geojson'))['features']}
for f in json.load(open(S + 'raw2/city_comm.geojson'))['features']:
    pr = f['properties']
    if f.get('geometry') and pr['CITY_COMM_NAME'] != 'LOS ANGELES':
        geo[('city' if pr['JURISDICTION'] == 'INCORPORATED CITY' else 'unincorporated', pr['CITY_COMM_NAME'])] = shape(f['geometry'])
st = json.load(open(DAY + 'data/story_stats.json'))
B = st['boyle']
for p in B['places']:
    p['median_income'], p['income_method'] = ai.median(p['name'], geo[(p['kind'], p['name'])], p['kind'])
B['city']['median_income'], B['county']['median_income'] = ai.CITY_LA, ai.COUNTY
B['income_src'] = 'U.S. Census Bureau, American Community Survey 5-year estimates 2020-2024 (B19013 published medians for cities and CDPs; B19001 brackets pooled over tracts for plan areas and composite communities)'
json.dump(st, open(DAY + 'data/story_stats.json', 'w'), indent=1)
for p in B['places'][:10]: print(f"{p['within_500ft_pct']:5.1f}%  ${p['median_income']:>7,}  {p['income_method']:14s} {p['name']}")
