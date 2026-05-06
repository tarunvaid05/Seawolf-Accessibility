import os
import json
import math
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
# Import methods from djikstra.py
from djikstra import (
    choose_snap_component,
    clone_graph,
    load_graph,
    snap_point,
    dijkstra,
    combine_polylines,
    encode_polyline,
)

app = FastAPI()

WANG_CENTER_BOUNDS = {
    "north": 40.91625,
    "south": 40.91565,
    "west": -73.12005,
    "east": -73.11925,
}
WANG_CENTER_ENTRANCE = {"lat": 40.915892, "lon": -73.119770}


def is_in_bounds(coords, bounds):
    lat, lon = coords
    return bounds["south"] <= lat <= bounds["north"] and bounds["west"] <= lon <= bounds["east"]


def haversine_distance(start, end):
    radius = 6371000
    start_lat, start_lon = start
    end_lat, end_lon = end
    phi1 = math.radians(start_lat)
    phi2 = math.radians(end_lat)
    dphi = math.radians(end_lat - start_lat)
    dlambda = math.radians(end_lon - start_lon)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def append_known_destination_extensions(points, start_coords, end_coords):
    total_extra_distance = 0.0

    if is_in_bounds(start_coords, WANG_CENTER_BOUNDS):
        start_entrance = WANG_CENTER_ENTRANCE.copy()
        first_point = points[0]
        total_extra_distance += haversine_distance(
            (start_entrance["lat"], start_entrance["lon"]),
            (first_point["lat"], first_point["lon"]),
        )
        points.insert(0, start_entrance)

    if is_in_bounds(end_coords, WANG_CENTER_BOUNDS):
        end_entrance = WANG_CENTER_ENTRANCE.copy()
        last_point = points[-1]
        total_extra_distance += haversine_distance(
            (last_point["lat"], last_point["lon"]),
            (end_entrance["lat"], end_entrance["lon"]),
        )
        points.append(end_entrance)

    return total_extra_distance

# Allow CORS so your frontend can access the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/directions")
def get_directions(start: str = Query(..., description="Start coordinate as 'lat,lng'"),
                   end: str = Query(..., description="End coordinate as 'lat,lng'")):
    """
    Calculates the best walking route between start and end coordinates using the custom graph and Dijkstra's algorithm.
    The result is transformed to mimic a Google Directions response so that your frontend's DirectionsRenderer can work.
    
    NOTE: Ensure that any helper function in route_cost (such as convert_coord) extracts only the (lat, lon) 2-tuple,
    so that extra keys (like "id") do not cause unpacking errors.
    """
    try:
        start_coords = tuple(map(float, start.split(',')))
        end_coords = tuple(map(float, end.split(',')))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Coordinates must be provided as 'lat,lng'") from e

    # Load the routing graph and nodes using the cached load_graph.
    try:
        base_graph, base_nodes = load_graph()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load routing data") from e

    component_id, component_by_node, _ = choose_snap_component(start_coords, end_coords, base_graph)
    if component_id is None:
        raise HTTPException(status_code=404, detail="Could not find a connected routing component for the provided coordinates.")

    graph, graph_nodes = clone_graph(base_graph, base_nodes)
    allowed_nodes = {
        node
        for node, node_component_id in component_by_node.items()
        if node_component_id == component_id
    }

    # Snap both points within the same connected component so Dijkstra can route between them.
    origin_snapped = snap_point(start_coords, graph, graph_nodes, allowed_nodes=allowed_nodes)
    if origin_snapped is not None:
        allowed_nodes.add(origin_snapped)
    destination_snapped = snap_point(end_coords, graph, graph_nodes, allowed_nodes=allowed_nodes)
    if origin_snapped is None or destination_snapped is None:
        raise HTTPException(status_code=404, detail="Could not snap provided coordinates onto the routing graph.")
        
    # Run Dijkstra's algorithm between the snapped nodes.
    total_distance, path, edges_in_path = dijkstra(graph, origin_snapped, destination_snapped)
    if path is None or edges_in_path is None:
        raise HTTPException(status_code=404, detail="No path found.")

    # Combine the polyline segments and encode them using the Google Polyline Algorithm.
    full_polyline = combine_polylines(edges_in_path)
    if not full_polyline or len(full_polyline) == 0:
        raise HTTPException(status_code=404, detail="No polyline found for the route.")
    
    # Convert each vertex dictionary to degrees.
    points = [{"lat": pt["lat"] / 1e9, "lon": pt["lon"] / 1e9} for pt in full_polyline]
    total_distance += append_known_destination_extensions(points, start_coords, end_coords)
    encoded = encode_polyline(points)
    
    # Build a mock Directions response that the frontend can work with.
    response = {
        "routes": [
            {
                "overview_polyline": {"points": encoded},
                "legs": [
                    {
                        "distance": {"value": total_distance},
                        "start_address": f"{start_coords[0]},{start_coords[1]}",
                        "end_address": f"{end_coords[0]},{end_coords[1]}"
                    }
                ]
            }
        ],
        "request": {
            "travelMode": "WALKING",
            "origin": f"{start_coords[0]},{start_coords[1]}",
            "destination": f"{end_coords[0]},{end_coords[1]}"
        }
    }
    return JSONResponse(content=response)
