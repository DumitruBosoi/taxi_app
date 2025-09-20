
import sqlite3
from typing import Optional, List
from config.constants import APP_DB
from model.vehicle import VEHICLES
from utils.helper import now_ts

class DB:
    def __init__(self, path: str = APP_DB):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self):
        c = self.conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, email TEXT UNIQUE, password TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, email TEXT UNIQUE, password TEXT,
                car_make TEXT, car_model TEXT, car_plate TEXT,
                is_available INTEGER DEFAULT 1
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, email TEXT UNIQUE, password TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                code TEXT PRIMARY KEY, name TEXT, capacity INTEGER, base_per_km REAL, per_min REAL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                driver_id INTEGER,
                pickup_text TEXT, dropoff_text TEXT,
                pickup_lat REAL, pickup_lon REAL,
                drop_lat REAL, drop_lon REAL,
                scheduled_at TEXT, created_at TEXT,
                vehicle_code TEXT, fare_tier TEXT, pax INTEGER,
                est_km REAL, est_minutes REAL, est_price REAL,
                status TEXT,
                tracking_json TEXT,
                track_idx INTEGER DEFAULT 0,
                last_update_at TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, ride_id INTEGER,
                rating INTEGER, comments TEXT, created_at TEXT
            )
            """
        )
     
        for v in VEHICLES:
            c.execute(
                "INSERT OR IGNORE INTO vehicles(code,name,capacity,base_per_km,per_min) VALUES(?,?,?,?,?)",
                (v.code, v.name, v.capacity, v.base_per_km, v.per_min),
            )
     
        c.execute(
            "INSERT OR IGNORE INTO admins(id,name,email,password) VALUES(1,'Admin','admin@local','admin')"
        )
        self.conn.commit()

    # users
    def create_user(self, name, email, password) -> Optional[int]:
        try:
            cur = self.conn.cursor()
            cur.execute("INSERT INTO users(name,email,password) VALUES (?,?,?)", (name, email, password))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_user(self, email, password) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        return cur.fetchone()

    # drivers
    def create_driver(self, name, email, password, make, model, plate) -> Optional[int]:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO drivers(name,email,password,car_make,car_model,car_plate) VALUES (?,?,?,?,?,?)",
                (name, email, password, make, model, plate),
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_driver(self, email, password) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM drivers WHERE email=? AND password=?", (email, password))
        return cur.fetchone()

    def set_driver_available(self, driver_id: int, available: bool):
        self.conn.execute("UPDATE drivers SET is_available=? WHERE id=?", (1 if available else 0, driver_id))
        self.conn.commit()

    # admins
    def get_admin(self, email, password) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM admins WHERE email=? AND password=?", (email, password))
        return cur.fetchone()

    # rides
    def add_ride(self, **kw) -> int:
        cur = self.conn.cursor()
        cols = ",".join(kw.keys())
        q = f"INSERT INTO rides ({cols}) VALUES ({','.join(['?']*len(kw))})"
        cur.execute(q, tuple(kw.values()))
        self.conn.commit()
        return cur.lastrowid

    def list_user_rides(self, user_id: int) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM rides WHERE user_id=? ORDER BY datetime(created_at) DESC", (user_id,))
        return cur.fetchall()

    def list_driver_queue(self) -> List[sqlite3.Row]:
       
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM rides WHERE status='Assigned' AND driver_id IS NULL ORDER BY datetime(created_at) ASC")
        return cur.fetchall()

    def get_ride(self, ride_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM rides WHERE id=?", (ride_id,))
        return cur.fetchone()

    def set_ride_driver(self, ride_id: int, driver_id: int):
        self.conn.execute("UPDATE rides SET driver_id=?, status='In-Progress', last_update_at=? WHERE id=?",
                          (driver_id, now_ts(), ride_id))
        self.conn.commit()

    def update_ride_tracking(self, ride_id: int, idx: int, status: Optional[str] = None):
        if status:
            self.conn.execute("UPDATE rides SET track_idx=?, last_update_at=?, status=? WHERE id=?",
                              (idx, now_ts(), status, ride_id))
        else:
            self.conn.execute("UPDATE rides SET track_idx=?, last_update_at=? WHERE id=?",
                              (idx, now_ts(), ride_id))
        self.conn.commit()

    def list_all_rides(self) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM rides ORDER BY datetime(created_at) DESC")
        return cur.fetchall()

    # feedback
    def add_feedback(self, user_id: int, ride_id: int, rating: int, comments: str):
        self.conn.execute(
            "INSERT INTO feedback(user_id,ride_id,rating,comments,created_at) VALUES (?,?,?,?,?)",
            (user_id, ride_id, rating, comments, now_ts()),
        )
        self.conn.commit()



