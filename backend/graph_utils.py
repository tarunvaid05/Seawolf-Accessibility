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

CAMPUS_POLYGON = Polygon([
    (40.9222, -73.1415),  # Adjust these points based on real measurements
    (40.9222, -73.1150),
    (40.9155, -73.1105),
    (40.9085, -73.1130),
    (40.9050, -73.1235),
    (40.9075, -73.1335),
    (40.9130, -73.1390),
    (40.9222, -73.1415)  # Must close the shape
])

# Adjust the spacing (in decimal degrees). 1 degree of lat ~ 111 km. 
# 0.0005 lat ~ ~55m. Tweak for desired density of points.
GRID_SPACING = 0.0005  

# For each grid point, connect it to its K nearest neighbors (within MAX_DIST_M meters).
K_NEAREST = 3
MAX_DIST_M = 200  