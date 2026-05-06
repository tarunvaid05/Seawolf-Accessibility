#!/usr/bin/env python3
import copy
import heapq
import json
import math
import route_cost

# Global cache variables for the graph and nodes.
GRAPH_CACHE = None
NODES_CACHE = None

CAMPUS_LAT_BOUNDS = (40.0, 41.0)
CAMPUS_LON_BOUNDS = (-74.0, -72.0)
COORD_SCALE = 1e9
REPAIRED_COORD_EDGE_PENALTY = 25.0

def is_supported_coord(lat, lon):
    return (
        CAMPUS_LAT_BOUNDS[0] <= lat <= CAMPUS_LAT_BOUNDS[1]
        and CAMPUS_LON_BOUNDS[0] <= lon <= CAMPUS_LON_BOUNDS[1]
    )

def normalize_scaled_point(point):
    normalized = point.copy()
    if needs_scale_repair(normalized):
        normalized["lat"] *= 100
        normalized["lon"] *= 100

    return normalized

def needs_scale_repair(point):
    lat = point["lat"] / COORD_SCALE
    lon = point["lon"] / COORD_SCALE
    if is_supported_coord(lat, lon):
        return False

    # Some generated ways are accidentally stored at 1e7 scale instead of 1e9.
    repaired_lat = point["lat"] * 100
    repaired_lon = point["lon"] * 100
    return is_supported_coord(repaired_lat / COORD_SCALE, repaired_lon / COORD_SCALE)

def iter_segment_points(segments):
    for seg in segments:
        for edge in seg["edges"]:
            yield edge["start"]
            yield edge["end"]
            yield from edge["polyline"]

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

def clone_graph(graph, nodes):
    """
    Returns a mutable per-request copy of the cached routing graph.
    snap_point mutates the graph by splitting edges, so requests must not share
    the cached graph object returned by load_graph.
    """
    return copy.deepcopy(graph), nodes.copy()

def get_connected_components(graph):
    """
    Computes connected components for the undirected graph representation.
    Returns (component_by_node, component_sizes).
    """
    component_by_node = {}
    component_sizes = {}
    component_id = 0

    for node in graph:
        if node in component_by_node:
            continue

        stack = [node]
        component_by_node[node] = component_id
        size = 0

        while stack:
            current = stack.pop()
            size += 1
            for neighbor, _, _ in graph.get(current, []):
                if neighbor not in component_by_node:
                    component_by_node[neighbor] = component_id
                    stack.append(neighbor)

        component_sizes[component_id] = size
        component_id += 1

    return component_by_node, component_sizes

def nearest_edges_by_component(P, graph, component_by_node):
    """
    Finds the best stair-aware edge projection for P within each connected component.
    """
    nearest = {}

    for u in graph:
        for v, _, poly in graph[u]:
            if u >= v:
                continue

            component_id = component_by_node.get(u)
            if component_id is None or component_by_node.get(v) != component_id:
                continue

            for i in range(len(poly) - 1):
                A = poly[i]
                B = poly[i+1]
                A_lat = A["lat"] / 1e9
                A_lon = A["lon"] / 1e9
                B_lat = B["lat"] / 1e9
                B_lon = B["lon"] / 1e9
                proj, _ = project_point_onto_segment(P, (A_lat, A_lon), (B_lat, B_lon))
                d = haversine(P[0], P[1], proj[0], proj[1])
                score = route_cost.compute_snap_cost(d, poly)

                if component_id not in nearest or score < nearest[component_id]:
                    nearest[component_id] = score

    return nearest

def choose_snap_component(start, end, graph):
    """
    Chooses a connected component that can route both endpoints.
    The selected component minimizes stair-aware snap score for the two points.
    """
    component_by_node, component_sizes = get_connected_components(graph)
    start_scores = nearest_edges_by_component(start, graph, component_by_node)
    end_scores = nearest_edges_by_component(end, graph, component_by_node)
    common_components = set(start_scores) & set(end_scores)

    if not common_components:
        return None, component_by_node, component_sizes

    component_id = min(
        common_components,
        key=lambda comp: (
            start_scores[comp] + end_scores[comp],
            max(start_scores[comp], end_scores[comp]),
            -component_sizes[comp],
        ),
    )

    return component_id, component_by_node, component_sizes

def load_graph():
    """
    Loads formatted_data.json and builds an undirected graph.
    Each junction vertex (identified by its "id") is a node.
    Each edge becomes bidirectional with a weight (distance) and its polyline.
    For the reverse direction, the polyline is stored in reverse.
    Uses caching to avoid reloading the graph on subsequent calls.
    """
    global GRAPH_CACHE, NODES_CACHE
    if GRAPH_CACHE is not None and NODES_CACHE is not None:
        return GRAPH_CACHE, NODES_CACHE
    with open("formatted_data.json", "r") as f:
        segments = json.load(f)
    max_node_id = max((point["id"] for point in iter_segment_points(segments)), default=0)
    next_synthetic_node_id = max_node_id + 1
    primary_coord_by_node_id = {}
    synthetic_id_by_coord = {}

    def normalize_graph_point(point):
        nonlocal next_synthetic_node_id

        normalized = normalize_scaled_point(point)
        original_id = normalized["id"]
        coord = (normalized["lat"], normalized["lon"])
        primary_coord = primary_coord_by_node_id.get(original_id)

        if primary_coord is None:
            primary_coord_by_node_id[original_id] = coord
            return normalized

        if primary_coord == coord:
            return normalized

        synthetic_key = (original_id, coord)
        synthetic_id = synthetic_id_by_coord.get(synthetic_key)
        if synthetic_id is None:
            synthetic_id = next_synthetic_node_id
            synthetic_id_by_coord[synthetic_key] = synthetic_id
            next_synthetic_node_id += 1

        normalized["id"] = synthetic_id
        return normalized

    graph = {}   # node_id -> list of (neighbor_id, distance, polyline)
    nodes = {}   # node_id -> (lat, lon) in degrees
    for seg in segments:
        for edge in seg["edges"]:
            raw_points = [edge["start"], edge["end"], *edge["polyline"]]
            has_repaired_coord = any(needs_scale_repair(point) for point in raw_points)
            start = normalize_graph_point(edge["start"])
            end = normalize_graph_point(edge["end"])
            polyline = [normalize_graph_point(point) for point in edge["polyline"]]
            start_id = start["id"]
            end_id = end["id"]
            polyline[0] = start
            polyline[-1] = end
            d = compute_polyline_distance(polyline)
            if has_repaired_coord:
                d += REPAIRED_COORD_EDGE_PENALTY
            for point in polyline:
                point_id = point["id"]
                if point_id not in nodes:
                    nodes[point_id] = (point["lat"] / 1e9, point["lon"] / 1e9)
            graph.setdefault(start_id, []).append((end_id, d, polyline))
            graph.setdefault(end_id, []).append((start_id, d, list(reversed(polyline))))
    GRAPH_CACHE = graph
    NODES_CACHE = nodes
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
    total_distance = sum(compute_polyline_distance(edge) for edge in edges_in_path)
    return total_distance, path, edges_in_path

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

def snap_point(P, graph, nodes, allowed_nodes=None):
    """
    Snaps point P (tuple (lat, lon) in degrees) onto the best point on an edge in the graph.
    The function iterates over each unique edge, finds the projection onto each segment,
    and selects the one with the best stair-aware score.
    It then splits that edge by inserting a new node at the projected point,
    updating the graph (both directions) accordingly.
    Returns the new node's id.
    """
    best_score = float('inf')
    best_edge_info = None  # Will hold (u, v, poly, segment_index, t)
    # Iterate over unique edges (consider only u < v to avoid duplicates).
    for u in graph:
        if allowed_nodes is not None and u not in allowed_nodes:
            continue
        for (v, weight, poly) in graph[u]:
            if allowed_nodes is not None and v not in allowed_nodes:
                continue
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
                    score = route_cost.compute_snap_cost(d, poly)
                    if score < best_score:
                        best_score = score
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
    origin = (40.914320, -73.121101)
    destination = (40.915454, -73.119767)
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
