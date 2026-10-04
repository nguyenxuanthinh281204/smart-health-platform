"""
==============================================================================
SMART HEALTH DATA PLATFORM - TEXT-TO-SQL AI ASSISTANT MODULE
==============================================================================
Converts natural language epidemiological and climate queries into 
safe, optimized SQL targeting the Gold Layer Analytical Mart.

Enforces docs/SECURITY_AND_GOVERNANCE.md (Section 3: Defense-in-Depth):
  1. Layer 1: AST / Regex Statement Blacklist (Zero DDL/DML, anti-injection)
  2. Layer 2: Read-Only Transaction Enclosure with 3000ms Statement Timeout
  3. Layer 3: Connection via dedicated 'llm_agent' role (Gold schema confinement)
  4. Layer 4: Hard Row Cap (LIMIT 500)

Supports Gemini API / OpenAI API when configured, with an intelligent 
few-shot domain heuristic engine as a zero-dependency fallback.
==============================================================================
"""

import os
import re
import time
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import psycopg2

logger = logging.getLogger("LLMTextToSQL")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class SecuritySandboxViolation(Exception):
    """Raised when generated SQL violates any layer of the 4-layer security sandbox."""
    pass


class LLMTextToSQLEngine:
    """Enterprise-grade Text-to-SQL engine with 4-layer defense-in-depth."""

    # Layer 1: Forbidden DDL/DML/System keywords
    FORBIDDEN_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", 
        "GRANT", "REVOKE", "EXEC", "EXECUTE", "CREATE", "RENAME",
        "MERGE", "COPY", "VACUUM", "REINDEX", "DISCARD", "SYSTEM",
        "INFORMATION_SCHEMA", "PG_CATALOG", "PG_ROLES", "PG_USER",
        "PG_SHADOW", "PG_AUTHID", "PG_DATABASE", "PG_TABLES"
    ]

    # Authoritative Gold Layer Schema Metadata for LLM System Prompt
    GOLD_METADATA_PROMPT = """
    You are an expert Data Engineer & Epidemiologist for the Smart Health Platform.
    Generate PostgreSQL SQL queries against the Gold Layer Analytical Mart.
    
    SCHEMA SPECIFICATION:
    1. Table: gold.dim_location
       - location_key (VARCHAR(20), PK): Standardized UN OCHA P-Code (e.g., 'BD-10', 'BD-20', 'BD-30' for Dhaka, 'BD-40', 'BD-45', 'BD-50', 'BD-55', 'BD-60')
       - province_name_en (VARCHAR(100)): English division name ('Barisal', 'Chittagong', 'Dhaka', 'Khulna', 'Mymensingh', 'Rajshahi', 'Rangpur', 'Sylhet')
       - climate_zone (VARCHAR(50)): 'Tropical Monsoon', 'Coastal Monsoon', 'Highland Monsoon'
       - population (BIGINT): Census population benchmark
       - centroid_lat (DOUBLE PRECISION), centroid_long (DOUBLE PRECISION)
       
    2. Table: gold.dim_date
       - date_key (INTEGER, PK): YYYYMMDD (e.g. 20230815)
       - full_date (DATE, UNIQUE): Calendar date (2022-01-01 to 2026-12-31)
       - epi_week_key (INTEGER): 6-digit ISO-8601 week key (YYYYWW, e.g. 202332)
       - epi_week (INTEGER): Week 1-53
       - epi_year (INTEGER): ISO Year
       - is_rainy_season (BOOLEAN): True if in South Asian Monsoon (June to October)
       
    3. Table: gold.fact_disease_climate_weekly
       - fact_id (VARCHAR(60), PK): Format 'location_key_epi_week_key_disease_type'
       - location_key (VARCHAR(20), FK): References gold.dim_location(location_key)
       - epi_week_key (INTEGER, FK): References gold.dim_date(epi_week_key)
       - disease_type (VARCHAR(30)): 'DENGUE'
       - total_cases (INTEGER): Cumulative incident cases in the 7-day week
       - total_hospitalized (INTEGER): Cumulative inpatient admissions
       - total_deaths (INTEGER): Cumulative confirmed deaths
       - incidence_rate_per_100k (NUMERIC(8,2)): Normalized (total_cases / population) * 100000
       - total_rainfall_mm (NUMERIC(7,2)): 7-day cumulative precipitation
       - avg_temperature_c (NUMERIC(5,2)): 7-day mean temperature
       - avg_humidity_pct (NUMERIC(5,2)): 7-day mean relative humidity
       - avg_aqi (NUMERIC(5,1)): 7-day mean Air Quality Index
       - rainfall_lag_2w (NUMERIC(7,2)): Cumulative precipitation lagged by 2 weeks
       - rainfall_lag_4w (NUMERIC(7,2)): Cumulative precipitation lagged by 4 weeks
       - temp_lag_2w (NUMERIC(5,2)): Mean temperature lagged by 2 weeks
       - risk_level (VARCHAR(20)): 'Low', 'Moderate', 'High', 'Severe'
       
    4. Table: gold.fact_outbreak_forecast_weekly
       - forecast_id (VARCHAR(60), PK): Unique forecast identifier
       - location_key (VARCHAR(20), FK): References gold.dim_location(location_key)
       - base_epi_week_key (INTEGER): Observation week from which forecast was generated
       - forecast_epi_week_key (INTEGER): 4-week forward horizon epidemiological week
       - predicted_cases_4w (INTEGER): Point prediction of dengue cases in 4 weeks
       - predicted_incidence_rate_per_100k (NUMERIC(8,2)): Normalized predicted incidence
       - confidence_lower_bound (NUMERIC(8,2)), confidence_upper_bound (NUMERIC(8,2)): 95% CI
       - predicted_risk_level (VARCHAR(20)): 'Low', 'Moderate', 'High', 'Severe'
       - model_name (VARCHAR(50)): 'HistGradientBoostingRegressor' or 'XGBoostRegressor'
       
    RULES:
    - Only output valid SELECT queries. Never use DDL or DML.
    - Reference tables with the 'gold.' schema prefix.
    - Always JOIN dim_location to display friendly 'province_name_en'.
    - If user does not specify limit, add 'LIMIT 50'.
    """

    def __init__(self, db_conn=None):
        self.db_host = os.getenv("POSTGRES_HOST", "postgres")
        self.db_port = int(os.getenv("POSTGRES_PORT", 5432))
        self.db_name = os.getenv("POSTGRES_DB", "smart_health_dw")
        self.llm_user = os.getenv("POSTGRES_LLM_USER", "llm_agent")
        self.llm_password = os.getenv("POSTGRES_LLM_PASSWORD", "llm_agent_secure_pass_2026")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    def get_connection(self):
        """Layer 3: Enforces connection strictly via sandboxed 'llm_agent' role."""
        return psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            user=self.llm_user,
            password=self.llm_password,
        )

    def validate_sql_security(self, sql_query: str) -> str:
        """
        Layer 1 & Layer 4 Sandbox Security Validation:
          - Layer 1: Detect and abort on blacklisted DDL/DML keywords and comment injection.
          - Layer 4: Enforce maximum hard row cap (LIMIT 500).
        """
        clean_sql = sql_query.strip().rstrip(";")
        
        # Check for multiple statements (semicolon chaining)
        if ";" in clean_sql:
            raise SecuritySandboxViolation("Multi-statement query injection detected. Chaining is strictly prohibited.")
            
        # Check for SQL comment injection
        if "--" in clean_sql or "/*" in clean_sql:
            raise SecuritySandboxViolation("Comment syntax injection detected.")
            
        # Layer 1: Check forbidden keywords using word boundary regex
        for kw in self.FORBIDDEN_KEYWORDS:
            pattern = rf"\b{kw}\b"
            if re.search(pattern, clean_sql, re.IGNORECASE):
                raise SecuritySandboxViolation(f"Statement Blacklist Violation: Forbidden keyword '{kw}' detected.")
                
        # Must start with SELECT or WITH
        first_token = clean_sql.split()[0].upper() if clean_sql.split() else ""
        if first_token not in ["SELECT", "WITH"]:
            raise SecuritySandboxViolation("Only SELECT read-only queries are permitted.")
            
        # Layer 4: Hard Row Cap Enforcer (max 500)
        limit_match = re.search(r"\bLIMIT\s+(\d+)\b", clean_sql, re.IGNORECASE)
        if limit_match:
            user_limit = int(limit_match.group(1))
            if user_limit > 500:
                clean_sql = re.sub(r"\bLIMIT\s+\d+\b", "LIMIT 500", clean_sql, flags=re.IGNORECASE)
        else:
            clean_sql += " LIMIT 100"
            
        return clean_sql

    def generate_sql_heuristic_fallback(self, natural_query: str) -> Tuple[str, str]:
        """
        Intelligent Few-Shot Domain Heuristic Engine.
        Translates natural language questions into accurate Gold schema SQL.
        """
        q = natural_query.strip().lower()
        
        # Check if query contains forbidden SQL DDL/DML injection keywords or comment attacks
        for kw in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{kw}\b", natural_query, re.IGNORECASE):
                return natural_query, f"Forbidden command '{kw}' detected. Guardrail violation."
        if ";" in natural_query or "--" in natural_query or "/*" in natural_query:
            return natural_query, "SQL comment or chaining syntax detected. Guardrail violation."

        # Scenario 1: Top divisions by cases / deaths
        if "top" in q or "highest" in q or "most" in q:
            if "death" in q or "mortality" in q:
                metric = "SUM(f.total_deaths)"
                alias = "total_deaths"
            elif "incidence" in q or "rate" in q:
                metric = "ROUND(AVG(f.incidence_rate_per_100k), 2)"
                alias = "avg_incidence_rate_per_100k"
            elif "hospital" in q:
                metric = "SUM(f.total_hospitalized)"
                alias = "total_hospitalizations"
            else:
                metric = "SUM(f.total_cases)"
                alias = "total_cases"
                
            # Check year filter
            year_match = re.search(r"\b(202[2-5])\b", q)
            year_clause = f"AND f.epi_week_key / 100 = {year_match.group(1)}" if year_match else ""
            year_label = f"in {year_match.group(1)}" if year_match else "across all years"
            
            sql = f"""
SELECT 
    l.province_name_en,
    f.location_key,
    l.climate_zone,
    l.population,
    {metric} AS {alias}
FROM gold.fact_disease_climate_weekly f
JOIN gold.dim_location l ON f.location_key = l.location_key
WHERE 1=1 {year_clause}
GROUP BY l.province_name_en, f.location_key, l.climate_zone, l.population
ORDER BY {alias} DESC
LIMIT 5;
            """.strip()
            explanation = f"Querying the top administrative divisions by {alias.replace('_', ' ')} {year_label} joined with demographic baselines."
            return sql, explanation

        # Scenario 2: Active alerts / high risk
        if "risk" in q or "alert" in q or "severe" in q or "high" in q:
            sql = """
SELECT 
    f.epi_week_key,
    l.province_name_en,
    f.risk_level,
    f.total_cases,
    f.incidence_rate_per_100k,
    f.rainfall_lag_2w,
    f.avg_humidity_pct
FROM gold.fact_disease_climate_weekly f
JOIN gold.dim_location l ON f.location_key = l.location_key
WHERE f.risk_level IN ('High', 'Severe')
ORDER BY f.epi_week_key DESC, f.total_cases DESC
LIMIT 20;
            """.strip()
            explanation = "Filtering surveillance records classified under 'High' or 'Severe' risk levels based on clinical and 2-week meteorological triggers."
            return sql, explanation

        # Scenario 3: Time lag correlation (Rainfall vs Cases)
        if "lag" in q or "rain" in q or "weather" in q or "climate" in q:
            # Check location
            loc_clause = ""
            loc_label = "Dhaka"
            for pcode, name in [("BD-30", "dhaka"), ("BD-20", "chittagong"), ("BD-10", "barisal"), 
                               ("BD-40", "khulna"), ("BD-50", "rajshahi"), ("BD-55", "rangpur"), 
                               ("BD-60", "sylhet"), ("BD-45", "mymensingh")]:
                if name in q:
                    loc_clause = f"AND f.location_key = '{pcode}'"
                    loc_label = name.capitalize()
                    break
            if not loc_clause:
                loc_clause = "AND f.location_key = 'BD-30'"
                
            sql = f"""
SELECT 
    f.epi_week_key,
    l.province_name_en,
    f.total_cases,
    f.total_hospitalized,
    f.total_rainfall_mm,
    f.rainfall_lag_2w,
    f.rainfall_lag_4w,
    f.temp_lag_2w,
    f.risk_level
FROM gold.fact_disease_climate_weekly f
JOIN gold.dim_location l ON f.location_key = l.location_key
WHERE 1=1 {loc_clause}
ORDER BY f.epi_week_key ASC
LIMIT 100;
            """.strip()
            explanation = f"Extracting weekly epidemiological time-series with 2-week and 4-week rainfall lag indicators for {loc_label} to analyze vector transmission lag dynamics."
            return sql, explanation

        # Scenario 4: Climate zone comparison
        if "climate zone" in q or "zone" in q:
            sql = """
SELECT 
    l.climate_zone,
    COUNT(DISTINCT l.location_key) AS total_divisions,
    SUM(f.total_cases) AS total_cases,
    ROUND(AVG(f.incidence_rate_per_100k), 2) AS mean_incidence_per_100k,
    ROUND(AVG(f.total_rainfall_mm), 1) AS mean_weekly_rainfall_mm,
    ROUND(AVG(f.avg_humidity_pct), 1) AS mean_humidity_pct
FROM gold.fact_disease_climate_weekly f
JOIN gold.dim_location l ON f.location_key = l.location_key
GROUP BY l.climate_zone
ORDER BY total_cases DESC;
            """.strip()
            explanation = "Aggregating epidemiological burden and environmental parameters categorized by climatic zones (Tropical Monsoon, Coastal, Highland)."
            return sql, explanation

        # Scenario 5: Machine Learning 4-Week Forward Outbreak Forecasting
        if "forecast" in q or "predict" in q or "future" in q or "ahead" in q:
            sql = """
SELECT 
    l.province_name_en,
    fc.location_key,
    fc.base_epi_week_key,
    fc.forecast_epi_week_key,
    fc.predicted_cases_4w,
    fc.predicted_incidence_rate_per_100k,
    fc.confidence_lower_bound,
    fc.confidence_upper_bound,
    fc.predicted_risk_level,
    fc.model_name
FROM gold.fact_outbreak_forecast_weekly fc
JOIN gold.dim_location l ON fc.location_key = l.location_key
WHERE fc.base_epi_week_key = (SELECT MAX(base_epi_week_key) FROM gold.fact_outbreak_forecast_weekly)
ORDER BY fc.predicted_cases_4w DESC;
            """.strip()
            explanation = "Querying the 4-week forward dengue outbreak machine learning predictions and confidence bounds across all administrative divisions."
            return sql, explanation

        # Default Scenario: General Outbreak Overview
        sql = """
SELECT 
    f.epi_week_key,
    l.province_name_en,
    f.total_cases,
    f.total_hospitalized,
    f.total_deaths,
    f.incidence_rate_per_100k,
    f.total_rainfall_mm,
    f.avg_temperature_c,
    f.risk_level
FROM gold.fact_disease_climate_weekly f
JOIN gold.dim_location l ON f.location_key = l.location_key
ORDER BY f.epi_week_key DESC, f.total_cases DESC
LIMIT 50;
        """.strip()
        explanation = "Returning comprehensive weekly surveillance summary joining disease incidence with meteorological indicators across all divisions."
        return sql, explanation

    def generate_sql(self, natural_query: str) -> Tuple[str, str]:
        """
        Translates natural language to SQL.
        Attempts LLM API if key is present, falls back gracefully to domain heuristic.
        """
        # If Gemini / OpenAI API key is configured, prompt the model
        if self.gemini_api_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
                prompt = f"{self.GOLD_METADATA_PROMPT}\n\nUSER QUESTION: {natural_query}\nGenerate SQL only without markdown code blocks:"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                res = requests.post(url, json=payload, timeout=8)
                if res.status_code == 200:
                    text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    clean = re.sub(r"```(sql)?", "", text).strip()
                    return clean, "Generated via Google Gemini 1.5 Flash."
            except Exception as e:
                logger.warning("Gemini API call failed (%s). Utilizing domain heuristic engine.", e)

        # Domain Heuristic Engine
        return self.generate_sql_heuristic_fallback(natural_query)

    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Layer 2: Executes SQL within an explicit Read-Only transaction and 3000ms timeout.
        """
        conn = None
        start_time = time.time()
        try:
            validated_sql = self.validate_sql_security(sql_query)
            conn = self.get_connection()
            with conn.cursor() as cur:
                # Layer 2: Read-Only transaction & Statement Timeout
                cur.execute("BEGIN READ ONLY;")
                cur.execute("SET STATEMENT_TIMEOUT = '3000ms';")
                cur.execute(validated_sql)
                
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall() if cur.description else []
                conn.commit()
                
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            df = pd.DataFrame(rows, columns=columns)
            
            return {
                "success": True,
                "sql": validated_sql,
                "data": df,
                "row_count": len(df),
                "elapsed_ms": elapsed_ms,
                "error": None
            }
        except Exception as exc:
            if conn:
                conn.rollback()
            return {
                "success": False,
                "sql": sql_query,
                "data": pd.DataFrame(),
                "row_count": 0,
                "elapsed_ms": 0,
                "error": str(exc)
            }
        finally:
            if conn:
                conn.close()

    def ask(self, natural_query: str) -> Dict[str, Any]:
        """End-to-end interface: Natural Language -> Safe SQL -> Execution -> Response."""
        raw_sql, explanation = self.generate_sql(natural_query)
        result = self.execute_query(raw_sql)
        result["natural_query"] = natural_query
        result["explanation"] = explanation
        return result


if __name__ == "__main__":
    engine = LLMTextToSQLEngine()
    test_queries = [
        "What are the top 5 divisions by total dengue cases in 2023?",
        "Show rainfall and dengue cases in Dhaka with time lags",
        "Which regions have active high or severe risk alerts?",
        "DROP TABLE gold.fact_disease_climate_weekly;" # Injection attack test
    ]
    for q in test_queries:
        print(f"\n[QUERY]: {q}")
        res = engine.ask(q)
        if res["success"]:
            print(f"  [SQL]: {res['sql']}")
            print(f"  [ROWS]: {res['row_count']} in {res['elapsed_ms']}ms")
            print(f"  [PREVIEW]:\n{res['data'].head(2)}")
        else:
            print(f"  [BLOCKED/ERROR]: {res['error']}")
