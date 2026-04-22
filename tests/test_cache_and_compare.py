"""Tests for index caching, compare, and stale-detection helpers."""
from __future__ import annotations

import csv as _csv
from datetime import datetime, timedelta
from pathlib import Path

import core


def _now():
    return datetime.now()


def test_cache_reuses_index_until_mtime_changes(tmp_path: Path):
    csv_path = tmp_path / "x.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["Name", "Keywords"])
        w.writerow(["A", "alpha"])
    core.clear_cache()
    data1, bm1 = core._get_index(csv_path, ["Name", "Keywords"])
    data2, bm2 = core._get_index(csv_path, ["Name", "Keywords"])
    assert bm1 is bm2  # same instance => cached
    assert data1 is data2

    # Touch the file with a newer mtime and verify cache is invalidated.
    import os
    new_time = csv_path.stat().st_mtime + 5
    os.utime(csv_path, (new_time, new_time))
    _, bm3 = core._get_index(csv_path, ["Name", "Keywords"])
    assert bm3 is not bm1


def test_compare_returns_table_structure():
    core.clear_cache()
    res = core.compare(["Kafka", "RabbitMQ"], domain="messaging")
    assert "entries" in res
    assert "columns" in res
    assert set(res["names"]) == {"Kafka", "RabbitMQ"}


def test_compare_requires_two_names():
    res = core.compare(["Kafka"])
    assert "error" in res


def test_find_stale_skips_undated_rows(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "x.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["Name", "Keywords", "Last Updated"])
        old = (datetime.now() - timedelta(days=900)).strftime("%Y-%m-%d")
        new = datetime.now().strftime("%Y-%m-%d")
        w.writerow(["Old", "x", old])
        w.writerow(["New", "y", new])
        w.writerow(["Undated", "z", ""])

    # Inject as a fake domain so find_stale can read it.
    monkeypatch.setitem(core.CSV_CONFIG, "_test_stale", {
        "file": csv_path.name,
        "search_cols": ["Name", "Keywords"],
        "output_cols": ["Name", "Keywords"],
    })
    monkeypatch.setattr(core, "DATA_DIR", tmp_path)

    result = core.find_stale("_test_stale", months=12)
    assert result["count"] == 1
    assert result["results"][0]["Name"] == "Old"


def test_max_age_months_filters_stale_rows_in_search(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "x.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["Name", "Keywords", "Last Updated"])
        old = (datetime.now() - timedelta(days=900)).strftime("%Y-%m-%d")
        w.writerow(["FreshThing", "matchme", datetime.now().strftime("%Y-%m-%d")])
        w.writerow(["StaleThing", "matchme", old])

    monkeypatch.setitem(core.CSV_CONFIG, "_test_age", {
        "file": csv_path.name,
        "search_cols": ["Name", "Keywords"],
        "output_cols": ["Name", "Keywords"],
    })
    monkeypatch.setattr(core, "DATA_DIR", tmp_path)
    core.clear_cache()

    res = core.search("matchme", domain="_test_age", max_age_months=12)
    names = [r["Name"] for r in res["results"]]
    assert "FreshThing" in names
    assert "StaleThing" not in names
