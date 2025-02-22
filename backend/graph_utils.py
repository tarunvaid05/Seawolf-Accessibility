import math
import googlemaps 
import networkx as nx
import pandas as pd
import numpy as np
import polyline
from scipy.spatial import KDTree
from shapely.geometry import Polygon
from config import GOOGLE_MAPS_API_KEY

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

###############################################################################
# 1) CONFIGURATION
###############################################################################
# Replace with your actual bounding box for Stony Brook University (approx. coords)

#done in counterclockwise for geospatial coordinates + shapely
CAMPUS_POLYGON = Polygon([
    (40.925398, -73.117393),  # Top-right (Northeast corner)
    (40.926034, -73.124602),  # Top-left (Northwest corner)
    (40.912822, -73.138967),  # on top of west apps
    (40.909763, -73.136451),  # under west j
    (40.908006, -73.126973),  # under tabler (updated)
    (40.908452, -73.124195),  # new coordinate
    (40.906895, -73.121700),  # new coordinate
    (40.905286, -73.122594),  # mid marine sciences
    (40.902669, -73.131498),  # far left map
    (40.893097, -73.127557),  # bottom left south p
    (40.893881, -73.120148),  # bottom right south p
    (40.900724, -73.122800),  # top right south p
    (40.904083, -73.107499),  # bottom right hospital
    (40.908453, -73.107537),  # mid right hospital
    (40.914851, -73.114094),  # top hospital
    (40.925398, -73.117393)   # Closing the loop (must match the first point)
])


# Adjust the spacing (in decimal degrees). 1 degree of lat ~ 111 km. 
# 0.0005 lat ~ ~55m. Tweak for desired density of points.
GRID_SPACING = 0.0005  

# For each grid point, connect it to its K nearest neighbors (within MAX_DIST_M meters).
K_NEAREST = 3
MAX_DIST_M = 200  