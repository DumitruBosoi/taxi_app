
from dataclasses import dataclass

@dataclass
class Vehicle:
    code: str
    name: str
    capacity: int
    base_per_km: float
    per_min: float

VEHICLES = [
    Vehicle("eco4", "Eco (4 pax)", 4, 50.0, 5.0),
    Vehicle("sed6", "Sedan (6 pax)", 6, 65.0, 6.5),
    Vehicle("van8", "Van (8 pax)", 8, 80.0, 8.0),
    Vehicle("bus12", "MiniBus (12 pax)", 12, 110.0, 10.0),
]
