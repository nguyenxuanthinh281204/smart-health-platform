-- ==============================================================================
-- SMART HEALTH DATA PLATFORM - POSTGRESQL INITIALIZATION SCRIPT
-- ==============================================================================
-- Automatically executed upon initial container startup via /docker-entrypoint-initdb.d/
-- Conforms strictly to docs/DATA_CONTRACTS.md and docs/SECURITY_AND_GOVERNANCE.md
-- ==============================================================================

-- 1. Enable Core PostgreSQL Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 2. Create Medallion Architecture Schemas
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

COMMENT ON SCHEMA bronze IS 'Raw, un-mutated ingestion tables with ingestion audit columns';
COMMENT ON SCHEMA silver IS 'Cleansed, deduplicated, unpivoted, and geospatially harmonized tables';
COMMENT ON SCHEMA gold IS 'Dimensional analytical mart (Star Schema: Dim_Location, Dim_Date, Fact)';

-- 3. Create Role-Based Access Control (RBAC) Roles
-- Notice: If roles already exist, DO blocks prevent syntax errors
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'bi_reader') THEN
        CREATE ROLE bi_reader WITH LOGIN PASSWORD 'bi_reader_secure_pass_2026';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'llm_agent') THEN
        CREATE ROLE llm_agent WITH LOGIN PASSWORD 'llm_agent_secure_pass_2026';
    END IF;
END
$$;

-- 4. Assign Permissions according to Principle of Least Privilege (PoLP)
-- (a) de_admin (Database Owner) has full privileges
GRANT ALL PRIVILEGES ON SCHEMA bronze TO de_admin;
GRANT ALL PRIVILEGES ON SCHEMA silver TO de_admin;
GRANT ALL PRIVILEGES ON SCHEMA gold TO de_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA bronze TO de_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA silver TO de_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gold TO de_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA bronze GRANT ALL PRIVILEGES ON TABLES TO de_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver GRANT ALL PRIVILEGES ON TABLES TO de_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT ALL PRIVILEGES ON TABLES TO de_admin;

-- (b) bi_reader: Read-Only access restricted exclusively to the Gold Mart
GRANT USAGE ON SCHEMA gold TO bi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO bi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO bi_reader;

-- (c) llm_agent: Read-Only access strictly on Gold Mart (Zero visibility into bronze/silver)
GRANT USAGE ON SCHEMA gold TO llm_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO llm_agent;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO llm_agent;

-- 5. Pre-create Bronze Raw Storage Tables (docs/DATA_CONTRACTS.md)

-- 5.1. Raw Dengue & Weather Daily Table (Kaggle Bangladesh / Vietnam)
CREATE TABLE IF NOT EXISTS bronze.raw_dengue_weather_daily (
    id SERIAL PRIMARY KEY,
    raw_date VARCHAR(50) NOT NULL,
    raw_location_name VARCHAR(100) NOT NULL,
    raw_cases VARCHAR(50),
    raw_hospitalized VARCHAR(50),
    raw_deaths VARCHAR(50),
    raw_temp_max VARCHAR(50),
    raw_temp_min VARCHAR(50),
    raw_rainfall VARCHAR(50),
    raw_humidity VARCHAR(50),
    _ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255) NOT NULL
);

-- 5.2. Raw UN OCHA Administrative Boundaries Table
CREATE TABLE IF NOT EXISTS bronze.raw_admin_boundaries (
    id SERIAL PRIMARY KEY,
    adm1_pcode VARCHAR(20) NOT NULL,
    adm1_name_en VARCHAR(100) NOT NULL,
    adm1_name_local VARCHAR(100),
    centroid_lat DOUBLE PRECISION NOT NULL,
    centroid_long DOUBLE PRECISION NOT NULL,
    population BIGINT,
    geom_geojson JSONB NOT NULL,
    _ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255) NOT NULL
);

-- 5.3. Raw Open-Meteo ERA5 Reanalysis Meteorological Table
CREATE TABLE IF NOT EXISTS bronze.raw_open_meteo_daily (
    id SERIAL PRIMARY KEY,
    location_key VARCHAR(20) NOT NULL,
    observation_date DATE NOT NULL,
    temp_max_c NUMERIC(5,2),
    temp_min_c NUMERIC(5,2),
    temp_mean_c NUMERIC(5,2),
    precipitation_sum_mm NUMERIC(6,2),
    relative_humidity_mean_pct NUMERIC(5,2),
    raw_payload JSONB,
    _ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255) NOT NULL
);

-- Indexing for optimized initial querying
CREATE INDEX IF NOT EXISTS idx_bronze_dengue_date ON bronze.raw_dengue_weather_daily(raw_date);
CREATE INDEX IF NOT EXISTS idx_bronze_boundaries_pcode ON bronze.raw_admin_boundaries(adm1_pcode);
CREATE INDEX IF NOT EXISTS idx_bronze_meteo_date ON bronze.raw_open_meteo_daily(location_key, observation_date);
