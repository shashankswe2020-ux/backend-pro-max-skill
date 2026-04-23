"""Tests for Tier 4.4 — Capacity calculators."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from backendpro.scripts.calc import (
        CALCULATORS,
        calc_bandwidth,
        calc_cache_hit,
        calc_concurrency,
        calc_fanout,
        calc_partitions,
        calc_qps,
        calc_storage,
        format_calc_result,
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "backend-pro-max"))
    from scripts.calc import (
        CALCULATORS,
        calc_bandwidth,
        calc_cache_hit,
        calc_concurrency,
        calc_fanout,
        calc_partitions,
        calc_qps,
        calc_storage,
        format_calc_result,
    )


class TestQPS:
    def test_basic(self):
        r = calc_qps(daily=100_000_000)
        assert r["avg_qps"] == pytest.approx(1157, rel=0.01)
        assert r["peak_qps"] == pytest.approx(3472, rel=0.01)

    def test_custom_peak_factor(self):
        r = calc_qps(daily=86_400, peak_factor=2)
        assert r["avg_qps"] == 1
        assert r["peak_qps"] == 2


class TestStorage:
    def test_basic(self):
        r = calc_storage(rows=1_000_000_000, row_bytes=200)
        assert r["raw_bytes"] == 200_000_000_000
        assert r["replicated_bytes"] == 600_000_000_000  # default replication=3

    def test_custom_replication(self):
        r = calc_storage(rows=1_000_000, row_bytes=100, replication=2)
        assert r["replicated_bytes"] == 200_000_000


class TestBandwidth:
    def test_basic(self):
        r = calc_bandwidth(qps=5000, payload_kb=2)
        assert r["bandwidth_mbps"] == pytest.approx(10.0, rel=0.01)


class TestConcurrency:
    def test_littles_law(self):
        r = calc_concurrency(rps=5000, latency_ms=50)
        assert r["concurrent_requests"] == 250


class TestPartitions:
    def test_basic(self):
        r = calc_partitions(target_throughput_mb=100, per_partition_mb=1)
        assert r["partitions"] == 100

    def test_rounding_up(self):
        r = calc_partitions(target_throughput_mb=101, per_partition_mb=10)
        assert r["partitions"] == 11


class TestCacheHit:
    def test_basic(self):
        r = calc_cache_hit(requests=1_000_000, cache_size=100_000)
        assert 0 < r["estimated_hit_rate"] <= 1.0


class TestFanout:
    def test_write_fanout(self):
        r = calc_fanout(followers=1000, posts_per_day=10)
        assert r["total_writes_per_day"] == 10_000


class TestRegistry:
    def test_all_calculators_registered(self):
        expected = {"qps", "storage", "bandwidth", "concurrency",
                    "partitions", "cache-hit", "fanout"}
        assert expected == set(CALCULATORS.keys())


class TestFormatting:
    def test_format_returns_string(self):
        r = calc_qps(daily=86_400)
        out = format_calc_result("qps", r)
        assert isinstance(out, str)
        assert "QPS" in out.upper() or "qps" in out.lower()

    def test_json_serialisable(self):
        r = calc_storage(rows=1000, row_bytes=100)
        json.dumps(r)  # should not raise
