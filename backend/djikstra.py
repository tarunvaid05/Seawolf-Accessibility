import json
import networkx as nx
from geopy.distance import geodesic
import polyline
from typing import List


def build_graph_from_walkable_json(json_path: str) -> nx.Graph:
    """
    Build a NetworkX graph from the walkable_paths.json file.
    - Each 'way' in the JSON is an object with:
        {
          "way_id": <some_way_id>,
          "refs": [
            {"id": <int>, "lat": <int>, "lon": <int>},
            ...
          ]
        }
    - We create a node for each 'ref' (using 'id' as the node ID).
    - Within each 'way', consecutive refs become edges, weighted by geodesic distance.
    """
    G = nx.Graph()

    with open(json_path, "r") as f:
        ways = json.load(f)

    for way in ways:
        refs = way.get("refs", [])
        if len(refs) < 2:
            continue  # Not enough refs to form an edge

        # Connect consecutive refs within this way
        for i in range(len(refs) - 1):
            ref_a = refs[i]
            ref_b = refs[i + 1]

            node_a_id = ref_a["id"]
            node_b_id = ref_b["id"]

            # Convert to standard lat/lon (adjust the divider if needed, e.g., 1e6 vs 1e9)
            lat_a = ref_a["lat"] / 1e9
            lon_a = ref_a["lon"] / 1e9
            lat_b = ref_b["lat"] / 1e9
            lon_b = ref_b["lon"] / 1e9

            if node_a_id not in G:
                G.add_node(node_a_id, lat=lat_a, lon=lon_a)
            if node_b_id not in G:
                G.add_node(node_b_id, lat=lat_b, lon=lon_b)

            dist_m = geodesic((lat_a, lon_a), (lat_b, lon_b)).meters
            G.add_edge(node_a_id, node_b_id, weight=dist_m)

    return G


def k_shortest_paths_as_polylines(
    G: nx.Graph,
    start_id: int,
    end_id: int,
    k: int = 3
) -> List[str]:
    """
    Find the top-k shortest paths (by distance) from 'start_id' to 'end_id'.
    Return each path as an encoded polyline string.
    """
    if start_id not in G or end_id not in G:
        return []

    paths_gen = nx.shortest_simple_paths(G, source=start_id, target=end_id, weight="weight")

    polylines = []
    count = 0

    for path in paths_gen:
        coords = []
        for node_id in path:
            lat = G.nodes[node_id]["lat"]
            lon = G.nodes[node_id]["lon"]
            coords.append((lat, lon))

        encoded = polyline.encode(coords)
        polylines.append(encoded)

        count += 1
        if count >= k:
            break

    return polylines


def main():
    json_path = "ways_output.json"  # Adjust if needed
    G = build_graph_from_walkable_json(json_path)

    # Example node IDs from your JSON; update these values to valid IDs
    start_id = 6164404478
    end_id = 7865937480

    top_3_polylines = k_shortest_paths_as_polylines(G, start_id, end_id, k=3)

    # Print to console for a quick check
    print(f"Found {len(top_3_polylines)} shortest path(s) from {start_id} to {end_id}:")
    for i, p in enumerate(top_3_polylines, start=1):
        print(f"Path {i}: {p}")

    # Write results to a text file in the same folder
    output_file = "dijkstra_results.txt"
    with open(output_file, "w") as f:
        f.write(f"Shortest paths between {start_id} and {end_id}\n")
        f.write(f"Total paths found: {len(top_3_polylines)}\n\n")
        for i, p in enumerate(top_3_polylines, start=1):
            f.write(f"Path {i}: {p}\n")

    print(f"\nResults saved to '{output_file}'.")


if __name__ == "__main__":
    main()
