"""Tests for the anti-patterns domain (Tier 2 — Task 2.4)."""
from __future__ import annotations

import csv
from pathlib import Path

from core import CSV_CONFIG, DATA_DIR, clear_cache, detect_domain, search


ANTIPATTERN_CSV = DATA_DIR / "anti-patterns.csv"


class TestAntiPatternCSV:
    """Validate the anti-patterns.csv data file."""

    def test_csv_exists(self):
        assert ANTIPATTERN_CSV.exists(), "anti-patterns.csv must exist"

    def test_minimum_rows(self):
        with open(ANTIPATTERN_CSV, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 15, f"Expected ≥15 rows, got {len(rows)}"

    def test_required_columns(self):
        with open(ANTIPATTERN_CSV, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            header = set(reader.fieldnames or [])
        for col in ["Name", "Category", "Symptom", "Root Cause", "Fix", "Severity", "Last Updated"]:
            assert col in header, f"Missing required column: {col}"

    def test_all_rows_have_name(self):
        with open(ANTIPATTERN_CSV, encoding="utf-8", newline="") as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                assert (row.get("Name") or "").strip(), f"Row {i} has empty Name"


class TestAntiPatternRegistration:
    """Verify antipattern domain is registered in CSV_CONFIG."""

    def test_domain_in_csv_config(self):
        assert "antipattern" in CSV_CONFIG

    def test_config_file_key(self):
        assert CSV_CONFIG["antipattern"]["file"] == "anti-patterns.csv"

    def test_search_cols_present(self):
        assert "Name" in CSV_CONFIG["antipattern"]["search_cols"]
        assert "Keywords" in CSV_CONFIG["antipattern"]["search_cols"]

    def test_output_cols_present(self):
        out = CSV_CONFIG["antipattern"]["output_cols"]
        for col in ["Name", "Symptom", "Root Cause", "Fix", "Severity"]:
            assert col in out, f"Missing output column: {col}"


class TestAntiPatternSearch:
    """Search queries against the antipattern domain."""

    def setup_method(self):
        clear_cache()

    def test_distributed_monolith(self):
        result = search("distributed monolith", domain="antipattern")
        assert result["count"] > 0
        names = [r["Name"] for r in result["results"]]
        assert any("Distributed Monolith" in n for n in names)

    def test_dual_writes(self):
        result = search("dual writes", domain="antipattern")
        assert result["count"] > 0
        names = [r["Name"] for r in result["results"]]
        assert any("Dual Writes" in n for n in names)

    def test_unbounded_retry(self):
        result = search("unbounded retry", domain="antipattern")
        assert result["count"] > 0
        names = [r["Name"] for r in result["results"]]
        assert any("Unbounded Retry" in n for n in names)

    def test_n_plus_1(self):
        result = search("n+1 query", domain="antipattern")
        assert result["count"] > 0

    def test_result_has_symptom_and_fix(self):
        result = search("god service", domain="antipattern")
        assert result["count"] > 0
        row = result["results"][0]
        assert row.get("Symptom"), "Result should have Symptom"
        assert row.get("Fix"), "Result should have Fix"


class TestAntiPatternDomainDetection:
    """Verify domain auto-detection routes to antipattern."""

    def test_detect_distributed_monolith(self):
        assert detect_domain("distributed monolith") == "antipattern"

    def test_detect_dual_writes(self):
        assert detect_domain("dual writes anti-pattern") == "antipattern"

    def test_detect_antipattern_keyword(self):
        assert detect_domain("common antipattern bad practice") == "antipattern"
