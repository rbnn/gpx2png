A small tool to produce images of your GPS track breadcrumbs over the top of
OSM mapping tile data.

Naïvely supports GPX files. If you have any other formats, for the
time being you can use `gpsbabel` to convert into GPX.

The tool is able to detect outliers based on the 99-percentile.

Usage: ./gpx2png.py [options] TRACK\_0.gpx [...TRACK\_N.gpx]

The program automatically concatenates the files 0 to N.

Available options:
  -o FILE   Write resulting image into FILE
  -w INT    Width of the track in pixels
  -c STR    Color of the track (e.g. blue, red, black,...)
  -z INT    Zoom-level of the background
  -p FLT    Change the percentile to FLT for outlier-suppression
  -v        Enable verbose output

More options can be set in the file config.py

Requirements:
  Pillow (http://pillow.readthedocs.io/en/3.1.x/index.html)
