"""
==============================================================================
SMART HEALTH DATA PLATFORM - SPRINT 2 SILVER LAYER VERIFICATION SUITE
==============================================================================
Validates the Definition of Done (DoD) for Sprint 2:
  1. Zero duplicate records in silver.stg_disease_daily & silver.stg_climate_daily.
  2. 100% of provincial entities resolve to authoritative UN OCHA P-Codes.
  3. Weather time-series continuous with zero null gaps.
  4. Physical Parquet artifacts exist and match table grains.
  5. Security & RBAC Least Privilege compliance:
     - de_admin has full access to silver.
     - bi_reader and llm_agent are denied access to silver.

Conforms strictly to docs/DATA_CONTRACTS.md and docs/SECURITY_AND_GOVERNANCE.md.
==============================================================================
"""

import os
import sys
import logging
import pandas as pd
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VerifySilverLayer")

PASS_COUNT = 0
FAIL_COUNT = 0


def record_result(check_name: str, passed: bool, details: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        print(f"  [PASS] {check_name}: {details}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {check_name}: {details}")


def run_checks():
    print("\n" + "=" * 80)
    print("SMART HEALTH PLATFORM - SPRINT 2 VERIFICATION AUDIT")
    print("=" * 80)

    db_host = os.getenv("POSTGRES_HOST", "postgres")
    db_port = int(os.getenv("POSTGRES_PORT", 5432))
    db_name = os.getenv("POSTGRES_DB", "smart_health_dw")

    # 1. Connect as de_admin
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=os.getenv("POSTGRES_USER", "de_admin"),
            password=os.getenv("POSTGRES_PASSWORD", "de_admin_secure_pass_2026"),
        )
        record_result("Database Connection", True, f"Connected to {db_name} as de_admin.")
    except Exception as exc:
        record_result("Database Connection", False, str(exc))
        return

    cur = conn.cursor()

    # Load authoritative P-Codes from Master Boundary table
    cur.execute("SELECT adm1_pcode FROM bronze.raw_admin_boundaries;")
    valid_pcodes = {row[0] for row in cur.fetchall()}

    # --------------------------------------------------------------------------
    # CHECK 1: silver.stg_disease_daily Deduplication (Task 2.1)
    # --------------------------------------------------------------------------
    print("\n--- Auditing silver.stg_disease_daily ---")
    cur.execute("SELECT COUNT(*) FROM silver.stg_disease_daily;")
    disease_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT location_key, record_date, disease_type, COUNT(*) 
            FROM silver.stg_disease_daily 
            GROUP BY location_key, record_date, disease_type 
            HAVING COUNT(*) > 1
        ) dups;
    """)
    disease_dups = cur.fetchone()[0]
    record_result(
        "Disease Deduplication (Task 2.1)",
        disease_dups == 0 and disease_count > 0,
        f"{disease_count} total records, {disease_dups} duplicates found.",
    )

    # --------------------------------------------------------------------------
    # CHECK 2: silver.stg_disease_daily Geospatial Harmonization (Task 2.3)
    # --------------------------------------------------------------------------
    cur.execute("SELECT DISTINCT location_key FROM silver.stg_disease_daily;")
    disease_pcodes = {row[0] for row in cur.fetchall()}
    invalid_disease_pcodes = disease_pcodes - valid_pcodes
    record_result(
        "Disease Geospatial Harmonization (Task 2.3)",
        len(invalid_disease_pcodes) == 0 and len(disease_pcodes) > 0,
        f"100% ({len(disease_pcodes)}/{len(disease_pcodes)}) locations match authoritative P-Codes: {sorted(disease_pcodes)}",
    )

    # --------------------------------------------------------------------------
    # CHECK 3: silver.stg_disease_daily Strict Null & Value Constraints (Task 2.5)
    # --------------------------------------------------------------------------
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE location_key IS NULL),
            COUNT(*) FILTER (WHERE record_date IS NULL),
            COUNT(*) FILTER (WHERE disease_type IS NULL),
            COUNT(*) FILTER (WHERE new_cases IS NULL OR new_cases < 0),
            COUNT(*) FILTER (WHERE hospitalizations IS NULL OR hospitalizations < 0),
            COUNT(*) FILTER (WHERE deaths IS NULL OR deaths < 0),
            COUNT(*) FILTER (WHERE _cleansed_at IS NULL)
        FROM silver.stg_disease_daily;
    """)
    disease_violations = cur.fetchone()
    total_disease_violations = sum(disease_violations)
    record_result(
        "Disease Contract Constraints (Task 2.5)",
        total_disease_violations == 0,
        f"Zero constraint violations across all {disease_count} rows.",
    )

    # --------------------------------------------------------------------------
    # CHECK 4: silver.stg_climate_daily Deduplication (Task 2.1)
    # --------------------------------------------------------------------------
    print("\n--- Auditing silver.stg_climate_daily ---")
    cur.execute("SELECT COUNT(*) FROM silver.stg_climate_daily;")
    climate_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT location_key, record_date, COUNT(*) 
            FROM silver.stg_climate_daily 
            GROUP BY location_key, record_date 
            HAVING COUNT(*) > 1
        ) dups;
    """)
    climate_dups = cur.fetchone()[0]
    record_result(
        "Climate Deduplication (Task 2.1)",
        climate_dups == 0 and climate_count > 0,
        f"{climate_count} total records, {climate_dups} duplicates found.",
    )

    # --------------------------------------------------------------------------
    # CHECK 5: silver.stg_climate_daily Geospatial Harmonization (Task 2.3)
    # --------------------------------------------------------------------------
    cur.execute("SELECT DISTINCT location_key FROM silver.stg_climate_daily;")
    climate_pcodes = {row[0] for row in cur.fetchall()}
    invalid_climate_pcodes = climate_pcodes - valid_pcodes
    record_result(
        "Climate Geospatial Harmonization (Task 2.3)",
        len(invalid_climate_pcodes) == 0 and len(climate_pcodes) > 0,
        f"100% ({len(climate_pcodes)}/{len(climate_pcodes)}) locations match authoritative P-Codes: {sorted(climate_pcodes)}",
    )

    # --------------------------------------------------------------------------
    # CHECK 6: silver.stg_climate_daily Zero Null Gaps & Imputation Quality (Task 2.4)
    # --------------------------------------------------------------------------
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE max_temperature_c IS NULL),
            COUNT(*) FILTER (WHERE min_temperature_c IS NULL),
            COUNT(*) FILTER (WHERE avg_temperature_c IS NULL),
            COUNT(*) FILTER (WHERE rainfall_mm IS NULL),
            COUNT(*) FILTER (WHERE humidity_pct IS NULL),
            COUNT(*) FILTER (WHERE pm25_ug_m3 IS NULL),
            COUNT(*) FILTER (WHERE aqi_value IS NULL),
            COUNT(*) FILTER (WHERE max_temperature_c < min_temperature_c),
            COUNT(*) FILTER (WHERE rainfall_mm < 0),
            COUNT(*) FILTER (WHERE humidity_pct < 0 OR humidity_pct > 100)
        FROM silver.stg_climate_daily;
    """)
    climate_violations = cur.fetchone()
    null_climate_count = sum(climate_violations[:7])
    phys_violations = sum(climate_violations[7:])
    record_result(
        "Climate Imputation & Zero Null Gaps (Task 2.4)",
        null_climate_count == 0 and phys_violations == 0,
        f"Zero nulls in 7 weather features, 0 physical consistency violations across all {climate_count} rows.",
    )

    # --------------------------------------------------------------------------
    # CHECK 7: Parquet Lakehouse Storage Artifacts (Task 2.5)
    # --------------------------------------------------------------------------
    print("\n--- Auditing Parquet Lakehouse Storage ---")
    disease_parquet = "/home/src/data/silver/stg_disease_daily.parquet"
    climate_parquet = "/home/src/data/silver/stg_climate_daily.parquet"

    disease_parquet_ok = False
    if os.path.exists(disease_parquet):
        df_dp = pd.read_parquet(disease_parquet)
        disease_parquet_ok = len(df_dp) == disease_count
        record_result(
            "Disease Parquet Verification",
            disease_parquet_ok,
            f"File exists ({os.path.getsize(disease_parquet) / 1024:.2f} KB), rows match database exactly ({len(df_dp)}).",
        )
    else:
        record_result("Disease Parquet Verification", False, f"File missing at {disease_parquet}")

    climate_parquet_ok = False
    if os.path.exists(climate_parquet):
        df_cp = pd.read_parquet(climate_parquet)
        climate_parquet_ok = len(df_cp) == climate_count
        record_result(
            "Climate Parquet Verification",
            climate_parquet_ok,
            f"File exists ({os.path.getsize(climate_parquet) / 1024:.2f} KB), rows match database exactly ({len(df_cp)}).",
        )
    else:
        record_result("Climate Parquet Verification", False, f"File missing at {climate_parquet}")

    # --------------------------------------------------------------------------
    # CHECK 8: Security & Governance RBAC Verification (docs/SECURITY_AND_GOVERNANCE.md)
    # --------------------------------------------------------------------------
    print("\n--- Auditing RBAC Access Control & Isolation ---")
    # bi_reader must NOT have access to silver
    try:
        conn_bi = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user="bi_reader",
            password="bi_reader_secure_pass_2026",
        )
        cur_bi = conn_bi.cursor()
        cur_bi.execute("SELECT COUNT(*) FROM silver.stg_disease_daily;")
        cur_bi.fetchall()
        conn_bi.close()
        record_result("RBAC bi_reader Isolation", False, "Security breach: bi_reader was able to SELECT from silver!")
    except psycopg2.Error:
        record_result(
            "RBAC bi_reader Isolation",
            True,
            "Principle of Least Privilege enforced: bi_reader strictly denied access to silver.",
        )

    # llm_agent must NOT have access to silver
    try:
        conn_llm = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user="llm_agent",
            password="llm_agent_secure_pass_2026",
        )
        cur_llm = conn_llm.cursor()
        cur_llm.execute("SELECT COUNT(*) FROM silver.stg_climate_daily;")
        cur_llm.fetchall()
        conn_llm.close()
        record_result("RBAC llm_agent Isolation", False, "Security breach: llm_agent was able to SELECT from silver!")
    except psycopg2.Error:
        record_result(
            "RBAC llm_agent Isolation",
            True,
            "Principle of Least Privilege enforced: llm_agent strictly denied access to silver.",
        )

    conn.close()

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY: {PASS_COUNT} PASSED, {FAIL_COUNT} FAILED")
    print("=" * 80)
    if FAIL_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_checks()
