"""
==============================================================================
SMART HEALTH DATA PLATFORM - GEOSPATIAL HARMONIZATION MODULE
==============================================================================
Standardizes provincial / administrative unit names to authoritative
UN OCHA P-Codes (Admin-1) per docs/DATA_CONTRACTS.md and docs/DOMAIN_RULES_AND_METRICS.md.

Enforces Task 2.3: Geospatial Harmonization.
==============================================================================
"""

import os
import re
import logging
from typing import Dict, Optional
import psycopg2

logger = logging.getLogger("GeospatialHarmonizer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class GeospatialHarmonizationError(Exception):
    """Raised when a location identifier cannot be mapped to an authoritative UN OCHA P-Code."""
    pass


class GeospatialHarmonizer:
    """Authoritative lookup resolver for UN OCHA P-Codes."""

    COMMON_ALIASES: Dict[str, str] = {
        # Common English spelling variations for Bangladesh Divisions
        "barishal": "BD-10",
        "barisal": "BD-10",
        "chattogram": "BD-20",
        "chittagong": "BD-20",
        "dhaka": "BD-30",
        "dacca": "BD-30",
        "khulna": "BD-40",
        "mymensingh": "BD-45",
        "rajshahi": "BD-50",
        "rangpur": "BD-55",
        "sylhet": "BD-60",
    }

    def __init__(self, db_conn=None):
        self.pcode_map: Dict[str, str] = {}
        self.valid_pcodes: set = set()
        self._load_authoritative_pcodes(db_conn)

    def _load_authoritative_pcodes(self, db_conn=None):
        """Loads boundary master records from bronze.raw_admin_boundaries."""
        own_conn = False
        try:
            if db_conn is None:
                db_conn = psycopg2.connect(
                    host=os.getenv("POSTGRES_HOST", "postgres"),
                    port=int(os.getenv("POSTGRES_PORT", 5432)),
                    database=os.getenv("POSTGRES_DB", "smart_health_dw"),
                    user=os.getenv("POSTGRES_USER", "de_admin"),
                    password=os.getenv("POSTGRES_PASSWORD", "de_admin_secure_pass_2026"),
                )
                own_conn = True

            with db_conn.cursor() as cur:
                cur.execute("SELECT adm1_pcode, adm1_name_en FROM bronze.raw_admin_boundaries;")
                rows = cur.fetchall()

            for pcode, name in rows:
                clean_pcode = pcode.strip().upper()
                self.valid_pcodes.add(clean_pcode)
                # Map exact P-Code
                self.pcode_map[clean_pcode.lower()] = clean_pcode
                # Map division name
                clean_name = self._normalize_str(name)
                self.pcode_map[clean_name] = clean_pcode

            # Register predefined aliases
            for alias, pcode in self.COMMON_ALIASES.items():
                if pcode in self.valid_pcodes:
                    self.pcode_map[self._normalize_str(alias)] = pcode

            logger.info("Loaded %d authoritative P-Codes with %d lookup keys.", len(self.valid_pcodes), len(self.pcode_map))
        except Exception as exc:
            logger.warning("Failed to load P-Codes dynamically from database: %s. Using fallback aliases.", exc)
            for alias, pcode in self.COMMON_ALIASES.items():
                self.valid_pcodes.add(pcode)
                self.pcode_map[self._normalize_str(alias)] = pcode
                self.pcode_map[pcode.lower()] = pcode
        finally:
            if own_conn and db_conn:
                db_conn.close()

    @staticmethod
    def _normalize_str(text: str) -> str:
        """Strips whitespace, converts to lowercase, and removes punctuation."""
        if not text:
            return ""
        return re.sub(r"[^\w\s-]", "", str(text).strip().lower())

    def harmonize(self, raw_location: Optional[str]) -> str:
        """
        Maps raw location strings to standard P-Code.
        
        Args:
            raw_location: Location string (e.g., 'Dhaka', 'chittagong', 'BD-30')
            
        Returns:
            Standardized UN OCHA P-Code (e.g., 'BD-30')
            
        Raises:
            GeospatialHarmonizationError: If location cannot be resolved.
        """
        if not raw_location or not str(raw_location).strip():
            raise GeospatialHarmonizationError("Empty or null raw location string provided.")

        clean_token = self._normalize_str(raw_location)

        # 1. Exact match in lookup map
        if clean_token in self.pcode_map:
            return self.pcode_map[clean_token]

        # 2. Check if token contains valid P-Code pattern (e.g., 'bd-30')
        upper_token = str(raw_location).strip().upper()
        if upper_token in self.valid_pcodes:
            return upper_token

        # 3. Fuzzy match across known names
        for key, pcode in self.pcode_map.items():
            if key in clean_token or clean_token in key:
                return pcode

        raise GeospatialHarmonizationError(
            f"Unable to resolve raw location '{raw_location}' to any authoritative UN OCHA P-Code."
        )

    def harmonize_series(self, series):
        """Vectorized harmonization for pandas Series."""
        return series.apply(self.harmonize)
