#!/usr/bin/env python3
import json
import heapq
import math

def haversine(lat1, lon1, lat2, lon2):
    """
    Compute the haversine distance (in meters) between two points given in degrees.
    """
    R = 6371000  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def load_nodes():
    """
    Loads nodes.json, which contains a list of all unique nodes.
    Each node is expected to have an "id", "lat", and "lon" (lat/lon are stored as integers, e.g. 40915681500).
    """
    with open("nodes.json", "r") as f:
        nodes_list = json.load(f)
    return nodes_list

def find_nearest_node(lat, lon, nodes_list, valid_ids=None):
    """
    Given a latitude and longitude (in degrees) and a list of nodes (from nodes.json),
    return the node (a dict) that is closest to the given coordinates.
    If valid_ids is provided (a set), only nodes whose id is in valid_ids are considered.
    """
    best_node = None
    best_distance = float('inf')
    for node in nodes_list:
        if valid_ids is not None and node["id"] not in valid_ids:
            continue
        node_lat = node["lat"] / 1e9
        node_lon = node["lon"] / 1e9
        d = haversine(lat, lon, node_lat, node_lon)
        if d < best_distance:
            best_distance = d
            best_node = node
    return best_node

def load_graph():
    """
    Loads formatted_data.json and builds an undirected graph.
    Each junction vertex (identified by its "id") is a node.
    Each edge from a segment becomes a bidirectional edge with a weight (distance)
    and carries its polyline (the list of vertices between the junctions).
    Note: For the reverse direction the polyline is reversed.
    """
    with open("formatted_data.json", "r") as f:
        segments = json.load(f)

    graph = {}  # node_id -> list of (neighbor_id, distance, polyline)
    nodes = {}  # node_id -> (lat, lon) in degrees

    for seg in segments:
        for edge in seg["edges"]:
            start = edge["start"]
            end = edge["end"]
            start_id = start["id"]
            end_id = end["id"]
            d = edge["distance"]

            # Record node coordinates (convert to proper degrees)
            if start_id not in nodes:
                nodes[start_id] = (start["lat"] / 1e9, start["lon"] / 1e9)
            if end_id not in nodes:
                nodes[end_id] = (end["lat"] / 1e9, end["lon"] / 1e9)

            # Add edge in both directions (undirected graph)
            graph.setdefault(start_id, []).append((end_id, d, edge["polyline"]))
            # For the reverse direction, reverse the polyline so that the start is at the beginning.
            graph.setdefault(end_id, []).append((start_id, d, list(reversed(edge["polyline"]))))
    return graph, nodes

def dijkstra(graph, start, goal):
    """
    Standard Dijkstra algorithm.
    Returns a tuple: (total_distance, list_of_node_ids, list_of_polyline_segments_used).
    """
    dist = {node: float('inf') for node in graph}
    previous = {node: None for node in graph}
    edge_used = {node: None for node in graph}  # stores the polyline for the edge that led to the node
    dist[start] = 0

    queue = [(0, start)]
    while queue:
        current_dist, current = heapq.heappop(queue)
        if current == goal:
            break
        if current_dist > dist[current]:
            continue
        for neighbor, weight, poly in graph[current]:
            alt = current_dist + weight
            if alt < dist[neighbor]:
                dist[neighbor] = alt
                previous[neighbor] = current
                edge_used[neighbor] = poly
                heapq.heappush(queue, (alt, neighbor))

    if dist[goal] == float('inf'):
        return None, None, None

    path = []
    edges_in_path = []
    node = goal
    while node is not None:
        path.append(node)
        node = previous[node]
    path.reverse()
    for i in range(1, len(path)):
        edges_in_path.append(edge_used[path[i]])
    return dist[goal], path, edges_in_path

def combine_polylines(polylines):
    """
    Combines a list of polyline segments (each a list of vertices) into one continuous polyline,
    removing duplicate junction vertices.
    """
    if not polylines:
        return []
    combined = polylines[0][:]
    for poly in polylines[1:]:
        # Remove the first vertex to avoid duplication
        combined.extend(poly[1:])
    return combined

def encode_polyline(points):
    """
    Encodes a polyline using the Google Encoded Polyline Algorithm.
    `points` is a list of dicts with "lat" and "lon" (in degrees).
    """
    def encode_coordinate(coordinate):
        coordinate = int(round(coordinate * 1e5))
        coordinate = coordinate << 1
        if coordinate < 0:
            coordinate = ~coordinate
        encoded = ""
        while coordinate >= 0x20:
            encoded += chr((0x20 | (coordinate & 0x1f)) + 63)
            coordinate >>= 5
        encoded += chr(coordinate + 63)
        return encoded

    result = ""
    prev_lat = 0
    prev_lon = 0
    for point in points:
        lat = point["lat"]
        lon = point["lon"]
        d_lat = lat - prev_lat
        d_lon = lon - prev_lon
        result += encode_coordinate(d_lat)
        result += encode_coordinate(d_lon)
        prev_lat = lat
        prev_lon = lon
    return result

def main():
    # Load the graph from formatted_data.json
    graph, graph_nodes = load_graph()
    if not graph:
        print("Graph is empty.")
        return

    # Load the canonical nodes list from nodes.json
    nodes_list = load_nodes()
    # Only consider nodes that appear in our graph
    valid_ids = set(graph.keys())

    # Specify the origin and destination coordinates in degrees.
    # (Format: latitude, longitude)
    # You can change these values as needed.
    origin_lat, origin_lon = 40.914521, -73.131887
    destination_lat, destination_lon = 40.914174, -73.124373

    # Find the nearest nodes to the provided coordinates.
    origin_node = find_nearest_node(origin_lat, origin_lon, nodes_list, valid_ids)
    destination_node = find_nearest_node(destination_lat, destination_lon, nodes_list, valid_ids)

    if origin_node is None or destination_node is None:
        print("Could not find a suitable origin or destination node.")
        return

    start = origin_node["id"]
    goal = destination_node["id"]

    print(f"Using origin node {start} (closest to {origin_lat}, {origin_lon})")
    print(f"Using destination node {goal} (closest to {destination_lat}, {destination_lon})")

    total_distance, path, edges_in_path = dijkstra(graph, start, goal)
    if path is None:
        print("No path found.")
        return

    print(f"Total distance: {total_distance:.2f} meters")

    full_polyline = combine_polylines(edges_in_path)

    print("Polyline for the best path (lat, lon):")
    # Convert the combined polyline to a list of points with lat/lon in degrees.
    points = [{"lat": point["lat"] / 1e9, "lon": point["lon"] / 1e9} for point in full_polyline]
    encoded = encode_polyline(points)

    # Print encoded polyline to the console.
    print(encoded)

    # Write the encoded polyline to best_path_polyline.json.
    with open("best_path_polyline.json", "w") as f:
        json.dump({"encoded_polyline": encoded}, f)

if __name__ == "__main__":
    main()
