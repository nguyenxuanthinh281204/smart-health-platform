# PROJECT CURRENT STATE (LIVING SNAPSHOT)

> **IMPORTANT NOTICE:**  
> This file serves as the **short-term memory (RAM)** of the project. Both the AI Agent and the Developer must update this document at the conclusion of each session to guarantee seamless context preservation.  
> **Last Updated:** 2026-10-04 (Sprint 3: Gold Layer & dbt Transformations Complete)

---

## 1. CURRENT POSITION OVERVIEW
* **Active Milestone:** **Sprint 4: Serving Layer & Interactive BI Dashboards**
* **Overall Completion Rate:** ~80% (Sprint 1, 2, and 3 Complete: Full Medallion Architecture Bronze -> Silver -> Gold active and verified)
* **Active Git Branch:** `main`
* **Primary Language:** **English** (All schemas, models, pipelines, and documentation)

---

## 2. RECENTLY COMPLETED TASKS
- [x] **Task 1.1 - 1.7 (Sprint 1 Complete):** Ingestion pipelines, Docker infrastructure, and Bronze storage (11,696 records across 3 raw tables).
- [x] **Task 2.1 - 2.5 (Sprint 2 Complete):** Silver data cleansing, deduplication, wide-to-long reshaping, P-Code harmonization, meteorological imputation (22,648 silver records populated and verified).
- [x] **Task 3.1 (dbt Initialization & Profile):**
  - Configured `dbt_project.yml` and `profiles.yml` targeting PostgreSQL `smart_health_dw` inside `smart_health_mageai` with `dbt-postgres 1.8.2`.
  - Configured custom `generate_schema_name` macro to cleanly route models into `gold.*`.
- [x] **Task 3.2 (Dimension Models):**
  - Built `gold.dim_location`: 8 administrative division records with UN OCHA P-Codes, coordinates, population, and GeoJSON boundary polygons.
  - Built `gold.dim_date`: 1,826 daily calendar records (2022 to 2026) mapped to ISO-8601 Epidemiological weeks (`YYYYWW`), quarters, and monsoon season flags.
- [x] **Task 3.3 (Analytical Fact Table):**
  - Built `gold.fact_disease_climate_weekly`: 1,576 records rolled up to the canonical `(location_key, epi_week_key, disease_type)` grain across 197 consecutive surveillance weeks.
- [x] **Task 3.4 (Advanced Feature Engineering & Window Functions):**
  - Population-normalized incidence rate per 100,000 population: `(total_cases / population) * 100,000`.
  - Time-lag features calculated via SQL window functions: `rainfall_lag_2w`, `rainfall_lag_4w`, `temp_lag_2w`.
  - Implemented 4-tier risk stratification matrix (`Severe`, `High`, `Moderate`, `Low`) adhering to `docs/DOMAIN_RULES_AND_METRICS.md`.
- [x] **Task 3.5 (Automated dbt Testing):**
  - Defined 33 rigorous schema tests (`unique`, `not_null`, `relationships`, `accepted_values`).
  - Executed `dbt build`: **36/36 passed** (3 models created, 33 tests passed, 0 failures).
- [x] **Task 3.6 (Data Documentation & Lineage):**
  - Compiled full documentation catalog and dependency graph via `dbt docs generate` (`catalog.json` & `manifest.json`).
  - Enforced Least Privilege RBAC: `bi_reader` and `llm_agent` granted `SELECT` access to `gold.*`.

---

## 3. NEXT IMMEDIATE STEPS (SPRINT 4: BI DASHBOARDS & SERVING LAYER)

When initiating the next working session, the AI must execute the following sequential tasks:

1. **Task 4.1: Connect Gold Layer Mart to Serving / BI Tooling**
   - Configure Streamlit application in `bi_dashboard/` or Looker Studio connector querying `gold.fact_disease_climate_weekly` and `gold.dim_location` via `bi_reader` credentials.
2. **Task 4.2: Build Interactive Epidemiological Choropleth Map**
   - Render division polygons colored by `incidence_rate_per_100k` and categorized by `risk_level` (Red, Orange, Yellow, Green).
   - Add dynamic filters: Epidemiological Week slider, Disease Type selector, Climate Zone filter.
3. **Task 4.3: Design Time-Lag Dual-Axis Correlation Visualizations**
   - Visualizing the 2–4 week incubation lag between peak rainfall events and clinical dengue hospitalization surges.
4. **Task 4.4: Build Public Health Actionable Alerting Matrix**
   - Early warning alert board displaying operational recommendations (Targeted fogging, larvicide deployment, clinic pre-positioning) per `docs/DOMAIN_RULES_AND_METRICS.md`.

---

## 4. TARGET ENVIRONMENT SPECIFICATIONS
* **Database:** PostgreSQL 16 (DB: `smart_health_dw`, User: `de_admin`, Port: `5432`)
* **Orchestrator:** Mage.ai (Port: `6789`)
* **Transformation Engine:** dbt-core 1.8.7 / dbt-postgres 1.8.2
* **Serving / UI:** Streamlit (Port: `8501`) / Looker Studio

---

## 5. TECHNICAL PITFALLS & MITIGATION STRATEGIES
* **Temporal Granularity Mismatch:** Climate data is collected hourly/daily; epidemiological surveillance reports are weekly (Epi-week). All daily metrics must be rolled up to the **Epi-week** grain before joining with the Fact table.
* **Geospatial Referential Integrity:** Strict enforcement of UN OCHA administrative P-Codes as foreign keys linking `Dim_Location` to `Fact_Disease_Climate_Weekly`.
