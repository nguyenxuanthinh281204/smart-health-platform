# PROJECT CURRENT STATE (LIVING SNAPSHOT)

> **IMPORTANT NOTICE:**  
> This file serves as the **short-term memory (RAM)** of the project. Both the AI Agent and the Developer must update this document at the conclusion of each session to guarantee seamless context preservation.  
> **Last Updated:** 2026-10-04 (Sprint 4: Serving Layer & BI Dashboards Complete)

---

## 1. CURRENT POSITION OVERVIEW
* **Active Milestone:** **Sprint 5: LLM Agent (Text-to-SQL) & Final Delivery Packaging**
* **Overall Completion Rate:** ~90% (Sprint 1, 2, 3, and 4 Complete: Full End-to-End Pipeline Ingestion -> Cleansing -> Star Schema Mart -> Serving BI Dashboard operational)
* **Active Git Branch:** `main`
* **Primary Language:** **English** (All schemas, models, pipelines, and documentation)

---

## 2. RECENTLY COMPLETED TASKS
- [x] **Task 1.1 - 1.7 (Sprint 1 Complete):** Ingestion pipelines, Docker infrastructure, and Bronze storage (11,696 records across 3 raw tables).
- [x] **Task 2.1 - 2.5 (Sprint 2 Complete):** Silver data cleansing, deduplication, wide-to-long reshaping, P-Code harmonization, meteorological imputation (22,648 silver records populated and verified).
- [x] **Task 3.1 - 3.6 (Sprint 3 Complete):** dbt dimensional models (`dim_location`, `dim_date`, `fact_disease_climate_weekly`), time-lag window functions, risk matrix, 36/36 tests passed, documentation catalog generated.
- [x] **Task 4.1 (Gold Layer BI Connection):**
  - Connected visual serving layer to PostgreSQL `smart_health_dw` strictly via `bi_reader` role conforming to Least Privilege access control.
  - Exposed HTTP dashboard endpoint on port `8501` with lightning-fast `77ms` load time (< 2s DoD requirement).
- [x] **Task 4.2 (Interactive Epidemiological Choropleth Heatmap):**
  - Built interactive Mapbox choropleth mapping 8 UN OCHA division boundaries (`geom_polygon`), styled dynamically by 4-tier risk stratification (`Severe`, `High`, `Moderate`, `Low`) and population-normalized incidence rates.
- [x] **Task 4.3 (Time-Lag Dual-Axis Correlation Visualizations):**
  - Visualized the biological vector incubation dynamic: dual-axis charts overlaying weekly precipitation and 2–4 week lag indicators against clinical hospitalization surges.
- [x] **Task 4.4 (Public Health Actionable Alerting Matrix):**
  - Integrated rule-based early warning matrix triggering alerts when antecedent rainfall lag > 50mm and humidity > 80% coincide with emerging cases.
  - Linked active alerts to standardized vector eradication operational interventions (ULV fogging, Abate larvicide, clinic pre-positioning) per `docs/DOMAIN_RULES_AND_METRICS.md`.

---

## 3. NEXT IMMEDIATE STEPS (SPRINT 5: LLM AGENT & FINAL PACKAGING)

When initiating the next working session, the AI must execute the following sequential tasks:

1. **Task 5.1: Text-to-SQL AI Module**
   - Construct natural language SQL generator using Gemini API / OpenAI API / LangChain querying `gold.*` via sandboxed `llm_agent` credentials (read-only, execution timeout).
2. **Task 5.2: Supply Metadata Context & Few-Shot Prompts**
   - Embed Gold Layer Star Schema data dictionary and domain rules into system prompts for high-accuracy SQL generation.
3. **Task 5.3: Streamlit Natural Language Chat UI**
   - Build an intuitive conversational interface in `bi_dashboard/` where public health analysts ask questions in natural language and receive formatted data tables and dynamic Plotly charts.
4. **Task 5.4: Production Packaging & Documentation**
   - Author authoritative root `README.md` with single-command `docker compose up -d` quickstart guide, architecture diagrams, and pipeline verification instructions.
5. **Task 5.5: Final Defense Artifacts**
   - Compile slide presentation outline and end-to-end demonstration scripts.

---

## 4. TARGET ENVIRONMENT SPECIFICATIONS
* **Database:** PostgreSQL 16 (DB: `smart_health_dw`, Port: `5432`)
* **Orchestrator:** Mage.ai (Port: `6789`)
* **BI Dashboard Serving:** Streamlit / Plotly Standalone (Port: `8501`)
* **Transformation Engine:** dbt-core 1.8.7 / dbt-postgres 1.8.2
* **RBAC Roles:** `de_admin` (Full), `bi_reader` (Gold Read-Only), `llm_agent` (Gold Sandboxed Read-Only)

---

## 5. TECHNICAL PITFALLS & MITIGATION STRATEGIES
* **Temporal Granularity Mismatch:** Climate data is collected hourly/daily; epidemiological surveillance reports are weekly (Epi-week). All daily metrics must be rolled up to the **Epi-week** grain before joining with the Fact table.
* **Geospatial Referential Integrity:** Strict enforcement of UN OCHA administrative P-Codes as foreign keys linking `Dim_Location` to `Fact_Disease_Climate_Weekly`.
