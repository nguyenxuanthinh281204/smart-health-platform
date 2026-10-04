# PROJECT CURRENT STATE (LIVING SNAPSHOT)

> **IMPORTANT NOTICE:**  
> This file serves as the **short-term memory (RAM)** of the project. Both the AI Agent and the Developer must update this document at the conclusion of each session to guarantee seamless context preservation.  
> **Last Updated:** 2026-10-04 (Initial Kick-off & Language Standardization)

---

## 1. CURRENT POSITION OVERVIEW
* **Active Milestone:** **Sprint 3: Data Warehouse & dbt Modeling (Gold Layer - Core Academic Focus)**
* **Overall Completion Rate:** ~60% (Sprint 1 & Sprint 2 Complete: Bronze & Silver layers operational, 22,648 silver records populated and verified)
* **Active Git Branch:** `main`
* **Primary Language:** **English** (All schemas, models, pipelines, and documentation)

---

## 2. RECENTLY COMPLETED TASKS
- [x] **Task 1.1 - 1.7 (Sprint 1 Complete):** Ingestion pipelines, Docker infrastructure, and Bronze storage (11,696 records across 3 raw tables).
- [x] **Task 2.1 (Idempotent Deduplication):**
  - Implemented deduplication logic on natural primary keys `(location_key, record_date, disease_type)` for disease surveillance and `(location_key, record_date)` for climate data.
  - Implemented PostgreSQL idempotent upsert logic with `ON CONFLICT DO UPDATE`.
- [x] **Task 2.2 (Wide-to-Long Reshaping):**
  - Standardized health metric columns into vertical long time-series format (`disease_type = 'DENGUE'`) adhering strictly to `silver.stg_disease_daily`.
- [x] **Task 2.3 (Geospatial Harmonization):**
  - Developed `pipelines/geospatial_harmonizer.py`: dynamically connects to `bronze.raw_admin_boundaries` and maps 100% of raw location variants (e.g. Dhaka, Chittagong, Barisal) to authoritative UN OCHA P-Codes (`BD-10` to `BD-60`).
- [x] **Task 2.4 (Meteorological Data Imputation):**
  - Implemented `pipelines/transform_silver_climate.py`: forward-fill and backward-fill for temperature metrics, 7-day rolling average for humidity, rainfall coalesced to 0.0, seasonal atmospheric interpolation for PM2.5, and standard US EPA formula for AQI calculation. Result: Zero null gaps across all 7 weather features.
- [x] **Task 2.5 (Silver Persistence & Contracts):**
  - Created DDL migration `docker/create_silver_tables.sql` enforcing primary keys, value checks, indexes, and Least Privilege RBAC.
  - Saved Parquet lakehouse files in `data/silver/stg_disease_daily.parquet` (10,960 records) and `data/silver/stg_climate_daily.parquet` (11,688 records).
  - Populated PostgreSQL `silver.stg_disease_daily` and `silver.stg_climate_daily`.
  - Authored and verified `scripts/verify_silver_layer.py`: passed 11/11 tests (uniqueness, referential integrity, zero nulls, Parquet integrity, RBAC isolation for `bi_reader` and `llm_agent`).

---

## 3. NEXT IMMEDIATE STEPS (SPRINT 3: GOLD LAYER & DBT MODELING)

When initiating the next working session, the AI must execute the following sequential tasks:

1. **Task 3.1: Initialize dbt Project**
   - Initialize dbt project under `dbt_transforms/` with `dbt-postgres` profile targeting `smart_health_dw`.
2. **Task 3.2: Build Dimension Models (`Dim_Date` & `Dim_Location`)**
   - `gold.dim_date`: Calendar date, ISO-8601 Epi-week (`to_char(record_date, 'IYYYIW')::integer`), quarter, month, monsoon flag.
   - `gold.dim_location`: P-Code primary key, division name, centroid coordinates, population, boundary GeoJSON polygon from `bronze.raw_admin_boundaries`.
3. **Task 3.3: Build Fact Table (`Fact_Disease_Climate_Weekly`)**
   - Aggregate daily silver metrics into Epi-week grain: 1 record per `(location_key, epi_week_key)`.
   - Aggregate weekly disease sums (cases, hospitalizations, deaths) and weekly climate indicators (mean temp, cumulative rain, mean humidity, mean AQI, PM2.5).
4. **Task 3.4: Implement Advanced dbt Window Functions & Feature Engineering**
   - Population-normalized incidence rate per 100,000: `(new_cases / population) * 100,000`.
   - 2-week and 4-week precipitation lags: `rainfall_lag_2w`, `rainfall_lag_4w`.
   - 2-week mean temperature lag: `temp_lag_2w`.
   - Multi-factor risk stratification matrix (`Severe`, `High`, `Moderate`, `Low`) per `docs/DOMAIN_RULES_AND_METRICS.md`.

---

## 4. TARGET ENVIRONMENT SPECIFICATIONS
* **Database:** PostgreSQL 16 (DB: `smart_health_dw`, User: `de_admin`, Port: `5432`)
* **Orchestrator:** Mage.ai (Port: `6789`)
* **Transformation Engine:** dbt-core (Target: `dev` mapped to PostgreSQL)
* **Serving / UI:** Streamlit (Port: `8501`) / Looker Studio

---

## 5. TECHNICAL PITFALLS & MITIGATION STRATEGIES
* **Temporal Granularity Mismatch:** Climate data is collected hourly/daily; epidemiological surveillance reports are weekly (Epi-week). All daily metrics must be rolled up to the **Epi-week** grain before joining with the Fact table.
* **Geospatial Referential Integrity:** Strict enforcement of UN OCHA administrative P-Codes as foreign keys linking `Dim_Location` to `Fact_Disease_Climate_Weekly`.

