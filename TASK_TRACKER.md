# PROJECT TASK TRACKER & WORK BREAKDOWN STRUCTURE (WBS)

> **User Guidelines:**
> * Status Legend: `[ ]` Not Started | `[/]` In Progress | `[x]` Completed | `[!]` Blocked.
> * Both AI and Developer must update this file whenever an item reaches completion.
> * Primary Language: **English**.

---

## SPRINT ROADMAP SUMMARY

| Sprint | Focus Area | Key Deliverable | Status |
| :---: | :--- | :--- | :---: |
| **Sprint 1** | Container Infrastructure & Raw Ingestion | Docker operational, Bronze Layer raw data ingested | `[x]` Completed |
| **Sprint 2** | Data Cleansing, Harmonization & Silver Layer | Deduplication, Wide-to-Long, P-Code standardization | `[/]` In Progress |
| **Sprint 3** | Data Warehouse & dbt Modeling (Gold Layer) | Star Schema, dbt models, Lag 2-4W, Incidence Rate | `[ ]` Pending |
| **Sprint 4** | Serving Layer & Interactive BI Dashboard | Looker Studio / Streamlit Choropleth Map & Trends | `[ ]` Pending |
| **Sprint 5** | LLM Text-to-SQL Agent & Project Handover | Natural language querying, presentation deck & demo | `[ ]` Pending |

---

## DETAILED TASK BREAKDOWN

### SPRINT 1: CONTAINER INFRASTRUCTURE & RAW INGESTION (BRONZE LAYER)
- [x] **Task 1.1:** Synthesize project requirements from technical documentation and 10 data source references.
- [x] **Task 1.2:** Deploy Zero Context Loss AI Operating Framework in English.
- [x] **Task 1.3:** Initialize standardized Data Engineering repository directory structure.
- [x] **Task 1.4:** Author `docker-compose.yml` (PostgreSQL 16, Mage.ai/Prefect, persistent volume bindings, health checks).
- [x] **Task 1.5:** Ingest UN OCHA Geospatial Administrative Boundaries (GeoJSON / P-Code master file).
- [x] **Task 1.6:** Implement automated Python ingestion scripts for Dengue & Climate data (Kaggle & Open-Meteo API).
- [x] **Task 1.7:** Land raw datasets into PostgreSQL `bronze` schema with audit columns (`_ingested_at`, `_source_file`).
> **Definition of Done (DoD):** Docker Compose boots up cleanly; Database connectivity verified; At least 2 core raw datasets successfully populated in the `bronze` schema. (VERIFIED: 3 tables, 11,696 records populated).

---

### SPRINT 2: DATA CLEANSING, HARMONIZATION & SILVER LAYER
- [ ] **Task 2.1:** Implement idempotent deduplication logic for epidemiological case records.
- [ ] **Task 2.2:** Transform time-series data structures from Wide format to Long format.
- [ ] **Task 2.3:** Geospatial Harmonization: Map disparate provincial names to standardized UN OCHA P-Codes in `Dim_Location`.
- [ ] **Task 2.4:** Missing Data Imputation: Apply Forward-Fill / Moving Average algorithms to fill intermittent weather sensor gaps.
- [ ] **Task 2.5:** Persist cleansed datasets into the `silver` schema with strict data typing (Date, Numeric, Text).
> **Definition of Done (DoD):** Zero duplicate records; 100% of provincial entities resolve to valid P-Codes; Weather time-series continuous with no null gaps.

---

### SPRINT 3: DATA WAREHOUSE & DBT MODELING (GOLD LAYER - CORE ACADEMIC FOCUS)
- [ ] **Task 3.1:** Initialize dbt project (`dbt init dbt_transforms`), configure `profiles.yml` targeting PostgreSQL.
- [ ] **Task 3.2:** Build Dimension Tables:
  - `dim_date`: Date key, epidemiological week (`epi_week`), year, month, quarter.
  - `dim_location`: P-Code key, province name, centroid coordinates, population, boundary polygon.
- [ ] **Task 3.3:** Build Fact Table `fact_disease_climate_weekly`:
  - Grain: 1 record per `(location_key, epi_week_key)`.
  - Health Metrics: New cases, hospitalizations, deaths.
  - Climate Metrics: Average/max/min temperature, cumulative rainfall, average humidity, AQI, PM2.5.
- [ ] **Task 3.4:** Implement Advanced dbt Window Functions & Feature Engineering:
  - **Incidence Rate per 100,000 Population:** `(cases / population) * 100000`.
  - **Time-Lag Features:**
    - `rainfall_lag_2w`: Cumulative rainfall lagged by 2 weeks.
    - `rainfall_lag_4w`: Cumulative rainfall lagged by 4 weeks.
    - `temp_lag_2w`: Mean temperature lagged by 2 weeks.
- [ ] **Task 3.5:** Configure automated dbt tests (`unique`, `not_null`, `relationships`, `accepted_values`).
- [ ] **Task 3.6:** Compile comprehensive documentation and data lineage graph (`dbt docs generate`).
> **Definition of Done (DoD):** `dbt run` and `dbt test` pass with 100% success; Lag 2W/4W and Incidence Rate accurately calculated; Lineage graph displays Staging $\to$ Intermediate $\to$ Marts.

---

### SPRINT 4: SERVING LAYER & INTERACTIVE BI DASHBOARDS
- [ ] **Task 4.1:** Connect Gold Layer mart to BI tooling (Looker Studio / Metabase / Streamlit).
- [ ] **Task 4.2:** Design **Epidemiological Choropleth Heatmap**:
  - Visualize risk stratification based on Incidence Rate per 100,000 population.
  - Dynamic filtering by Epidemiological Week and Geographic Region.
- [ ] **Task 4.3:** Design **Time-Lag Correlation Visualizations**:
  - Dual-axis time series demonstrating the 2–4 week lag between peak rainfall and peak dengue hospitalizations.
- [ ] **Task 4.4:** Build **Risk Alerting Matrix**:
  - Real-time rule-based alerting identifying regions where humidity > 80% and rainfall > 50mm within the preceding 2 weeks.
> **Definition of Done (DoD):** Dashboard interactive, responsive (< 2s load time), and clearly validates the hypothesis that early climate signals predict epidemic surges.

---

### SPRINT 5: LLM AGENT (TEXT-TO-SQL) & PROJECT PACKAGING
- [ ] **Task 5.1:** Construct Python Text-to-SQL module utilizing Gemini API / OpenAI API / LangChain.
- [ ] **Task 5.2:** Supply Gold Layer metadata schema and sample prompts to enable context-aware SQL generation.
- [ ] **Task 5.3:** Build an intuitive Streamlit Chat UI for natural language data querying and dynamic chart rendering.
- [ ] **Task 5.4:** Compose comprehensive `README.md` with single-command `docker-compose up` setup instructions.
- [ ] **Task 5.5:** Prepare final defense assets (Slide presentation deck and end-to-end pipeline demonstration video).
> **Definition of Done (DoD):** End-to-end platform functional from Ingestion $\to$ Warehouse $\to$ Dashboard $\to$ LLM Q&A; System packaged and defense-ready.
