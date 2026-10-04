# SYSTEM-WIDE NAMING CONVENTIONS & CODING STYLE GUIDE

> **Document Status:** Authoritative Style Guide  
> **Mandatory Rule:** All database objects, SQL queries, dbt models, Python variables, functions, filenames, and Git commit messages MUST conform to these exact naming conventions.

---

## 1. DATABASE & DBT NAMING CONVENTIONS (POSTGRESQL & DBT)

All database identifiers (schemas, tables, columns, constraints, indexes) MUST strictly use **`lower_snake_case`**. Never use camelCase, PascalCase, or uppercase letters in SQL identifiers.

### 1.1. Schema & Layer Prefixes

| Layer | Schema Name | Purpose & Pattern | Example |
| :--- | :--- | :--- | :--- |
| **Bronze** | `bronze` | Raw landed data as-is from external sources | `bronze.raw_dengue_bangladesh_daily` |
| **Silver (Staging)** | `silver` | Source-cleaned staging views / tables | `silver.stg_kaggle__dengue_daily` |
| **Silver (Intermediate)** | `silver` | Reshaped, joined, or harmonized data | `silver.int_disease__harmonized_weekly` |
| **Gold (Dimension)** | `gold` | Conformed business dimensions | `gold.dim_location`, `gold.dim_date` |
| **Gold (Fact)** | `gold` | Analytical fact marts aggregated to specific grain | `gold.fact_disease_climate_weekly` |

### 1.2. dbt Model File Organization

```text
dbt_transforms/models/
├── staging/
│   ├── kaggle/
│   │   ├── src_kaggle.yml              # Source declarations & raw tests
│   │   └── stg_kaggle__dengue_daily.sql # Pattern: stg_<source>__<entity>
│   └── un_ocha/
│       ├── src_un_ocha.yml
│       └── stg_un_ocha__boundaries.sql
├── intermediate/
│   └── int_disease__harmonized_weekly.sql # Pattern: int_<entity>__<action>
└── marts/
    ├── dim_location.sql                # Pattern: dim_<entity>
    ├── dim_date.sql
    ├── fact_disease_climate_weekly.sql # Pattern: fact_<process>_<grain>
    └── schema.yml                      # Gold column tests & descriptions
```

### 1.3. Column Naming Rules & Suffix Standard

Every column must indicate its semantic role through clear prefixes or suffixes:

| Column Semantic Role | Suffix / Pattern | Example | Rule |
| :--- | :---: | :--- | :--- |
| **Primary Key (Surrogate)** | `*_key` or `*_id` | `location_key`, `date_key`, `fact_id` | Surrogate integer or hash string |
| **Foreign Key** | `*_key` | `location_key`, `epi_week_key` | Must match primary key of parent dimension |
| **Calendar Date** | `*_date` | `record_date`, `full_date` | SQL type `DATE` |
| **Audit Timestamp** | `*_at` | `_ingested_at`, `_cleansed_at`, `created_at` | SQL type `TIMESTAMP WITH TIME ZONE` |
| **Boolean Flag** | `is_*` or `has_*` | `is_rainy_season`, `has_outbreak` | SQL type `BOOLEAN` |
| **Count / Integer Volume**| `total_*` or `num_*` | `total_cases`, `total_deaths`, `num_districts` | SQL type `INTEGER` or `BIGINT` |
| **Continuous Metric** | `<agg>_<metric>_<unit>` | `avg_temperature_c`, `max_temperature_c`, `total_rainfall_mm`, `avg_humidity_pct` | Explicit unit suffix (`_c`, `_mm`, `_pct`, `_ug_m3`) |
| **Calculated Ratio / Rate**| `*_rate_per_<scale>` | `incidence_rate_per_100k` | Clearly states population denominator |
| **Lagged Metric** | `<metric>_lag_<window>` | `rainfall_lag_2w`, `rainfall_lag_4w`, `temp_lag_2w` | Window duration explicitly stated (`2w` = 2 weeks) |

---

## 2. PYTHON CODING STANDARDS (PEP 8 ALIGNMENT)

All Python code in `pipelines/`, `bi_dashboard/`, and utility scripts must adhere to **PEP 8**:

* **Filenames & Modules:** `lower_snake_case.py`  
  * *Good:* `extract_open_meteo.py`, `geo_harmonizer.py`, `app.py`  
  * *Bad:* `ExtractOpenMeteo.py`, `data-loader.py`
* **Classes:** `PascalCase`  
  * *Good:* `OpenMeteoExtractor`, `DenguePipelineRunner`  
  * *Bad:* `open_meteo_extractor`, `dengue_pipeline`
* **Functions & Methods:** `lower_snake_case`  
  * *Good:* `def fetch_weather_by_centroid(lat: float, lon: float) -> dict:`  
  * *Bad:* `def FetchWeather(...)`, `def fetchWeather(...)`
* **Constants & Global Variables:** `UPPER_SNAKE_CASE`  
  * *Good:* `DEFAULT_TIMEOUT_SECONDS = 30`, `MAX_RETRIES = 3`  
  * *Bad:* `defaultTimeout = 30`
* **Type Hinting:** Mandatory on all public functions:
  ```python
  def calculate_incidence_rate(case_count: int, population: int) -> float:
      """Calculates normalized cases per 100,000 residents."""
      if population <= 0:
          return 0.0
      return round((case_count / population) * 100_000, 2)
  ```

---

## 3. DOCKER & ENVIRONMENT CONFIGURATION

* **Service Names:** Lowercase alphanumeric strings (`postgres`, `mageai`, `streamlit`).
* **Environment Variables:** `UPPER_SNAKE_CASE`  
  * Database credentials: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`.
  * API Keys: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `OPEN_METEO_API_KEY`.
  * Internal paths: `BRONZE_DATA_PATH`, `SILVER_DATA_PATH`.

---

## 4. GIT WORKFLOW & CONVENTIONAL COMMITS

All Git commit messages MUST follow the **Conventional Commits** specification:

$$\mathbf{Format:}\quad \text{<type>(<optional scope>): <description in imperative mood>}$$

### Types:
* `feat:` A new feature or pipeline component (e.g., `feat(ingestion): add open-meteo batch extraction DAG`).
* `fix:` A bug fix in an existing pipeline or model (e.g., `fix(dbt): correct window partition in rainfall_lag_2w`).
* `docs:` Documentation changes only (e.g., `docs: add security specification and naming conventions`).
* `refactor:` Code restructuring without changing functional behavior (e.g., `refactor(pipelines): modularize geo lookup logic`).
* `test:` Adding or adjusting dbt or unit tests (e.g., `test(dbt): add not_null test for location_key`).
* `chore:` Infrastructure, docker configs, or dependency updates (e.g., `chore(docker): bump postgres to 16.2-alpine`).
