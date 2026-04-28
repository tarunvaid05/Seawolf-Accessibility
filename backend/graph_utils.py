import math
import googlemaps 
import networkx as nx
import pandas as pd
import numpy as np
import polyline
from scipy.spatial import KDTree
from config import GOOGLE_MAPS_API_KEY

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

###############################################################################
# 1) CONFIGURATION
###############################################################################
# Replace with your actual bounding box for Stony Brook University (approx. coords)
BOUNDING_BOX = [40.9100, 40.9190, -73.1310, -73.1150]  # [min_lat, max_lat, min_lng, max_lng]

# Adjust the spacing (in decimal degrees). 1 degree of lat ~ 111 km. 
# 0.0005 lat ~ ~55m. Tweak for desired density of points.
GRID_SPACING = 0.0005  

# For each grid point, connect it to its K nearest neighbors (within MAX_DIST_M meters).
K_NEAREST = 3
MAX_DIST_M = 200  