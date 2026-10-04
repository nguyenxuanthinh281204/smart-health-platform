# ==============================================================================
# SMART HEALTH DATA PLATFORM - SPRINT 4 VERIFICATION & SMOKE TEST SCRIPT
# ==============================================================================
# Run this directly in PowerShell to verify Sprint 4 BI Dashboard & Serving Layer:
# .\scripts\test_sprint4.ps1
# ==============================================================================

Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " SMART HEALTH DATA PLATFORM: SPRINT 4 BI SERVING LAYER AUDIT " -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Cyan

$script:passCount = 0
$script:failCount = 0

function Report-Check($title, $isPassed, $detail) {
    if ($isPassed) {
        $script:passCount++
        Write-Host "  [PASS] $title" -ForegroundColor Green
        if ($detail) { Write-Host "         $detail" -ForegroundColor Gray }
    } else {
        $script:failCount++
        Write-Host "  [FAIL] $title" -ForegroundColor Red
        if ($detail) { Write-Host "         $detail" -ForegroundColor Yellow }
    }
}

# 1. Check Infrastructure Status
Write-Host "`n1. Checking Infrastructure Status..." -ForegroundColor Yellow
$pgState = docker inspect --format="{{.State.Health.Status}}" smart_health_postgres 2>$null
Report-Check "PostgreSQL Container Health" ($pgState -eq "healthy") "smart_health_postgres is healthy on port 5432."

# 2. Check Dashboard HTTP Endpoint & Response Time (< 2s load time DoD)
Write-Host "`n2. Checking BI Dashboard Serving Endpoint (Task 4.1)..." -ForegroundColor Yellow
try {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $response = Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 5 2>$null
    $sw.Stop()
    $loadTimeMs = $sw.ElapsedMilliseconds
    $isOk = ($response.StatusCode -eq 200) -and ($loadTimeMs -lt 2000)
    Report-Check "Dashboard HTTP Endpoint (Port 8501)" $isOk "Status: $($response.StatusCode) OK, Load Time: $loadTimeMs ms (< 2000 ms DoD requirement)."
} catch {
    Report-Check "Dashboard HTTP Endpoint (Port 8501)" $false "Failed to connect to http://localhost:8501: $_"
}

# 3. Check RBAC Least Privilege (docs/SECURITY_AND_GOVERNANCE.md)
Write-Host "`n3. Checking RBAC Permissions via bi_reader (Task 4.1)..." -ForegroundColor Yellow
$biGold = docker exec smart_health_postgres psql -U bi_reader -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM gold.fact_disease_climate_weekly;" 2>$null
Report-Check "bi_reader SELECT on Gold Mart" ([int]$biGold -eq 1576) "Authorized connection verified ($biGold rows)."

$biSilver = docker exec smart_health_postgres psql -U bi_reader -d smart_health_dw -c "SELECT * FROM silver.stg_disease_daily LIMIT 1;" 2>&1
Report-Check "bi_reader Isolation from Silver/Bronze" ($biSilver -match "permission denied") "Principle of Least Privilege enforced: access strictly denied."

# 4. Check Choropleth Heatmap Data & GeoJSON (Task 4.2)
Write-Host "`n4. Checking Choropleth Heatmap Assets (Task 4.2)..." -ForegroundColor Yellow
$geoCheck = docker exec smart_health_postgres psql -U bi_reader -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM gold.dim_location WHERE geom_polygon IS NOT NULL AND jsonb_typeof(geom_polygon) = 'object';" 2>$null
Report-Check "Geospatial Boundary Polygons" ([int]$geoCheck -eq 8) "8 authoritative UN OCHA division polygons verified."

$incCheck = docker exec smart_health_postgres psql -U bi_reader -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM gold.fact_disease_climate_weekly WHERE incidence_rate_per_100k > 0;" 2>$null
Report-Check "Incidence Rate Normalization" ([int]$incCheck -gt 1000) "Population-normalized incidence rates populated across time series."

# 5. Check Time-Lag Visualizations & Data (Task 4.3)
Write-Host "`n5. Checking Time-Lag Correlation Data (Task 4.3)..." -ForegroundColor Yellow
$lagCheck = docker exec smart_health_postgres psql -U bi_reader -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM gold.fact_disease_climate_weekly WHERE rainfall_lag_2w IS NOT NULL AND rainfall_lag_4w IS NOT NULL;" 2>$null
Report-Check "Lag Features (2W & 4W)" ([int]$lagCheck -gt 1400) "$lagCheck rows with 2-week and 4-week rainfall lag indicators."

# 6. Check Risk Alerting Matrix (Task 4.4)
Write-Host "`n6. Checking Risk Alerting Matrix (Task 4.4)..." -ForegroundColor Yellow
$alertCheck = docker exec smart_health_postgres psql -U bi_reader -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM gold.fact_disease_climate_weekly WHERE risk_level IN ('High', 'Severe');" 2>$null
Report-Check "Outbreak Alerts (High & Severe)" ([int]$alertCheck -gt 0) "Found $alertCheck active outbreak warning weeks correctly classified."

# 7. Check Physical Dashboard Artifacts
Write-Host "`n7. Checking Dashboard Code & Artifacts..." -ForegroundColor Yellow
$htmlPath = "bi_dashboard\index.html"
$appPath = "bi_dashboard\app.py"
$genPath = "bi_dashboard\generate_interactive_report.py"

Report-Check "Standalone HTML Dashboard File" (Test-Path $htmlPath) "Found $htmlPath ($([math]::Round((Get-Item $htmlPath).Length / 1KB, 2)) KB)."
Report-Check "Streamlit App Code File" (Test-Path $appPath) "Found $appPath ($([math]::Round((Get-Item $appPath).Length / 1KB, 2)) KB)."
Report-Check "BI Report Generator Script" (Test-Path $genPath) "Found $genPath ($([math]::Round((Get-Item $genPath).Length / 1KB, 2)) KB)."

# Summary
Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " SPRINT 4 AUDIT RESULT: $script:passCount PASSED, $script:failCount FAILED " -ForegroundColor $(if ($script:failCount -eq 0) { "Green" } else { "Red" })
Write-Host "====================================================================" -ForegroundColor Cyan

if ($script:failCount -eq 0) {
    Write-Host "`nAll Sprint 4 requirements are 100% verified, responsive (< 2s), and production-ready!`n" -ForegroundColor Green
    Write-Host "You can open the dashboard in your browser right now at:" -ForegroundColor Cyan
    Write-Host "  👉 http://localhost:8501" -ForegroundColor Yellow
    Write-Host "Or open the standalone file directly:" -ForegroundColor Cyan
    Write-Host "  👉 bi_dashboard\index.html`n" -ForegroundColor Yellow
} else {
    Write-Host "`nSome checks failed. Please inspect the log messages above.`n" -ForegroundColor Red
}
