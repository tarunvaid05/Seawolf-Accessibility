from fastapi import FastAPI
import requests
import polyline
import json  # For debugging

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hardcoded start and end locations
ORIGIN = "East Side Dining, John S. Toll Drive, Stony Brook, NY 11794"
DESTINATION = "SAC Plaza, Student Activities Center, Suite 220, Stony Brook, NY 11790"
GOOGLE_MAPS_API_KEY = "AIzaSyAvyVfvVXEjsGEQHPIYP0HjPMN_BRhzPQg"  # Replace with your actual API key

@app.get("/get_routes")
def get_routes():
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={ORIGIN}&destination={DESTINATION}&alternatives=true&mode=walking&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    data = response.json()

    # DEBUG: Print the full API response in the terminal
    print("\n===== Google API Response =====")
    print(json.dumps(data, indent=4))  # Pretty-print the JSON response

    routes = []
    if "routes" in data and len(data["routes"]) > 0:
        print(f"Number of routes received: {len(data['routes'])}")  # Debugging log
        for i, route in enumerate(data["routes"]):
            encoded_polyline = route["overview_polyline"]["points"]
            decoded_polyline = polyline.decode(encoded_polyline)  # Convert to list of (lat, lng) tuples

            # DEBUG: Print decoded polyline coordinates
            print(f"Route {i + 1} coordinates: {decoded_polyline}")
            
            routes.append({
                "route_number": i + 1,
                "total_distance": route["legs"][0]["distance"]["text"],  # Example: "4.3 miles"
                "total_duration": route["legs"][0]["duration"]["text"],  # Example: "8 mins"
                "coordinates": decoded_polyline  # List of (lat, lng) tuples
            })

        return {"routes": routes}
    else:
        return {"error": "No routes found", "api_response": data}

# Run the server: uvicorn main:app --reload


