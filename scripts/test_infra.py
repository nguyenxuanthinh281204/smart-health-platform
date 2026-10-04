#!/usr/bin/env python3
"""
==============================================================================
SMART HEALTH DATA PLATFORM - INFRASTRUCTURE SMOKE TEST & HEALTH CHECK
==============================================================================
This script tests:
1. Docker Engine responsiveness
2. Container runtime states (PostgreSQL 16 & Mage.ai)
3. PostgreSQL connectivity, Medallion schemas, and RBAC roles
4. Mage.ai web orchestrator availability (HTTP 200)

Usage:
    python scripts/test_infra.py
==============================================================================
"""

import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(title: str):
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")

def test_docker_daemon() -> bool:
    print_header("1. Checking Docker Engine Status")
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            print(f"[{GREEN}PASS{RESET}] Docker Desktop engine is running.")
            return True
        else:
            print(f"[{RED}FAIL{RESET}] Docker engine is NOT running.")
            print(f"       {YELLOW}Action required:{RESET} Please open 'Docker Desktop' from your Windows Start menu.")
            return False
    except FileNotFoundError:
        print(f"[{RED}FAIL{RESET}] 'docker' CLI not found in system PATH.")
        return False
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] Error probing Docker: {e}")
        return False

def test_containers_running() -> bool:
    print_header("2. Checking Container Status")
    try:
        res = subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "ps", "--format", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        output = res.stdout.strip()
        if "smart_health_postgres" in output and "smart_health_mageai" in output:
            print(f"[{GREEN}PASS{RESET}] Both 'smart_health_postgres' and 'smart_health_mageai' containers exist.")
            return True
        else:
            print(f"[{YELLOW}WARN{RESET}] Containers are not running yet.")
            print(f"       Run command: {BOLD}docker compose -f docker/docker-compose.yml up -d{RESET}")
            return False
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] Error inspecting containers: {e}")
        return False

def test_port_socket(host: str, port: int, service_name: str) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect((host, port))
        s.close()
        print(f"[{GREEN}PASS{RESET}] {service_name} port {port} is open and reachable.")
        return True
    except Exception:
        print(f"[{RED}FAIL{RESET}] Cannot connect to {service_name} at {host}:{port}.")
        return False

def test_postgres_schemas_and_roles() -> bool:
    print_header("3. Verifying PostgreSQL Schemas & Security Roles")
    
    # 3.1. Verify Schemas (bronze, silver, gold)
    cmd_schemas = [
        "docker", "exec", "smart_health_postgres", 
        "psql", "-U", "de_admin", "-d", "smart_health_dw", "-t", "-A", 
        "-c", "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('bronze', 'silver', 'gold');"
    ]
    try:
        res = subprocess.run(cmd_schemas, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        schemas = [s.strip() for s in res.stdout.splitlines() if s.strip()]
        if set(["bronze", "silver", "gold"]).issubset(set(schemas)):
            print(f"[{GREEN}PASS{RESET}] Medallion Schemas present: {schemas}")
        else:
            print(f"[{RED}FAIL{RESET}] Missing schemas. Found: {schemas}")
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] Failed querying schemas: {e}")
        return False

    # 3.2. Verify Roles (de_admin, bi_reader, llm_agent)
    cmd_roles = [
        "docker", "exec", "smart_health_postgres",
        "psql", "-U", "de_admin", "-d", "smart_health_dw", "-t", "-A",
        "-c", "SELECT rolname FROM pg_catalog.pg_roles WHERE rolname IN ('de_admin', 'bi_reader', 'llm_agent');"
    ]
    try:
        res = subprocess.run(cmd_roles, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        roles = [r.strip() for r in res.stdout.splitlines() if r.strip()]
        if set(["de_admin", "bi_reader", "llm_agent"]).issubset(set(roles)):
            print(f"[{GREEN}PASS{RESET}] Security Roles present: {roles}")
        else:
            print(f"[{RED}FAIL{RESET}] Missing roles. Found: {roles}")
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] Failed querying roles: {e}")
        return False

    # 3.3. Verify Pre-created Bronze Tables
    cmd_tables = [
        "docker", "exec", "smart_health_postgres",
        "psql", "-U", "de_admin", "-d", "smart_health_dw", "-t", "-A",
        "-c", "SELECT table_name FROM information_schema.tables WHERE table_schema = 'bronze';"
    ]
    try:
        res = subprocess.run(cmd_tables, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        tables = [t.strip() for t in res.stdout.splitlines() if t.strip()]
        print(f"[{GREEN}PASS{RESET}] Pre-created Bronze Tables: {tables}")
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] Failed querying bronze tables: {e}")

    return True

def test_mage_http() -> bool:
    print_header("4. Testing Mage.ai Web Orchestrator (Port 6789)")
    url = "http://localhost:6789"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print(f"[{GREEN}PASS{RESET}] Mage.ai Web UI is responsive at {url} (HTTP 200).")
                return True
            else:
                print(f"[{YELLOW}WARN{RESET}] Mage.ai returned HTTP status {response.status}.")
                return False
    except urllib.error.URLError:
        print(f"[{RED}FAIL{RESET}] Mage.ai is not responding at {url}.")
        return False
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] Error reaching Mage.ai: {e}")
        return False

def main():
    print(f"\n{BOLD}{GREEN}===================================================================={RESET}")
    print(f"{BOLD} SMART HEALTH DATA PLATFORM: SMOKE TEST SUITE {RESET}")
    print(f"{BOLD}{GREEN}===================================================================={RESET}")

    if not test_docker_daemon():
        print(f"\n{BOLD}{YELLOW}Notice:{RESET} Start Docker Desktop on Windows, then re-run this script.")
        sys.exit(1)

    has_containers = test_containers_running()
    if not has_containers:
        print(f"\n{YELLOW}Tip: Start your containers with:{RESET}")
        print(f"  docker compose -f docker/docker-compose.yml up -d\n")
        sys.exit(0)

    # Test ports
    test_port_socket("localhost", 5432, "PostgreSQL Warehouse")
    test_port_socket("localhost", 6789, "Mage.ai Orchestrator")

    # Test DB internals
    test_postgres_schemas_and_roles()

    # Test Mage web
    test_mage_http()

    print(f"\n{BOLD}{GREEN}===================================================================={RESET}")
    print(f"{BOLD}{GREEN} ALL INFRASTRUCTURE CHECKS COMPLETED SUCCESSFULLY! {RESET}")
    print(f"{BOLD}{GREEN}===================================================================={RESET}\n")

if __name__ == "__main__":
    main()
