#!/usr/bin/env python3
import json
import heapq
import math
import route_cost

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

def project_point_onto_segment(P, A, B):
    """
    Projects point P onto segment AB.
    P, A, B are tuples (lat, lon) in degrees.
    Uses an equirectangular approximation (with scaling by cos(P.lat)).
    Returns (projected_point, t) where t is the parameter (clamped to [0,1]).
    """
    lat_rad = math.radians(P[0])
    cos_lat = math.cos(lat_rad)
    def to_xy(point):
        lat, lon = point
        return (lon * cos_lat, lat)
    Pxy = to_xy(P)
    Axy = to_xy(A)
    Bxy = to_xy(B)
    Ax, Ay = Axy
    Bx, By = Bxy
    Px, Py = Pxy
    dx = Bx - Ax
    dy = By - Ay
    if dx == 0 and dy == 0:
        return A, 0
    t = ((Px - Ax) * dx + (Py - Ay) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    Qx = Ax + t * dx
    Qy = Ay + t * dy
    Qlon = Qx / cos_lat
    Qlat = Qy
    return (Qlat, Qlon), t

def compute_polyline_distance(polyline):
    """
    Given a polyline (list of vertices with "lat" and "lon" as integers),
    compute the total distance in meters.
    """
    total = 0.0
    for i in range(len(polyline) - 1):
        A = polyline[i]
        B = polyline[i+1]
        A_lat = A["lat"] / 1e9
        A_lon = A["lon"] / 1e9
        B_lat = B["lat"] / 1e9
        B_lon = B["lon"] / 1e9
        total += haversine(A_lat, A_lon, B_lat, B_lon)
    return total

def remove_edge_from_graph(graph, u, v, poly):
    """
    Removes from graph[u] the edge going to v that has polyline equal to poly.
    """
    if u in graph:
        new_edges = []
        for edge in graph[u]:
            neighbor, weight, p = edge
            if neighbor == v and p == poly:
                continue
            new_edges.append(edge)
        graph[u] = new_edges

def add_edge_to_graph(graph, u, v, poly, distance):
    """
    Adds an edge from u to v with the given polyline and weight.
    """
    graph.setdefault(u, []).append((v, distance, poly))

def load_graph():
    """
    Loads formatted_data.json and builds an undirected graph.
    Each junction vertex (identified by its "id") is a node.
    Each edge becomes bidirectional with a weight (distance) and its polyline.
    For the reverse direction, the polyline is stored in reverse.
    """
    with open("formatted_data.json", "r") as f:
        segments = json.load(f)
    graph = {}   # node_id -> list of (neighbor_id, distance, polyline)
    nodes = {}   # node_id -> (lat, lon) in degrees
    for seg in segments:
        for edge in seg["edges"]:
            start = edge["start"]
            end = edge["end"]
            start_id = start["id"]
            end_id = end["id"]
            d = edge["distance"]
            if start_id not in nodes:
                nodes[start_id] = (start["lat"] / 1e9, start["lon"] / 1e9)
            if end_id not in nodes:
                nodes[end_id] = (end["lat"] / 1e9, end["lon"] / 1e9)
            graph.setdefault(start_id, []).append((end_id, d, edge["polyline"]))
            graph.setdefault(end_id, []).append((start_id, d, list(reversed(edge["polyline"]))))
    return graph, nodes

def dijkstra(graph, start, goal):
    """
    Standard Dijkstra algorithm.
    Returns a tuple: (total_distance, list_of_node_ids, list_of_polyline_segments used).
    """
    dist = {node: float('inf') for node in graph}
    previous = {node: None for node in graph}
    edge_used = {node: None for node in graph}
    dist[start] = 0
    queue = [(0, start)]
    while queue:
        current_dist, current = heapq.heappop(queue)
        if current == goal:
            break
        if current_dist > dist[current]:
            continue
        for neighbor, weight, poly in graph[current]:
            alt = current_dist + weight + route_cost.compute_edge_cost(poly)
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
        combined.extend(poly[1:])
    return combined

def encode_polyline(points):
    """
    Encodes a polyline using the Google Encoded Polyline Algorithm.
    Points is a list of dicts with "lat" and "lon" (in degrees).
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

def load_nodes():
    """
    Loads nodes.json, which contains a list of all unique nodes.
    """
    with open("nodes.json", "r") as f:
        nodes_list = json.load(f)
    return nodes_list

def snap_point(P, graph, nodes):
    """
    Snaps point P (tuple (lat, lon) in degrees) onto the closest point on any edge in the graph.
    The function iterates over each unique edge, finds the projection onto each segment,
    and selects the one with minimum haversine distance.
    It then splits that edge by inserting a new node at the projected point,
    updating the graph (both directions) accordingly.
    Returns the new node's id.
    """
    best_distance = float('inf')
    best_edge_info = None  # Will hold (u, v, poly, segment_index, t)
    # Iterate over unique edges (consider only u < v to avoid duplicates).
    for u in graph:
        for (v, weight, poly) in graph[u]:
            if u < v:
                for i in range(len(poly) - 1):
                    A = poly[i]
                    B = poly[i+1]
                    A_lat = A["lat"] / 1e9
                    A_lon = A["lon"] / 1e9
                    B_lat = B["lat"] / 1e9
                    B_lon = B["lon"] / 1e9
                    proj, t = project_point_onto_segment(P, (A_lat, A_lon), (B_lat, B_lon))
                    d = haversine(P[0], P[1], proj[0], proj[1])
                    if d < best_distance:
                        best_distance = d
                        best_edge_info = (u, v, poly, i, t)
    if best_edge_info is None:
        return None
    u, v, poly, i, t = best_edge_info
    # Compute snapped point on the segment between poly[i] and poly[i+1].
    A = poly[i]
    B = poly[i+1]
    A_lat = A["lat"] / 1e9
    A_lon = A["lon"] / 1e9
    B_lat = B["lat"] / 1e9
    B_lon = B["lon"] / 1e9
    snapped_lat = A_lat + t * (B_lat - A_lat)
    snapped_lon = A_lon + t * (B_lon - A_lon)
    snapped_lat_int = round(snapped_lat * 1e9)
    snapped_lon_int = round(snapped_lon * 1e9)
    new_id = max(nodes.keys()) + 1 if nodes else 1
    new_node = {"id": new_id, "lat": snapped_lat_int, "lon": snapped_lon_int}
    # Add new node to our nodes dictionary.
    nodes[new_id] = (snapped_lat, snapped_lon)
    # Split the original polyline into two segments.
    new_vertex = {"id": new_id, "lat": snapped_lat_int, "lon": snapped_lon_int}
    new_polyline1 = poly[:i+1] + [new_vertex]
    new_polyline2 = [new_vertex] + poly[i+1:]
    d1 = compute_polyline_distance(new_polyline1)
    d2 = compute_polyline_distance(new_polyline2)
    # Remove the original edge from both directions.
    remove_edge_from_graph(graph, u, v, poly)
    remove_edge_from_graph(graph, v, u, list(reversed(poly)))
    # Add the two new edges (and their reverse counterparts).
    add_edge_to_graph(graph, u, new_id, new_polyline1, d1)
    add_edge_to_graph(graph, new_id, u, list(reversed(new_polyline1)), d1)
    add_edge_to_graph(graph, new_id, v, new_polyline2, d2)
    add_edge_to_graph(graph, v, new_id, list(reversed(new_polyline2)), d2)
    return new_id

def main():
    # Load the graph (from formatted_data.json) and nodes (from formatted_data.json)
    graph, graph_nodes = load_graph()
    if not graph:
        print("Graph is empty.")
        return
    # Load the full list of nodes from nodes.json (if needed for other purposes)
    nodes_list = load_nodes()
    # Specify origin and destination coordinates in degrees.
    # (Format: latitude, longitude)
    origin = (40.9146917, -73.1225788)
    destination = (40.9172855, -73.1210774)
    # Snap the origin and destination onto the graph.
    origin_node = snap_point(origin, graph, graph_nodes)
    destination_node = snap_point(destination, graph, graph_nodes)
    if origin_node is None or destination_node is None:
        print("Could not snap origin or destination to the graph.")
        return
    print(f"Using snapped origin node: {origin_node}")
    print(f"Using snapped destination node: {destination_node}")
    # Run Dijkstra's algorithm between the snapped nodes.
    total_distance, path, edges_in_path = dijkstra(graph, origin_node, destination_node)
    if path is None:
        print("No path found.")
        return
    print(f"Total distance: {total_distance:.2f} meters")
    full_polyline = combine_polylines(edges_in_path)
    print("Polyline for the best path (lat, lon):")
    # Convert each vertex to degrees.
    points = [{"lat": point["lat"] / 1e9, "lon": point["lon"] / 1e9} for point in full_polyline]
    encoded = encode_polyline(points)
    print(encoded)
    # Write the encoded polyline to best_path_polyline.json.
    with open("best_path_polyline.json", "w") as f:
        json.dump({"encoded_polyline": encoded}, f)

if __name__ == "__main__":
    main()
