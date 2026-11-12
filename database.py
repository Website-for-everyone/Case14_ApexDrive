"""
Apex Drive — SQLite Database Engine
Stores supercar inventory, specifications, rental bookings, and KYC records.
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, date

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "apexdrive.db"))

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Supercars fleet table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS supercars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        engine TEXT NOT NULL,
        horsepower INTEGER NOT NULL,
        torque_nm INTEGER NOT NULL,
        accel_0_100 REAL NOT NULL,
        top_speed_kmh INTEGER NOT NULL,
        daily_rate_rub INTEGER NOT NULL,
        deposit_rub INTEGER NOT NULL,
        sound_frequency REAL NOT NULL,
        description TEXT NOT NULL,
        is_available BOOLEAN DEFAULT 1
    )
    """)
    
    # Rental bookings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_code TEXT UNIQUE NOT NULL,
        car_id INTEGER NOT NULL,
        client_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        driver_age INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        rental_days INTEGER NOT NULL,
        mileage_package TEXT NOT NULL,
        insurance_tier TEXT NOT NULL,
        daily_rate_rub INTEGER NOT NULL,
        total_rent_rub INTEGER NOT NULL,
        deposit_rub INTEGER NOT NULL,
        kyc_status TEXT DEFAULT 'pending',
        license_photo_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (car_id) REFERENCES supercars(id)
    )
    """)
    
    # Seed default supercar fleet if empty
    cursor.execute("SELECT COUNT(*) FROM supercars")
    if cursor.fetchone()[0] == 0:
        default_fleet = [
            ("Porsche 911 GT3 RS (992)", "porsche_gt3rs", "4.0L Naturally Aspirated Boxer-6", 525, 465, 3.2, 296, 65000, 150000, 180.0, "Трековый болид с гигантским антикрылом DRS и красной зоной до 9000 об/мин.", 1),
            ("Ferrari F8 Tributo", "ferrari_f8", "3.9L Twin-Turbo V8", 720, 770, 2.9, 340, 85000, 200000, 220.0, "Итальянский шедевр аэродинамики со звуком формульного мотора и разгоном до сотни быстрее 3 секунд.", 1),
            ("Lamborghini Huracán EVO", "lambo_huracan", "5.2L Naturally Aspirated V10", 640, 600, 2.9, 325, 80000, 180000, 195.0, "Громогласный полноприводный V10 с взрывной динамикой и яростным выхлопом в режиме Corsa.", 1),
            ("McLaren 720S Spider", "mclaren_720s", "4.0L Twin-Turbo V8", 720, 770, 2.9, 341, 90000, 220000, 240.0, "Карбоновый монокок, подъемные двери-крылья бабочки и складная жесткая крыша за 11 секунд.", 1),
            ("Audi R8 V10 Performance", "audi_r8", "5.2L FSI V10 Quattro", 620, 580, 3.1, 331, 55000, 120000, 190.0, "Легендарный атмосферный суперкар на каждый день с эталонным звуком и идеальной управляемостью.", 1)
        ]
        cursor.executemany("""
        INSERT INTO supercars 
        (name, slug, engine, horsepower, torque_nm, accel_0_100, top_speed_kmh, daily_rate_rub, deposit_rub, sound_frequency, description, is_available)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, default_fleet)
        
    conn.commit()
    conn.close()

def get_all_cars() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM supercars ORDER BY daily_rate_rub ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_car_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM supercars WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_car_by_id(car_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM supercars WHERE id = ?", (car_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def check_dates_availability(car_id: int, start_date_str: str, end_date_str: str) -> bool:
    """Checks if car has overlapping confirmed bookings."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT COUNT(*) FROM rentals 
    WHERE car_id = ? 
      AND (
          (start_date <= ? AND end_date >= ?) OR
          (start_date <= ? AND end_date >= ?) OR
          (start_date >= ? AND end_date <= ?)
      )
    """, (car_id, start_date_str, start_date_str, end_date_str, end_date_str, start_date_str, end_date_str))
    overlap_count = cursor.fetchone()[0]
    conn.close()
    return overlap_count == 0

def create_rental_booking(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    import random
    code = f"APEX-{random.randint(1000, 9999)}"
    
    cursor.execute("""
    INSERT INTO rentals 
    (booking_code, car_id, client_name, phone, driver_age, start_date, end_date, rental_days, mileage_package, insurance_tier, daily_rate_rub, total_rent_rub, deposit_rub, kyc_status, license_photo_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        code,
        data["car_id"],
        data["client_name"],
        data["phone"],
        data["driver_age"],
        data["start_date"],
        data["end_date"],
        data["rental_days"],
        data.get("mileage_package", "200km"),
        data.get("insurance_tier", "standard"),
        data["daily_rate_rub"],
        data["total_rent_rub"],
        data["deposit_rub"],
        data.get("kyc_status", "pending"),
        data.get("license_photo_id", None)
    ))
    booking_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    data["booking_id"] = booking_id
    data["booking_code"] = code
    return data

def get_rental_by_code(code: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT r.*, c.name as car_name, c.horsepower, c.engine
    FROM rentals r
    JOIN supercars c ON r.car_id = c.id
    WHERE r.booking_code = ?
    """, (code,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# Initialize on import
init_db()
