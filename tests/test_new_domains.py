"""Tests for Tier 4 — 12 new domain CSVs + latency numbers domain."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

# Import from core — handles both installed and direct invocation.
try:
    from backendpro.scripts.core import CSV_CONFIG, DATA_DIR, clear_cache, detect_domain, search
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "backend-pro-max"))
    from scripts.core import CSV_CONFIG, DATA_DIR, clear_cache, detect_domain, search


# ── helpers ──────────────────────────────────────────────────────────────────

def _row_count(domain: str) -> int:
    cfg = CSV_CONFIG[domain]
    with open(DATA_DIR / cfg["file"], encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def _header(domain: str) -> list[str]:
    cfg = CSV_CONFIG[domain]
    with open(DATA_DIR / cfg["file"], encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or [])


# ── parameterised: every new domain is registered and has minimum rows ───────

NEW_DOMAINS = {
    "cost":          {"min_rows": 20, "query": "egress cost AWS",           "detect_query": "cross-AZ data transfer cost"},
    "migration":     {"min_rows": 15, "query": "strangler fig",             "detect_query": "strangler fig migration cutover zero-downtime"},
    "incident":      {"min_rows": 15, "query": "severity matrix",           "detect_query": "production outage severity matrix"},
    "capacity":      {"min_rows": 15, "query": "Little's Law",              "detect_query": "Little's Law queue theory capacity"},
    "compliance":    {"min_rows": 15, "query": "SOC2 logging",              "detect_query": "SOC2 audit logging requirements"},
    "multi-tenant":  {"min_rows": 12, "query": "noisy neighbor",            "detect_query": "noisy neighbor multi-tenant isolation"},
    "release":       {"min_rows": 15, "query": "canary deployment",         "detect_query": "canary deployment rollback strategy"},
    "ml-platform":   {"min_rows": 12, "query": "feature store",             "detect_query": "feature store model registry ml platform"},
    "edge":          {"min_rows": 10, "query": "cloudflare workers",        "detect_query": "edge compute cloudflare workers wasm"},
    "mobile-backend":{"min_rows": 10, "query": "BFF pattern",              "detect_query": "backend for frontend mobile offline sync"},
    "api-contract":  {"min_rows": 12, "query": "schema evolution",          "detect_query": "openapi schema evolution api contract"},
    "interview":     {"min_rows": 12, "query": "system design rubric",      "detect_query": "system design interview rubric staff engineer"},
    "latency":       {"min_rows": 25, "query": "NVMe",                      "detect_query": "NVMe latency numbers"},
}


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_cache()
    yield
    clear_cache()


class TestNewDomainRegistration:
    """Every new domain must be registered in CSV_CONFIG."""

    @pytest.mark.parametrize("domain", NEW_DOMAINS.keys())
    def test_domain_in_csv_config(self, domain):
        assert domain in CSV_CONFIG, f"{domain} not registered in CSV_CONFIG"


class TestNewDomainRowCounts:
    """Every new domain CSV must have at least its minimum row count."""

    @pytest.mark.parametrize("domain,spec", NEW_DOMAINS.items())
    def test_minimum_rows(self, domain, spec):
        count = _row_count(domain)
        assert count >= spec["min_rows"], (
            f"{domain}: expected ≥{spec['min_rows']} rows, got {count}"
        )


class TestNewDomainSearch:
    """Searching each new domain must return results."""

    @pytest.mark.parametrize("domain,spec", NEW_DOMAINS.items())
    def test_search_returns_results(self, domain, spec):
        result = search(spec["query"], domain=domain, max_results=3)
        assert result["results"], (
            f"search('{spec['query']}', domain='{domain}') returned no results"
        )


class TestNewDomainAutoDetection:
    """Auto-detection should route queries to the correct new domain."""

    @pytest.mark.parametrize("domain,spec", NEW_DOMAINS.items())
    def test_detect_domain(self, domain, spec):
        detected = detect_domain(spec["detect_query"])
        assert detected == domain, (
            f"detect_domain('{spec['detect_query']}') = '{detected}', expected '{domain}'"
        )


class TestNewDomainSourceColumns:
    """Every new row should have Source URL and Last Updated columns."""

    @pytest.mark.parametrize("domain", NEW_DOMAINS.keys())
    def test_has_source_url_column(self, domain):
        hdr = _header(domain)
        assert "Source URL" in hdr, f"{domain} CSV missing 'Source URL' column"

    @pytest.mark.parametrize("domain", NEW_DOMAINS.keys())
    def test_has_last_updated_column(self, domain):
        hdr = _header(domain)
        assert "Last Updated" in hdr, f"{domain} CSV missing 'Last Updated' column"
