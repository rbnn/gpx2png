#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
	© 2015 John Drinkwater <john@nextraweb.com>
	http://johndrinkwater.name/code/gpx2png/

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

from optparse import OptionParser
import logging as log
import gpx

# need to include CC notice if we use tiles
cnotice = "CC BY-SA OpenStreetMap"

# variables
__version__ = 0.50

# XXX we are just using defaults now

if __name__ == "__main__":

	# Now support CLI arguments!
	parser = OptionParser(usage="usage: gpx2png.py [options] file.gpx")
	parser.add_option("-v", "--verbose",
			action="store_true", dest="verbose", default=False,
			help="output progress messages to stdout")
	parser.add_option("-o", "--output",
			action="store", dest="filename", default='',
			help="filename to write the track image to")
	parser.add_option("-b", "--background",
			action="store_false", dest="background", default=True,
			help="disable output of OSM tile background")

	(options, args) = parser.parse_args()
	if options.verbose: log.getLogger().setLevel(log.NOTSET)

	if len(args) == 0:
		parser.print_help()
		sys.exit(-1)

	if len(args) == 1:
		track = gpx.loadFromFile( args[0] )
		track.setOptions( options.__dict__ )
		track.drawTrack()
	else:
		# TODO Support more than one file in the same image
		for path in args:
			track = gpx.loadFromFile( path )
			track.setOptions( options.__dict__ )
			# atm, with multiple, we just let each one output once
			track.drawTrack()
