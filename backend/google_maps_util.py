import googlemaps
import polyline
import json
from config import GOOGLE_MAPS_API_KEY  # Import the API key from config

# Initialize the Google Maps client using the API key from config.py
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

"""
    Retrieve directions from the Google Maps Directions API.
    Args:
        start_loc: The starting location of the route.
        end_loc: The ending location of the route.
        mode: The mode of transportation. Default is walking.
    Returns:
        A dictionary containing the route information.
"""
def get_direction(start_loc: str, end_loc: str, mode: str = "walking") -> dict:
    directions_result = gmaps.directions(start_loc, end_loc, mode=mode)
    return directions_result


"""
    Decode a polyline string into a list of coordinates.
    Args:
        polyline_str: The polyline string to decode.
    Returns:
        A list of coordinates.
"""
def decode_polyline(polyline_str: str) -> list:
    return polyline.decode(polyline_str)

"""
    Get elevation data along a route from a polyline string.
    Args:
        polyline_str: The polyline string to get elevation data from.
    Returns:
        A list of elevation data.
"""
def get_elevation(polyline_str: str) -> list:
    coordinates = decode_polyline(polyline_str)
    elevation = gmaps.elevation(coordinates)
    return elevation

"""
    Parse the directions result to extract individual route segments (steps).
    Each segment includes the start/end locations, distance, duration, and polyline.
    Args:
        directions: The directions result to extract segments from.
    Returns:
        A list of route segments, a list of dictionaries where each represent a route seg.
"""
def extract_route_segments(directions: dict) -> list:
    segments = []
    try:
        for leg in directions_result[0]['legs']:
            for step in leg['steps']:
                segment = {
                    'start_location': step['start_location'],
                    'end_location': step['end_location'],
                    'distance': step['distance']['value'],
                    'duration': step['duration']['value'],
                    'polyline': step['polyline']['points']
                }
                segments.append(segment)
    except (IndexError, KeyError) as e:
        print("Error parsing directions result:", e)
    return segments

if __name__ == "__main__":
    start = "300 Circle Rd, Stony Brook, NY 11790"
    end = "Student Activities Center, Suite 220, Stony Brook, NY 11790"

    # Get directions from Google Maps API
    directions_result = get_direction(start, end)

    # Pretty-print the raw directions result
    print("\n📍 **Raw Directions Result:**")
    print(json.dumps(directions_result, indent=4))

    # Extract route segments
    segments = extract_route_segments(directions_result)

    # Print extracted segments in a structured format
    print("\n🚀 **Extracted Route Segments:**")
    for idx, seg in enumerate(segments, start=1):
        print(f"\n--- Segment {idx} ---")
        print(json.dumps(seg, indent=4))  # Pretty-print each segment dictionary


    ## Get elevation data for the first segment
    if segments:
        first_polyline = segments[0]['polyline']
        elevation_data = get_elevation_a(first_polyline)
        print("Elevation Data for First Segment:")
        for point in elevation_data:
            print(point)
    