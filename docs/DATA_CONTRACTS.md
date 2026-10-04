# DATA CONTRACTS & COLUMN-LEVEL SCHEMA REGISTRY

> **Target Audience:** AI Coding Agents & Data Engineers  
> **Mandatory Rule:** Ingestion scripts, SQL transforms, and dbt models MUST strictly conform to these exact column names, data types, and primary key definitions. Do NOT invent alternate column aliases.

---

## 1. STORAGE SCHEMA ARCHITECTURE

```text
Database: smart_health_dw
├── schema: bronze       # Raw, un-mutated ingestion tables + metadata audit columns
├── schema: silver       # Cleansed, deduplicated, unpivoted, harmonized relational tables
└── schema: gold         # Dimensional Star Schema (conformed dims + analytical fact marts)
```

---

## 2. BRONZE LAYER CONTRACTS (RAW INGESTION)

Every table in `bronze` must retain the original raw format while appending two mandatory audit columns:
* `_ingested_at` (`TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP`): Ingestion timestamp.
* `_source_file` (`VARCHAR(255)`): Origin filename or API endpoint URI.

### 2.1. `bronze.raw_dengue_weather_daily`
Source: Kaggle Bangladesh / Vietnam Dengue & Weather Benchmark (`CSV`)

| Source Raw Column | Bronze Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :---: | :--- |
| `Date` | `raw_date` | `VARCHAR(50)` | No | Raw date string (e.g., `YYYY-MM-DD` or `DD/MM/YYYY`) |
| `Division` / `District` | `raw_location_name`| `VARCHAR(100)`| No | Raw provincial/district name |
| `Cases` / `Dengue_Cases`| `raw_cases` | `VARCHAR(50)` | Yes | Raw string of case count |
| `Hospitalized` | `raw_hospitalized` | `VARCHAR(50)` | Yes | Inpatient admissions count string |
| `Deaths` | `raw_deaths` | `VARCHAR(50)` | Yes | Death count string |
| `Max Temperature (C)` | `raw_temp_max` | `VARCHAR(50)` | Yes | Maximum temperature recorded string |
| `Min Temperature (C)` | `raw_temp_min` | `VARCHAR(50)` | Yes | Minimum temperature recorded string |
| `Rainfall (mm)` | `raw_rainfall` | `VARCHAR(50)` | Yes | Precipitation sum string |
| `Relative Humidity (%)`| `raw_humidity` | `VARCHAR(50)` | Yes | Relative humidity percentage string |
| *(Metadata)* | `_ingested_at` | `TIMESTAMPTZ` | No | Pipeline ingestion timestamp |
| *(Metadata)* | `_source_file` | `VARCHAR(255)`| No | File source name |

### 2.2. `bronze.raw_admin_boundaries`
Source: UN OCHA Humanitarian Data Exchange (HDX COD-AB) (`GeoJSON / Shapefile`)

| Bronze Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `adm1_pcode` | `VARCHAR(20)` | No | Standardized UN OCHA P-Code (e.g., `VN-HN`, `BD-10`) |
| `adm1_name_en` | `VARCHAR(100)` | No | English administrative unit name |
| `adm1_name_local` | `VARCHAR(100)` | Yes | Native script / local administrative name |
| `centroid_lat` | `DOUBLE PRECISION`| No | Centroid latitude coordinate |
| `centroid_long` | `DOUBLE PRECISION`| No | Centroid longitude coordinate |
| `population` | `BIGINT` | Yes | Local census population size |
| `geom_geojson` | `JSONB` | No | Boundary polygon geometry in GeoJSON format |
| `_ingested_at` | `TIMESTAMPTZ` | No | Pipeline ingestion timestamp |
| `_source_file` | `VARCHAR(255)` | No | Data source reference |

---

## 3. SILVER LAYER CONTRACTS (CLEANSED & HARMONIZED)

All data types are cast to strict SQL types. Missing numerical values are imputed.

### 3.1. `silver.stg_disease_daily`
* **Grain:** 1 record per `(location_key, record_date, disease_type)`
* **Primary Key:** `(location_key, record_date, disease_type)`

| Column Name | Data Type | Nullable | Transformation / Cleansing Rule |
| :--- | :--- | :---: | :--- |
| `location_key` | `VARCHAR(20)` | No | Standardized UN OCHA P-Code via fuzzy lookup |
| `record_date` | `DATE` | No | Standardized ISO `YYYY-MM-DD` |
| `disease_type` | `VARCHAR(30)` | No | Standardized enum: `'DENGUE'`, `'RESPIRATORY'`, `'CHOLERA'` |
| `new_cases` | `INTEGER` | No | Cast integer, `COALESCE(new_cases, 0)` |
| `hospitalizations` | `INTEGER` | No | Cast integer, `COALESCE(hospitalizations, 0)` |
| `deaths` | `INTEGER` | No | Cast integer, `COALESCE(deaths, 0)` |
| `_cleansed_at` | `TIMESTAMPTZ` | No | Audit timestamp when silver record was created |

### 3.2. `silver.stg_climate_daily`
* **Grain:** 1 record per `(location_key, record_date)`
* **Primary Key:** `(location_key, record_date)`

| Column Name | Data Type | Nullable | Transformation / Cleansing Rule |
| :--- | :--- | :---: | :--- |
| `location_key` | `VARCHAR(20)` | No | Standardized UN OCHA P-Code |
| `record_date` | `DATE` | No | Standardized ISO `YYYY-MM-DD` |
| `max_temperature_c`| `NUMERIC(5,2)`| Yes | Forward-filled if missing |
| `min_temperature_c`| `NUMERIC(5,2)`| Yes | Forward-filled if missing |
| `avg_temperature_c`| `NUMERIC(5,2)`| Yes | Computed as `(max + min)/2` if mean missing |
| `rainfall_mm` | `NUMERIC(6,2)`| No | `COALESCE(rainfall_mm, 0.0)` |
| `humidity_pct` | `NUMERIC(5,2)`| Yes | Rolling 7-day average imputation |
| `pm25_ug_m3` | `NUMERIC(6,2)`| Yes | Interpolated air quality sensor values |
| `aqi_value` | `NUMERIC(5,1)`| Yes | Standardized Air Quality Index |
| `_cleansed_at` | `TIMESTAMPTZ` | No | Audit timestamp |

---

## 4. GOLD LAYER CONTRACTS (DIMENSIONAL STAR SCHEMA)

### 4.1. `gold.dim_location`
* **Primary Key:** `location_key`

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :---: | :--- |
| `location_key` | `VARCHAR(20)` | `PRIMARY KEY` | Standardized UN OCHA P-Code |
| `province_name_en` | `VARCHAR(100)`| `NOT NULL` | Province name in English |
| `province_name_local`| `VARCHAR(100)`| | Province name in local language |
| `climate_zone` | `VARCHAR(50)` | `NOT NULL` | Tropical Monsoon, Highland, Coastal |
| `centroid_lat` | `DOUBLE PRECISION`| `NOT NULL` | Latitude for GIS point placement |
| `centroid_long` | `DOUBLE PRECISION`| `NOT NULL` | Longitude for GIS point placement |
| `population` | `BIGINT` | `NOT NULL` | Population benchmark for rate normalization |
| `geom_polygon` | `JSONB` / `GEOMETRY`| `NOT NULL` | Boundary geometry for Choropleth maps |

### 4.2. `gold.dim_date`
* **Primary Key:** `date_key` (Format: `YYYYMMDD`)

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :---: | :--- |
| `date_key` | `INTEGER` | `PRIMARY KEY` | Surrogate key (e.g., `20241005`) |
| `full_date` | `DATE` | `NOT NULL, UNIQUE`| Calendar date |
| `epi_week_key` | `INTEGER` | `NOT NULL` | Epidemiological week key (`YYYYWW`, e.g., `202440`) |
| `epi_week` | `INTEGER` | `NOT NULL` | Week number (1–53) |
| `epi_year` | `INTEGER` | `NOT NULL` | Epidemiological Year |
| `month_number` | `INTEGER` | `NOT NULL` | Month (1–12) |
| `quarter` | `INTEGER` | `NOT NULL` | Quarter (1–4) |
| `is_rainy_season` | `BOOLEAN` | `NOT NULL` | Flag: True if month in local monsoon season |

### 4.3. `gold.fact_disease_climate_weekly`
* **Primary Key:** `fact_id` (`location_key || '_' || epi_week_key || '_' || disease_type`)
* **Foreign Keys:** `location_key` $\to$ `dim_location`, `epi_week_key` $\to$ `dim_date`

| Column Name | Data Type | Constraints | Formulation / Aggregation Logic |
| :--- | :--- | :---: | :--- |
| `fact_id` | `VARCHAR(60)` | `PRIMARY KEY` | MD5 or string concatenation surrogate key |
| `location_key` | `VARCHAR(20)` | `FK, NOT NULL` | Standardized UN OCHA P-Code |
| `epi_week_key` | `INTEGER` | `FK, NOT NULL` | Year-Week key (e.g., `202440`) |
| `disease_type` | `VARCHAR(30)` | `NOT NULL` | `'DENGUE'`, `'RESPIRATORY'`, `'CHOLERA'` |
| `total_cases` | `INTEGER` | `NOT NULL` | `SUM(new_cases)` over the Epi-week |
| `total_hospitalized`| `INTEGER` | `NOT NULL` | `SUM(hospitalizations)` |
| `total_deaths` | `INTEGER` | `NOT NULL` | `SUM(deaths)` |
| `incidence_rate_per_100k`| `NUMERIC(8,2)`| `NOT NULL` | `ROUND((SUM(new_cases)::numeric / population) * 100000, 2)` |
| `avg_temperature_c`| `NUMERIC(5,2)`| Yes | `AVG(avg_temperature_c)` across 7 days |
| `max_temperature_c`| `NUMERIC(5,2)`| Yes | `MAX(max_temperature_c)` across 7 days |
| `min_temperature_c`| `NUMERIC(5,2)`| Yes | `MIN(min_temperature_c)` across 7 days |
| `total_rainfall_mm`| `NUMERIC(7,2)`| `NOT NULL` | `SUM(rainfall_mm)` cumulative 7-day precipitation |
| `avg_humidity_pct` | `NUMERIC(5,2)`| Yes | `AVG(humidity_pct)` 7-day relative humidity |
| `avg_pm25` | `NUMERIC(6,2)`| Yes | `AVG(pm25_ug_m3)` 7-day mean PM2.5 |
| `avg_aqi` | `NUMERIC(5,1)`| Yes | `AVG(aqi_value)` 7-day mean AQI |
| `rainfall_lag_2w` | `NUMERIC(7,2)`| Yes | `LAG(total_rainfall_mm, 2) OVER (...)` |
| `rainfall_lag_4w` | `NUMERIC(7,2)`| Yes | `LAG(total_rainfall_mm, 4) OVER (...)` |
| `temp_lag_2w` | `NUMERIC(5,2)`| Yes | `LAG(avg_temperature_c, 2) OVER (...)` |
| `risk_level` | `VARCHAR(20)` | `NOT NULL` | Evaluated via `DOMAIN_RULES_AND_METRICS.md` |
