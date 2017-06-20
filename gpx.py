#!/usr/bin/env python
# coding: utf8

from PIL import Image, ImageDraw
import os
import sys
import zipfile
from xml.dom.minidom import parse, parseString
import logging as log
import gfx

# GPX helper class, for singular files
class GPX:
	points = []
	pointsbounds = [(),()]

	tiles = []
	tilesbounds = [(),(), ()]

	options = {
		'size': 2, # Max tile w×h for output image
		'border': 20, # TODO distance from edge of image to nearest path?
		'background': True, # Use OSM tiles to flesh the background out
		'antialiased': True,
		'linecolour': 'black',
		'linewidth': 1,
		'filename': '', # Default output filename if not provided
		'renderer': 'mapnik', # OSM server to use
		'cache': 'cache', # Default cache location
		'notice': 'normal'
		}

	def __init__( self ): log.debug('GPX()')

	def setOptions( self, opt ):
		self.options.update(opt)

		# Push the selected tile server into options
		tileservers = { 'mapnik': 'http://tile.openstreetmap.org',
						'osmarender': 'http://tah.openstreetmap.org/Tiles/tile/',
						'cyclemap': 'http://andy.sandbox.cloudmade.com/tiles/cycle/',
						}
		tileserver = { 'tileserver' : tileservers.get( self.options.get('renderer') ) }
		self.options.update(tileserver)

		log.debug('GPX.setOptions(%s)' % self.options)

	def load( self, dom ):
		log.debug('GPX.load()')

		# we're going to be ignorant of anything but trkpt for now
		# TODO support waypoints, track segments
		trackPoints = dom.getElementsByTagName('trkpt')
		self.points = map( lambda x: [float(x.getAttribute('lat')), float(x.getAttribute('lon'))], trackPoints)
		self.computeBounds()

	def loadFromFile( self, file ):
		log.debug('loadFromFile(%s)' % file)

		self.trackname = file
		dom = parse(file)
		self.load(dom)

	def loadFromString( self, string ):
		log.debug('loadFromString()')

		dom = parseString(string)
		self.load(dom)

	# calculate lat/long bounds of path
	# calculate tile area, and produce tile bounds
	def computeBounds( self ):
		log.debug('GPX.computeBounds()')

		latmin = longmin = 200000
		latmax = longmax = -200000

		for point in self.points:
			latmin = min(point[0], latmin)
			latmax = max(point[0], latmax)
			longmin = min(point[1], longmin)
			longmax = max(point[1], longmax)
		self.pointsbounds = [(latmax, longmin), (latmin, longmax)]

		self.tiles = gfx.Tile.calculateTilesAuto( self.pointsbounds, self.options.get('size') )

		self.tilesbounds[0] = gfx.Tile.getCoords( self.tiles['x']['min'], self.tiles['y']['min'], self.tiles['zoom'] )
		# because tile coords are from top left
		self.tilesbounds[1] = gfx.Tile.getCoords( self.tiles['x']['max']+1, self.tiles['y']['max']+1, self.tiles['zoom'] )
		self.tilesbounds[2] = (	self.tilesbounds[0][0] - self.tilesbounds[1][0],
							self.tilesbounds[0][1] - self.tilesbounds[1][1] )

	def drawTrack( self, filename = '' ):
		log.debug('GPX.drawTrack()')

		if filename == '' or filename == None:
			filename = self.options.get('filename')

		if filename == '' or filename == None:
			trackFile, trackType = os.path.splitext( self.trackname )
			filename = trackFile + '.png'

		imagesize = ( self.tiles['x']['count'] * 256, self.tiles['y']['count'] * 256 )
		image = Image.new("RGB", imagesize, '#ffffff')

		# If user wants OSM tile background, do it
		# TODO without OSM tiles, our current code wont crop the track well
		if self.options.get('background'):
			cachelocation = os.path.join('.',  self.options.get('cache'), self.options.get('renderer'))
			image = gfx.Tile.populateBackground(self.options.get('tileserver'), cachelocation, self.tiles, image)

		# compute pixel locations
		pointlist = map( lambda x: gfx.Tile.getPixelForCoord(x, self.tilesbounds, imagesize), self.points)

		# TODO give user option to style

		# XXX Supersample our line to make it smarter
		if self.options.get('antialiased'):
			newsize = (imagesize[0]*4, imagesize[1]*4)
			background = image.resize( newsize )
			draw = ImageDraw.ImageDraw(background)
			pointlist = map( lambda x: gfx.Tile.getPixelForCoord(x, self.tilesbounds, newsize), self.points)
			draw.line(pointlist, fill=self.options.get('linecolour'), width=self.options.get('linewidth')*4)
			image = background.resize( imagesize, Image.ANTIALIAS )
		else:
			draw = ImageDraw.Draw(image)
			pointlist = map( lambda x: gfx.Tile.getPixelForCoord(x, self.tilesbounds, imagesize), self.points)
			draw.line(pointlist, fill=self.options.get('linecolour'), width=self.options.get('linewidth'))

		# Attempt to intelligently trim the image if its over
		# TODO give user a gutter option
		# TODO give user a scale option
		# TODO move to function
		size = self.options.get('size')
		if size*size < self.tiles['x']['count']*self.tiles['y']['count']:
			path = [ gfx.Tile.getPixelForCoord( self.pointsbounds[0], self.tilesbounds, imagesize),
					gfx.Tile.getPixelForCoord( self.pointsbounds[1], self.tilesbounds, imagesize) ]
			imagebox = [ [0,0], list(imagesize) ]
			# so here we have a bounding box for the path, can we trim edges of image?
			if imagesize[0] > size * 256:
				# TODO assumption is, we can trim a tile, might need 2 × in future
				if path[1][0] - path [0][0] < imagesize[0] - 256:
					# We can trim
					centrex = (path[1][0] - path [0][0])/2 + path[0][0]
					halfwidth = ((imagesize[0] - 256) / 2)
					imagebox[0][0] = centrex - halfwidth
					imagebox[1][0] = centrex + halfwidth

			if imagesize[1] > size * 256:
				# TODO same as above
				if path[1][1] - path [0][1] < imagesize[1] - 256:
					centrey = (path[1][1] - path [0][1])/2 + path[0][1]
					halfwidth = ((imagesize[1] - 256) / 2)
					imagebox[0][1] = centrey - halfwidth
					imagebox[1][1] = centrey + halfwidth

			imagebox = reduce(lambda x,y: x+y,imagebox)
			image = image.crop( imagebox )

		#trim = int(256/2)
		#image = image.crop( tuple( [trim, trim] + map( lambda x: x-trim, image.size) ) )

		# Only draw if OSM background used.
		if self.options.get('background'):
			# Draw CC licence image
			ccimage = 'cc-by-sa.' + self.options.get('notice') + '.png'
			# TODO fail if image is missing
			cclogo = Image.open(ccimage)
			cclocation = {
				'small': (85,20),  # small 80 × 15
				'normal': (93,36), # normal 88 × 31
			}.get( self.options.get('notice'), (85,20) )
			cclocation = (image.size[0] - cclocation[0], image.size[1] - cclocation[1] )
			image.paste(cclogo, cclocation, cclogo)
			# Draw OSM logo
			osmlogo = Image.open('osm.png')
			osmlogosize = {
				'small': 16,  # small 80 × 15
				'normal': 32, # normal 88 × 31
			}.get( self.options.get('notice'), 32 )
			osmlogo = osmlogo.resize( (osmlogosize,osmlogosize), Image.ANTIALIAS)
			osmlocation = (cclocation[0] - osmlogosize - 5, cclocation[1])
			image.paste(osmlogo, osmlocation, osmlogo)


		# write file
		image.save(filename, "PNG")

class KML(GPX):

	def load( self, dom ):
		log.debug('KML.load()')

		# we're going to be ignorant of anything but gx:coord for now
		# TODO support waypoints, track segments
		trackPoints = dom.getElementsByTagName('gx:coord')
		trackPoints = [ x.firstChild.data.split() for x in trackPoints ]
		self.points = map( lambda x: [float(x[1]), float(x[0])], trackPoints)
		self.computeBounds()

class KMZ(KML):

	def loadFromFile( self, file ):
		log.debug('KMX.loadFromFile(%s)' % file)

		if not zipfile.is_zipfile( file ):
			log.error('File is not a valid ZIP')
			sys.exit(-1)

		self.trackname = file

		with zipfile.ZipFile( file, 'r' ) as kml:
			file_contents = kml.read( 'doc.kml' )

		dom = parseString(file_contents)
		self.load(dom)

def loadFromFile( trackpath ):

	trackFile, trackType = os.path.splitext( trackpath )
	# since OS do not love mime types :'( we do the stupid thing, test on extension!!!
	if trackType == '.gpx':
		log.info('Selected GPX parser')
		track = GPX()
	elif trackType == '.kml':
		log.info('Selected KML parser')
		track = KML()
	elif trackType == '.kmz':
		log.info('Selected KMZ parser')
		track = KMZ()
	else:
		log.error('Invalid filetype provided: %s' % track)
		sys.exit(-1)

	track.loadFromFile( trackpath )
	return track
