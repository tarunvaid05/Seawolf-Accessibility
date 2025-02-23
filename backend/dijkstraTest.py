import json
import math
import networkx as nx
import polyline  # pip install polyline

# Haversine formula to compute the great-circle distance between two (lat, lon) points in meters.
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Set the desired maximum segment length (e.g., 5-10 meters) between nodes.
MAX_SEGMENT_LENGTH = 2  # meters

# Set the tolerance for connecting nodes in the graph.
TOLERANCE = 10  # meters

# Load the JSON data from file.
with open('/Users/tarun/CS/Projects/HopperHacks25/public/ways_output.json', 'r') as f:
    ways = json.load(f)

# Create a dictionary to hold node data.
# We'll add both the original nodes and intermediate (subdivided) nodes.
nodes = {}

# Process each way.
for w_index, way in enumerate(ways):
    refs = way.get("refs", [])
    if not refs:
        continue
    # Convert the first ref to degrees and add as a node.
    prev_lat = refs[0]["lat"] * 1e-9
    prev_lon = refs[0]["lon"] * 1e-9
    # Save the original node.
    node_id = f"w{w_index}_r0"
    nodes[node_id] = (prev_lat, prev_lon)
    
    # Process subsequent refs and generate intermediate nodes if needed.
    for r_index in range(1, len(refs)):
        curr_lat = refs[r_index]["lat"] * 1e-9
        curr_lon = refs[r_index]["lon"] * 1e-9
        
        # Compute the total distance of the segment.
        seg_distance = haversine(prev_lat, prev_lon, curr_lat, curr_lon)
        # Determine how many subdivisions are needed.
        steps = max(1, math.ceil(seg_distance / MAX_SEGMENT_LENGTH))
        
        # Generate intermediate nodes (excluding the last point, which becomes original).
        for step in range(1, steps):
            t = step / steps
            interp_lat = prev_lat + (curr_lat - prev_lat) * t
            interp_lon = prev_lon + (curr_lon - prev_lon) * t
            interp_id = f"w{w_index}_r{r_index}_interp_{step}"
            nodes[interp_id] = (interp_lat, interp_lon)
        
        # Finally, add the current original node.
        orig_id = f"w{w_index}_r{r_index}"
        nodes[orig_id] = (curr_lat, curr_lon)
        
        # Update previous coordinate for next segment.
        prev_lat, prev_lon = curr_lat, curr_lon

# Create the graph and add each node with its position attribute.
G = nx.Graph()
for node_id, coord in nodes.items():
    G.add_node(node_id, pos=coord)

# Add hard-coded origin and destination nodes.
origin_node = 'origin'
destination_node = 'destination'
origin_coord = (40.91402, -73.13046)      # Example coordinate for "East Side Dining..."
destination_coord = (40.91350, -73.13150)  # Example coordinate for "SAC Plaza..."
G.add_node(origin_node, pos=origin_coord)
G.add_node(destination_node, pos=destination_coord)

# Gather list of all node IDs.
node_ids = list(G.nodes.keys())

# For every pair of nodes, add an edge if the distance is less than the tolerance.
n = len(node_ids)
for i in range(n):
    for j in range(i + 1, n):
        id1 = node_ids[i]
        id2 = node_ids[j]
        (lat1, lon1) = G.nodes[id1]['pos']
        (lat2, lon2) = G.nodes[id2]['pos']
        d = haversine(lat1, lon1, lat2, lon2)
        if d <= TOLERANCE:
            G.add_edge(id1, id2, weight=d)

# Set source and target as the hard-coded origin and destination.
source = origin_node
target = destination_node

print(f"Computing shortest path from {source} to {target} using tolerance = {TOLERANCE} meters.")

try:
    path = nx.dijkstra_path(G, source=source, target=target, weight='weight')
    total_distance = nx.dijkstra_path_length(G, source=source, target=target, weight='weight')
    
    # Print the path node IDs.
    print("Shortest Path (node IDs):", " -> ".join(path))
    
    # Retrieve and print the coordinates for each node in the path.
    route_coords = [G.nodes[node]['pos'] for node in path]
    print("Path Coordinates:")
    for node, coord in zip(path, route_coords):
        print(f"  {node}: {coord}")
    
    print(f"Total Distance: {total_distance:.2f} meters")
    
    # Encode the route coordinates into a polyline string and print it.
    polyline_str = polyline.encode(route_coords)
    print("Encoded Polyline String:")
    print(polyline_str)
    
except nx.NetworkXNoPath:
    print(f"No adjacent path found between {source} and {target} with the current tolerance.")