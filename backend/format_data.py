#!/usr/bin/env python3
import json
import math

def haversine(lat1, lon1, lat2, lon2):
    """
    Compute the haversine distance (in meters) between two points.
    """
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def main():
    # Load the original ways_output.json
    with open("ways_output.json", "r") as f:
        ways = json.load(f)

    # Count how many times each vertex id appears across all segments.
    ref_counts = {}
    for way in ways:
        for ref in way["refs"]:
            ref_id = ref["id"]
            ref_counts[ref_id] = ref_counts.get(ref_id, 0) + 1

    formatted_segments = []
    for way in ways:
        # Identify junction indices (where the vertex is shared with another segment)
        junction_indices = [i for i, ref in enumerate(way["refs"]) if ref_counts.get(ref["id"], 0) > 1]
        # Discard segments that do not have at least two junctions (i.e. no adjacent segment)
        if len(junction_indices) < 2:
            continue

        edges = []
        total_distance = 0.0
        # For each consecutive pair of junction indices, extract an edge.
        for i in range(len(junction_indices) - 1):
            start_idx = junction_indices[i]
            end_idx = junction_indices[i + 1]
            # Safety check: if indices are equal or out-of-order, skip.
            if end_idx <= start_idx:
                continue
            sub_polyline = way["refs"][start_idx:end_idx + 1]
            edge_distance = 0.0
            # Sum the distances between consecutive vertices along the sub-polyline.
            for j in range(len(sub_polyline) - 1):
                p1 = sub_polyline[j]
                p2 = sub_polyline[j + 1]
                # Divide by 1e9 to convert the stored integer lat/lon to proper degrees.
                d = haversine(p1["lat"] / 1e9, p1["lon"] / 1e9, p2["lat"] / 1e9, p2["lon"] / 1e9)
                edge_distance += d
            total_distance += edge_distance
            edges.append({
                "start": sub_polyline[0],
                "end": sub_polyline[-1],
                "polyline": sub_polyline,
                "distance": edge_distance
            })

        formatted_segments.append({
            "way_id": way["way_id"],
            "total_distance": total_distance,
            "edges": edges
        })

    # Write the new, formatted data to formatted_data.json
    with open("formatted_data.json", "w") as f:
        json.dump(formatted_segments, f, indent=2)
    print("Formatted data written to formatted_data.json")

if __name__ == "__main__":
    main()