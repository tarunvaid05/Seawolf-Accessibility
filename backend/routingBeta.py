import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import googlemaps
from datetime import datetime
from config import GOOGLE_MAPS_API_KEY  # Import the API key from config

app = FastAPI()

# Allow CORS so your frontend can access the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the API key from the environment.
API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    raise Exception("Please set the GOOGLE_MAPS_API_KEY environment variable.")

# Initialize the googlemaps client.
gmaps = googlemaps.Client(key=API_KEY)

@app.get("/api/directions")
def get_directions(start: str = Query(..., description="Start coordinate as 'lat,lng'"),
                   end: str = Query(..., description="End coordinate as 'lat,lng'")):
    """
    Get the best walking route between start and end coordinates.
    """
    try:
        start_coords = tuple(map(float, start.split(',')))
        end_coords = tuple(map(float, end.split(',')))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Coordinates must be provided as 'lat,lng'") from e

    now = datetime.now()
    # Get driving directions—here we use walking mode.
    directions_result = gmaps.directions(
        origin=start_coords,
        destination=end_coords,
        mode="walking",
        departure_time=now
    )

    if not directions_result:
        raise HTTPException(status_code=404, detail="No walking route found.")

    # Return the best (first) route.
    return directions_result[0]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)