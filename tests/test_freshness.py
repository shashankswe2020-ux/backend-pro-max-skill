"""Tests for the freshness scanner."""
from __future__ import annotations

import csv as _csv
from pathlib import Path
from unittest.mock import patch

import freshness


def _make_csv(tmp_path: Path, name: str, header: list[str], rows: list[list[str]]) -> Path:
    f = tmp_path / name
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(header)
        for row in rows:
            w.writerow(row)
    return f


def test_find_stale_rows_detects_old_dates(tmp_path: Path):
    f = _make_csv(tmp_path, "test.csv",
                  ["Name", "Last Updated"],
                  [["Old Row", "2020-01-01"], ["New Row", "2026-01-01"]])
    stale = freshness.find_stale_rows(f, max_age_months=18)
    assert len(stale) == 1
    assert stale[0]["name"] == "Old Row"
    assert stale[0]["age_months"] > 18


def test_find_stale_rows_empty_dates_skipped(tmp_path: Path):
    f = _make_csv(tmp_path, "test.csv",
                  ["Name", "Last Updated"],
                  [["No Date", ""]])
    stale = freshness.find_stale_rows(f, max_age_months=18)
    assert stale == []


def test_find_stale_rows_missing_file():
    stale = freshness.find_stale_rows(Path("/nonexistent.csv"))
    assert stale == []


def test_check_url_success():
    with patch("freshness.urllib.request.urlopen") as mock:
        mock.return_value.__enter__ = lambda s: s
        mock.return_value.__exit__ = lambda s, *a: None
        mock.return_value.status = 200
        result = freshness.check_url("https://example.com")
        assert result["ok"] is True
        assert result["status"] == 200


def test_check_url_failure():
    import urllib.error
    with patch("freshness.urllib.request.urlopen") as mock:
        mock.side_effect = urllib.error.URLError("timeout")
        result = freshness.check_url("https://broken.example.com", retries=1)
        assert result["ok"] is False


def test_issue_title_format():
    result = {
        "domain": "database",
        "file": "databases.csv",
        "stale": [{"line": 2, "name": "X", "last_updated": "2020-01-01", "age_months": 72}],
        "broken": [],
    }
    title = freshness.issue_title(result)
    assert title == "[Freshness] database: 1 stale, 0 broken URLs"


def test_format_issue_body_contains_stale_table():
    result = {
        "domain": "database",
        "file": "databases.csv",
        "stale": [{"line": 2, "name": "PostgreSQL", "last_updated": "2020-01-01", "age_months": 72}],
        "broken": [],
    }
    body = freshness.format_issue_body(result)
    assert "Stale Rows" in body
    assert "PostgreSQL" in body
    assert "L2" in body


def test_format_issue_body_contains_broken_urls():
    result = {
        "domain": "database",
        "file": "databases.csv",
        "stale": [],
        "broken": [{"line": 3, "name": "Redis", "url": "https://broken.example.com", "status": 404, "error": "Not Found"}],
    }
    body = freshness.format_issue_body(result)
    assert "Broken URLs" in body
    assert "Redis" in body
    assert "404" in body


def test_check_existing_issue_no_gh_cli():
    """When gh CLI is not available, should return False (no duplicate detected)."""
    with patch("freshness.subprocess.run", side_effect=FileNotFoundError):
        assert freshness.check_existing_issue("database") is False


def test_scan_all_with_no_stale(tmp_path: Path, monkeypatch):
    """If nothing is stale, scan_all returns empty."""
    # Patch DATA_DIR to tmp_path with a single CSV
    monkeypatch.setattr(freshness, "DATA_DIR", tmp_path)
    monkeypatch.setattr(freshness, "CSV_CONFIG", {
        "test": {"file": "test.csv"},
    })
    monkeypatch.setattr(freshness, "STACK_CONFIG", {})
    _make_csv(tmp_path, "test.csv",
              ["Name", "Last Updated", "Source URL"],
              [["Fresh", "2026-01-01", ""]])
    results = freshness.scan_all(check_urls=False)
    assert results == []


def test_scan_all_finds_stale(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(freshness, "DATA_DIR", tmp_path)
    monkeypatch.setattr(freshness, "CSV_CONFIG", {
        "test": {"file": "test.csv"},
    })
    monkeypatch.setattr(freshness, "STACK_CONFIG", {})
    _make_csv(tmp_path, "test.csv",
              ["Name", "Last Updated", "Source URL"],
              [["Old", "2020-01-01", ""]])
    results = freshness.scan_all(check_urls=False)
    assert len(results) == 1
    assert results[0]["domain"] == "test"
    assert len(results[0]["stale"]) == 1
