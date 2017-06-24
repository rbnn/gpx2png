#!/usr/bin/env python
# coding: utf8

from gpx2png import getURL_mapnik

# Outliers exceed the 99-th percentile
perc = 99.0

# Default output name
fname = 'map.png'

options = dict(
  # Tile-Provider
  url = getURL_mapnik,
  # Local directory to cache tiles
  cache = 'db',
  # Default zoom-level
  zoom = 7,
  # Width of each tile
  xsize = 256,
  # Height of each tile
  ysize = 256,
  # Number of additional tiles left/right of the track
  xpad = 1,
  # Number of additional tiles above/below the track
  ypad = 1,
  # Default color of the track
  color = 'blue',
  # Default linewidth of the track
  width = 3,
  )
