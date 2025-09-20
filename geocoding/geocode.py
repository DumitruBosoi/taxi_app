import math
import requests
from typing import List, Tuple, Optional
from config.constants import AVERAGE_SPEED_KMH, USER_AGENT, OSRM_URL

def geocode(query: str) -> Optional[Tuple[str, float, float]]:
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": query, "format": "json", "limit": 1}
        r = requests.get(url, params=params, headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        item = data[0]
        return item["display_name"], float(item["lat"]), float(item["lon"])
    except Exception:
        return None


def route_osrm(p1: Tuple[float, float], p2: Tuple[float, float]) -> Optional[Tuple[float, float, List[Tuple[float, float]]]]:
    try:
        lat1, lon1 = p1
        lat2, lon2 = p2
        url = OSRM_URL.format(lat1=lat1, lon1=lon1, lat2=lat2, lon2=lon2)
        r = requests.get(url, headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        data = r.json()
        routes = data.get("routes") or []
        if not routes:
            return None
        rt = routes[0]
        km = rt["distance"] / 1000.0
        minutes = rt["duration"] / 60.0
        coords = [(lat, lon) for lon, lat in rt["geometry"]["coordinates"]]
        return km, minutes, coords
    except Exception:
        return None


def haversine_km(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    lat1, lon1 = p1
    lat2, lon2 = p2
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def interpolate_line(a: Tuple[float, float], b: Tuple[float, float], steps: int = 50) -> List[Tuple[float, float]]:
    lat1, lon1 = a
    lat2, lon2 = b
    pts = []
    for i in range(steps + 1):
        t = i / steps
        pts.append((lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t))
    return pts


def estimate_route(p1: Tuple[float, float], p2: Tuple[float, float]):
    r = route_osrm(p1, p2)
    if r:
        return r
    km = haversine_km(p1, p2)
    minutes = max(5.0, (km / max(5.0, AVERAGE_SPEED_KMH)) * 60.0)
    coords = interpolate_line(p1, p2, 50)
    return km, minutes, coords



