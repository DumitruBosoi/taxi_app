from datetime import datetime
import json
import sqlite3
from config.constants import FARE_TIERS
from model.vehicle import VEHICLES, Vehicle


def calc_fare(vehicle: Vehicle, tier: str, km: float, minutes: float, pax: int) -> float:
    if pax > vehicle.capacity:
        raise ValueError(f"{vehicle.name} fits up to {vehicle.capacity} pax")
    mult = FARE_TIERS.get(tier, 1.0)
    return (vehicle.base_per_km * km + vehicle.per_min * minutes) * mult

def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def advance_track_idx(ride: sqlite3.Row) -> int:
    """Advance track index based on elapsed real time and estimated minutes."""
    coords = json.loads(ride["tracking_json"] or "[]")
    if not coords:
        return ride["track_idx"]
    last = ride["last_update_at"]
    if not last:
        return ride["track_idx"]
    elapsed = (datetime.now() - datetime.fromisoformat(last)).total_seconds()
    total_pts = max(1, len(coords) - 1)
    pps = max(0.5, total_pts / max(1.0, ride["est_minutes"]) / 1.2)  
    advance = int(elapsed * pps)
    return min(total_pts, ride["track_idx"] + max(0, advance))

def get_vehicle(code_or_name: str) -> Vehicle:
    for v in VEHICLES:
        if v.code == code_or_name or v.name == code_or_name:
            return v
    return VEHICLES[0]