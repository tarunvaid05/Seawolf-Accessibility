import math
import heapq
import json
import polyline
from google_maps_util import get_elevation  # This function uses a polyline string to get elevation data
from typing import Tuple
import networkx as nx
from typing import List

# A very large cost to penalize staircase segments
HUGE_PENALTY = 1e6

def convert_coord(coord) -> tuple:
    if isinstance(coord, dict):
        return (coord['lat'], coord['lng'])
    return coord

"""
    Calculate the haversine distance between two points (lat, lon) in meters.
    Args:
        coord1: The first coordinate.
        coord2: The second coordinate.
    Returns:
        The haversine distance between the two coordinates.
"""
def haversine_distance(coord1: tuple, coord2: tuple) -> float:
    lat1, lon1 = convert_coord(coord1)
    lat2, lon2 = convert_coord(coord2)
    R = 6371000  # radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

"""
    Check whether a route segment (a list of (lat, lon) tuples) overlaps with a staircase segment 
    (also a list of (lat, lon) tuples). Overlap is defined as any point of the segment being within
    'threshold' meters of any point of the staircase.
    
    Args:
        segment_coords: List of (lat, lon) tuples from the route segment.
        staircase_coords: List of (lat, lon) tuples defining a staircase from ways_output.json.
        threshold: The maximum distance (in meters) to consider as overlapping.
    
    Returns:
        True if any point in segment_coords is within threshold meters of any staircase point.
    """
def segment_overlaps_staircase(segment_coords: list, staircase_coords: list, threshold) -> bool:
    for coord in segment_coords:
        for stair_pt in staircase_coords:
            print("haversine distance", haversine_distance(coord, stair_pt))
            if haversine_distance(coord, stair_pt) <= threshold:
                return True
    return False


"""
    Checks if a segment overlaps with any staircase in the provided list.
    
    Args:
        segment_coords: List of (lat, lon) tuples for the route segment.
        staircases: List of staircase segments; each staircase is itself a list of (lat, lon) tuples.
        threshold: Distance threshold in meters.
        
    Returns:
        True if the segment overlaps any staircase; otherwise False.
    """
def segment_overlaps_any_staircase(segment_coords: list, staircases: list, threshold) -> bool:
    for staircase in staircases:
        if segment_overlaps_staircase(segment_coords, staircase, threshold):
            return True
    return False

def compute_edge_cost(poly, staircase_threshold: float = 1000000000):
    if not poly:
        return 0.0

    # Build the list of coordinate tuples from poly.
    segment_coords = [(pt["lat"], pt["lon"]) for pt in poly]

    # Compute the total distance along the segment.
    total_cost = 0.0
    with open("stairs.json", "r") as f:
        staircases = json.load(f)
    # If any point in the segment is within staircase_threshold (meters) of any staircase point,
    # add a huge penalty.
    if segment_overlaps_any_staircase(segment_coords, staircases, threshold=staircase_threshold):
        total_cost += HUGE_PENALTY

    return total_cost

