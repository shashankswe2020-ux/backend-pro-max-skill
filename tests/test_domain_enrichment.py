"""Offline regression checks for the source-reviewed domain enrichment."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import urlparse

import core
import pytest

REVIEWED_DOMAINS = {
    "antipattern": 18,
    "migration": 18,
    "incident": 19,
    "capacity": 18,
    "compliance": 18,
    "multi-tenant": 16,
    "release": 18,
    "ml-platform": 15,
    "edge": 13,
    "mobile-backend": 13,
    "api-contract": 16,
    "interview": 15,
    "latency": 26,
}


def _records(domain):
    path = core.DATA_DIR / core.CSV_CONFIG[domain]["file"]
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.reader(source))


def _row(domain, name):
    header, *records = _records(domain)
    return next(dict(zip(header, record)) for record in records if record[0] == name)


@pytest.mark.parametrize("domain, minimum", REVIEWED_DOMAINS.items())
def test_enriched_domain_record_integrity(domain, minimum):
    header, *records = _records(domain)
    assert len(records) >= minimum
    assert len(header) == len(set(header)), domain
    assert len({record[0] for record in records}) == len(records), domain
    for record in records:
        assert len(record) == len(header), (domain, record[0])
        row = dict(zip(header, record))
        source = urlparse(row["Source URL"])
        assert source.scheme == "https" and source.hostname, (domain, record[0])
        assert row["Source Type"].strip(), (domain, record[0])
        assert row["Last Updated"].strip(), (domain, record[0])


@pytest.mark.parametrize("domain", REVIEWED_DOMAINS)
def test_domain_has_review_ledger(domain):
    ledger = Path(__file__).resolve().parents[1] / "docs" / "reviews" / f"domain-{domain}-2026-09-29.md"
    assert ledger.is_file()
    assert "https://" in ledger.read_text(encoding="utf-8")


@pytest.mark.parametrize("domain", REVIEWED_DOMAINS)
def test_enriched_row_identities_remain_searchable(domain):
    header, *records = _records(domain)
    for record in records:
        name = record[0]
        results = core.search(name, domain=domain, max_results=5)["results"]
        assert any(result[header[0]] == name for result in results), (domain, name)


@pytest.mark.parametrize("name, expected", [
    ("USL (Universal Scalability Law)", 10 / (1 + 0.01 * 9 + 0.001 * 10 * 9)),
    ("Amdahl's Law", 1 / ((1 - 0.95) + 0.95 / 16)),
])
def test_corrected_scalability_examples(name, expected):
    example = _row("capacity", name)["Example Calculation"]
    match = re.search(r"= ([0-9.]+)x", example)
    assert match is not None
    assert float(match.group(1)) == pytest.approx(expected, abs=0.005)


def test_capacity_examples_distinguish_units_and_stability():
    bandwidth = _row("capacity", "Bandwidth Estimation")["Example Calculation"]
    assert "2000 B = 10 MB/s = 80 Mbit/s" in bandwidth
    assert "2048 B instead gives 81.92 Mbit/s" in bandwidth
    assert "no finite drain time" in _row("capacity", "Queue Backlog Drain Time")["Gotcha"]
    assert "completion_rate <= arrival_rate" in _row("capacity", "Queue Backlog Drain Time")["Gotcha"]
    assert "7.2 h" in _row("capacity", "SLO Error Budget")["Rule of Thumb"]
    assert "not TIME_WAIT" in _row("capacity", "TCP Connection Capacity")["Gotcha"]


def test_unverified_latency_estimates_are_not_marked_current():
    header, *records = _records("latency")
    for record in records:
        row = dict(zip(header, record))
        if "unverified" in row["Notes"].casefold():
            assert row["Last Updated"] != "2026-09-29", row["Operation"]
        assert re.fullmatch(r"\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)? (?:ns|μs|ms|s)", row["Latency"])


def test_unverified_compliance_mappings_are_not_marked_current():
    header, *records = _records("compliance")
    for record in records:
        row = dict(zip(header, record))
        if "unverified" in " ".join(row.values()).casefold():
            assert row["Last Updated"] != "2026-09-29", row["Name"]
    assert "unless risk is unlikely" in _row("compliance", "Data Breach Notification")["Engineering Requirement"]
    assert "not a blanket opt-in regime" in _row("compliance", "Consent Management")["Gotcha"]


def test_tenant_isolation_caveats_are_preserved():
    rls = _row("multi-tenant", "Row-Level Security (RLS)")
    assert "BYPASSRLS" in rls["Weaknesses"]
    assert "FORCE does not constrain" in rls["Gotcha"]
    cache = _row("multi-tenant", "Tenant-Aware Caching")
    assert "Authorize cache hits as well as misses" in cache["Gotcha"]
    session = _row("multi-tenant", "Transaction-Scoped Tenant Context")
    assert "not protection from arbitrary SQL" in session["Weaknesses"]
