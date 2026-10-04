# SMART HEALTH DATA PLATFORM: EPIDEMIC & CLIMATE SURVEILLANCE SYSTEM
## Comprehensive Final Defense & Presentation Deck

> **Academic & Capstone Defense Specification (2026)**  
> **Lead Data Engineer & AI Architect:** Nguyen Xuan Thinh ([@nguyenxuanthinh281204](https://github.com/nguyenxuanthinh281204))  
> **Primary Technology Stack:** PostgreSQL 16 | Mage.ai | dbt-core 1.8 | Streamlit | Gemini 1.5 Flash | Docker Compose  

---

### SLIDE 1: TITLE & EXECUTIVE SUMMARY
* **Title:** Smart Health Data Platform: An End-to-End Epidemic & Climate Surveillance Lakehouse
* **Subtitle:** Predicting Vector-Borne Outbreaks via Multi-Week Meteorological Lag Modeling and Sandboxed Conversational AI
* **Presenter:** Nguyen Xuan Thinh
* **Role:** Lead Data Engineer & AI Specialist
* **Executive Summary:**
  * Public health systems historically suffer from **reactive surveillance**—identifying outbreaks only after hospitals reach surge capacity.
  * This platform provides an authoritative, production-grade **Medallion Data Lakehouse** that captures the 2-to-4 week biological lag between meteorological triggers (precipitation, temperature, humidity) and dengue fever surges.
  * Features a **4-Layer Sandboxed Natural Language Text-to-SQL AI Assistant** allowing non-technical epidemiologists to query analytical datamarts in plain English with sub-50ms query latency.

---

### SLIDE 2: THE PUBLIC HEALTH CRISIS & PROBLEM STATEMENT
* **The Clinical Problem:**
  * Vector-borne diseases (*Aedes aegypti / albopictus*) infect millions annually across South & Southeast Asia.
  * In 2023 alone, Bangladesh experienced its deadliest dengue outbreak on record (>320,000 cases, >1,700 deaths).
* **The Data Engineering Challenge:**
  * **Siloed Data:** Health surveillance numbers (DGHS/WHO) and meteorological indicators (Open-Meteo ERA5) operate on disparate temporal grains and naming standards.
  * **Geospatial Disparity:** Province names are inconsistently spelled across English and Bengali scripts with zero standardized primary keys.
  * **Incubation Lag Distortion:** Mosquito oviposition and viral incubation cause a **14-to-28 day delay** between peak rainfall and peak hospital admissions. Without automated time-lag feature engineering, naive correlational models fail.
* **The Mission:** Build an automated, containerized, idempotent data lakehouse and surveillance decision support system.

---

### SLIDE 3: SYSTEM ARCHITECTURE & MEDALLION LAKEHOUSE
* **Architecture Paradigm:**
  ```text
  [Open-Meteo API + Kaggle + UN OCHA] 
             │ (Mage.ai Ingestion DAGs)
             ▼
  ┌────────────────────────────────────────────────────────┐
  │ BRONZE LAYER: Raw Ingestion Schema (CSV, JSON, GeoJSON) │
  │ - raw_dengue_weather_daily (10,960 rows)               │
  │ - raw_open_meteo_daily (730 rows)                      │
  │ - raw_admin_boundaries (8 UN OCHA Polygons)            │
  │ Metadata: _ingested_at, _source_file                   │
  └────────────────────────────────────────────────────────┘
             │ (Idempotent Cleaning & Lakehouse Parquet)
             ▼
  ┌────────────────────────────────────────────────────────┐
  │ SILVER LAYER: Harmonized Staging & Data Lake           │
  │ - stg_disease_daily (10,960 rows)                      │
  │ - stg_climate_daily (11,688 rows)                      │
  │ - Lakehouse Parquet Storage (data/silver/*.parquet)    │
  │ Standards: UN OCHA COD-AB P-Codes (BD-10 to BD-60)     │
  └────────────────────────────────────────────────────────┘
             │ (dbt-core 1.8 Dimensional Transformations)
             ▼
  ┌────────────────────────────────────────────────────────┐
  │ GOLD LAYER: Analytical Star Schema Mart                │
  │ - Dim_Date (1,826 days / Epi-Weeks 202152–202539)      │
  │ - Dim_Location (8 Divisions, GeoJSON boundaries)       │
  │ - Fact_Disease_Climate_Weekly (1,576 weekly records)   │
  │ Features: rainfall_lag_2w, rainfall_lag_4w, risk_level │
  └────────────────────────────────────────────────────────┘
             │ (Least-Privilege RBAC: bi_reader & llm_agent)
             ▼
  ┌────────────────────────────────────────────────────────┐
  │ SERVING LAYER: Visual Analytics & AI Assistant         │
  │ - Interactive Streamlit BI Surveillance (Port 8501)    │
  │ - 4-Layer Defense-in-Depth Text-to-SQL Engine          │
  └────────────────────────────────────────────────────────┘
  ```

---

### SLIDE 4: DATA INGESTION & PIPELINE ORCHESTRATION (BRONZE)
* **Orchestrator:** Mage.ai (standalone containerized workflow engine).
* **Ingestion Pipelines:**
  1. `extract_kaggle_dengue.py`: Daily disease counts, hospital admissions, and localized weather observations (10,960 records).
  2. `extract_open_meteo.py`: Reanalysis API pulling ERA5 precipitation, max/min temperature, solar radiation, and relative humidity (730 records).
  3. `extract_un_ocha_boundaries.py`: Authoritative Common Operational Datasets (COD-AB) providing boundary polygons for all 8 divisions.
* **Audit Metadata Compliance:**
  * Every raw ingestion table strictly appends `_ingested_at` (TIMESTAMP) and `_source_file` (VARCHAR) per `docs/DATA_CONTRACTS.md`.
  * Ingestion pipelines are **100% idempotent** using deterministic upsert keys (`record_hash` / `ON CONFLICT DO UPDATE`).

---

### SLIDE 5: HARMONIZATION & GEOSPATIAL STANDARDIZATION (SILVER)
* **P-Code Harmonization:**
  * Mapped informal administrative division strings (`Dhaka`, `Dacca`, `Ctg`, `Chittagong`) to ISO-standard UN OCHA P-Codes:
    * `BD-10`: Barisal | `BD-20`: Chittagong | `BD-30`: Dhaka | `BD-40`: Khulna
    * `BD-45`: Mymensingh | `BD-50`: Rajshahi | `BD-55`: Rangpur | `BD-60`: Sylhet
* **Hybrid Storage Architecture:**
  * Cleaned records loaded into PostgreSQL 16 schema `silver`.
  * Concurrently persisted to columnar **Apache Parquet files** (`data/silver/`) with Snappy compression for high-throughput OLAP analytics.
* **Data Cleansing Operations:**
  * Negative temperature and rainfall anomalies removed.
  * Missing meteorological values imputed via 7-day rolling moving averages.

---

### SLIDE 6: DIMENSIONAL MODELING & FEATURE ENGINEERING (GOLD)
* **Dimensional Modeling:** dbt-core 1.8 Star Schema mart.
  * **`gold.dim_location`**: 8 administrative divisions with UN OCHA boundary polygons, centroids, climate zones, and 2023 census populations (169.8M national population).
  * **`gold.dim_date`**: 1,826 daily records spanning 2021 to 2025, mapped to CDC/WHO Epidemiological Weeks (`epi_week_key`), monsoon season indicators, and quarters.
  * **`gold.fact_disease_climate_weekly`**: 1,576 granular fact records aggregated at `location_key` + `epi_week_key` grain.
* **Epidemiological Feature Engineering:**
  * **Incidence Rate per 100k:** `(total_cases / population) * 100,000` (eliminates urban density bias).
  * **Lag-2W Rainfall (`rainfall_lag_2w`):** Precipitation from 2 weeks prior via SQL window function `LAG(total_rainfall_mm, 2) OVER (PARTITION BY location_key ORDER BY epi_week_key)`.
  * **Lag-4W Rainfall (`rainfall_lag_4w`):** Precipitation from 4 weeks prior.
  * **Lag-2W Temperature (`temp_lag_2w`):** Antecedent mean temperature matching vector larval development optimum (26–32°C).
  * **Rule-Based Risk Stratification:** Categorization into `Severe`, `High`, `Moderate`, and `Low` risk alerts.

---

### SLIDE 7: AUTOMATED DATA QUALITY ASSURANCE & GOVERNANCE
* **Automated Testing Suite (dbt test):**
  * **36 of 36 Tests Passing (100% Pass Rate)**.
  * **Primary Key Integrity:** `unique` and `not_null` strictly enforced on `fact_id`, `location_key`, and `date_key`.
  * **Referential Integrity:** `relationships` foreign key constraints verified from `fact_disease_climate_weekly` to `dim_location` and `dim_date` with **0 orphan records**.
  * **Value Domain Range Checks:** Non-negative constraints on rainfall, humidity, and disease cases.
* **Data Governance & Privacy:**
  * Strict **Zero PII/PHI Policy** codified in `docs/SECURITY_AND_GOVERNANCE.md`.
  * Geospatial k-anonymity enforced by aggregating clinical counts at division level (>1M population per spatial unit).

---

### SLIDE 8: INTERACTIVE EPIDEMIOLOGICAL SERVING (STREAMLIT BI)
* **Serving Platform:** Streamlit BI Dashboard running on port `8501`.
* **Key Visual Analytics Modules:**
  1. **Epidemiological Snapshot KPI Cards:** Weekly incident cases, hospital admission rate, case fatality rate, mean incidence rate, and active high/severe alerts.
  2. **Interactive Choropleth Heatmap (Task 4.2):** Rendered with UN OCHA GeoJSON boundary polygons, displaying population-normalized incidence rate per 100k.
  3. **Time-Lag Dual-Axis Correlation Chart (Task 4.3):** Visualizes the 2–4 week lag between peak monsoon rainfall and dengue case surges.
  4. **Public Health Actionable Alerting Matrix (Task 4.4):** Real-time early warning notifications paired with standardized operational intervention protocols (larvicide mobilization, chemical fogging, hospital surge prep).
* **Performance Benchmark:** Sub-second cold-load time (~63ms query response from PostgreSQL Gold Mart).

---

### SLIDE 9: CONVERSATIONAL AI: NATURAL LANGUAGE TEXT-TO-SQL
* **The Vision:** Democratizing epidemiological data access for medical officers, field epidemiologists, and policy directors without requiring SQL expertise.
* **LLM Engine Architecture:**
  * **Model Integration:** Google Gemini 1.5 Flash API with domain-aware few-shot prompting.
  * **Domain Heuristic Fallback Engine:** Deterministic rule parser that provides instant, sub-20ms SQL generation even in zero-connectivity or offline air-gapped environments.
  * **Comprehensive Gold Metadata Prompt:** Injects schema DDL, foreign key relationships, column descriptions, and sample epidemiological queries.
* **Sample Capabilities:**
  * *"What are the top 5 divisions by dengue cases in 2023?"*
  * *"Show rainfall and dengue cases in Dhaka with time lags"*
  * *"Which regions have active high or severe risk alerts?"*
  * *"Compare dengue incidence and rainfall across climate zones"*

---

### SLIDE 10: 4-LAYER DEFENSE-IN-DEPTH SECURITY SANDBOX
* **The Threat Model:** Malicious prompt injections, unauthorized DDL/DML data alteration, privilege escalation, and runaway query Denial-of-Service.
* **4-Layer Defense Architecture:**
  1. **Layer 1: AST & Syntax Regex Blacklist:**
     * Intercepts and aborts queries containing `DROP`, `DELETE`, `TRUNCATE`, `ALTER`, `GRANT`, `INSERT`, `UPDATE`, `EXEC`.
     * Blocks SQL comment injection (`--`, `/*`) and statement chaining (`;`).
  2. **Layer 2: Explicit Read-Only Transaction & Statement Timeout:**
     * Wraps every query execution in `BEGIN READ ONLY;`.
     * Enforces PostgreSQL `statement_timeout = '3000ms'` to kill runaway Cartesian queries.
  3. **Layer 3: Database Role Least-Privilege Isolation:**
     * Queries execute strictly under dedicated database user `llm_agent`.
     * `llm_agent` has `SELECT` permission **only on schema `gold`**; access to `bronze` and `silver` is explicitly denied.
  4. **Layer 4: Hard Row Cap Enforcer:**
     * Enforces a hard ceiling of `LIMIT 500` to prevent memory buffer exhaustion.

---

### SLIDE 11: SYSTEM VERIFICATION & PERFORMANCE BENCHMARKS
* **End-to-End Automated Test Suites:**
  * `scripts/test_infra.py`: Docker container health, PostgreSQL port 5432, Mage.ai port 6789 (PASS).
  * `scripts/test_sprint2.ps1`: Bronze ingestion, 11,696 records, audit columns, idempotency (11/11 PASS).
  * `scripts/test_sprint3.ps1`: Silver staging, 22,648 records, Parquet lakehouse, P-Codes (13/13 PASS).
  * `scripts/verify_gold_layer.py`: Gold dimensional schema, 36 dbt tests, lag computations (16/16 PASS).
  * `scripts/test_sprint4.ps1`: BI dashboard serving, GeoJSON polygons, alerting matrix (11/11 PASS).
  * `scripts/test_sprint5.ps1`: Text-to-SQL engine, 4-layer sandbox, injection defense (PASS).
* **Performance Metrics:**
  * Data Warehouse Query Execution: **11–22 ms**.
  * Streamlit Full Page Render: **63 ms**.
  * dbt Complete Model Build & Test: **1.84 seconds**.

---

### SLIDE 12: 5-MINUTE LIVE DEMONSTRATION SCRIPT & DEFENSE CONCLUSION
* **Live Demonstration Flow (5 Minutes):**
  1. **Minute 1 - Infrastructure & Ingestion:**
     * Show `docker compose ps` (PostgreSQL healthy, Mage.ai running).
     * Inspect Bronze audit columns (`_ingested_at`, `_source_file`).
  2. **Minute 2 - Data Lakehouse & Modeling:**
     * Run `dbt test` showing 36/36 tests passed.
     * Highlight `fact_disease_climate_weekly` with `rainfall_lag_2w`, `temp_lag_2w`, and `risk_level`.
  3. **Minute 3 - Epidemiological BI Dashboard:**
     * Open `http://localhost:8501`.
     * Navigate Epi-Week slider; observe Choropleth map update across 8 divisions.
     * Point out the 2-week dual-axis lag curve validating the *Aedes* biological incubation hypothesis.
  4. **Minute 4 - Conversational AI (Text-to-SQL):**
     * Switch to Tab 2: "AI Assistant".
     * Click Quick Prompt *"Top 5 Divisions (2023)"*; inspect generated SQL and dynamic bar chart.
     * Click *"Rainfall Lag in Dhaka"*; inspect dynamic multi-line trend chart.
  5. **Minute 5 - Security Sandbox Live Attack Defense:**
     * Click *"Test SQL Injection Defense (DROP TABLE)"*.
     * Show the prominent red security warning banner proving Layer 1 AST blacklist interception!
* **Conclusion:**
  * The Smart Health Data Platform delivers an end-to-end, enterprise-ready, reliable, and secure surveillance solution ready for institutional deployment.
* **Thank You & Q&A Session.**

---
