"""Tests for the coverage module — KB coverage analysis."""
from __future__ import annotations

import json

import core
from coverage import (
    _count_by_category,
    _load_targets,
    analyse_all,
    analyse_domain,
    format_badge,
    format_coverage,
    format_coverage_json,
)


def test_count_by_category_returns_dict():
    core.clear_cache()
    counts = _count_by_category("pattern")
    assert isinstance(counts, dict)
    assert all(isinstance(v, int) for v in counts.values())


def test_count_by_category_unknown_domain():
    assert _count_by_category("nonexistent") == {}


def test_analyse_domain_shape():
    core.clear_cache()
    targets = _load_targets()
    report = analyse_domain("pattern", targets)
    assert report["domain"] == "pattern"
    assert "total_rows" in report
    assert report["total_rows"] > 0
    assert "categories" in report
    assert "gaps" in report
    assert "thin" in report
    assert "source_url_pct" in report


def test_analyse_domain_unknown():
    report = analyse_domain("nonexistent", {})
    assert "error" in report


def test_analyse_all_shape():
    core.clear_cache()
    targets = _load_targets()
    report = analyse_all(targets)
    assert "summary" in report
    assert "domains" in report
    summary = report["summary"]
    assert summary["total_rows"] > 0
    assert summary["domain_count"] > 0
    assert "avg_rows_per_domain" in summary
    assert "source_url_pct" in summary


def test_analyse_all_domain_filter():
    core.clear_cache()
    targets = _load_targets()
    report = analyse_all(targets, domain_filter="database")
    assert len(report["domains"]) == 1
    assert report["domains"][0]["domain"] == "database"


def test_format_coverage_contains_domain():
    core.clear_cache()
    targets = _load_targets()
    report = analyse_all(targets, domain_filter="messaging")
    output = format_coverage(report)
    assert "messaging" in output
    assert "rows" in output


def test_format_coverage_json_valid():
    core.clear_cache()
    targets = _load_targets()
    report = analyse_all(targets, domain_filter="database")
    output = format_coverage_json(report)
    parsed = json.loads(output)
    assert "summary" in parsed


def test_format_badge_returns_url():
    core.clear_cache()
    targets = _load_targets()
    report = analyse_all(targets)
    url = format_badge(report)
    assert url.startswith("https://img.shields.io/badge/")


def test_gap_detection():
    """If targets list a category not in CSV, it appears in gaps."""
    core.clear_cache()
    fake_targets = {"pattern": ["Nonexistent Category XYZ"]}
    report = analyse_domain("pattern", fake_targets)
    assert "Nonexistent Category XYZ" in report["gaps"]


def test_thin_detection():
    """Categories with < THIN_THRESHOLD rows should appear in thin."""
    core.clear_cache()
    report = analyse_domain("pattern", {})
    # thin dict should contain category: count pairs where count < 3
    for _cat, count in report.get("thin", {}).items():
        assert count < 3


def test_source_url_pct_reasonable():
    """Source URL percentage should be 0-100."""
    core.clear_cache()
    report = analyse_domain("pattern", {})
    assert 0 <= report["source_url_pct"] <= 100
