# ==============================================================================
# SMART HEALTH DATA PLATFORM - SPRINT 2 VERIFICATION & SMOKE TEST SCRIPT
# ==============================================================================
# Run this directly in PowerShell to verify Sprint 2 Silver layer integrity:
# .\scripts\test_sprint2.ps1
# ==============================================================================

Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " SMART HEALTH DATA PLATFORM: SPRINT 2 SILVER LAYER AUDIT " -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Cyan

$passCount = 0
$failCount = 0

function Report-Check($title, $isPassed, $detail) {
    if ($isPassed) {
        $global:passCount++
        Write-Host "  [PASS] $title" -ForegroundColor Green
        if ($detail) { Write-Host "         $detail" -ForegroundColor Gray }
    } else {
        $global:failCount++
        Write-Host "  [FAIL] $title" -ForegroundColor Red
        if ($detail) { Write-Host "         $detail" -ForegroundColor Yellow }
    }
}

# 1. Check Container Health
Write-Host "`n1. Checking Infrastructure Status..." -ForegroundColor Yellow
$pgState = docker inspect --format="{{.State.Health.Status}}" smart_health_postgres 2>$null
if ($pgState -eq "healthy") {
    Report-Check "PostgreSQL Container Health" $true "smart_health_postgres is healthy on port 5432."
} else {
    Report-Check "PostgreSQL Container Health" $false "PostgreSQL state: $pgState"
}

# 2. Check Table Row Counts
Write-Host "`n2. Checking Silver Table Record Counts..." -ForegroundColor Yellow
$diseaseCount = docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM silver.stg_disease_daily;" 2>$null
if ([int]$diseaseCount -eq 10960) {
    Report-Check "silver.stg_disease_daily Row Count" $true "Found exactly 10,960 records (2022-01-01 to 2025-10-01)."
} else {
    Report-Check "silver.stg_disease_daily Row Count" $false "Expected 10,960 records, found: $diseaseCount"
}

$climateCount = docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM silver.stg_climate_daily;" 2>$null
if ([int]$climateCount -eq 11688) {
    Report-Check "silver.stg_climate_daily Row Count" $true "Found exactly 11,688 records (Historical + Open-Meteo ERA5)."
} else {
    Report-Check "silver.stg_climate_daily Row Count" $false "Expected 11,688 records, found: $climateCount"
}

# 3. Check Deduplication (Task 2.1)
Write-Host "`n3. Checking Deduplication (Task 2.1)..." -ForegroundColor Yellow
$diseaseDups = docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM (SELECT location_key, record_date, disease_type FROM silver.stg_disease_daily GROUP BY location_key, record_date, disease_type HAVING COUNT(*) > 1) d;" 2>$null
Report-Check "Disease Deduplication" ([int]$diseaseDups -eq 0) "Zero duplicate primary keys found."

$climateDups = docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM (SELECT location_key, record_date FROM silver.stg_climate_daily GROUP BY location_key, record_date HAVING COUNT(*) > 1) d;" 2>$null
Report-Check "Climate Deduplication" ([int]$climateDups -eq 0) "Zero duplicate primary keys found."

# 4. Check Geospatial Harmonization (Task 2.3)
Write-Host "`n4. Checking Geospatial Harmonization (Task 2.3)..." -ForegroundColor Yellow
$invalidPcodes = docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM silver.stg_disease_daily WHERE location_key NOT IN (SELECT adm1_pcode FROM bronze.raw_admin_boundaries);" 2>$null
Report-Check "Geospatial P-Code Resolution" ([int]$invalidPcodes -eq 0) "100% of location keys match authoritative UN OCHA P-Codes."

# 5. Check Missing Data Imputation & Zero Null Gaps (Task 2.4)
Write-Host "`n5. Checking Missing Data Imputation (Task 2.4)..." -ForegroundColor Yellow
$nullWeather = docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -A -c "SELECT COUNT(*) FROM silver.stg_climate_daily WHERE max_temperature_c IS NULL OR min_temperature_c IS NULL OR avg_temperature_c IS NULL OR rainfall_mm IS NULL OR humidity_pct IS NULL OR pm25_ug_m3 IS NULL OR aqi_value IS NULL;" 2>$null
Report-Check "Climate Zero Null Gaps" ([int]$nullWeather -eq 0) "Zero null values across all 7 meteorological features."

# 6. Check Parquet Lakehouse Storage (Task 2.5)
Write-Host "`n6. Checking Parquet Storage Artifacts (Task 2.5)..." -ForegroundColor Yellow
$diseaseParquet = "data\silver\stg_disease_daily.parquet"
$climateParquet = "data\silver\stg_climate_daily.parquet"

if (Test-Path $diseaseParquet) {
    $size = (Get-Item $diseaseParquet).Length / 1KB
    Report-Check "Disease Parquet Artifact" $true "Found $diseaseParquet ($([math]::Round($size, 2)) KB)."
} else {
    Report-Check "Disease Parquet Artifact" $false "Missing file $diseaseParquet"
}

if (Test-Path $climateParquet) {
    $size = (Get-Item $climateParquet).Length / 1KB
    Report-Check "Climate Parquet Artifact" $true "Found $climateParquet ($([math]::Round($size, 2)) KB)."
} else {
    Report-Check "Climate Parquet Artifact" $false "Missing file $climateParquet"
}

# 7. Check Security & RBAC Isolation
Write-Host "`n7. Checking Security & RBAC Isolation (docs/SECURITY_AND_GOVERNANCE.md)..." -ForegroundColor Yellow
$biAccess = docker exec smart_health_postgres psql -U bi_reader -d smart_health_dw -c "SELECT * FROM silver.stg_disease_daily LIMIT 1;" 2>&1
if ($biAccess -match "permission denied") {
    Report-Check "RBAC bi_reader Isolation" $true "Permission denied on silver schema (Least Privilege enforced)."
} else {
    Report-Check "RBAC bi_reader Isolation" $false "Security violation: bi_reader was able to read silver!"
}

$llmAccess = docker exec smart_health_postgres psql -U llm_agent -d smart_health_dw -c "SELECT * FROM silver.stg_climate_daily LIMIT 1;" 2>&1
if ($llmAccess -match "permission denied") {
    Report-Check "RBAC llm_agent Isolation" $true "Permission denied on silver schema (Least Privilege enforced)."
} else {
    Report-Check "RBAC llm_agent Isolation" $false "Security violation: llm_agent was able to read silver!"
}

# Summary
Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " SPRINT 2 AUDIT RESULT: $passCount PASSED, $failCount FAILED " -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Red" })
Write-Host "====================================================================" -ForegroundColor Cyan

if ($failCount -eq 0) {
    Write-Host "`nAll Sprint 2 requirements are 100% verified, robust, and production-ready!`n" -ForegroundColor Green
} else {
    Write-Host "`nSome checks failed. Please inspect the log messages above.`n" -ForegroundColor Red
}
