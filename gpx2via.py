#!/usr/bin/env python
# coding: utf8
import gpx2png
import geopy
from geopy.distance import great_circle
import logging as log
import pandas as pd
import numpy as np
import config

class Waypoint:
  #{{{
  def __init__(self, cy = None, cn = None, cc = None):
    self.city = cy
    self.country = cn
    self.country_code = cc

  def getCity(self):
    if self.city is None: return '?'
    else: return self.city

  def getCountry(self):
    if self.country is None: return '?'
    else: return self.country

  def getCountryCode(self):
    if self.country_code is None: return '?'
    else: return self.country_code

  def longText(self):
    return '%s in %s' % (self.getCity(), self.getCountry())

  def shortText(self):
    return '%s(%s)' % (self.getCity(), self.getCountryCode())
  #}}}


def lookupCoordinate(lat, lon):
  #{{{
  try:
    nom = geopy.Nominatim()
    rev = nom.reverse((lat, lon), exactly_one = True)
  except:  return Waypoint()
  
  city = None
  for f in ['village', 'town', 'city', 'state']:
    city = rev.raw['address'].get(f, None)
    if city is not None: break

  c_code = rev.raw['address'].get('country_code', '??')
  c_name = rev.raw['address'].get('country', '??').split(',')[0]

  return Waypoint(city, c_name, c_code)
  #}}}


def lookupMultipleCoordinates(data, steps = config.via_steps):
  #{{{
  assert data is not None
  places = geopy.Nominatim()
  grp_data = data.groupby(pd.TimeGrouper(freq = steps)).mean()

  old_via = None
  waypoints = pd.Series()

  log.info('Looking up %i coordinates...' % len(grp_data))
  for ts, (lat, lon) in grp_data.iterrows():
    new_via = lookupCoordinate(lat, lon)
    if old_via == new_via.shortText(): continue
    waypoints.loc[ts] = new_via
    old_via = new_via.shortText()

  return waypoints
  #}}}
    

def calculateTrackLenght(data):
  #{{{
  # Combine start and end points
  X0 = data.add_suffix('_0')
  X1 = data.shift(-1).add_suffix('_1')
  # Calculate distance along the great circle
  DX = pd.concat([X0, X1], axis = 1).iloc[:-1].apply(
    lambda x: great_circle(
      tuple(x[['lat_0', 'lon_0']]),
      tuple(x[['lat_1', 'lon_1']])),
    axis = 1)
  return DX.sum()
  #}}}


if '__main__' == __name__:
  import os, sys
  from getopt import getopt

  enable_bulk = False

  opts, args = getopt(sys.argv[1:], 's:p:vbh')
  for opt, val in opts:
    if '-s' == opt: config.via_steps = val
    elif '-p' == opt: config.perc = val
    elif '-v' == opt: log.getLogger().setLevel(log.INFO)
    elif '-b' == opt: enable_bulk = True
    elif '-h' == opt:
      print '''Usage: %s [options] FILE...

Calculate waypoints for given tracks in FILE...

Available options:
  -s X    Lookup waypoints every X (eg. `15Min\')
  -p FLT  Percentile for outlier detection
  -b      Evaluate files seperately (bulk)
  -v      Generate verbose output
  -h      Show this message and terminate
''' % os.path.basename(sys.argv[0])
      sys.exit(0)

  job_list = [gpx2png.loadFromFile(fname) for fname in args]
  if enable_bulk: job_list = [pd.concat(job_list)] + job_list

  for i, X in enumerate(job_list):
    # X = gpx2png.loadFromMultipleFiles(args)
    X = gpx2png.removeOutliersByPercentile(X, config.perc)
    if 0 < i: print ''
    print 'Route %i: %s' % (i + (1 - enable_bulk), X.index[0].strftime('%d.%m.%Y %H:%M'))

    # Zeiten
    t_from, t_till = (X.index[0], X.index[-1])
    print 'Zeitraum(UTC): %s -- %s' % (t_from, t_till)
    print u'Länge: %.2f km in %s' % (1e-3 * calculateTrackLenght(X).meters, t_till - t_from)

    # Wegpunkte
    wpts = lookupMultipleCoordinates(X, config.via_steps)
    print u'Von:  %s' % wpts[0].longText()
    if 2 < len(wpts):
      print u'Über: %s' % wpts[1].longText()
      for via in wpts[2:-1]: print '      %s' % via.longText()
    print u'Nach: %s' % wpts[-1].longText()
