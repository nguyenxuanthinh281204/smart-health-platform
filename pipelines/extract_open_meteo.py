#!/usr/bin/env python3
"""
==============================================================================
PIPELINE: EXTRACT OPEN-METEO WEATHER API DATASET (BRONZE LAYER)
==============================================================================
Task: 1.6 - Ingest Open-Meteo Meteorological Time-Series
Target Table: bronze.raw_open_meteo_daily
Specification: docs/DATA_CONTRACTS.md & docs/SECURITY_AND_GOVERNANCE.md
==============================================================================
"""

import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
import requests
import psycopg2
from psycopg2.extras import execute_batch, Json

OPEN_METEO_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Target Coordinates for Administrative Centroids
LOCATIONS = [
    {"location_key": "BD-10", "name": "Barisal", "lat": 22.7010, "long": 90.3535},
    {"location_key": "BD-20", "name": "Chittagong", "lat": 22.3569, "long": 91.7832},
    {"location_key": "BD-30", "name": "Dhaka", "lat": 23.8103, "long": 90.4125},
    {"location_key": "BD-40", "name": "Khulna", "lat": 22.8456, "long": 89.5403},
    {"location_key": "BD-50", "name": "Rajshahi", "lat": 24.3745, "long": 88.6042},
    {"location_key": "BD-55", "name": "Rangpur", "lat": 25.7439, "long": 89.2752},
    {"location_key": "BD-60", "name": "Sylhet", "lat": 24.8949, "long": 91.8687},
    {"location_key": "BD-45", "name": "Mymensingh", "lat": 24.7471, "long": 90.4203},
]

def fetch_open_meteo_weather(lat: float, lon: float, start_date: str, end_date: str, max_retries: int = 3) -> dict:
    """
    Fetches daily meteorological metrics from Open-Meteo Archive API
    with exponential backoff retry logic adhering to docs/SECURITY_AND_GOVERNANCE.md.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
            "relative_humidity_2m_mean"
        ],
        "timezone": "auto"
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait_time = attempt * 3
                print(f"[WARN] Rate-limited (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"[WARN] HTTP {response.status_code}: {response.text}")
        except requests.RequestException as e:
            wait_time = attempt * 2
            print(f"[WARN] Request error on attempt {attempt}: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            
    print(f"[ERROR] Failed to fetch data for lat={lat}, lon={lon} after {max_retries} attempts.")
    return {}

def get_db_connection():
    """Establishes connection to PostgreSQL warehouse."""
    return psycopg2.connect(
        dbname=os.environ.get("POSTGRES_DB", "smart_health_dw"),
        user=os.environ.get("POSTGRES_USER", "de_admin"),
        password=os.environ.get("POSTGRES_PASSWORD", "de_admin_secure_pass_2026"),
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", 5432))
    )

def run_extraction():
    print("\n[INFO] Starting Task 1.6 (Part 2): Open-Meteo ERA5 Reanalysis API Ingestion...")
    
    # Query sample window: Recent 90 days of high-fidelity meteorological data
    end_date_obj = date.today() - timedelta(days=5)  # ERA5 typically has 5-day latency
    start_date_obj = end_date_obj - timedelta(days=90)
    
    start_date_str = start_date_obj.strftime("%Y-%m-%d")
    end_date_str = end_date_obj.strftime("%Y-%m-%d")
    
    bronze_dir = os.environ.get("BRONZE_DATA_PATH", "/home/src/data/bronze")
    raw_payload_dir = os.path.join(bronze_dir, "open_meteo_raw")
    os.makedirs(raw_payload_dir, exist_ok=True)
    
    all_db_records = []
    ingested_at = datetime.now(timezone.utc)
    
    for loc in LOCATIONS:
        pcode = loc["location_key"]
        print(f"[INFO] Querying Open-Meteo ERA5 for {loc['name']} ({pcode}) [{start_date_str} to {end_date_str}]...")
        
        weather_json = fetch_open_meteo_weather(loc["lat"], loc["long"], start_date_str, end_date_str)
        if not weather_json or "daily" not in weather_json:
            continue
            
        # 1. Persist raw JSON payload into Bronze data lake
        payload_filename = f"open_meteo_{pcode}_{start_date_str}_{end_date_str}.json"
        payload_filepath = os.path.join(raw_payload_dir, payload_filename)
        with open(payload_filepath, "w", encoding="utf-8") as f:
            json.dump(weather_json, f, indent=2)
            
        daily = weather_json["daily"]
        dates = daily.get("time", [])
        temp_maxs = daily.get("temperature_2m_max", [])
        temp_mins = daily.get("temperature_2m_min", [])
        temp_means = daily.get("temperature_2m_mean", [])
        rainfalls = daily.get("precipitation_sum", [])
        humidities = daily.get("relative_humidity_2m_mean", [])
        
        for i, obs_date in enumerate(dates):
            all_db_records.append((
                pcode,
                obs_date,
                temp_maxs[i] if i < len(temp_maxs) else None,
                temp_mins[i] if i < len(temp_mins) else None,
                temp_means[i] if i < len(temp_means) else None,
                rainfalls[i] if i < len(rainfalls) else None,
                humidities[i] if i < len(humidities) else None,
                Json({"latitude": loc["lat"], "longitude": loc["long"], "elevation": weather_json.get("elevation")}),
                ingested_at,
                payload_filename
            ))
            
        time.sleep(0.5)  # Friendly politeness delay for public API
        
    print(f"[INFO] Total meteorological daily observations fetched: {len(all_db_records)}")
    
    if all_db_records:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert records into bronze.raw_open_meteo_daily
        insert_sql = """
            INSERT INTO bronze.raw_open_meteo_daily (
                location_key, observation_date, temp_max_c, temp_min_c,
                temp_mean_c, precipitation_sum_mm, relative_humidity_mean_pct,
                raw_payload, _ingested_at, _source_file
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        
        # Remove any existing rows for these location keys in this date range to remain idempotent
        location_keys = tuple(set(r[0] for r in all_db_records))
        cur.execute(
            "DELETE FROM bronze.raw_open_meteo_daily WHERE location_key IN %s AND observation_date BETWEEN %s AND %s;",
            (location_keys, start_date_str, end_date_str)
        )
        
        execute_batch(cur, insert_sql, all_db_records, page_size=1000)
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM bronze.raw_open_meteo_daily;")
        total_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        print(f"[SUCCESS] Ingested {len(all_db_records)} records into bronze.raw_open_meteo_daily.")
        print(f"[SUCCESS] Total records in bronze.raw_open_meteo_daily: {total_count}")
    else:
        print("[WARN] No records fetched from Open-Meteo API.")

if __name__ == "__main__":
    run_extraction()
