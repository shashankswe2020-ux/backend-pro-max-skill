"""Tests for the CSV validator + the on-disk CSVs themselves."""
from __future__ import annotations

import csv as _csv
from pathlib import Path

import core
import validate


def test_all_shipped_csvs_pass_validation():
    """The repository's CSVs must always pass the validator."""
    errors = validate.validate_all()
    assert errors == [], "Shipped CSVs failed validation:\n" + "\n".join(errors)


def test_validator_flags_missing_column(tmp_path: Path, monkeypatch):
    bad = tmp_path / "bad.csv"
    with open(bad, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["WrongHeader"])
        w.writerow(["x"])
    errors = validate._validate_file(
        "test", bad,
        search_cols=["Name", "Keywords"],
        output_cols=["Name"],
    )
    assert any("missing search column 'Name'" in e for e in errors)


def test_validator_flags_bad_date(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    with open(bad, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["Name", "Last Updated"])
        w.writerow(["Foo", "not-a-date"])
    errors = validate._validate_file(
        "test", bad, search_cols=["Name"], output_cols=["Name", "Last Updated"],
    )
    assert any("unparseable date" in e for e in errors)


def test_validator_accepts_valid_dates(tmp_path: Path):
    good = tmp_path / "good.csv"
    with open(good, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["Name", "Last Updated"])
        w.writerow(["A", "2026-01-15"])
        w.writerow(["B", "2025"])
        w.writerow(["C", ""])  # empty is allowed
    errors = validate._validate_file(
        "test", good, search_cols=["Name"], output_cols=["Name", "Last Updated"],
    )
    assert errors == []


def test_every_domain_has_csv_on_disk():
    for domain, cfg in core.CSV_CONFIG.items():
        assert (core.DATA_DIR / cfg["file"]).exists(), f"missing CSV for {domain}"


def test_every_stack_has_csv_on_disk():
    for stack, cfg in core.STACK_CONFIG.items():
        assert (core.DATA_DIR / cfg["file"]).exists(), f"missing CSV for stack {stack}"
