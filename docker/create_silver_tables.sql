-- ==============================================================================
-- SMART HEALTH DATA PLATFORM - SILVER LAYER SCHEMA CREATION SCRIPT
-- ==============================================================================
-- Defines clean, harmonized, typed tables conforming strictly to:
--   - docs/DATA_CONTRACTS.md (Section 3: Silver Layer Contracts)
--   - docs/SECURITY_AND_GOVERNANCE.md (Section 2: Least Privilege RBAC)
--   - docs/NAMING_CONVENTIONS.md (lower_snake_case, explicit prefixes)
-- ==============================================================================

-- Ensure Silver schema exists
CREATE SCHEMA IF NOT EXISTS silver;
COMMENT ON SCHEMA silver IS 'Cleansed, deduplicated, unpivoted, and geospatially harmonized staging tables';

-- 1. Silver Disease Daily Staging Table
-- Grain: 1 record per (location_key, record_date, disease_type)
CREATE TABLE IF NOT EXISTS silver.stg_disease_daily (
    location_key VARCHAR(20) NOT NULL,
    record_date DATE NOT NULL,
    disease_type VARCHAR(30) NOT NULL,
    new_cases INTEGER NOT NULL DEFAULT 0,
    hospitalizations INTEGER NOT NULL DEFAULT 0,
    deaths INTEGER NOT NULL DEFAULT 0,
    _cleansed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_silver_stg_disease_daily PRIMARY KEY (location_key, record_date, disease_type),
    CONSTRAINT chk_silver_disease_type CHECK (disease_type IN ('DENGUE', 'RESPIRATORY', 'CHOLERA', 'COVID19', 'MALARIA')),
    CONSTRAINT chk_silver_cases_nonneg CHECK (new_cases >= 0),
    CONSTRAINT chk_silver_hosp_nonneg CHECK (hospitalizations >= 0),
    CONSTRAINT chk_silver_deaths_nonneg CHECK (deaths >= 0)
);

COMMENT ON TABLE silver.stg_disease_daily IS 'Cleansed daily epidemiological case reports mapped to UN OCHA P-Codes';
COMMENT ON COLUMN silver.stg_disease_daily.location_key IS 'Standardized UN OCHA P-Code (e.g., BD-30)';
COMMENT ON COLUMN silver.stg_disease_daily.record_date IS 'Observation date in ISO-8601 format (YYYY-MM-DD)';
COMMENT ON COLUMN silver.stg_disease_daily.disease_type IS 'Harmonized disease indicator (DENGUE, RESPIRATORY, CHOLERA)';
COMMENT ON COLUMN silver.stg_disease_daily.new_cases IS 'Daily newly diagnosed incident cases';
COMMENT ON COLUMN silver.stg_disease_daily.hospitalizations IS 'Daily inpatient hospital admissions';
COMMENT ON COLUMN silver.stg_disease_daily.deaths IS 'Daily confirmed mortality count';
COMMENT ON COLUMN silver.stg_disease_daily._cleansed_at IS 'Timestamp of data cleansing and transformation';

CREATE INDEX IF NOT EXISTS idx_silver_disease_loc_date ON silver.stg_disease_daily(location_key, record_date);
CREATE INDEX IF NOT EXISTS idx_silver_disease_date ON silver.stg_disease_daily(record_date);
CREATE INDEX IF NOT EXISTS idx_silver_disease_type ON silver.stg_disease_daily(disease_type);

-- 2. Silver Climate Daily Staging Table
-- Grain: 1 record per (location_key, record_date)
CREATE TABLE IF NOT EXISTS silver.stg_climate_daily (
    location_key VARCHAR(20) NOT NULL,
    record_date DATE NOT NULL,
    max_temperature_c NUMERIC(5,2),
    min_temperature_c NUMERIC(5,2),
    avg_temperature_c NUMERIC(5,2),
    rainfall_mm NUMERIC(6,2) NOT NULL DEFAULT 0.0,
    humidity_pct NUMERIC(5,2),
    pm25_ug_m3 NUMERIC(6,2),
    aqi_value NUMERIC(5,1),
    _cleansed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_silver_stg_climate_daily PRIMARY KEY (location_key, record_date),
    CONSTRAINT chk_silver_rainfall_nonneg CHECK (rainfall_mm >= 0.0),
    CONSTRAINT chk_silver_humidity_range CHECK (humidity_pct IS NULL OR (humidity_pct >= 0.0 AND humidity_pct <= 100.0)),
    CONSTRAINT chk_silver_aqi_nonneg CHECK (aqi_value IS NULL OR aqi_value >= 0.0)
);

COMMENT ON TABLE silver.stg_climate_daily IS 'Cleansed and imputed daily meteorological and environmental indicators';
COMMENT ON COLUMN silver.stg_climate_daily.location_key IS 'Standardized UN OCHA P-Code (e.g., BD-30)';
COMMENT ON COLUMN silver.stg_climate_daily.record_date IS 'Observation date in ISO-8601 format (YYYY-MM-DD)';
COMMENT ON COLUMN silver.stg_climate_daily.max_temperature_c IS 'Maximum recorded daily temperature in Celsius';
COMMENT ON COLUMN silver.stg_climate_daily.min_temperature_c IS 'Minimum recorded daily temperature in Celsius';
COMMENT ON COLUMN silver.stg_climate_daily.avg_temperature_c IS 'Arithmetic mean daily temperature in Celsius';
COMMENT ON COLUMN silver.stg_climate_daily.rainfall_mm IS 'Total daily precipitation in millimeters';
COMMENT ON COLUMN silver.stg_climate_daily.humidity_pct IS 'Mean daily relative humidity percentage';
COMMENT ON COLUMN silver.stg_climate_daily.pm25_ug_m3 IS 'Fine particulate matter PM2.5 concentration in ug/m3';
COMMENT ON COLUMN silver.stg_climate_daily.aqi_value IS 'Harmonized Air Quality Index (EPA standard)';
COMMENT ON COLUMN silver.stg_climate_daily._cleansed_at IS 'Timestamp of data cleansing and transformation';

CREATE INDEX IF NOT EXISTS idx_silver_climate_loc_date ON silver.stg_climate_daily(location_key, record_date);
CREATE INDEX IF NOT EXISTS idx_silver_climate_date ON silver.stg_climate_daily(record_date);

-- 3. RBAC Permissions Enforcement
-- de_admin has full DDL/DML access
GRANT ALL PRIVILEGES ON SCHEMA silver TO de_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA silver TO de_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver GRANT ALL PRIVILEGES ON TABLES TO de_admin;

-- bi_reader and llm_agent are strictly denied access to silver per PoLP
REVOKE ALL ON SCHEMA silver FROM bi_reader, llm_agent;
