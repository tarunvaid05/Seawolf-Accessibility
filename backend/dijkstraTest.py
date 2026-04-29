import networkx as nx

# Define graph nodes (latitude, longitude for reference, but unused in weight)
nodes = {
    'A': (40.7128, -74.0060),  # New York
    'B': (34.0522, -118.2437), # Los Angeles
    'C': (41.8781, -87.6298),  # Chicago
    'D': (29.7604, -95.3698),  # Houston
    'E': (33.4484, -112.0740), # Phoenix
    'F': (39.7392, -104.9903)  # Denver
}

# Create a graph
G = nx.Graph()

# Add nodes
for node in nodes:
    G.add_node(node)

# Define adjacent edges (all with weight 1)
edges = [
    ('A', 'C'), ('C', 'F'), ('F', 'E'), ('E', 'B'), ('B', 'D'), ('D', 'C')
]

# Add edges with equal weight of 1
G.add_edges_from(edges, weight=1)

# Compute the shortest path using Dijkstra (with equal weights)
source, target = 'A', 'B'

try:
    path = nx.dijkstra_path(G, source=source, target=target, weight='weight')
    distance = nx.dijkstra_path_length(G, source=source, target=target, weight='weight')

    print("Shortest Path (equal weights):", " -> ".join(path))
    print(f"Total Steps (edges traversed): {distance}")

except nx.NetworkXNoPath:
    print(f"No path found between {source} and {target}.")
