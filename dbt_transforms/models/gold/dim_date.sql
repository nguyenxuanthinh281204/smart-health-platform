{{ config(
    materialized='table',
    schema='gold',
    unique_key='date_key',
    post_hook=[
        "GRANT SELECT ON {{ this }} TO bi_reader",
        "GRANT SELECT ON {{ this }} TO llm_agent"
    ]
) }}

/*
==============================================================================
DIM_DATE: Standardized Calendar & Epidemiological Date Dimension
==============================================================================
Provides date surrogate keys, ISO-8601 Epi-Week alignment, calendar attributes,
and monsoon seasonal indicators from 2022 to 2026.

Conforms strictly to docs/DATA_CONTRACTS.md (Section 4.2) and
docs/DOMAIN_RULES_AND_METRICS.md (Section 1).
==============================================================================
*/

WITH date_spine AS (
    SELECT 
        d::date AS full_date
    FROM generate_series('2022-01-01'::date, '2026-12-31'::date, '1 day'::interval) AS d
)

SELECT
    to_char(full_date, 'YYYYMMDD')::integer AS date_key,
    full_date,
    to_char(full_date, 'IYYYIW')::integer AS epi_week_key,
    to_char(full_date, 'IW')::integer AS epi_week,
    to_char(full_date, 'IYYY')::integer AS epi_year,
    EXTRACT(MONTH FROM full_date)::integer AS month_number,
    EXTRACT(QUARTER FROM full_date)::integer AS quarter,
    (EXTRACT(MONTH FROM full_date) BETWEEN 6 AND 10) AS is_rainy_season
FROM date_spine
ORDER BY full_date ASC
