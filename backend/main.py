import os
from fastapi import FastAPI
import requests
import polyline
import json  # For debugging
from fastapi.middleware.cors import CORSMiddleware
from route_cost import compute_edge_cost  # Import the cost function

app = FastAPI()

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],  # explicitly allow your frontend origin
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
    try:
        url = (
            f"https://maps.googleapis.com/maps/api/directions/json?"
            f"origin={ORIGIN}&destination={DESTINATION}&alternatives=true&mode=walking&key={GOOGLE_MAPS_API_KEY}"
        )
        response = requests.get(url)
        data = response.json()

        # DEBUG: Print the full API response in the terminal.
        print("\n===== Google API Response =====")
        print(json.dumps(data, indent=4))

        routes = []
        colors = ["red", "blue", "green", "purple", "orange"]

        if "routes" in data and len(data["routes"]) > 0:
            print(f"Number of routes received: {len(data['routes'])}")
            for i, route in enumerate(data["routes"]):
                try:
                    if "overview_polyline" not in route or "points" not in route["overview_polyline"]:
                        raise ValueError(f"Route {i+1} missing overview_polyline data. Full route data: {route}")
                    
                    encoded_polyline = route["overview_polyline"]["points"]
                    decoded_polyline = polyline.decode(encoded_polyline)
                    poly_dict = [{"lat": coord[0], "lon": coord[1]} for coord in decoded_polyline]

                    # Calculate the cost based solely on the distance.
                    # The API returns distance in meters under route["legs"][0]["distance"]["value"]
                    distance = route["legs"][0]["distance"]["value"]
                    # You can adjust the cost factor as needed. Here, we simply use distance as cost.
                    cost = distance

                    # Cycle through the colors.
                    route_color = colors[i % len(colors)]

                    print(f"Route {i + 1}: Color = {route_color}, Cost = {cost}")

                    routes.append({
                        "route_number": i + 1,
                        "total_distance": route["legs"][0]["distance"]["text"],
                        "total_duration": route["legs"][0]["duration"]["text"],
                        "cost": cost,
                        "color": route_color,
                        "coordinates": decoded_polyline
                    })
                except Exception as route_error:
                    print(f"Error processing route {i+1}: {route_error}")
            return {"routes": routes}
        else:
            print("No routes found in the API response.")
            return {"error": "No routes found", "api_response": data}
    except Exception as e:
        print("Error in get_routes:", e)
        return {"error": str(e)}