"""
Unit and Smoke Tests for Case 14: Apex Drive
Verifies supercar fleet data, rental quote engine, date availability collisions, API routes, and bot registration.
"""

import pytest
import os
import sys
from datetime import date, timedelta

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from backend.app import app, calculate_quote
import database
from bot.bot import router, create_bot_and_dispatcher
from fastapi.testclient import TestClient

client = TestClient(app)

def test_database_fleet():
    cars = database.get_all_cars()
    assert len(cars) == 5
    slugs = [c["slug"] for c in cars]
    assert "porsche_gt3rs" in slugs
    assert "ferrari_f8" in slugs
    assert "lambo_huracan" in slugs

def test_quote_calculation_standard():
    car = database.get_car_by_slug("porsche_gt3rs")
    today = date.today()
    s_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")
    e_date = (today + timedelta(days=4)).strftime("%Y-%m-%d") # 3 days

    quote = calculate_quote(
        car=car,
        start_date_str=s_date,
        end_date_str=e_date,
        driver_age=30,
        mileage_package="200km",
        insurance_tier="standard"
    )
    assert quote["rental_days"] == 3
    assert quote["is_young_driver"] is False
    assert quote["total_rent_rub"] == 65000 * 3
    assert quote["deposit_rub"] == 150000

def test_quote_young_driver_surcharge():
    car = database.get_car_by_slug("porsche_gt3rs")
    today = date.today()
    s_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    e_date = (today + timedelta(days=1)).strftime("%Y-%m-%d") # 1 day

    quote = calculate_quote(
        car=car,
        start_date_str=s_date,
        end_date_str=e_date,
        driver_age=22, # Young driver
        mileage_package="200km",
        insurance_tier="standard"
    )
    assert quote["is_young_driver"] is True
    # 65000 * 1.20 = 78000
    assert quote["adjusted_daily_rate"] == 78000
    assert quote["total_rent_rub"] == 78000

def test_quote_underage_rejected():
    car = database.get_car_by_slug("ferrari_f8")
    today = date.today()
    s_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    with pytest.raises(Exception):
        calculate_quote(car, s_date, s_date, driver_age=19)

def test_quote_duration_limit():
    car = database.get_car_by_slug("ferrari_f8")
    today = date.today()
    s_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    e_date = (today + timedelta(days=45)).strftime("%Y-%m-%d") # 45 days > 30 days
    with pytest.raises(Exception):
        calculate_quote(car, s_date, e_date, driver_age=30)

def test_availability_and_booking_collision():
    car = database.get_car_by_slug("mclaren_720s")
    s_date = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    e_date = (date.today() + timedelta(days=12)).strftime("%Y-%m-%d")

    # Initially free
    assert database.check_dates_availability(car["id"], s_date, e_date) is True

    # Book dates
    database.create_rental_booking({
        "car_id": car["id"],
        "client_name": "Test Driver",
        "phone": "+79991112233",
        "driver_age": 30,
        "start_date": s_date,
        "end_date": e_date,
        "rental_days": 3,
        "daily_rate_rub": car["daily_rate_rub"],
        "total_rent_rub": car["daily_rate_rub"] * 3,
        "deposit_rub": car["deposit_rub"]
    })

    # Now must NOT be available
    assert database.check_dates_availability(car["id"], s_date, e_date) is False

def test_api_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "APEX" in response.text

def test_api_cars_endpoint():
    response = client.get("/api/cars")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["fleet"]) == 5

def test_api_calculate_endpoint():
    today = date.today()
    payload = {
        "car_id": 1,
        "start_date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
        "end_date": (today + timedelta(days=4)).strftime("%Y-%m-%d"),
        "driver_age": 28,
        "mileage_package": "400km",
        "insurance_tier": "vip_shield"
    }
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["quote"]["rental_days"] == 2

def test_api_rentals_validation():
    # Empty client name
    res_bad = client.post("/api/rentals", json={
        "car_id": 1, "client_name": "", "phone": "", "driver_age": 25,
        "start_date": "2026-11-20", "end_date": "2026-11-21"
    })
    assert res_bad.status_code == 422

def test_bot_registration():
    bot, dp = create_bot_and_dispatcher()
    assert bot is not None
    assert dp is not None
    assert len(router.message.handlers) >= 1
    assert len(router.callback_query.handlers) >= 5
