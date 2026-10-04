# PROJECT CURRENT STATE (LIVING SNAPSHOT)

> **IMPORTANT NOTICE:**  
> This file serves as the **short-term memory (RAM)** of the project. Both the AI Agent and the Developer must update this document at the conclusion of each session to guarantee seamless context preservation.  
> **Last Updated:** 2026-10-04 (Initial Kick-off & Language Standardization)

---

## 1. CURRENT POSITION OVERVIEW
* **Active Milestone:** **Sprint 0 / Sprint 1: Infrastructure & Ingestion Pipeline Setup**
* **Overall Completion Rate:** ~5% (Requirements synthesized, 10 data sources cataloged, Zero Context Loss AI Framework established in English)
* **Active Git Branch:** `main` (or `feature/infra-setup`)
* **Primary Language:** **English** (All schemas, models, pipelines, and documentation)

---

## 2. RECENTLY COMPLETED TASKS
- [x] Comprehensive review and synthesis of project requirements:
  - Technical architecture (Medallion architecture, Star Schema, Time-Lag Analysis, Incidence Rate / 100k population).
  - Data sources evaluation (10 verified datasets from Kaggle, HDX HumData, Open-Meteo, WHO, JHU).
- [x] Technical feasibility confirmed (**9.5 / 10 rating**) and 5-Sprint roadmap designed.
- [x] Multi-layer Zero Context Loss Architecture deployed in English:
  - [AGENTS.md](file:///d:/Fresher26/mokProject/AGENTS.md) — Master AI operating directive (Root).
  - [PROJECT_STATE.md](file:///d:/Fresher26/mokProject/PROJECT_STATE.md) — Current state snapshot (Root - this file).
  - [TASK_TRACKER.md](file:///d:/Fresher26/mokProject/TASK_TRACKER.md) — Comprehensive Sprint WBS with acceptance criteria (Root).
  - [README.md](file:///d:/Fresher26/mokProject/README.md) — Enterprise GitHub repository documentation (Root).
  - [docs/ROADMAP.md](file:///d:/Fresher26/mokProject/docs/ROADMAP.md) — Comprehensive 5-Sprint timeline, Gantt chart, and milestones.
  - [docs/USE_CASES_AND_ACTORS.md](file:///d:/Fresher26/mokProject/docs/USE_CASES_AND_ACTORS.md) — Detailed user personas, 5 functional modules, and end-to-end use case specifications.
  - [docs/DATA_SPECIFICATION.md](file:///d:/Fresher26/mokProject/docs/DATA_SPECIFICATION.md) — Data catalog, schemas, and mathematical formulas.
  - [docs/DATA_CONTRACTS.md](file:///d:/Fresher26/mokProject/docs/DATA_CONTRACTS.md) — Column-level schema registry across Bronze, Silver, and Gold.
  - [docs/DOMAIN_RULES_AND_METRICS.md](file:///d:/Fresher26/mokProject/docs/DOMAIN_RULES_AND_METRICS.md) — Epidemiological rules, vector biology thresholds, and risk matrix.
  - [docs/SECURITY_AND_GOVERNANCE.md](file:///d:/Fresher26/mokProject/docs/SECURITY_AND_GOVERNANCE.md) — Zero PII policy, RBAC roles, and LLM query sandboxing.
  - [docs/NAMING_CONVENTIONS.md](file:///d:/Fresher26/mokProject/docs/NAMING_CONVENTIONS.md) — Standardized snake_case, dbt modeling organization, and PEP 8 standards.
  - [docs/PROMPT_TEMPLATES.md](file:///d:/Fresher26/mokProject/docs/PROMPT_TEMPLATES.md) — Production prompts for commanding AI agents.
  - [.agents/rules/smart_health_protocol.md](file:///d:/Fresher26/mokProject/.agents/rules/smart_health_protocol.md) — IDE auto-rule.
  - [.agents/rules/modern_health_ui.md](file:///d:/Fresher26/mokProject/.agents/rules/modern_health_ui.md) — Modern Glassmorphism & PyDeck 3D UI/UX design tokens.

---

## 3. NEXT IMMEDIATE STEPS

When initiating the next working session, the AI must execute the following sequential tasks:

1. **Step 1: Standard Data Engineering Project Directory Scaffolding**
   - Create the standard production directory layout:
     ```text
     mokProject/
     ├── docker/
     │   └── docker-compose.yml       # PostgreSQL 16 + Mage.ai services
     ├── data/
     │   ├── bronze/                  # Raw downloaded files (JSON/CSV)
     │   ├── silver/                  # Cleaned and harmonized files (Parquet)
     │   └── gold/                    # Analytical datamart files
     ├── pipelines/                   # Mage.ai DAGs & Python ingestion scripts
     ├── dbt_transforms/              # dbt project (models, macros, tests)
     ├── bi_dashboard/                # Dashboards / Streamlit applications
     └── docs/                        # Specifications & Architecture diagrams
     ```
2. **Step 2: Multi-Container Setup via Docker Compose**
   - Configure `docker/docker-compose.yml`:
     - `postgres`: Port `5432` (Data Warehouse service).
     - `mageai`: Port `6789` (Orchestration & Workflow management).
     - Provide `.env.example` with environment variable templates.
3. **Step 3: Bronze Layer Ingestion Pipeline**
   - Implement automated Python ingestion scripts to acquire initial core datasets:
     - Dengue & Climate dataset (Bangladesh / Vietnam benchmark).
     - UN OCHA Vietnam Sub-national Administrative Boundaries (GeoJSON / P-Codes).

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
