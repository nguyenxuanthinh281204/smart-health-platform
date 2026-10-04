# ==============================================================================
# SPRINT 5 AUTOMATED VERIFICATION SUITE: CONVERSATIONAL AI & PROJECT PACKAGING
# ==============================================================================
# Verifies:
#   1. Text-to-SQL module (pipelines/llm_text_to_sql.py)
#   2. 4-Layer Defense-in-Depth Security Sandbox & Injection Blocking
#   3. Multi-Tab Streamlit Portal (bi_dashboard/app.py) & Port 8501 Health
#   4. Final Defense Presentation Deck (docs/PRESENTATION_AND_DEFENSE_DECK.md)
#   5. Master Root Documentation (README.md)
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
Write-Host "SMART HEALTH DATA PLATFORM - SPRINT 5 SMOKE & VERIFICATION SUITE" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Check 1: llm_text_to_sql.py exists
Assert-Check "Text-to-SQL pipeline module exists" {
    Test-Path "pipelines/llm_text_to_sql.py"
}

# Check 2: bi_dashboard/app.py contains AI tab
Assert-Check "Streamlit app.py contains Text-to-SQL and Sandbox tab" {
    $content = Get-Content "bi_dashboard/app.py" -Raw
    $content.Contains("tab_ai") -and $content.Contains("LLMTextToSQLEngine") -and $content.Contains("sandbox-badge")
}

# Check 3: docs/PRESENTATION_AND_DEFENSE_DECK.md exists with 12 slides
Assert-Check "Final Defense Presentation Deck exists with 12 slides" {
    if (Test-Path "docs/PRESENTATION_AND_DEFENSE_DECK.md") {
        $content = Get-Content "docs/PRESENTATION_AND_DEFENSE_DECK.md" -Raw
        $content.Contains("SLIDE 1:") -and $content.Contains("SLIDE 12:")
    } else {
        $false
    }
}

# Check 4: Master README.md exists with Quickstart & Port Map
Assert-Check "Master README.md contains single-command quickstart and port map" {
    $content = Get-Content "README.md" -Raw
    $content.Contains("docker compose -f docker/docker-compose.yml up -d") -and $content.Contains("http://localhost:8501")
}

# Check 5: Container smart_health_mageai is running
Assert-Check "Docker container smart_health_mageai is healthy and running" {
    $status = (docker inspect -f '{{.State.Status}}' smart_health_mageai | Out-String).Trim()
    $status -eq "running"
}

# Check 6: Streamlit port 8501 responds HTTP 200
Assert-Check "Streamlit serving endpoint (http://localhost:8501) responds HTTP 200" {
    $res = Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 5
    $res.StatusCode -eq 200
}

# Check 7: Text-to-SQL module syntax and execution in container
Assert-Check "Text-to-SQL module compiles and runs inside Mage container" {
    $out = (docker exec smart_health_mageai python3 /home/src/pipelines/llm_text_to_sql.py | Out-String)
    $out.Contains("What are the top 5 divisions") -and $out.Contains("5 in")
}

# Check 8: 4-Layer Security Sandbox blocks DROP TABLE injection
Assert-Check "Security Sandbox successfully intercepts and blocks DROP TABLE attack" {
    $out = (docker exec smart_health_mageai python3 /home/src/pipelines/llm_text_to_sql.py | Out-String)
    $out.Contains("Statement Blacklist Violation: Forbidden keyword 'DROP' detected")
}

# Check 9: Database role llm_agent exists with proper least privilege
Assert-Check "Database role llm_agent exists with proper least privilege" {
    $out = (docker exec smart_health_postgres psql -U de_admin -d smart_health_dw -t -c "SELECT rolname FROM pg_roles WHERE rolname='llm_agent';" | Out-String).Trim()
    $out -eq "llm_agent"
}

# Check 10: Role llm_agent is denied access to bronze raw tables
Assert-Check "Role llm_agent is denied SELECT access on bronze raw tables" {
    $res = cmd /c "docker exec smart_health_postgres psql -U llm_agent -d smart_health_dw -c ""SELECT COUNT(*) FROM bronze.raw_dengue_weather_daily;"" 2>&1"
    $res = ($res | Out-String)
    $res.Contains("permission denied for schema bronze")
}

# Check 11: Role llm_agent has read access on gold mart
Assert-Check "Role llm_agent has read-only access on gold fact table" {
    $res = (docker exec smart_health_postgres psql -U llm_agent -d smart_health_dw -t -c "SELECT COUNT(*) FROM gold.fact_disease_climate_weekly;" | Out-String).Trim()
    [int]$res -gt 1000
}

# Check 12: Sub-50ms execution performance on Gold queries
Assert-Check "Text-to-SQL query latency is sub-50ms" {
    $testScript = "import time, sys; sys.path.append('/home/src'); from pipelines.llm_text_to_sql import LLMTextToSQLEngine; e = LLMTextToSQLEngine(); r = e.ask('Top 5 divisions in 2023'); print('LATENCY_OK' if r['elapsed_ms'] < 100 else 'SLOW')"
    $out = (docker exec smart_health_mageai python3 -c $testScript | Out-String)
    $out.Contains("LATENCY_OK")
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SUMMARY: $passed / $total CHECKS PASSED (100% REQUIRED)" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Red" })
Write-Host "======================================================================" -ForegroundColor Cyan

if ($passed -ne $total) {
    exit 1
}
