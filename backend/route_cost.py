import json
import math
from functools import lru_cache
from typing import Dict, List, Tuple

# Known stair edges should be avoided unless no route exists without them.
HUGE_PENALTY = 1e6

# Existing data cannot distinguish every ramp from nearby stairs, so keep the
# clearance buffer conservative. This catches routes that hug known stair geometry
# without treating all nearby outdoor paths as impossible.
STAIR_CLEARANCE_METERS = 1.0
NEAR_STAIR_PENALTY = 100.0
STAIR_SEGMENT_TOLERANCE_METERS = 0.05

Coord = Tuple[float, float]
PointSignature = Tuple[int, int, int]


def _coord_from_scaled(coord: Dict[str, float]) -> Coord:
    return coord["lat"] / 1e9, coord["lon"] / 1e9


def _signature(poly: List[Dict[str, float]]) -> Tuple[PointSignature, ...]:
    return tuple((pt.get("id"), pt["lat"], pt["lon"]) for pt in poly)


def _haversine(coord1: Coord, coord2: Coord) -> float:
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def haversine_distance(coord1: Dict[str, float], coord2: Dict[str, float]) -> float:
    return _haversine(_coord_from_scaled(coord1), _coord_from_scaled(coord2))


def _project_point_onto_segment(point: Coord, start: Coord, end: Coord) -> Coord:
    lat_rad = math.radians(point[0])
    cos_lat = math.cos(lat_rad)

    def to_xy(coord: Coord) -> Coord:
        lat, lon = coord
        return lon * cos_lat, lat

    px, py = to_xy(point)
    ax, ay = to_xy(start)
    bx, by = to_xy(end)
    dx = bx - ax
    dy = by - ay

    if dx == 0 and dy == 0:
        return start

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    qx = ax + t * dx
    qy = ay + t * dy
    return qy, qx / cos_lat


def _point_to_segment_distance(point: Coord, start: Coord, end: Coord) -> float:
    projected = _project_point_onto_segment(point, start, end)
    return _haversine(point, projected)


def _segments_intersect(a: Coord, b: Coord, c: Coord, d: Coord) -> bool:
    lat_rad = math.radians((a[0] + b[0] + c[0] + d[0]) / 4)
    cos_lat = math.cos(lat_rad)

    def to_xy(coord: Coord) -> Coord:
        lat, lon = coord
        return lon * cos_lat, lat

    ax, ay = to_xy(a)
    bx, by = to_xy(b)
    cx, cy = to_xy(c)
    dx, dy = to_xy(d)

    def orientation(p: Coord, q: Coord, r: Coord) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_segment(p: Coord, q: Coord, r: Coord) -> bool:
        return (
            min(p[0], r[0]) <= q[0] <= max(p[0], r[0])
            and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])
        )

    A = (ax, ay)
    B = (bx, by)
    C = (cx, cy)
    D = (dx, dy)
    o1 = orientation(A, B, C)
    o2 = orientation(A, B, D)
    o3 = orientation(C, D, A)
    o4 = orientation(C, D, B)
    epsilon = 1e-14

    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    if abs(o1) <= epsilon and on_segment(A, C, B):
        return True
    if abs(o2) <= epsilon and on_segment(A, D, B):
        return True
    if abs(o3) <= epsilon and on_segment(C, A, D):
        return True
    if abs(o4) <= epsilon and on_segment(C, B, D):
        return True

    return False


def _segment_to_segment_distance(a: Coord, b: Coord, c: Coord, d: Coord) -> float:
    if _segments_intersect(a, b, c, d):
        return 0.0

    return min(
        _point_to_segment_distance(a, c, d),
        _point_to_segment_distance(b, c, d),
        _point_to_segment_distance(c, a, b),
        _point_to_segment_distance(d, a, b),
    )


@lru_cache(maxsize=1)
def _load_stair_data():
    with open("stairs.json", "r") as f:
        staircases = json.load(f)

    stair_node_pairs = set()
    stair_segments = []

    for staircase in staircases:
        refs = staircase["refs"]
        for i in range(len(refs) - 1):
            start = refs[i]
            end = refs[i + 1]
            stair_node_pairs.add(frozenset((start.get("id"), end.get("id"))))
            stair_segments.append((_coord_from_scaled(start), _coord_from_scaled(end)))

    return staircases, stair_node_pairs, tuple(stair_segments)


def _edge_has_known_stair_node_pair(poly_signature: Tuple[PointSignature, ...]) -> bool:
    _, stair_node_pairs, _ = _load_stair_data()

    for i in range(len(poly_signature) - 1):
        start_id = poly_signature[i][0]
        end_id = poly_signature[i + 1][0]
        if frozenset((start_id, end_id)) in stair_node_pairs:
            return True

    return False


def _edge_lies_on_stair_segment(
    route_start: Coord,
    route_end: Coord,
    stair_start: Coord,
    stair_end: Coord,
) -> bool:
    return (
        _point_to_segment_distance(route_start, stair_start, stair_end) <= STAIR_SEGMENT_TOLERANCE_METERS
        and _point_to_segment_distance(route_end, stair_start, stair_end) <= STAIR_SEGMENT_TOLERANCE_METERS
    )


@lru_cache(maxsize=20000)
def _edge_stair_proximity(poly_signature: Tuple[PointSignature, ...]) -> Tuple[bool, float]:
    if len(poly_signature) < 2:
        return False, float("inf")

    if _edge_has_known_stair_node_pair(poly_signature):
        return True, 0.0

    _, _, stair_segments = _load_stair_data()
    route_points = [(lat / 1e9, lon / 1e9) for _, lat, lon in poly_signature]
    min_distance = float("inf")

    for i in range(len(route_points) - 1):
        route_start = route_points[i]
        route_end = route_points[i + 1]

        for stair_start, stair_end in stair_segments:
            if _edge_lies_on_stair_segment(route_start, route_end, stair_start, stair_end):
                return True, 0.0

            distance = _segment_to_segment_distance(route_start, route_end, stair_start, stair_end)
            if distance < min_distance:
                min_distance = distance

    return False, min_distance


def stair_proximity(poly: List[Dict[str, float]]) -> Tuple[bool, float]:
    return _edge_stair_proximity(_signature(poly))


def compute_edge_cost(
    poly: List[Dict[str, float]],
    staircase_threshold: float = STAIR_CLEARANCE_METERS,
) -> float:
    if not poly:
        return 0.0

    is_stair_edge, stair_distance = stair_proximity(poly)
    if is_stair_edge:
        return HUGE_PENALTY
    if stair_distance <= staircase_threshold:
        return NEAR_STAIR_PENALTY

    return 0.0


def compute_snap_cost(distance_to_edge: float, poly: List[Dict[str, float]]) -> float:
    return distance_to_edge + compute_edge_cost(poly)


def segment_overlaps_staircase(
    segment_coords: List[Dict[str, float]],
    staircase_coords: Dict[str, float],
    threshold: float,
) -> bool:
    if len(segment_coords) < 2 or len(staircase_coords["refs"]) < 2:
        return False

    route_points = [_coord_from_scaled(coord) for coord in segment_coords]
    stair_points = [_coord_from_scaled(coord) for coord in staircase_coords["refs"]]

    for i in range(len(route_points) - 1):
        for j in range(len(stair_points) - 1):
            distance = _segment_to_segment_distance(
                route_points[i],
                route_points[i + 1],
                stair_points[j],
                stair_points[j + 1],
            )
            if distance <= threshold:
                return True

    return False


def segment_overlaps_any_staircase(
    segment_coords: List[Dict[str, float]],
    staircases: List[Dict[str, float]],
    threshold: float,
) -> bool:
    for staircase in staircases:
        if segment_overlaps_staircase(segment_coords, staircase, threshold):
            return True
    return False


def poly_overlaps_staircase(
    poly: List[Dict[str, float]],
    staircase_threshold: float = STAIR_CLEARANCE_METERS,
) -> bool:
    is_stair_edge, stair_distance = stair_proximity(poly)
    return is_stair_edge or stair_distance <= staircase_threshold
