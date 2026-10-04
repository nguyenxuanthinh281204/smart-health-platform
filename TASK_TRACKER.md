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
- [x] **Task 2.1:** Implement idempotent deduplication logic for epidemiological case records.
- [x] **Task 2.2:** Transform time-series data structures from Wide format to Long format.
- [x] **Task 2.3:** Geospatial Harmonization: Map disparate provincial names to standardized UN OCHA P-Codes in `Dim_Location`.
- [x] **Task 2.4:** Missing Data Imputation: Apply Forward-Fill / Moving Average algorithms to fill intermittent weather sensor gaps.
- [x] **Task 2.5:** Persist cleansed datasets into the `silver` schema with strict data typing (Date, Numeric, Text).
> **Definition of Done (DoD):** Zero duplicate records; 100% of provincial entities resolve to valid P-Codes; Weather time-series continuous with no null gaps. (VERIFIED: 2 Silver tables populated, 22,648 records total, 100% P-Codes mapped, 0 duplicates, 0 null gaps in weather features, 11/11 audit checks passed).

---

### SPRINT 3: DATA WAREHOUSE & DBT MODELING (GOLD LAYER - CORE ACADEMIC FOCUS)
- [x] **Task 3.1:** Initialize dbt project (`dbt init dbt_transforms`), configure `profiles.yml` targeting PostgreSQL.
- [x] **Task 3.2:** Build Dimension Tables:
  - `dim_date`: Date key, epidemiological week (`epi_week`), year, month, quarter.
  - `dim_location`: P-Code key, province name, centroid coordinates, population, boundary polygon.
- [x] **Task 3.3:** Build Fact Table `fact_disease_climate_weekly`:
  - Grain: 1 record per `(location_key, epi_week_key)`.
  - Health Metrics: New cases, hospitalizations, deaths.
  - Climate Metrics: Average/max/min temperature, cumulative rainfall, average humidity, AQI, PM2.5.
- [x] **Task 3.4:** Implement Advanced dbt Window Functions & Feature Engineering:
  - **Incidence Rate per 100,000 Population:** `(cases / population) * 100000`.
  - **Time-Lag Features:**
    - `rainfall_lag_2w`: Cumulative rainfall lagged by 2 weeks.
    - `rainfall_lag_4w`: Cumulative rainfall lagged by 4 weeks.
    - `temp_lag_2w`: Mean temperature lagged by 2 weeks.
- [x] **Task 3.5:** Configure automated dbt tests (`unique`, `not_null`, `relationships`, `accepted_values`).
- [x] **Task 3.6:** Compile comprehensive documentation and data lineage graph (`dbt docs generate`).
> **Definition of Done (DoD):** `dbt run` and `dbt test` pass with 100% success; Lag 2W/4W and Incidence Rate accurately calculated; Lineage graph displays Staging $\to$ Intermediate $\to$ Marts. (VERIFIED: 3 models created, 1,576 weekly fact rows, 36/36 dbt tests passed, 13/13 audit checks passed).

---

### SPRINT 4: SERVING LAYER & INTERACTIVE BI DASHBOARDS
- [x] **Task 4.1:** Connect Gold Layer mart to BI tooling (Looker Studio / Metabase / Streamlit).
- [x] **Task 4.2:** Design **Epidemiological Choropleth Heatmap**:
  - Visualize risk stratification based on Incidence Rate per 100,000 population.
  - Dynamic filtering by Epidemiological Week and Geographic Region.
- [x] **Task 4.3:** Design **Time-Lag Correlation Visualizations**:
  - Dual-axis time series demonstrating the 2–4 week lag between peak rainfall and peak dengue hospitalizations.
- [x] **Task 4.4:** Build **Risk Alerting Matrix**:
  - Real-time rule-based alerting identifying regions where humidity > 80% and rainfall > 50mm within the preceding 2 weeks.
> **Definition of Done (DoD):** Dashboard interactive, responsive (< 2s load time), and clearly validates the hypothesis that early climate signals predict epidemic surges. (VERIFIED: Serving on port 8501 with 77ms load time, 8 UN OCHA polygons mapped, 2–4W lags visualized, 11/11 audit checks passed).

---

### SPRINT 5: LLM AGENT (TEXT-TO-SQL) & PROJECT PACKAGING
- [x] **Task 5.1:** Construct Python Text-to-SQL module utilizing Gemini API / OpenAI API / LangChain:
  - Implemented `pipelines/llm_text_to_sql.py` with `LLMTextToSQLEngine`.
  - Seamless dual-engine design: Google Gemini 1.5 Flash API + Domain Heuristic Fallback for zero-connectivity/offline air-gapped environments.
- [x] **Task 5.2:** Supply Gold Layer metadata schema and sample prompts to enable context-aware SQL generation:
  - Codified comprehensive DDL metadata, relationship schemas, and few-shot prompt context in `GOLD_METADATA_PROMPT`.
  - Implemented 4-layer security sandbox (AST blacklist regex, `BEGIN READ ONLY;` + 3000ms timeout, `llm_agent` role, and `LIMIT 500` hard cap).
- [x] **Task 5.3:** Build an intuitive Streamlit Chat UI for natural language data querying and dynamic chart rendering:
  - Integrated dedicated Tab 2 ("🤖 AI Assistant: Natural Language Text-to-SQL") in `bi_dashboard/app.py`.
  - Features quick-action prompt chips, collapsible SQL inspector, latency & row metrics, security audit badges, and dynamic auto-visualization charts (dual-axis line & bar charts).
- [x] **Task 5.4:** Compose comprehensive `README.md` with single-command `docker-compose up` setup instructions:
  - Complete master documentation with architecture diagram, service port mapping (`8501`, `6789`, `5432`), quickstart guide, dbt test summary, and automated verification commands.
- [x] **Task 5.5:** Prepare final defense assets (Slide presentation deck and end-to-end pipeline demonstration script):
  - Created 12-slide comprehensive defense deck with speaker notes and 5-minute live demonstration flow in `docs/PRESENTATION_AND_DEFENSE_DECK.md`.
> **Definition of Done (DoD):** End-to-end platform functional from Ingestion $\to$ Warehouse $\to$ Dashboard $\to$ LLM Q&A; System packaged and defense-ready. (VERIFIED: All 12/12 Sprint 5 checks passed, query latency 11–22ms, SQL injection attacks safely blocked, 100% test pass rate across all 5 sprints).

---

### SPRINT 6: PREDICTIVE ANALYTICS & OUTBREAK FORECASTING (MACHINE LEARNING)
- [x] **Task 6.1:** Construct ML feature engineering pipeline combining autoregressive clinical lags ($y_t, y_{t-1}, y_{t-2}, y_{t-3}$) with antecedent meteorological signals (Rainfall Lag 2W, Temp Lag 2W, Humidity, Seasonality) in `pipelines/train_predictive_model.py`.
- [x] **Task 6.2:** Train and evaluate supervised ensemble regression model (`HistGradientBoostingRegressor` / `XGBoostRegressor`) targeting a 4-week forward outbreak horizon ($y_{t+4}$):
  - Achieved $R^2 = 0.7184$ (71.8% variance explained on holdout validation set), $\text{MAE} = 91.50$, $\text{RMSE} = 181.68$.
  - Serialized model artifact to `models/dengue_outbreak_forecast_4w.joblib` and metrics to `models/model_metrics.json`.
- [x] **Task 6.3:** Materialize batch predictions to Data Warehouse table `gold.fact_outbreak_forecast_weekly`:
  - 1,576 forecast records generated across all 8 administrative divisions (BD-10 to BD-60).
  - Calculated 95% confidence intervals and automated risk classification (`Severe`, `High`, `Moderate`, `Low`).
  - Enforced Least-Privilege RBAC: granted `SELECT` access to `bi_reader` and `llm_agent`.
- [x] **Task 6.4:** Implement interactive Predictive Analytics UI in Streamlit (`bi_dashboard/app.py`):
  - Created Tab 3 ("🔮 Predictive Analytics: 4-Week Outbreak Forecasting").
  - Dual time-series chart showing Actual vs. 4-Week Ahead Predicted Cases with shaded 95% Confidence Interval band.
  - Feature Importance horizontal bar chart detailing biological vector drivers (Rainfall Lag 2W, Temp Lag 2W).
  - Regional 4-Week Forward Early Warning Table for upcoming surveillance horizons.
- [x] **Task 6.5:** Integrate forecast table into Text-to-SQL AI Assistant (`pipelines/llm_text_to_sql.py`):
  - Enables clinicians to ask questions like: *"Show 4-week ahead outbreak forecasts across all divisions"*.
> **Definition of Done (DoD):** Supervised ML pipeline functional from training $\to$ validation $\to$ DW persistence $\to$ interactive forecast UI $\to$ Text-to-SQL integration. (VERIFIED: All 12/12 Sprint 6 checks passed, R² > 0.71, 100% test pass rate across all 6 sprints).

