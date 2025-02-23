import os
import json
import math
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

# Import methods from djikstra.py (which now uses absolute paths for its JSON files)
# and from route_cost.py (which has the updated staircase threshold).
from djikstra import load_graph, snap_point, dijkstra, combine_polylines, encode_polyline

app = FastAPI()

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
    Calculates the best walking route between start and end coordinates using your custom graph 
    and Dijkstra’s algorithm (which now properly penalizes routes that pass over stairs).
    """
    try:
        start_coords = tuple(map(float, start.split(',')))
        end_coords = tuple(map(float, end.split(',')))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Coordinates must be provided as 'lat,lng'") from e

    try:
        graph, graph_nodes = load_graph()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load routing data") from e

    # Snap the provided start and end onto the routing graph.
    origin_snapped = snap_point(start_coords, graph, graph_nodes)
    destination_snapped = snap_point(end_coords, graph, graph_nodes)
    if origin_snapped is None or destination_snapped is None:
        raise HTTPException(status_code=404, detail="Could not snap provided coordinates onto the routing graph.")

    # Run Dijkstra’s algorithm between the snapped nodes.
    total_distance, path, edges_in_path = dijkstra(graph, origin_snapped, destination_snapped)
    if path is None or edges_in_path is None:
        raise HTTPException(status_code=404, detail="No path found.")

    # Combine the polyline segments and encode the resulting polyline.
    full_polyline = combine_polylines(edges_in_path)
    if not full_polyline or len(full_polyline) == 0:
        raise HTTPException(status_code=404, detail="No polyline found for the route.")

    # Convert each vertex from the internal (scaled) representation to degrees.
    points = [{"lat": pt["lat"] / 1e9, "lon": pt["lon"] / 1e9} for pt in full_polyline]
    encoded = encode_polyline(points)

    # Build a mock Directions response that your frontend can work with.
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
