# ==============================================================================
# SMART HEALTH DATA PLATFORM - WINDOWS POWERSHELL SMOKE TEST & HEALTH CHECK
# ==============================================================================
# Run this anytime to verify your Docker, Database, and Mage.ai connections:
# .\scripts\test_infra.ps1
# ==============================================================================

Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " SMART HEALTH DATA PLATFORM: INFRASTRUCTURE HEALTH CHECK " -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Cyan

# 1. Test Docker Desktop Daemon
Write-Host "`n1. Checking Docker Engine Status..." -ForegroundColor Yellow
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Docker Desktop engine is NOT running." -ForegroundColor Red
    Write-Host "       Action: Please open 'Docker Desktop' from your Windows Start Menu and wait 20s until the whale icon turns green." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "[PASS] Docker Desktop engine is running smoothly." -ForegroundColor Green
}

# 2. Test Container Status
Write-Host "`n2. Checking Docker Containers..." -ForegroundColor Yellow
$containers = docker compose -f docker/docker-compose.yml ps 2>&1
if ($containers -match "smart_health_postgres" -and $containers -match "smart_health_mageai") {
    Write-Host "[PASS] Both containers ('smart_health_postgres' & 'smart_health_mageai') are registered." -ForegroundColor Green
} else {
    Write-Host "[WARN] Containers are not running yet." -ForegroundColor Yellow
    Write-Host "       Start them with: docker compose -f docker/docker-compose.yml up -d" -ForegroundColor Cyan
    exit 0
}

# 3. Test PostgreSQL Port 5432
Write-Host "`n3. Testing PostgreSQL Port 5432..." -ForegroundColor Yellow
$tcpPg = Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet
if ($tcpPg) {
    Write-Host "[PASS] Port 5432 is open and listening." -ForegroundColor Green
} else {
    Write-Host "[FAIL] Cannot reach PostgreSQL on port 5432." -ForegroundColor Red
}

# 4. Test Medallion Schemas in Database
Write-Host "`n4. Verifying Medallion Schemas (bronze, silver, gold)..." -ForegroundColor Yellow
$schemaCheck = docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -A -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('bronze', 'silver', 'gold');" 2>&1
if ($schemaCheck -match "bronze" -and $schemaCheck -match "silver" -and $schemaCheck -match "gold") {
    Write-Host "[PASS] All 3 Medallion Schemas found: bronze, silver, gold." -ForegroundColor Green
} else {
    Write-Host "[FAIL] Missing schemas. Output: $schemaCheck" -ForegroundColor Red
}

# 5. Test RBAC Security Roles
Write-Host "`n5. Verifying RBAC Security Roles (de_admin, bi_reader, llm_agent)..." -ForegroundColor Yellow
$rolesCheck = docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -A -c "SELECT rolname FROM pg_catalog.pg_roles WHERE rolname IN ('de_admin', 'bi_reader', 'llm_agent');" 2>&1
if ($rolesCheck -match "de_admin" -and $rolesCheck -match "bi_reader" -and $rolesCheck -match "llm_agent") {
    Write-Host "[PASS] All 3 RBAC Roles found: de_admin, bi_reader, llm_agent." -ForegroundColor Green
} else {
    Write-Host "[FAIL] Missing roles. Output: $rolesCheck" -ForegroundColor Red
}

# 6. Test Mage.ai Web Orchestrator Port 6789
Write-Host "`n6. Testing Mage.ai Web Orchestrator (Port 6789)..." -ForegroundColor Yellow
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:6789" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
        Write-Host "[PASS] Mage.ai Web UI is responsive at http://localhost:6789 (HTTP 200)." -ForegroundColor Green
    }
} catch {
    Write-Host "[WARN] Mage.ai is still initializing or unreachable on port 6789." -ForegroundColor Yellow
}

Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " ALL CHECKS COMPLETED!" -ForegroundColor Green
Write-Host "====================================================================`n" -ForegroundColor Cyan
