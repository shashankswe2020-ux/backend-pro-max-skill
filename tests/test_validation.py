"""Tests for the CSV validator + the on-disk CSVs themselves."""
from __future__ import annotations

import csv as _csv
from pathlib import Path

import core
import validate


def test_all_shipped_csvs_pass_validation():
    """The repository's CSVs must always pass the validator."""
    errors, _warnings = validate.validate_all()
    assert errors == [], "Shipped CSVs failed validation:\n" + "\n".join(errors)


def test_validator_flags_missing_column(tmp_path: Path, monkeypatch):
    bad = tmp_path / "bad.csv"
    with open(bad, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["WrongHeader"])
        w.writerow(["x"])
    errors, _warnings = validate._validate_file(
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
    errors, _warnings = validate._validate_file(
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
    errors, _warnings = validate._validate_file(
        "test", good, search_cols=["Name"], output_cols=["Name", "Last Updated"],
    )
    assert errors == []


def test_every_domain_has_csv_on_disk():
    for domain, cfg in core.CSV_CONFIG.items():
        assert (core.DATA_DIR / cfg["file"]).exists(), f"missing CSV for {domain}"


def test_every_stack_has_csv_on_disk():
    for stack, cfg in core.STACK_CONFIG.items():
        assert (core.DATA_DIR / cfg["file"]).exists(), f"missing CSV for stack {stack}"


# ---- Tier 5: Source Type enum validation ----

def test_validator_flags_invalid_source_type(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    with open(bad, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["Name", "Source Type"])
        w.writerow(["Foo", "random-invalid"])
    errors, _warnings = validate._validate_file(
        "test", bad, search_cols=["Name"], output_cols=["Name", "Source Type"],
    )
    assert any("invalid Source Type" in e for e in errors)


def test_validator_accepts_valid_source_types(tmp_path: Path):
    good = tmp_path / "good.csv"
    with open(good, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["Name", "Source Type"])
        w.writerow(["A", "official-docs"])
        w.writerow(["B", "paper"])
        w.writerow(["C", "rfc"])
        w.writerow(["D", ""])  # empty is allowed
    errors, _warnings = validate._validate_file(
        "test", good, search_cols=["Name"], output_cols=["Name", "Source Type"],
    )
    assert errors == []


def test_source_type_enum_is_complete():
    """Ensure the enum covers the expected values."""
    expected = {
        "official-docs", "paper", "postmortem", "engineering-blog",
        "book", "benchmark", "rfc",
    }
    assert validate.VALID_SOURCE_TYPES == expected


# ---- Tier 5: Soft warnings for missing Source URL / Last Updated ----

def test_soft_mode_warns_missing_source_url(tmp_path: Path):
    f = tmp_path / "test.csv"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(["Name", "Source URL", "Last Updated"])
        w.writerow(["Foo", "", "2025-01-01"])
    errors, warnings = validate._validate_file(
        "test", f,
        search_cols=["Name"],
        output_cols=["Name", "Source URL", "Last Updated"],
    )
    assert errors == []
    assert any("missing Source URL" in w for w in warnings)


def test_soft_mode_warns_missing_last_updated(tmp_path: Path):
    f = tmp_path / "test.csv"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(["Name", "Source URL", "Last Updated"])
        w.writerow(["Foo", "https://example.com", ""])
    errors, warnings = validate._validate_file(
        "test", f,
        search_cols=["Name"],
        output_cols=["Name", "Source URL", "Last Updated"],
    )
    assert errors == []
    assert any("missing Last Updated" in w for w in warnings)


# ---- Tier 5: Strict mode ----

def test_strict_mode_fails_missing_source_url(tmp_path: Path):
    f = tmp_path / "test.csv"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(["Name", "Source URL", "Last Updated"])
        w.writerow(["Foo", "", "2025-01-01"])
    errors, _warnings = validate._validate_file(
        "test", f,
        search_cols=["Name"],
        output_cols=["Name", "Source URL", "Last Updated"],
        strict=True,
    )
    assert any("missing Source URL" in e for e in errors)


def test_strict_mode_fails_missing_last_updated(tmp_path: Path):
    f = tmp_path / "test.csv"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(["Name", "Source URL", "Last Updated"])
        w.writerow(["Foo", "https://example.com", ""])
    errors, _warnings = validate._validate_file(
        "test", f,
        search_cols=["Name"],
        output_cols=["Name", "Source URL", "Last Updated"],
        strict=True,
    )
    assert any("missing Last Updated" in e for e in errors)


def test_strict_mode_passes_complete_row(tmp_path: Path):
    f = tmp_path / "test.csv"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(["Name", "Source URL", "Source Type", "Last Updated"])
        w.writerow(["Foo", "https://example.com", "official-docs", "2025-01-01"])
    errors, warnings = validate._validate_file(
        "test", f,
        search_cols=["Name"],
        output_cols=["Name", "Source URL", "Source Type", "Last Updated"],
        strict=True,
    )
    assert errors == []
    assert warnings == []


# ---- Tier 5: All domain CSVs have trust columns ----

def test_all_domain_csvs_have_source_url_column():
    """Every domain CSV must have a Source URL column."""
    for domain, cfg in core.CSV_CONFIG.items():
        assert "Source URL" in cfg["output_cols"], (
            f"domain '{domain}' missing Source URL in output_cols"
        )


def test_all_domain_csvs_have_source_type_column():
    """Every domain CSV must have a Source Type column."""
    for domain, cfg in core.CSV_CONFIG.items():
        assert "Source Type" in cfg["output_cols"], (
            f"domain '{domain}' missing Source Type in output_cols"
        )


def test_all_domain_csvs_have_last_updated_column():
    """Every domain CSV must have a Last Updated column."""
    for domain, cfg in core.CSV_CONFIG.items():
        assert "Last Updated" in cfg["output_cols"], (
            f"domain '{domain}' missing Last Updated in output_cols"
        )


def test_all_domain_csv_headers_have_trust_columns():
    """On-disk CSV headers must include Source URL, Source Type, Last Updated."""
    for domain, cfg in core.CSV_CONFIG.items():
        filepath = core.DATA_DIR / cfg["file"]
        with open(filepath, encoding="utf-8", newline="") as f:
            header = f.readline().strip().split(",")
        for col in ("Source URL", "Source Type", "Last Updated"):
            assert col in header, (
                f"domain '{domain}' ({cfg['file']}): missing '{col}' in CSV header"
            )


def test_all_stack_csv_headers_have_source_url_and_last_updated():
    """Stack CSVs must have Source URL and Last Updated columns."""
    for stack, cfg in core.STACK_CONFIG.items():
        filepath = core.DATA_DIR / cfg["file"]
        with open(filepath, encoding="utf-8", newline="") as f:
            header = f.readline().strip().split(",")
        for col in ("Source URL", "Last Updated"):
            assert col in header, (
                f"stack '{stack}' ({cfg['file']}): missing '{col}' in CSV header"
            )
