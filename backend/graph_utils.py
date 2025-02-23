import math
import googlemaps 
import networkx as nx
import pandas as pd
import numpy as np
import polyline
import requests
import folium
from shapely.geometry import Polygon, LineString, Point
from config import GOOGLE_MAPS_API_KEY

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

###############################################################################
# 1) CONFIGURATION
###############################################################################
# Define the campus polygon for Stony Brook University
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

###############################################################################
# 2) FETCH WALKWAYS FROM OPENSTREETMAP (OSM) USING OVERPASS API
###############################################################################
overpass_url = "https://overpass-api.de/api/interpreter"

# Define the Overpass API query for all footways inside SBU bounding box
query = f"""
[out:json];
way["highway"="footway"]({CAMPUS_POLYGON.bounds[1]},{CAMPUS_POLYGON.bounds[0]},
                          {CAMPUS_POLYGON.bounds[3]},{CAMPUS_POLYGON.bounds[2]});
out geom;
"""

# Request data from Overpass API
response = requests.get(overpass_url, params={"data": query})

if response.status_code == 200:
    data = response.json()
    all_walkways = []

    # Process each way (walkway) found
    for element in data["elements"]:
        if "geometry" in element:
            coords = [(point["lat"], point["lon"]) for point in element["geometry"]]
            all_walkways.append(LineString(coords))

    print(f"Fetched {len(all_walkways)} walkways from OpenStreetMap.")
else:
    print("Overpass API request failed.")
    all_walkways = []

###############################################################################
# 3) FILTER WALKWAYS INSIDE CAMPUS POLYGON
###############################################################################
inside_walkways = []
for walkway in all_walkways:
    intersection = CAMPUS_POLYGON.intersection(walkway)
    if not intersection.is_empty:
        if intersection.geom_type == "LineString":
            inside_walkways.append(intersection)
        elif intersection.geom_type == "MultiLineString":
            inside_walkways.extend(intersection.geoms)

print(f"Found {len(inside_walkways)} walkway segment(s) inside the campus.")

###############################################################################
# 4) INTERPOLATE NODES ALONG WALKWAYS
###############################################################################
def haversine(coord1, coord2):
    R = 6371000  # Earth radius in meters
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def interpolate_points(points, spacing=2.0):
    if not points:
        return []
    
    interpolated = [points[0]]
    for i in range(1, len(points)):
        start, end = points[i - 1], points[i]
        dist = haversine(start, end)
        if dist > spacing:
            num_steps = int(dist // spacing)
            for j in range(1, num_steps + 1):
                frac = j * spacing / dist
                interp_lat = start[0] + (end[0] - start[0]) * frac
                interp_lon = start[1] + (end[1] - start[1]) * frac
                interpolated.append((interp_lat, interp_lon))
        else:
            interpolated.append(end)
    return interpolated

# Collect interpolated walkway nodes
walkway_nodes = []
for segment in inside_walkways:
    walkway_nodes.extend(interpolate_points(list(segment.coords), spacing=2.0))

print(f"Generated {len(walkway_nodes)} nodes along the walkway(s) inside campus.")

###############################################################################
# 5) BUILD NETWORK GRAPH OF WALKWAYS
###############################################################################
G = nx.Graph()

for coord in walkway_nodes:
    G.add_node(coord)

# Connect nodes along each walkway
for segment in inside_walkways:
    segment_nodes = interpolate_points(list(segment.coords), spacing=2.0)
    for i in range(len(segment_nodes) - 1):
        c1, c2 = segment_nodes[i], segment_nodes[i + 1]
        G.add_edge(c1, c2, weight=haversine(c1, c2))

print(f"Graph constructed with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")

###############################################################################
# 6) VISUALIZE WALKWAYS WITH FOLIUM
###############################################################################
# Center map at the campus centroid
campus_center = CAMPUS_POLYGON.centroid
m = folium.Map(location=[campus_center.y, campus_center.x], zoom_start=16)

# Add campus boundary
folium.Polygon(
    locations=[(lat, lon) for lat, lon in CAMPUS_POLYGON.exterior.coords],
    color='blue',
    fill=True,
    fill_opacity=0.1,
    weight=2
).add_to(m)

# Add walkways as red polylines
for segment in inside_walkways:
    folium.PolyLine(
        locations=[(lat, lon) for lat, lon in segment.coords],
        color='red',
        weight=3,
        opacity=0.8
    ).add_to(m)

# Add nodes as small green circles
for coord in walkway_nodes:
    folium.CircleMarker(
        location=coord,
        radius=1,
        color='green',
        fill=True,
        fill_color='green',
        fill_opacity=0.7
    ).add_to(m)

# Save the map
m.save("sbu_walkways.html")
print("Map saved as 'sbu_walkways.html'.")
