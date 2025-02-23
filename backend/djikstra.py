#!/usr/bin/env python3
import json
import heapq
import math

def load_graph():
    """
    Loads formatted_data.json and builds an undirected graph.
    Each junction vertex (identified by its id) is a node.
    Each edge from a segment becomes a bidirectional edge with a weight (distance)
    and carries its polyline (the list of vertices between the junctions).
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
    Returns a tuple: (total distance, list of node ids forming the path, list of polyline edges used).
    """
    dist = {node: float('inf') for node in graph}
    previous = {node: None for node in graph}
    edge_used = {node: None for node in graph}  # store the polyline for the edge that led to the node
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

def main():
    graph, nodes = load_graph()
    if not graph:
        print("Graph is empty.")
        return

    all_nodes = list(graph.keys())
    start = all_nodes[0]
    goal = all_nodes[-1]
    print(f"Running Dijkstra from node {start} to node {goal}")

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

    # 1) Print to console (optional)
    print(encoded)

    # 2) ALSO write to a small JSON file:
    with open("best_path_polyline.json", "w") as f:
        json.dump({"encoded_polyline": encoded}, f)

if __name__ == "__main__":
    main()
