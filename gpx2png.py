#!/usr/bin/env python
# coding: utf8

import pandas as pd
import numpy as np
import os
import datetime
from xml.dom.minidom import parse
import logging as log
from itertools import product
from urllib import urlretrieve
from PIL import Image, ImageDraw
import random


def loadFromFile(path):
  #{{{
  assert os.path.splitext(path)[1] == '.gpx'
  log.info('Loading file: %s' % path)

  dom = parse(path)
  tmp = dom.getElementsByTagName('trkpt')

  return pd.DataFrame(dict(
    lat = map(lambda x: float(x.getAttribute('lat')), tmp),
    lon = map(lambda x: float(x.getAttribute('lon')), tmp),
    ),
    index = map(lambda x: datetime.datetime.strptime(
        x.getElementsByTagName('time')[0].firstChild.nodeValue,
        '%Y-%m-%dT%H:%M:%SZ'),
      tmp)
  )
  #}}}


def loadFromMultipleFiles(paths):
  #{{{
  data = map(lambda x: loadFromFile(x), paths)
  return pd.concat(data)
  #}}}


def getTrackTileNumbers(track, zoom):
  #{{{
  r_lat = np.deg2rad(track['lat'])
  n = 2. ** zoom
  return pd.DataFrame(dict(
    xtile = np.array((track['lon'] + 180.) / 360. * n, dtype = float),
    ytile = np.array((1. - np.log(np.tan(r_lat) + (1 / np.cos(r_lat))) / np.pi) / 2. * n, dtype = float),
    ),
    index = track.index
  )
  #}}}
  

def fetchTile(x, y, zoom, opts):
  #{{{
  tile = opts['url'](zoom, x, y)
  local_dir = os.path.join(opts['cache'], str(zoom))
  local_file = os.path.join(local_dir, 'tile_%i_%i.png' % (x, y))

  if not os.path.exists(local_file):
    log.info('Fetching tile: %s' % tile)
    local_dir = os.path.join(opts['cache'], str(zoom))
    if not os.path.exists(local_dir): os.mkdir(local_dir)
    urlretrieve(tile, local_file)
  else: log.info('Using cached tile: %s' % local_file)

  return local_file
  #}}}


def createMap(data, opts, full = True):
  #{{{
  if not os.path.exists(opts['cache']):
    log.info('Creating cache-db `%s\'...' % opts['cache'])
    os.makedirs(opts['cache'])

  # Boundaries for the image
  x_min, x_max = (data['xtile'].min() - opts['xpad'], data['xtile'].max() + opts['xpad'])
  y_min, y_max = (data['ytile'].min() - opts['ypad'], data['ytile'].max() + opts['ypad'])

  # Create image
  image_size = np.array((
    opts['xsize'] * (x_max - x_min + 1),
    opts['ysize'] * (y_max - y_min + 1)), dtype = int)
  image = Image.new('RGB', image_size, '#ffffff')

  if full:
    for x, y in product(xrange(x_min, x_max + 1), xrange(y_min, y_max + 1)):
      tile_fname = fetchTile(x, y, opts['zoom'] , opts)
      tile = Image.open(tile_fname)
      image.paste(tile, (opts['xsize'] * (x - x_min), opts['ysize'] * (y - y_min)))
      del tile
  else:
    for idx, (x, y) in data[['xtile', 'ytile']].drop_duplicates().iterrows():
      tile_fname = fetchTile(x, y, opts['zoom'] , opts)
      tile = Image.open(tile_fname)
      image.paste(tile, (opts['xsize'] * (x - x_min), opts['ysize'] * (y - y_min)))
      del tile
    
  return image 
  #}}}


def drawTrack(img, data, opts):
  #{{{
  x_off = data['xtile'].astype(int).min() - opts['xpad']
  y_off = data['ytile'].astype(int).min() - opts['ypad']
  X = opts['xsize'] * (data['xtile'] - x_off)
  Y = opts['ysize'] * (data['ytile'] - y_off)
  gc = ImageDraw.Draw(img)
  gc.line(zip(X, Y), fill = opts['color'], width = opts['width'])
  #}}}


def removeOutliersByPercentile(X, perc = 99.0):
  #{{{
  d_lat = X['lat'].diff().fillna(0.).abs()
  d_lon = X['lon'].diff().fillna(0.).abs()
  lat_99 = np.percentile(d_lat, perc)
  lon_99 = np.percentile(d_lon, perc)
  I_lat = (d_lat <= lat_99)
  I_lon = (d_lon <= lon_99)
  return X[I_lat & I_lon]
  #}}}
    

def saveMap(img, fname):
  #{{{
  assert fname is not None, 'No filename given!'
  log.info('Writing map to file: %s' % fname)
  base, ext = os.path.splitext(fname.lower())
  
  ftype = None
  if '.png' == ext: ftype = 'PNG'
  elif ext in ['.jpg', '.jpeg']: ftype = 'JPEG'
  assert ftype is not None, 'Invalid image type!'
  
  img.save(fname, ftype)
  return fname
  #}}}


def getURL_mapnik(zoom, x, y):
  #{{{
  assert 0 <= zoom <= 14, 'Mapnik requires zoom-levels 0...18!'
  urls = {
    1: 'http://tile.openstreetmap.org/%i/%i/%i.png', 
    2: 'http://a.tile.openstreetmap.org/%i/%i/%i.png', 
    3: 'http://b.tile.openstreetmap.org/%i/%i/%i.png', 
    4: 'http://c.tile.openstreetmap.org/%i/%i/%i.png', 
    }
  i = random.randint(1, len(urls))
  return urls[i] % (zoom, x, y)
  #}}}

  
if '__main__' == __name__:
  import sys
  from getopt import getopt
  import config

  opts, args = getopt(sys.argv[1:], 'o:w:c:z:p:v')
  for opt, val in opts:
    if '-o' == opt: config.fname = val
    elif '-w' == opt: config.options['width'] = int(val)
    elif '-c' == opt: config.options['color'] = val
    elif '-z' == opt: config.options['zoom'] = int(val)
    elif '-p' == opt: config.perc = float(val)
    elif '-v' == opt: log.getLogger().setLevel(log.INFO)

  X = loadFromMultipleFiles(args)
  X = removeOutliersByPercentile(X, config.perc)
  
  N = getTrackTileNumbers(X, config.options['zoom'])
  img = createMap(N.astype(int), config.options)
  drawTrack(img, N, config.options)
  saveMap(img, config.fname)
