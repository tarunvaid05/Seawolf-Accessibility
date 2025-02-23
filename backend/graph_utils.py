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
GRID_SPACING = 0.00001800180018 

# For each grid point, connect it to its K nearest neighbors (within MAX_DIST_M meters).
K_NEAREST = 3
MAX_DIST_M = 200  





###############################################################################
# 3) HELPER FUNCTIONS
###############################################################################

def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Calculate the great-circle distance (in meters) between two lat/lng points.
    """
    R = 6371000.0  # Radius of the Earth in meters
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def generate_polygon_grid_points(polygon, spacing=0.0005):
    """
    Generate a grid of (lat, lng) points covering the bounding box of 'polygon'
    and return only those points that lie inside the polygon.
    """
    # Note: If your polygon is defined as (lat, lng), then polygon.bounds returns
    # (min_lat, min_lng, max_lat, max_lng).
    min_lat, min_lng, max_lat, max_lng = polygon.bounds
    lat_vals = np.arange(min_lat, max_lat, spacing)
    lng_vals = np.arange(min_lng, max_lng, spacing)
    points = []
    for lat in lat_vals:
        for lng in lng_vals:
            if polygon.contains(Point(lat, lng)):
                points.append((float(lat), float(lng)))
    return points

def snap_grid_points(points, interpolate=False):
    """
    Snap a list of grid points to the nearest road or walkway using the Google Roads API.
    'points' is a list of (lat, lng) tuples.
    Returns a new list of snapped points (if available; otherwise, retains original).
    """
    try:
        # The Snap to Roads API requires the points to be provided as a path string.
        snapped = gmaps.snap_to_roads(points=points, interpolate=interpolate)
        # Build a mapping from original index to snapped coordinate.
        snapped_dict = {}
        for s in snapped:
            orig_idx = s.get('originalIndex')
            if orig_idx is not None:
                snapped_dict[orig_idx] = (
                    s['location']['latitude'],
                    s['location']['longitude']
                )
        # Reconstruct the list: if a point was snapped, use its new coordinate.
        snapped_points = [snapped_dict.get(i, point) for i, point in enumerate(points)]
        return snapped_points
    except Exception as e:
        print("Snap to Roads API error:", e)
        return points

def get_directions_steps(start, end):
    """
    Use the Google Directions API (walking mode) to fetch step-by-step directions
    between two coordinates.
    Returns a list of steps with:
      - 'polyline': list of (lat, lng) coordinates
      - 'distance_m': distance in meters for the step
      - 'has_stairs': boolean flag (if 'stairs' or 'steps' appear in the instructions)
    """
    try:
        directions_result = gmaps.directions(start, end, mode="walking")
        if not directions_result:
            return []
        
        steps = directions_result[0]['legs'][0]['steps']
        detailed_steps = []
        for s in steps:
            encoded_poly = s['polyline']['points']
            coords = polyline.decode(encoded_poly)
            distance_m = s['distance']['value']
            instructions = s['html_instructions'].lower()
            has_stairs = ("stairs" in instructions or "steps" in instructions)
            detailed_steps.append({
                'polyline': coords,
                'distance_m': distance_m,
                'has_stairs': has_stairs
            })
        return detailed_steps
    except Exception as e:
        print(f"Error fetching directions from {start} to {end}: {e}")
        return []

###############################################################################
# 4) BUILD THE NETWORKX GRAPH
###############################################################################
campus_graph = nx.Graph()

def add_steps_to_graph(steps):
    """
    For each step (with a decoded polyline) returned from the Directions API,
    break it into segments and add them as edges to campus_graph.
    Stores attributes: distance, stairs flag, and a placeholder for elevation_change.
    """
    for step in steps:
        coords = step['polyline']
        has_stairs = step['has_stairs']
        # Break polyline into individual segments
        for i in range(len(coords) - 1):
            lat1, lng1 = coords[i]
            lat2, lng2 = coords[i+1]
            segment_distance = haversine_distance(lat1, lng1, lat2, lng2)
            
            # Ensure nodes exist with placeholders for attributes
            if not campus_graph.has_node((lat1, lng1)):
                campus_graph.add_node((lat1, lng1), elevation=None, accessible_entrance=False)
            if not campus_graph.has_node((lat2, lng2)):
                campus_graph.add_node((lat2, lng2), elevation=None, accessible_entrance=False)
            
            # Add or update the edge
            if campus_graph.has_edge((lat1, lng1), (lat2, lng2)):
                # Update distance if new segment is shorter and merge stairs flag
                existing = campus_graph[(lat1, lng1)][(lat2, lng2)]
                if segment_distance < existing['distance']:
                    existing['distance'] = segment_distance
                existing['stairs'] = existing['stairs'] or has_stairs
            else:
                campus_graph.add_edge((lat1, lng1), (lat2, lng2),
                                      distance=segment_distance,
                                      stairs=has_stairs,
                                      elevation_change=None)

def build_walkable_graph(grid_points, k=3, max_dist_m=200):
    """
    For each grid point, find the k nearest neighbors (within max_dist_m) and
    query Google Directions to obtain walking routes. Then add these segments
    to campus_graph.
    """
    # Build a KDTree for efficient nearest neighbor search.
    tree = KDTree(grid_points)
    for i, point in enumerate(grid_points):
        lat, lng = point
        dists, idxs = tree.query([lat, lng], k=k+1)  # first neighbor is the point itself
        for dist, neighbor_idx in zip(dists[0][1:], idxs[0][1:]):
            neighbor = grid_points[neighbor_idx]
            # Skip if distance exceeds the threshold
            if haversine_distance(lat, lng, neighbor[0], neighbor[1]) > max_dist_m:
                continue
            # Query walking directions from point to neighbor
            steps = get_directions_steps((lat, lng), (neighbor[0], neighbor[1]))
            if steps:
                add_steps_to_graph(steps)

def merge_close_nodes(tolerance=1.0):
    """
    Optionally merge nodes that are within 'tolerance' meters of each other.
    A naive approach (O(n^2)); consider spatial indexing for large graphs.
    """
    merged = True
    while merged:
        merged = False
        nodes = list(campus_graph.nodes())
        for i in range(len(nodes)):
            if merged:
                break
            for j in range(i+1, len(nodes)):
                n1, n2 = nodes[i], nodes[j]
                if not (campus_graph.has_node(n1) and campus_graph.has_node(n2)):
                    continue
                if haversine_distance(n1[0], n1[1], n2[0], n2[1]) < tolerance:
                    # Merge n2 into n1: reassign edges and merge attributes
                    for nbr in list(campus_graph.neighbors(n2)):
                        edge_data = campus_graph.get_edge_data(n2, nbr)
                        if not campus_graph.has_edge(n1, nbr):
                            campus_graph.add_edge(n1, nbr, **edge_data)
                        else:
                            # Merge edge attributes (e.g., take the minimum distance)
                            campus_graph[n1][nbr]['stairs'] |= edge_data.get('stairs', False)
                            campus_graph[n1][nbr]['distance'] = min(campus_graph[n1][nbr]['distance'],
                                                                    edge_data.get('distance'))
                    for key, value in campus_graph.nodes[n2].items():
                        campus_graph.nodes[n1].setdefault(key, value)
                    campus_graph.remove_node(n2)
                    merged = True
                    break

###############################################################################
# 5) ELEVATION DATA INTEGRATION
###############################################################################
def get_elevation(coords):
    """
    Query the Google Elevation API for a list of (lat, lng) coordinates.
    Returns a list of elevation values (in meters).
    """
    results = []
    BATCH_SIZE = 50
    for i in range(0, len(coords), BATCH_SIZE):
        batch = coords[i:i+BATCH_SIZE]
        try:
            elev_result = gmaps.elevation(batch)
            results.extend([e['elevation'] for e in elev_result])
        except Exception as e:
            print(f"Elevation API error: {e}")
            results.extend([0] * len(batch))
    return results

def update_elevations_on_graph():
    """
    Fetch elevation for every node in campus_graph and update each edge with
    the absolute elevation change.
    """
    nodes = list(campus_graph.nodes())
    elevations = get_elevation(nodes)
    for i, node in enumerate(nodes):
        campus_graph.nodes[node]['elevation'] = elevations[i]
    
    # Update each edge with elevation change
    for u, v, data in campus_graph.edges(data=True):
        elev_u = campus_graph.nodes[u].get('elevation', 0)
        elev_v = campus_graph.nodes[v].get('elevation', 0)
        data['elevation_change'] = abs(elev_u - elev_v)


import gmplot

def visualize_graph_on_googlemap(graph, api_key, output_file="campus_graph.html", zoom=16):
    """
    Visualize a NetworkX graph on a Google Map using gmplot.
    Nodes are drawn as red markers and edges as blue lines.

    Parameters:
      graph: NetworkX graph with nodes as (lat, lng) tuples.
      api_key: Google Maps API Key (string)
      output_file: Filename for the output HTML file.
      zoom: Zoom level for the map (higher means more zoomed in).
    """
    if not api_key:
        raise ValueError("Google Maps API key is required for visualization.")

    # Compute center of the map (average of node coordinates)
    lats = [node[0] for node in graph.nodes()]
    lngs = [node[1] for node in graph.nodes()]
    center_lat = sum(lats) / len(lats)
    center_lng = sum(lngs) / len(lngs)

    # Create a gmplot object with the computed center
    gmap = gmplot.GoogleMapPlotter(center_lat, center_lng, zoom)
    gmap.apikey = api_key  # Set the Google Maps API key

    # Plot nodes (red markers)
    gmap.scatter(lats, lngs, color="red", size=40, marker=True)

    # Plot edges (blue lines)
    for u, v in graph.edges():
        lat_line = [u[0], v[0]]
        lng_line = [u[1], v[1]]
        gmap.plot(lat_line, lng_line, color="blue", edge_width=2.5)

    # Generate the HTML file
    gmap.draw(output_file)
    print(f"Graph visualization saved to {output_file}")
