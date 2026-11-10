"""Median household income, American Community Survey 5-year 2020-2024 (the most recent release), shared by the charts.

Inputs (keyless Census Bureau files, in raw4/acs/):
  acsdt5y2024-b19001.dat   households by 16 income brackets   (table-based summary file, www2.census.gov)
  acsdt5y2024-b19013.dat   published median household income   (same)
  gaz_tracts_06.txt        2024 Gazetteer, tract internal points
  gaz_place_06.txt         2024 Gazetteer, places (cities and CDPs) with their GEOIDs
Two ways to a median:
  published(name)   the Bureau's own median for a city or census-designated place, matched by name
  pooled(geom)      the area's census tracts (by internal point) pooled, median interpolated within its B19001 bracket
"""
import csv
import numpy as np
from shapely import contains_xy

S = ''
BR = [0, 10e3, 15e3, 20e3, 25e3, 30e3, 35e3, 40e3, 45e3, 50e3, 60e3, 75e3, 100e3, 125e3, 150e3, 200e3, None]
TOP = 200000   # B19001's top bracket is $200,000 or more

_tr = {}
with open(S + 'raw4/acs/acsdt5y2024-b19001.dat') as f:
    rd = csv.reader(f, delimiter='|'); hdr = next(rd); ix = [hdr.index(f'B19001_E{i:03d}') for i in range(2, 18)]
    for row in rd:
        if row[0].startswith('1400000US06037'):
            _tr[row[0][9:]] = np.array([float(row[i] or 0) for i in ix])
_pub = {}
with open(S + 'raw4/acs/acsdt5y2024-b19013.dat') as f:
    rd = csv.reader(f, delimiter='|'); hdr = next(rd); k = hdr.index('B19013_E001')
    for row in rd:
        if row[0].startswith(('0500000US06', '1600000US06')) and row[k] not in ('', '-', 'N'):
            try: _pub[row[0]] = int(float(row[k]))
            except ValueError: pass
_tlon, _tlat, _tid = [], [], []
with open(S + 'raw4/acs/gaz_tracts_06.txt') as f:
    rd = csv.reader(f, delimiter='\t'); hdr = [h.strip() for h in next(rd)]
    for r in rd:
        g = r[hdr.index('GEOID')].strip()
        if g in _tr: _tid.append(g); _tlat.append(float(r[hdr.index('INTPTLAT')])); _tlon.append(float(r[hdr.index('INTPTLONG')]))
_tlon, _tlat = np.array(_tlon), np.array(_tlat)
_place = {}
with open(S + 'raw4/acs/gaz_place_06.txt') as f:
    rd = csv.reader(f, delimiter='\t'); hdr = [h.strip() for h in next(rd)]
    for r in rd:
        _place[r[hdr.index('NAME')].strip().lower()] = '1600000US' + r[hdr.index('GEOID')].strip()

COUNTY = _pub['0500000US06037']
CITY_LA = _pub['1600000US0644000']

def published(name):
    """the Bureau's median for a city or CDP whose name matches (County boundary names are upper case, ' - ' joins)"""
    k = name.lower().replace(' - ', '-')
    for suffix in (' city', ' cdp'):
        g = _place.get(k + suffix)
        if g and g in _pub: return _pub[g]
    return None

def pooled(geom):
    m = contains_xy(geom, _tlon, _tlat)
    if not m.any(): return None
    c = sum(_tr[_tid[i]] for i in np.nonzero(m)[0]); half = c.sum() / 2; cum = 0.0
    for j, cnt in enumerate(c):
        if cum + cnt >= half:
            if BR[j + 1] is None: return TOP
            return int(round(BR[j] + (half - cum) / cnt * (BR[j + 1] - BR[j]), -2))
        cum += cnt

def median(name, geom, kind):
    """(income, method): a city or CDP gets the published median; a plan area or composite community is pooled"""
    if kind != 'la':
        v = published(name)
        if v is not None: return v, 'published'
    return pooled(geom), 'pooled tracts'

# ---------------------------------------------------------------------------------------------------------------
# Transit commute share: workers 16+ who get to work by public transportation (excluding taxicab), table B08301
# (E010 / E001), ACS 5-year 2020-2024 (raw4/acs/acsdt5y2024-b08301.dat). A share pools by simple sums.
_tw = {}          # tract -> (workers, transit)
_pw = {}          # county / place GEO_ID -> (workers, transit)
with open(S + 'raw4/acs/acsdt5y2024-b08301.dat') as f:
    rd = csv.reader(f, delimiter='|'); hdr = next(rd); i1, i10 = hdr.index('B08301_E001'), hdr.index('B08301_E010')
    for row in rd:
        g = row[0]
        if g.startswith('1400000US06037') or g.startswith(('0500000US06', '1600000US06')):
            try: v = (float(row[i1] or 0), float(row[i10] or 0))
            except ValueError: continue
            if g.startswith('1400000US'): _tw[g[9:]] = v
            else: _pw[g] = v
def _pct(w, t): return round(t / w * 100, 1) if w else None
TRANSIT_COUNTY = _pct(*_pw['0500000US06037'])
TRANSIT_CITY_LA = _pct(*_pw['1600000US0644000'])

def transit_share(name, geom, kind):
    """(percent of workers commuting by public transit, method)"""
    if kind != 'la':
        k = name.lower().replace(' - ', '-')
        for suffix in (' city', ' cdp'):
            g = _place.get(k + suffix)
            if g and g in _pw: return _pct(*_pw[g]), 'published'
    m = contains_xy(geom, _tlon, _tlat)
    w = sum(_tw[_tid[i]][0] for i in np.nonzero(m)[0] if _tid[i] in _tw); t = sum(_tw[_tid[i]][1] for i in np.nonzero(m)[0] if _tid[i] in _tw)
    return _pct(w, t), 'pooled tracts'
