"""
Apex Drive — FastAPI Backend
Provides supercar telemetry, dynamic rental calculator, and reservation management.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import os
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

app = FastAPI(title="Apex Drive Supercar Rental API", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def calculate_quote(car: Dict[str, Any], start_date_str: str, end_date_str: str,
                    driver_age: int, mileage_package: str = "200km", insurance_tier: str = "standard") -> Dict[str, Any]:
    try:
        s_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Неверный формат дат (ожидается YYYY-MM-DD)")

    today = date.today()
    if s_date < today:
        raise HTTPException(status_code=400, detail="Дата начала аренды не может быть в прошлом")
    if e_date < s_date:
        raise HTTPException(status_code=400, detail="Дата возврата не может быть раньше даты выдачи")
        
    days = (e_date - s_date).days + 1
    if days > 30:
        raise HTTPException(status_code=400, detail="Максимальный срок разовой аренды — 30 дней")
        
    if driver_age < 21:
        raise HTTPException(status_code=400, detail="Минимальный возраст водителя для аренды суперкара — 21 год")

    base_daily = car["daily_rate_rub"]
    
    # Age surcharge
    age_multiplier = 1.20 if (21 <= driver_age <= 24) else 1.0
    
    # Mileage add-on per day
    mileage_addon = 0
    if mileage_package == "400km":
        mileage_addon = 10000
    elif mileage_package == "unlimited":
        mileage_addon = 25000

    # Insurance add-on & deposit
    insurance_addon = 0
    deposit_multiplier = 1.0
    if insurance_tier == "vip_shield":
        insurance_addon = 15000
        deposit_multiplier = 0.5

    daily_total = round((base_daily * age_multiplier) + mileage_addon + insurance_addon)
    total_rent = daily_total * days
    final_deposit = round(car["deposit_rub"] * deposit_multiplier)

    return {
        "car_id": car["id"],
        "car_name": car["name"],
        "start_date": start_date_str,
        "end_date": end_date_str,
        "rental_days": days,
        "driver_age": driver_age,
        "is_young_driver": (21 <= driver_age <= 24),
        "base_daily_rate": base_daily,
        "adjusted_daily_rate": daily_total,
        "total_rent_rub": total_rent,
        "deposit_rub": final_deposit,
        "mileage_package": mileage_package,
        "insurance_tier": insurance_tier
    }

class QuoteRequest(BaseModel):
    car_id: int
    start_date: str
    end_date: str
    driver_age: int = 25
    mileage_package: str = "200km"
    insurance_tier: str = "standard"

class RentalSubmitRequest(BaseModel):
    car_id: int
    client_name: str
    phone: str
    driver_age: int
    start_date: str
    end_date: str
    mileage_package: str = "200km"
    insurance_tier: str = "standard"
    notes: Optional[str] = ""

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Apex Drive Supercar Rental Backend</h1>")

@app.get("/api/cars")
async def api_get_cars():
    cars = database.get_all_cars()
    return {"status": "ok", "fleet": cars}

@app.get("/api/availability")
async def api_check_availability(car_id: int = Query(...), start_date: str = Query(...), end_date: str = Query(...)):
    available = database.check_dates_availability(car_id, start_date, end_date)
    return {"status": "ok", "car_id": car_id, "start_date": start_date, "end_date": end_date, "available": available}

@app.post("/api/calculate")
async def api_calculate(req: QuoteRequest):
    car = database.get_car_by_id(req.car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
        
    quote = calculate_quote(
        car=car,
        start_date_str=req.start_date,
        end_date_str=req.end_date,
        driver_age=req.driver_age,
        mileage_package=req.mileage_package,
        insurance_tier=req.insurance_tier
    )
    return {"status": "ok", "quote": quote}

@app.post("/api/rentals")
async def api_submit_rental(req: RentalSubmitRequest):
    if not req.client_name.strip() or not req.phone.strip():
        raise HTTPException(status_code=422, detail="Укажите имя и телефон водителя")
        
    car = database.get_car_by_id(req.car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    # Check date overlap
    if not database.check_dates_availability(req.car_id, req.start_date, req.end_date):
        raise HTTPException(status_code=409, detail="На выбранные даты этот суперкар уже забронирован другим клиентом")

    quote = calculate_quote(
        car=car,
        start_date_str=req.start_date,
        end_date_str=req.end_date,
        driver_age=req.driver_age,
        mileage_package=req.mileage_package,
        insurance_tier=req.insurance_tier
    )

    booking_data = {
        "car_id": car["id"],
        "client_name": req.client_name,
        "phone": req.phone,
        "driver_age": req.driver_age,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "rental_days": quote["rental_days"],
        "mileage_package": req.mileage_package,
        "insurance_tier": req.insurance_tier,
        "daily_rate_rub": quote["adjusted_daily_rate"],
        "total_rent_rub": quote["total_rent_rub"],
        "deposit_rub": quote["deposit_rub"],
        "kyc_status": "pending_driver_license"
    }
    
    created = database.create_rental_booking(booking_data)
    
    lead_payload = {
        "project_name": "ApexDrive",
        "lead_type": "supercar_rental_reservation",
        "client_data": {
            "name": req.client_name,
            "phone": req.phone,
            "car": car["name"],
            "dates": f"{req.start_date} -> {req.end_date} ({quote['rental_days']} дн.)",
            "total_rub": quote["total_rent_rub"],
            "deposit_rub": quote["deposit_rub"],
            "code": created["booking_code"]
        },
        "target_recipient": "@Idrisov_prod",
        "booking_id": created["booking_id"]
    }

    return {
        "status": "ok",
        "booking": created,
        "quote": quote,
        "lead_payload": lead_payload,
        "message": f"Бронирование #{created['booking_code']} зарегистрировано! Ожидаем фото прав для завершения KYC."
    }
