#!/usr/bin/env python
# coding: utf8

from PIL import Image, ImageDraw
import urllib
import math, os, sys
import logging as log

# Static methods for tile maths
class Tile:

	# Returns an OSM tile coordinate for the lat, long provided
	@staticmethod
	def getNumber( lat, long, zoom ):
		# Code from OSM
		latrad = math.radians(lat)
		n = 2.0 ** zoom
		xtile = int((long + 180.0) / 360.0 * n)
		ytile = int((1.0 - math.log(math.tan(latrad) + (1 / math.cos(latrad))) / math.pi) / 2.0 * n)
		return (xtile, ytile)

	# Returns a lat, long for the provided OSM tile coordinate
	@staticmethod
	def getCoords( xtile, ytile, zoom ):
		# Code from OSM
		n = 2.0 ** zoom
		long = xtile / n * 360.0 - 180.0
		latrad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
		lat = math.degrees(latrad)
		return(lat, long)

	# Return a URL for the tile at the tileserver
	@staticmethod
	def getTileURL( tileserver, tilex, tiley, zoom ):
		return '/'.join( [tileserver, zoom, str(tilex), str(tiley)] ) + '.png'

	# returns tile bounding box for the points at this zoom level
	@staticmethod
	def calculateTiles( bounds, zoom = 10 ):
		log.debug('Track.calculateTiles()')

		tilexmin = tileymin = 200000
		tilexmax = tileymax = 0
		[tilexmin, tileymin] = Tile.getNumber( bounds[0][0], bounds[0][1], zoom )
		[tilexmax, tileymax] = Tile.getNumber( bounds[1][0], bounds[1][1], zoom )

		return {'x': { 'min':tilexmin, 'max':tilexmax , 'count': tilexmax - tilexmin +1 },
				'y': { 'min':tileymin, 'max':tileymax , 'count': tileymax - tileymin +1 },
				'zoom': zoom }

	# returns tile bounding box that is automatically scaled to a correct zoom level.
	# The BB is +1 in all directions so we can trim the image later ()
	@staticmethod
	def calculateTilesAuto( bounds, size ):
		log.debug('Track.calculateTilesAuto()')

		zoomdefault = 16

		# get the default scale tiles
		tiles = Tile.calculateTiles( bounds, zoomdefault )
		while ( (tiles['x']['count']) * (tiles['y']['count']) >= ( size * size) ):
			zoomdefault -= 1
			tiles['x']['count'] >>= 1
			tiles['y']['count'] >>= 1

		# get the re-scaled tiles
		return Tile.calculateTiles( bounds, zoomdefault )

	@staticmethod
	def getPixelForCoord( point, bounds, imagesize ):
		return (int((bounds[0][1] - point[1] ) / bounds[2][1] * imagesize[0]) ,
				int((bounds[0][0] - point[0] ) / bounds[2][0] * imagesize[1]))

	# TODO fetch more bordering tiles than we need, so we can better fit our image!
	@staticmethod
	def populateBackground( server, cachelocation, tiles, image ):

		rootx = tiles['x']['min']
		rooty = tiles['y']['min']
		zoom = str(tiles['zoom'])

		if not os.path.isdir(cachelocation):
			os.makedirs(cachelocation)

		for x in range(tiles['x']['min'],tiles['x']['min'] + tiles['x']['count'] + 1):
			for y in range(tiles['y']['min'],tiles['y']['min'] + tiles['y']['count'] + 1):
				fromx = abs(rootx - x)
				fromy = abs(rooty - y)
				temptilename = '-'.join( [zoom, str(x), str(y) ] ) + '.png'
				temptilename = os.path.join(cachelocation, temptilename)
				# TODO thread this?
				# TODO also support it failing
				if not os.path.isfile( temptilename ):
					log.info('Fetching tile %i x %i…' % (x, y))
					urllib.urlretrieve( Tile.getTileURL( server, x, y, zoom ), temptilename )

				tile = Image.open( temptilename )
				image.paste( tile, (256*fromx, 256*fromy ))

		return image
