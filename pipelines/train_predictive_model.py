"""
==============================================================================
SMART HEALTH DATA PLATFORM - SPRINT 6 PREDICTIVE ANALYTICS PIPELINE
==============================================================================
Role: Machine Learning 4-Week Forward Dengue Outbreak Forecasting
Implements:
  - Task 6.1: Feature Engineering Pipeline (Autoregressive + Meteorological Lags)
  - Task 6.2: Supervised Ensemble Regression Training & Evaluation (R2, MAE, RMSE)
  - Task 6.3: Batch Inference & Persistence to gold.fact_outbreak_forecast_weekly
  - RBAC Granting: SELECT access to bi_reader and llm_agent per SECURITY_AND_GOVERNANCE.md
==============================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime
import numpy as np
import pandas as pd
import psycopg2
import joblib

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Model directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, "dengue_outbreak_forecast_4w.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "model_metrics.json")


def get_db_connection():
    """Connect as de_admin for table creation and schema management."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "smart_health_dw"),
        user=os.getenv("POSTGRES_USER", "de_admin"),
        password=os.getenv("POSTGRES_PASSWORD", "de_admin_secure_pass_2026"),
    )


def init_forecast_table(conn):
    """Initializes the Gold layer forecast fact table and grants RBAC permissions."""
    ddl = """
    CREATE TABLE IF NOT EXISTS gold.fact_outbreak_forecast_weekly (
        forecast_id VARCHAR(60) PRIMARY KEY,
        location_key VARCHAR(20) NOT NULL REFERENCES gold.dim_location(location_key),
        base_epi_week_key INTEGER NOT NULL,
        forecast_epi_week_key INTEGER NOT NULL,
        predicted_cases_4w INTEGER NOT NULL,
        predicted_incidence_rate_per_100k NUMERIC(8, 2) NOT NULL,
        confidence_lower_bound NUMERIC(8, 2) NOT NULL,
        confidence_upper_bound NUMERIC(8, 2) NOT NULL,
        predicted_risk_level VARCHAR(20) NOT NULL,
        model_name VARCHAR(50) NOT NULL,
        r2_score NUMERIC(6, 4) NOT NULL,
        mae_score NUMERIC(8, 2) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_fcst_location_week 
        ON gold.fact_outbreak_forecast_weekly(location_key, forecast_epi_week_key);

    CREATE INDEX IF NOT EXISTS idx_fcst_risk_level 
        ON gold.fact_outbreak_forecast_weekly(predicted_risk_level);

    -- Least Privilege RBAC Enforcement
    GRANT SELECT ON gold.fact_outbreak_forecast_weekly TO bi_reader;
    GRANT SELECT ON gold.fact_outbreak_forecast_weekly TO llm_agent;
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
        conn.commit()
    logger.info("Initialized gold.fact_outbreak_forecast_weekly and configured RBAC permissions.")


def extract_features(conn):
    """Extracts historical facts joined with locations and dates for ML modeling."""
    query = """
    SELECT 
        f.location_key,
        l.province_name_en,
        l.climate_zone,
        l.population,
        f.epi_week_key,
        f.total_cases,
        f.total_hospitalized,
        f.total_deaths,
        f.incidence_rate_per_100k,
        f.total_rainfall_mm,
        f.rainfall_lag_2w,
        f.rainfall_lag_4w,
        f.avg_temperature_c,
        f.temp_lag_2w,
        f.avg_humidity_pct
    FROM gold.fact_disease_climate_weekly f
    JOIN gold.dim_location l ON f.location_key = l.location_key
    ORDER BY f.location_key ASC, f.epi_week_key ASC;
    """
    df = pd.read_sql_query(query, conn)
    logger.info("Extracted %d historical fact records across %d divisions.", len(df), df["location_key"].nunique())
    return df


def engineer_ml_dataset(df):
    """
    Constructs autoregressive lags, seasonality cycles, and 4-week forward target.
    Target: cases_ahead_4w (total dengue cases at t + 4 weeks).
    """
    df_list = []
    for loc_key, group in df.groupby("location_key"):
        grp = group.sort_values("epi_week_key").copy()
        
        # 1. Autoregressive disease lags (t-1, t-2, t-3, t-4)
        grp["cases_lag_1w"] = grp["total_cases"].shift(1)
        grp["cases_lag_2w"] = grp["total_cases"].shift(2)
        grp["cases_lag_3w"] = grp["total_cases"].shift(3)
        grp["cases_lag_4w"] = grp["total_cases"].shift(4)

        # 2. Forward target: cases 4 weeks in the future (t+4)
        grp["cases_ahead_4w"] = grp["total_cases"].shift(-4)
        grp["target_week_key"] = grp["epi_week_key"].shift(-4)

        # 3. Cyclical seasonality from epi_week
        # Extract week number from YYYYWW
        grp["week_num"] = grp["epi_week_key"] % 100
        grp["sin_week"] = np.sin(2 * np.pi * grp["week_num"] / 52.0)
        grp["cos_week"] = np.cos(2 * np.pi * grp["week_num"] / 52.0)

        df_list.append(grp)

    df_featured = pd.concat(df_list, ignore_index=True)
    
    # Fill early lag nulls with 0 or forward fill
    feature_cols = [
        "cases_lag_1w", "cases_lag_2w", "cases_lag_3w", "cases_lag_4w",
        "total_cases", "incidence_rate_per_100k",
        "total_rainfall_mm", "rainfall_lag_2w", "rainfall_lag_4w",
        "avg_temperature_c", "temp_lag_2w", "avg_humidity_pct",
        "sin_week", "cos_week", "population"
    ]
    df_featured[feature_cols] = df_featured[feature_cols].fillna(0)
    
    return df_featured, feature_cols


def train_model(df_featured, feature_cols):
    """
    Trains a robust ensemble regressor with chronological train/test split.
    Uses XGBoost if available, else Scikit-Learn HistGradientBoostingRegressor.
    """
    # Exclude rows where 4-week target is NaN (the last 4 weeks of dataset)
    train_mask = df_featured["cases_ahead_4w"].notnull()
    df_train_pool = df_featured[train_mask].copy()

    # Chronological split: train on weeks < 202501, test on 2025
    train_split = df_train_pool["epi_week_key"] < 202501
    test_split = df_train_pool["epi_week_key"] >= 202501

    X_train = df_train_pool.loc[train_split, feature_cols]
    y_train = df_train_pool.loc[train_split, "cases_ahead_4w"]

    X_test = df_train_pool.loc[test_split, feature_cols]
    y_test = df_train_pool.loc[test_split, "cases_ahead_4w"]

    # Choose model
    model_name = "HistGradientBoostingRegressor"
    try:
        import xgboost as xgb
        model = xgb.XGBRegressor(
            n_estimators=120,
            learning_rate=0.07,
            max_depth=5,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42
        )
        model_name = "XGBoostRegressor"
        logger.info("Selected XGBoostRegressor for predictive modeling.")
    except Exception:
        from sklearn.ensemble import HistGradientBoostingRegressor
        model = HistGradientBoostingRegressor(
            max_iter=120,
            learning_rate=0.07,
            max_depth=5,
            random_state=42
        )
        model_name = "HistGradientBoostingRegressor"
        logger.info("Selected HistGradientBoostingRegressor for predictive modeling.")

    # Fit model
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    y_pred = np.maximum(y_pred, 0) # Non-negative cases constraint

    from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
    r2 = float(r2_score(y_test, y_pred))
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    logger.info("Model Training Complete [%s]: R2=%.4f | MAE=%.2f | RMSE=%.2f", model_name, r2, mae, rmse)

    # Save model artifact
    joblib.dump({"model": model, "feature_cols": feature_cols, "model_name": model_name, "rmse": rmse}, MODEL_PATH)
    metrics_data = {
        "model_name": model_name,
        "r2_score": round(r2, 4),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "trained_at": datetime.now().isoformat()
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics_data, f, indent=2)

    return model, model_name, r2, mae, rmse


def generate_forecasts(model, model_name, r2, mae, rmse, df_featured, feature_cols, conn):
    """
    Generates batch predictions and upserts into gold.fact_outbreak_forecast_weekly.
    Covers historical validation horizon + active future 4-week prediction.
    """
    # Predict for all rows
    X_all = df_featured[feature_cols]
    preds = model.predict(X_all)
    preds = np.maximum(preds, 0) # cases cannot be negative

    df_forecasts = df_featured.copy()
    df_forecasts["pred_cases_4w"] = preds.round().astype(int)

    # Calculate 4-week ahead target epi_week_key
    # If target_week_key is null (last 4 rows per division), project forward 4 weeks
    def calculate_forward_week(base_week, offset=4):
        year = base_week // 100
        week = base_week % 100
        new_week = week + offset
        if new_week > 52:
            year += 1
            new_week -= 52
        return year * 100 + new_week

    records_to_insert = []
    for _, row in df_forecasts.iterrows():
        base_week = int(row["epi_week_key"])
        target_week = int(row["target_week_key"]) if pd.notnull(row["target_week_key"]) else calculate_forward_week(base_week, 4)
        loc_key = str(row["location_key"])
        pop = float(row["population"])
        
        pred_cases = int(row["pred_cases_4w"])
        pred_inc = round((pred_cases / pop) * 100000.0, 2)
        ci_lower = max(0.0, round(pred_cases - 1.96 * rmse, 2))
        ci_upper = round(pred_cases + 1.96 * rmse, 2)

        # Risk level determination based on predicted incidence and antecedent climate
        rain_lag = float(row["rainfall_lag_2w"])
        humidity = float(row["avg_humidity_pct"])
        
        if pred_inc >= 50.0 or (pred_inc >= 20.0 and rain_lag >= 80.0 and humidity >= 80.0):
            risk_level = "Severe"
        elif pred_inc >= 20.0 or (pred_inc >= 10.0 and rain_lag >= 50.0):
            risk_level = "High"
        elif pred_inc >= 5.0 or rain_lag >= 60.0:
            risk_level = "Moderate"
        else:
            risk_level = "Low"

        forecast_id = f"{loc_key}_{base_week}_H4"
        
        records_to_insert.append((
            forecast_id,
            loc_key,
            base_week,
            target_week,
            pred_cases,
            pred_inc,
            ci_lower,
            ci_upper,
            risk_level,
            model_name,
            round(r2, 4),
            round(mae, 2)
        ))

    # Batch upsert into PostgreSQL
    upsert_sql = """
    INSERT INTO gold.fact_outbreak_forecast_weekly (
        forecast_id, location_key, base_epi_week_key, forecast_epi_week_key,
        predicted_cases_4w, predicted_incidence_rate_per_100k,
        confidence_lower_bound, confidence_upper_bound, predicted_risk_level,
        model_name, r2_score, mae_score, created_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (forecast_id) DO UPDATE SET
        predicted_cases_4w = EXCLUDED.predicted_cases_4w,
        predicted_incidence_rate_per_100k = EXCLUDED.predicted_incidence_rate_per_100k,
        confidence_lower_bound = EXCLUDED.confidence_lower_bound,
        confidence_upper_bound = EXCLUDED.confidence_upper_bound,
        predicted_risk_level = EXCLUDED.predicted_risk_level,
        r2_score = EXCLUDED.r2_score,
        mae_score = EXCLUDED.mae_score,
        created_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        from psycopg2.extras import execute_batch
        execute_batch(cur, upsert_sql, records_to_insert, page_size=500)
        conn.commit()

    logger.info("Successfully upserted %d outbreak forecast records into gold.fact_outbreak_forecast_weekly.", len(records_to_insert))


def run_pipeline():
    """Main execution entrypoint for Sprint 6 ML Pipeline."""
    logger.info("=== Starting Sprint 6 Predictive Analytics Pipeline ===")
    conn = get_db_connection()
    try:
        init_forecast_table(conn)
        df_raw = extract_features(conn)
        df_featured, feature_cols = engineer_ml_dataset(df_raw)
        model, model_name, r2, mae, rmse = train_model(df_featured, feature_cols)
        generate_forecasts(model, model_name, r2, mae, rmse, df_featured, feature_cols, conn)
        logger.info("=== Sprint 6 Pipeline Completed Successfully ===")
    finally:
        conn.close()


if __name__ == "__main__":
    run_pipeline()
