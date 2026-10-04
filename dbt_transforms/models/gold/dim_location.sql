{{ config(
    materialized='table',
    schema='gold',
    unique_key='location_key',
    post_hook=[
        "GRANT SELECT ON {{ this }} TO bi_reader",
        "GRANT SELECT ON {{ this }} TO llm_agent"
    ]
) }}

/*
==============================================================================
DIM_LOCATION: Standardized Administrative Dimension Table
==============================================================================
Provides geospatial coordinates, boundary polygons, population baselines,
and climatic zones mapped to UN OCHA P-Codes.

Conforms strictly to docs/DATA_CONTRACTS.md (Section 4.1).
==============================================================================
*/

WITH source_boundaries AS (
    SELECT
        adm1_pcode,
        adm1_name_en,
        adm1_name_local,
        centroid_lat,
        centroid_long,
        population,
        geom_geojson
    FROM {{ source('bronze', 'raw_admin_boundaries') }}
)

SELECT
    adm1_pcode::varchar(20) AS location_key,
    adm1_name_en::varchar(100) AS province_name_en,
    adm1_name_local::varchar(100) AS province_name_local,
    CASE 
        WHEN adm1_pcode IN ('BD-10', 'BD-20') THEN 'Coastal Monsoon'
        WHEN adm1_pcode = 'BD-60' THEN 'Highland Monsoon'
        ELSE 'Tropical Monsoon'
    END::varchar(50) AS climate_zone,
    centroid_lat::double precision AS centroid_lat,
    centroid_long::double precision AS centroid_long,
    population::bigint AS population,
    geom_geojson::jsonb AS geom_polygon
FROM source_boundaries
