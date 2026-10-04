{{ config(
    materialized='table',
    schema='gold',
    unique_key='fact_id',
    post_hook=[
        "GRANT SELECT ON {{ this }} TO bi_reader",
        "GRANT SELECT ON {{ this }} TO llm_agent"
    ]
) }}

/*
==============================================================================
FACT_DISEASE_CLIMATE_WEEKLY: Core Analytical Mart Fact Table
==============================================================================
Grain: 1 record per (location_key, epi_week_key, disease_type)
Primary Key: fact_id
Foreign Keys: location_key -> dim_location, epi_week_key -> dim_date

Features:
  - Population-normalized incidence rate per 100,000 population
  - 2-week and 4-week rainfall lags (rainfall_lag_2w, rainfall_lag_4w)
  - 2-week mean temperature lag (temp_lag_2w)
  - Multi-factor risk stratification matrix (Severe, High, Moderate, Low)

Conforms strictly to docs/DATA_CONTRACTS.md (Section 4.3) and
docs/DOMAIN_RULES_AND_METRICS.md.
==============================================================================
*/

WITH disease_weekly AS (
    SELECT
        d.location_key,
        dt.epi_week_key,
        d.disease_type,
        SUM(d.new_cases)::integer AS total_cases,
        SUM(d.hospitalizations)::integer AS total_hospitalized,
        SUM(d.deaths)::integer AS total_deaths
    FROM {{ source('silver', 'stg_disease_daily') }} d
    JOIN {{ ref('dim_date') }} dt 
        ON d.record_date = dt.full_date
    GROUP BY d.location_key, dt.epi_week_key, d.disease_type
),

climate_weekly AS (
    SELECT
        c.location_key,
        dt.epi_week_key,
        ROUND(AVG(c.avg_temperature_c)::numeric, 2) AS avg_temperature_c,
        ROUND(MAX(c.max_temperature_c)::numeric, 2) AS max_temperature_c,
        ROUND(MIN(c.min_temperature_c)::numeric, 2) AS min_temperature_c,
        ROUND(SUM(c.rainfall_mm)::numeric, 2) AS total_rainfall_mm,
        ROUND(AVG(c.humidity_pct)::numeric, 2) AS avg_humidity_pct,
        ROUND(AVG(c.pm25_ug_m3)::numeric, 2) AS avg_pm25,
        ROUND(AVG(c.aqi_value)::numeric, 1) AS avg_aqi
    FROM {{ source('silver', 'stg_climate_daily') }} c
    JOIN {{ ref('dim_date') }} dt 
        ON c.record_date = dt.full_date
    GROUP BY c.location_key, dt.epi_week_key
),

joined_base AS (
    SELECT
        (dw.location_key || '_' || dw.epi_week_key::varchar || '_' || dw.disease_type)::varchar(60) AS fact_id,
        dw.location_key,
        dw.epi_week_key,
        dw.disease_type,
        dw.total_cases,
        dw.total_hospitalized,
        dw.total_deaths,
        loc.population,
        ROUND((dw.total_cases::numeric / NULLIF(loc.population, 0)) * 100000.0, 2) AS incidence_rate_per_100k,
        cw.avg_temperature_c,
        cw.max_temperature_c,
        cw.min_temperature_c,
        COALESCE(cw.total_rainfall_mm, 0.0) AS total_rainfall_mm,
        cw.avg_humidity_pct,
        cw.avg_pm25,
        cw.avg_aqi
    FROM disease_weekly dw
    LEFT JOIN climate_weekly cw 
        ON dw.location_key = cw.location_key 
        AND dw.epi_week_key = cw.epi_week_key
    JOIN {{ ref('dim_location') }} loc 
        ON dw.location_key = loc.location_key
),

with_lags AS (
    SELECT
        fact_id,
        location_key,
        epi_week_key,
        disease_type,
        total_cases,
        total_hospitalized,
        total_deaths,
        incidence_rate_per_100k,
        avg_temperature_c,
        max_temperature_c,
        min_temperature_c,
        total_rainfall_mm,
        avg_humidity_pct,
        avg_pm25,
        avg_aqi,
        LAG(total_rainfall_mm, 2) OVER (
            PARTITION BY location_key, disease_type 
            ORDER BY epi_week_key ASC
        ) AS rainfall_lag_2w,
        LAG(total_rainfall_mm, 4) OVER (
            PARTITION BY location_key, disease_type 
            ORDER BY epi_week_key ASC
        ) AS rainfall_lag_4w,
        LAG(avg_temperature_c, 2) OVER (
            PARTITION BY location_key, disease_type 
            ORDER BY epi_week_key ASC
        ) AS temp_lag_2w
    FROM joined_base
)

SELECT
    fact_id,
    location_key,
    epi_week_key,
    disease_type,
    total_cases,
    total_hospitalized,
    total_deaths,
    incidence_rate_per_100k,
    avg_temperature_c,
    max_temperature_c,
    min_temperature_c,
    total_rainfall_mm,
    avg_humidity_pct,
    avg_pm25,
    avg_aqi,
    rainfall_lag_2w,
    rainfall_lag_4w,
    temp_lag_2w,
    CASE
        -- 1. SEVERE (Red Alert): Critical disease burden OR combined high cases with severe climate triggers
        WHEN incidence_rate_per_100k >= 50.0 
          OR (incidence_rate_per_100k >= 20.0 AND COALESCE(rainfall_lag_2w, 0.0) >= 80.0 AND COALESCE(avg_humidity_pct, 0.0) >= 80.0)
        THEN 'Severe'

        -- 2. HIGH (Orange Alert): Significant transmission OR moderate cases with upcoming climate surge
        WHEN incidence_rate_per_100k >= 20.0
          OR (incidence_rate_per_100k >= 10.0 AND COALESCE(rainfall_lag_2w, 0.0) >= 50.0 AND COALESCE(temp_lag_2w, 0.0) BETWEEN 26.0 AND 32.0)
        THEN 'High'

        -- 3. MODERATE (Yellow Alert): Notable cases OR strong breeding indicators preceding clinical surge
        WHEN incidence_rate_per_100k >= 5.0
          OR (COALESCE(rainfall_lag_2w, 0.0) >= 60.0 AND COALESCE(avg_humidity_pct, 0.0) >= 75.0)
          OR (COALESCE(rainfall_lag_4w, 0.0) >= 100.0)
        THEN 'Moderate'

        -- 4. LOW (Green / Normal): Minimal disease activity within historical norms
        ELSE 'Low'
    END AS risk_level
FROM with_lags
ORDER BY location_key ASC, epi_week_key ASC
