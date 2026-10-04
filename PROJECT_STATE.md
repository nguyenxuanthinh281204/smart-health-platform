# PROJECT CURRENT STATE (LIVING SNAPSHOT)

> **IMPORTANT NOTICE:**  
> This file serves as the **short-term memory (RAM)** of the project. Both the AI Agent and the Developer must update this document at the conclusion of each session to guarantee seamless context preservation.  
> **Last Updated:** 2026-10-04 (Initial Kick-off & Language Standardization)

---

## 1. CURRENT POSITION OVERVIEW
* **Active Milestone:** **Sprint 2: Data Cleansing, Harmonization & Silver Layer**
* **Overall Completion Rate:** ~40% (Sprint 1 Complete: Infrastructure online, 3 Bronze datasets ingested with 11,696 records)
* **Active Git Branch:** `main`
* **Primary Language:** **English** (All schemas, models, pipelines, and documentation)

---

## 2. RECENTLY COMPLETED TASKS
- [x] **Task 1.1:** Synthesized project requirements, architectures, and 10 verified datasets.
- [x] **Task 1.2:** Deployed Zero Context Loss AI Operating Framework in English (`AGENTS.md`, `ROADMAP.md`, `DATA_CONTRACTS.md`, `DOMAIN_RULES_AND_METRICS.md`, `SECURITY_AND_GOVERNANCE.md`, `NAMING_CONVENTIONS.md`, `USE_CASES_AND_ACTORS.md`).
- [x] **Task 1.3 (Repository Scaffolding):** Initialized layout (`docker/`, `data/bronze/`, `data/silver/`, `data/gold/`, `pipelines/`, `dbt_transforms/`, `bi_dashboard/`).
- [x] **Task 1.4 (Containerization & Initialization):** Authored `docker/docker-compose.yml`, `docker/init_db.sql` (Medallion schemas, RBAC roles `de_admin`, `bi_reader`, `llm_agent`), `.env.example`, and `.env`.
- [x] **Task 1.5 (UN OCHA Boundary Ingestion):** Ingested master administrative division boundaries (GeoJSON polygon, centroid lat/long, population, P-Codes) into `bronze.raw_admin_boundaries` (8 divisions).
- [x] **Task 1.6 & Task 1.7 (Dengue & Climate Ingestion into Bronze):**
  - Implemented `pipelines/extract_dengue_weather.py`: Ingested 10,960 daily surveillance records into `bronze.raw_dengue_weather_daily`.
  - Implemented `pipelines/extract_open_meteo.py`: Polled real Open-Meteo ERA5 API and ingested 728 daily meteorological records into `bronze.raw_open_meteo_daily`.
  - Successfully verified audit columns (`_ingested_at`, `_source_file`) across all 3 raw tables.

---

## 3. NEXT IMMEDIATE STEPS (SPRINT 2: SILVER LAYER)

When initiating the next working session, the AI must execute the following sequential tasks:

1. **Task 2.1: Deduplication Pipeline for Health Records**
   - Implement deduplication logic ensuring only distinct `(record_date, location_key, disease_type)` combinations pass to Silver.
2. **Task 2.2: Time-Series Reshaping (Wide-to-Long)**
   - Reshape wide temporal structures into vertical records adhering to `silver.stg_disease_daily` in `docs/DATA_CONTRACTS.md`.
3. **Task 2.3: Geospatial Harmonization (P-Code Mapping)**
   - Standardize location names to UN OCHA P-Codes using fuzzy lookup against `bronze.raw_admin_boundaries`.
4. **Task 2.4: Meteorological Data Imputation**
   - Apply forward-fill and rolling averages for missing sensor values into `silver.stg_climate_daily`.

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
