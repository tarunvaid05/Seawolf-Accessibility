import math
import heapq
import json
from google_maps_util import get_elevation  # This function uses a polyline string to get elevation data
from typing import List, Dict

# A very large cost to penalize staircase segments
HUGE_PENALTY = 1e6

def haversine_distance(coord1: Dict[str, float], coord2: Dict[str, float]) -> float:
    """
    Calculate the haversine distance between two points (lat, lon) in meters.
    Args:
        coord1: The first coordinate as a dictionary with 'lat' and 'lon' keys.
        coord2: The second coordinate as a dictionary with 'lat' and 'lon' keys.
    Returns:
        The haversine distance between the two coordinates in meters.
    """
    lat1, lon1 = coord1["lat"], coord1["lon"]
    lat2, lon2 = coord2["lat"], coord2["lon"]

    lat1 = lat1 / 1e9
    lon1 = lon1 / 1e9
    lat2 = lat2 / 1e9
    lon2 = lon2 / 1e9
    R = 6371000  # radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def segment_overlaps_staircase(segment_coords: List[Dict[str, float]], staircase_coords: Dict[str, float], threshold: float) -> bool:
    """
    Check whether a route segment (a list of dict-based coordinates) overlaps with a staircase segment 
    (also a list of dict-based coordinates). Overlap is defined as any point of the segment being within
    'threshold' meters of any point of the staircase.
    
    Args:
        segment_coords: List of dict-based coordinates from the route segment.
        staircase_coords: List of dict-based coordinates defining a staircase from ways_output.json.
        threshold: The maximum distance (in meters) to consider as overlapping.
    
    Returns:
        True if any point in segment_coords is within threshold meters of any staircase point.
    """
    for coord in segment_coords:
        for stair_pt in staircase_coords["refs"]:
            if haversine_distance(coord, stair_pt) <= threshold:
                return True
    return False

def segment_overlaps_any_staircase(segment_coords: List[Dict[str, float]], staircases: List[Dict[str, float]], threshold: float) -> bool:
    """
    Checks if a segment overlaps with any staircase in the provided list.
    
    Args:
        segment_coords: List of dict-based coordinates for the route segment.
        staircases: List of staircase segments; each staircase is itself a list of dict-based coordinates.
        threshold: Distance threshold in meters.
        
    Returns:
        True if the segment overlaps any staircase; otherwise False.
    """
    for staircase in staircases: 
        if segment_overlaps_staircase(segment_coords, staircase, threshold): 
            return True 
    return False

def compute_edge_cost(poly: List[Dict[str, float]], staircase_threshold: float = 0.001) -> float:
    """
    Computes the cost for a segment based solely on its geometry and the staircase data.

    The segment (poly) is a list of dictionaries, each with keys "id", "lat", and "lon".  
    The staircase data is read from "stairs.json" (which is expected to be a list of staircase segments,  
    where each segment is itself a list of (lat, lon) tuples in degrees).

    The function computes the total distance along the poly segment (using haversine_distance).  
    If any coordinate in the segment overlaps any staircase (within the given threshold in meters),  
    a huge penalty is added.

    Parameters:
      poly: List of dictionaries representing coordinates, e.g.:
            [
              {"id": 686565882, "lat": 40912855400, "lon": -73132155500},
              {"id": 5994624358, "lat": 40912860000, "lon": -73132098500}
            ]
            (Note: lat and lon are already scaled down to degrees.)
      staircase_threshold: Maximum distance in meters to consider a point overlapping a staircase.
                           (Defaults to 1e-6, but you can adjust as needed.)

    Returns:
      The computed cost (float) for traversing the segment.
    """
    if not poly:
        return 0.0

    # Build the list of coordinate dictionaries from poly.
    segment_coords = [{"lat": pt["lat"], "lon": pt["lon"]} for pt in poly]

    total_cost = 0.0
    with open("stairs.json", "r") as f:
        staircases = json.load(f)
    
    # If any point in the segment is within staircase_threshold (meters) of any staircase point,
    # add a huge penalty.
    if segment_overlaps_any_staircase(segment_coords, staircases, threshold=staircase_threshold):
        total_cost += HUGE_PENALTY

    return total_cost

def poly_overlaps_staircase(poly: List[Dict[str, float]], staircase_threshold: float = 0.001) -> bool:
    """
    Checks if a polyline segment overlaps with any staircase.

    Parameters:
      poly: List of dictionaries representing coordinates, e.g.:
            [
              {"id": 686565882, "lat": 40912855400, "lon": -73132155500},
              {"id": 5994624358, "lat": 40912860000, "lon": -73132098500}
            ]
            (Note: lat and lon are already scaled down to degrees.)
      staircase_threshold: Maximum distance in meters to consider a point overlapping a staircase.
                           (Defaults to 1e-6, but you can adjust as needed.)

    Returns:
      True if the polyline segment overlaps any staircase; otherwise False.
    """
    if not poly:
        return False

    # Build the list of coordinate dictionaries from poly.
    segment_coords = [{"lat": pt["lat"], "lon": pt["lon"]} for pt in poly]

    with open("stairs.json", "r") as f:
        staircases = json.load(f)
    
    # Check if any point in the segment is within staircase_threshold (meters) of any staircase point.
    return segment_overlaps_any_staircase(segment_coords, staircases, threshold=staircase_threshold)