"""Tests for the provenance auto-populator."""
from __future__ import annotations

import csv as _csv
from pathlib import Path
from unittest.mock import patch

import provenance


def _make_csv(tmp_path: Path, name: str, header: list[str], rows: list[list[str]]) -> Path:
    f = tmp_path / name
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(header)
        for row in rows:
            w.writerow(row)
    return f


def test_validate_version_valid():
    assert provenance.validate_version("1.0.0") is True
    assert provenance.validate_version("0.4.0") is True
    assert provenance.validate_version("v2.1.3") is True
    assert provenance.validate_version("") is True


def test_validate_version_invalid():
    assert provenance.validate_version("not-semver") is False
    assert provenance.validate_version("abc") is False


def test_populate_provenance_adds_columns(tmp_path: Path):
    f = _make_csv(tmp_path, "test.csv",
                  ["Name", "Notes"],
                  [["Foo", "bar"]])
    with patch.object(provenance, "git_blame_authors", return_value={}):
        with patch.object(provenance, "latest_version_tag", return_value=""):
            provenance.populate_provenance(f)

    with open(f, encoding="utf-8", newline="") as fh:
        reader = _csv.DictReader(fh)
        header = reader.fieldnames
    assert "Added By" in header
    assert "Last Reviewed By" in header
    assert "Version" in header


def test_populate_provenance_fills_author(tmp_path: Path):
    f = _make_csv(tmp_path, "test.csv",
                  ["Name", "Added By", "Last Reviewed By", "Version"],
                  [["Foo", "", "", ""]])
    with patch.object(provenance, "git_blame_authors", return_value={2: "Alice"}):
        with patch.object(provenance, "latest_version_tag", return_value="0.4.0"):
            result = provenance.populate_provenance(f)

    assert result["rows_updated"] == 1
    with open(f, encoding="utf-8", newline="") as fh:
        rows = list(_csv.DictReader(fh))
    assert rows[0]["Added By"] == "Alice (auto)"
    assert rows[0]["Version"] == "0.4.0"


def test_populate_provenance_skips_existing(tmp_path: Path):
    f = _make_csv(tmp_path, "test.csv",
                  ["Name", "Added By", "Last Reviewed By", "Version"],
                  [["Foo", "Bob", "", "0.3.0"]])
    with patch.object(provenance, "git_blame_authors", return_value={2: "Alice"}):
        with patch.object(provenance, "latest_version_tag", return_value="0.4.0"):
            result = provenance.populate_provenance(f)

    assert result["rows_updated"] == 0


def test_populate_provenance_dry_run_no_write(tmp_path: Path):
    f = _make_csv(tmp_path, "test.csv",
                  ["Name"],
                  [["Foo"]])
    original = f.read_text()
    with patch.object(provenance, "git_blame_authors", return_value={}):
        with patch.object(provenance, "latest_version_tag", return_value="0.4.0"):
            provenance.populate_provenance(f, dry_run=True)
    assert f.read_text() == original


def test_populate_provenance_missing_file():
    result = provenance.populate_provenance(Path("/nonexistent.csv"))
    assert result["rows_updated"] == 0
    assert "error" in result


def test_git_blame_authors_handles_missing_git():
    with patch("provenance.subprocess.run", side_effect=FileNotFoundError):
        authors = provenance.git_blame_authors(Path("/fake.csv"))
    assert authors == {}


def test_latest_version_tag_handles_missing_git():
    with patch("provenance.subprocess.run", side_effect=FileNotFoundError):
        tag = provenance.latest_version_tag()
    assert tag == ""
