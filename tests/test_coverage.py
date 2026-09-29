"""Tests for the coverage module — KB coverage analysis."""
from __future__ import annotations

import json

import core
import pytest
from backendpro.scripts import coverage as kb_coverage
from backendpro.scripts.coverage import (
    _count_by_category,
    _load_targets,
    analyse_all,
    analyse_domain,
    format_badge,
    format_coverage,
    format_coverage_json,
)


def test_bundled_targets_match_repository(monkeypatch, tmp_path):
    expected = _load_targets()
    assert expected
    monkeypatch.setattr(kb_coverage, "_TARGETS_PATH", tmp_path / "missing.yml")
    assert _load_targets() == expected


def test_missing_targets_fail_explicitly(monkeypatch, tmp_path):
    monkeypatch.setattr(kb_coverage, "_TARGETS_PATH", tmp_path / "missing.yml")
    monkeypatch.setattr(kb_coverage, "DATA_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="Coverage targets"):
        _load_targets()


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


def test_gap_detection_normalizes_category_spelling():
    core.clear_cache()
    targets = {"database": ["Wide Column", " TIME_SERIES ", "rdbms", "Absent Category"]}
    report = analyse_domain("database", targets)
    assert report["gaps"] == ["Absent Category"]
    assert "Wide-column" in report["categories"]


def test_topic_aliases_report_row_evidence():
    report = analyse_domain("testing", {"testing": ["Contract", "Performance", "Absent"]})
    assert report["gaps"] == ["Absent"]
    assert report["target_matches"]["Contract"] == ["Contract tests"]
    assert report["target_matches"]["Performance"] == ["Load tests", "Stress / soak tests"]


def test_aliases_do_not_match_descriptions():
    rows = [{"Name": "Unrelated", "Category": "Integration", "Description": "Contract tests"}]
    assert kb_coverage._target_matches("testing", rows, ["Contract"]) == {"Contract": []}


def test_all_alias_values_reference_existing_rows():
    aliases = json.loads((core.DATA_DIR / "coverage-aliases.json").read_text(encoding="utf-8"))
    targets = _load_targets()
    for domain, rules in aliases.items():
        rows = core._load_csv(core.DATA_DIR / core.CSV_CONFIG[domain]["file"])
        category_col = kb_coverage._category_col(domain)
        name_col = next(iter(rows[0]))
        for target, fields in rules.items():
            assert target in targets[domain]
            for field, values in fields.items():
                assert field in ("category", "name")
                column = category_col if field == "category" else name_col
                actual = {row[column] for row in rows}
                assert set(values) <= actual, (domain, target, set(values) - actual)


def test_declared_targets_have_coverage():
    report = analyse_all(_load_targets())
    assert report["summary"]["total_gaps"] == 0


@pytest.mark.parametrize("domain, name", [
    ("pattern", "Decompose by Business Capability"),
    ("pattern", "Distributed Tracing"),
    ("messaging", "Kafka Streams"),
    ("cloud", "Amazon VPC"),
    ("security", "Authentication hardening"),
    ("security", "Object-level authorization"),
    ("reliability", "Graceful degradation"),
])
def test_reviewed_gap_entries_are_searchable_and_sourced(domain, name):
    config = core.CSV_CONFIG[domain]
    name_col = config["output_cols"][0]
    rows = core._load_csv(core.DATA_DIR / config["file"])
    row = next(row for row in rows if row[name_col] == name)
    assert row["Source URL"].startswith("https://")
    assert row["Last Updated"] == "2026-09-29"
    result = core.search(name, domain=domain)
    assert any(hit[name_col] == name for hit in result["results"])


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
