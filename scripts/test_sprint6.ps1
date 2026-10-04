# ==============================================================================
# SPRINT 6 AUTOMATED VERIFICATION SUITE: PREDICTIVE MACHINE LEARNING FORECASTING
# ==============================================================================
# Verifies:
#   1. Predictive ML Pipeline (pipelines/train_predictive_model.py)
#   2. Model Artifact & Evaluation Metrics (models/model_metrics.json R2 > 0.65)
#   3. Gold Layer Forecast Table (gold.fact_outbreak_forecast_weekly)
#   4. Referential Integrity & 8 Administrative Divisions Coverage
#   5. Multi-Tier RBAC (bi_reader & llm_agent read access)
#   6. Interactive Streamlit Forecast UI & Port 8501 Health
# ==============================================================================

$passed = 0
$total = 0

function Assert-Check {
    param(
        [string]$Description,
        [scriptblock]$Test
    )
    $script:total++
    Write-Host -NoNewline "[$script:total] Checking: $Description... "
    try {
        $result = & $Test
        if ($result -eq $true) {
            Write-Host -ForegroundColor Green "[PASS]"
            $script:passed++
        } else {
            Write-Host -ForegroundColor Red "[FAIL] - Assertion returned false"
        }
    } catch {
        Write-Host -ForegroundColor Red "[FAIL] - Error: $_"
    }
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "SMART HEALTH DATA PLATFORM - SPRINT 6 PREDICTIVE ML AUDIT SUITE" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Check 1: Training pipeline exists
Assert-Check "Machine Learning pipeline (train_predictive_model.py) exists" {
    Test-Path "pipelines/train_predictive_model.py"
}

# Check 2: Model artifact exists
Assert-Check "Trained ML model artifact (.joblib) exists" {
    Test-Path "models/dengue_outbreak_forecast_4w.joblib"
}

# Check 3: Model metrics validation (R2 > 0.65)
Assert-Check "Model evaluation metrics exist and R2 score > 0.65" {
    if (Test-Path "models/model_metrics.json") {
        $json = Get-Content "models/model_metrics.json" -Raw | ConvertFrom-Json
        $json.r2_score -gt 0.65 -and $json.mae -gt 0
    } else {
        $false
    }
}

# Check 4: gold.fact_outbreak_forecast_weekly table exists in PostgreSQL
Assert-Check "gold.fact_outbreak_forecast_weekly table exists in PostgreSQL" {
    $out = (docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -c "SELECT to_regclass('gold.fact_outbreak_forecast_weekly');" | Out-String).Trim()
    $out -eq "gold.fact_outbreak_forecast_weekly"
}

# Check 5: Forecast table row count equals 1576
Assert-Check "Forecast table populated with full historical & future horizons (1576 rows)" {
    $cnt = (docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -c "SELECT COUNT(*) FROM gold.fact_outbreak_forecast_weekly;" | Out-String).Trim()
    [int]$cnt -eq 1576
}

# Check 6: All 8 administrative divisions covered
Assert-Check "All 8 administrative divisions have 4-week forward projections" {
    $divs = (docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -c "SELECT COUNT(DISTINCT location_key) FROM gold.fact_outbreak_forecast_weekly;" | Out-String).Trim()
    [int]$divs -eq 8
}

# Check 7: Referential Integrity between forecast fact and dim_location
Assert-Check "Zero orphan location keys in gold.fact_outbreak_forecast_weekly" {
    $orphans = (docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -c "SELECT COUNT(*) FROM gold.fact_outbreak_forecast_weekly fc LEFT JOIN gold.dim_location l ON fc.location_key = l.location_key WHERE l.location_key IS NULL;" | Out-String).Trim()
    [int]$orphans -eq 0
}

# Check 8: bi_reader has read access to forecast table
Assert-Check "Role bi_reader has authorized SELECT access to forecast table" {
    $res = (docker exec smart_health_postgres psql -U bi_reader -d smart_health_dw -t -c "SELECT COUNT(*) FROM gold.fact_outbreak_forecast_weekly;" | Out-String).Trim()
    [int]$res -eq 1576
}

# Check 9: llm_agent has read access to forecast table
Assert-Check "Role llm_agent has authorized SELECT access to forecast table" {
    $res = (docker exec smart_health_postgres psql -U llm_agent -d smart_health_dw -t -c "SELECT COUNT(*) FROM gold.fact_outbreak_forecast_weekly;" | Out-String).Trim()
    [int]$res -eq 1576
}

# Check 10: Text-to-SQL engine can query forecast table via natural language
Assert-Check "AI Assistant translates natural language query to forecast SQL" {
    $script = "import sys; sys.path.append('/home/src'); from pipelines.llm_text_to_sql import LLMTextToSQLEngine; e = LLMTextToSQLEngine(); r = e.ask('Show 4-week ahead outbreak forecasts across all divisions'); print('SUCCESS' if r['success'] and r['row_count'] > 0 else 'FAIL')"
    $out = (docker exec smart_health_mageai python3 -c $script | Out-String)
    $out.Contains("SUCCESS")
}

# Check 11: Streamlit app.py contains Tab 3 for Predictive Analytics
Assert-Check "Streamlit app.py contains tab_pred and predictive charts" {
    $content = Get-Content "bi_dashboard/app.py" -Raw
    $content.Contains("tab_pred") -and $content.Contains("pred_chart_actual_vs_forecast") -and $content.Contains("pred_chart_feature_importance")
}

# Check 12: Streamlit serving port 8501 responds HTTP 200
Assert-Check "Streamlit serving portal (http://localhost:8501) responds HTTP 200" {
    $res = Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 5
    $res.StatusCode -eq 200
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SUMMARY: $passed / $total CHECKS PASSED (100% REQUIRED)" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Red" })
Write-Host "======================================================================" -ForegroundColor Cyan

if ($passed -ne $total) {
    exit 1
}
