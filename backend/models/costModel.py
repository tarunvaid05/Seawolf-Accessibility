import requests
import numpy as np
import math
from route_cost import compute_manual_cost
from config import GOOGLE_MAPS_API_KEY
# You might read this key from an environment variable or config file
GOOGLE_MAPS_ELEVATION_URL = "https://maps.googleapis.com/maps/api/elevation/json"

def haversine_distance(coord1, coord2):
    """Calculate distance in meters between two (lat, lng) points."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_elevation_for_path(path):
    """
    Given a path as a list of (lat, lng) tuples,
    call the Google Elevation API to get elevations.
    """
    locations = "|".join([f"{lat},{lng}" for lat, lng in path])
    params = {
        "locations": locations,
        "key": GOOGLE_MAPS_API_KEY
    }
    response = requests.get(GOOGLE_MAPS_ELEVATION_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "OK":
            elevations = [result["elevation"] for result in data["results"]]
            return elevations
        else:
            raise Exception(f"Elevation API returned error: {data['status']}")
    else:
        raise Exception("Failed to fetch elevation data.")

def compute_slope(elevations, path):
    """
    Compute the average slope (rise over run) along the path.
    """
    if len(elevations) < 2:
        return 0
    slopes = []
    for i in range(len(elevations) - 1):
        elev_diff = elevations[i+1] - elevations[i]
        distance = haversine_distance(path[i], path[i+1])
        if distance > 0:
            slopes.append(elev_diff / distance)
    return np.mean(slopes) if slopes else 0

def extract_features(route):
    """
    Given a route dictionary with keys:
      - "distance": total route distance in meters,
      - "path": list of (lat, lng) points along the route,
      - "stairs": (optional) an integer count of stairs,
    Compute and return a feature vector: 
         [distance, average slope, stairs count]
    """
    distance = route.get("distance", 0)
    path = route.get("path", [])
    stairs = route.get("stairs", 0)
    try:
        elevations = get_elevation_for_path(path)
        avg_slope = compute_slope(elevations, path)
    except Exception as e:
        print("Error computing slope:", e)
        avg_slope = 0
    return [distance, avg_slope, stairs]

if __name__ == "__main__":
    # Sample test route
    sample_route = {
        "distance": 1200,  
        "path": [(40.910412, -73.124705), (40.911000, -73.125000)],
        "stairs": 1
    }
    features = extract_features(sample_route)
    print("Extracted features:", features)
    cost = compute_manual_cost(features)
    print("Computed manual cost:", cost)