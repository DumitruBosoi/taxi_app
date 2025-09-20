import os

PRIMARY = "#0E7C4F" 
OSRM_URL = "http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
AVERAGE_SPEED_KMH = 35.0
USER_AGENT = {"User-Agent": "TaxiStreamlit/1.0 (edu-demo)"}
FARE_TIERS = {"Basic": 1.0, "Advanced": 1.2, "Premium": 1.5}
DEFAULT_CENTER = (24.8607, 67.0011)
APP_DB = os.environ.get("TAXI_DB", "taxi_streamlit.db")
