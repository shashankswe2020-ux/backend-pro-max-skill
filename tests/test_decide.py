"""Tests for the decide module (Tier 1 – Decision Intelligence)."""
from __future__ import annotations

from core import apply_constraints, parse_constraints
from decide import (
    _get_name,
    _parse_scale,
    _qps_from_daily,
    _storage_estimate,
    adr,
    decide,
    design,
    extract_constraints,
    format_adr,
    format_decide,
    format_design,
)

# ── _get_name ────────────────────────────────────────────────────────

class TestGetName:
    def test_name_key(self):
        assert _get_name({"Name": "PostgreSQL", "Category": "RDBMS"}) == "PostgreSQL"

    def test_technology_key(self):
        assert _get_name({"Technology": "pgx", "Category": "DB"}) == "pgx"

    def test_pattern_key(self):
        assert _get_name({"Pattern": "Circuit Breaker"}) == "Circuit Breaker"

    def test_fallback(self):
        assert _get_name({"Foo": "Bar"}) == "Bar"

    def test_empty(self):
        assert _get_name({}) == ""


# ── extract_constraints ──────────────────────────────────────────────

class TestExtractConstraints:
    def test_throughput_extraction(self):
        facets = extract_constraints("I need 50k requests/sec with low latency")
        assert facets.get("throughput") == "high"
        assert "_throughput_raw" in facets

    def test_latency_extraction(self):
        facets = extract_constraints("sub 5ms latency required")
        assert facets.get("latency") == "low-ms"

    def test_empty_query(self):
        assert extract_constraints("") == {}

    def test_no_constraints(self):
        assert extract_constraints("best database for users") == {}

    def test_adjective_high_throughput(self):
        facets = extract_constraints("I need high throughput")
        assert facets.get("throughput") == "high"

    def test_adjective_low_latency(self):
        facets = extract_constraints("low latency required")
        assert facets.get("latency") == "low-ms"

    def test_cloud_gcp(self):
        facets = extract_constraints("GCP-native solution")
        assert facets.get("cloud") == "gcp"

    def test_consistency_strong(self):
        facets = extract_constraints("strong consistency required")
        assert facets.get("consistency") == "strong"

    def test_ordering(self):
        facets = extract_constraints("ordered per-tenant delivery")
        assert facets.get("ordering") is True


# ── parse_constraints ────────────────────────────────────────────────

class TestParseConstraints:
    def test_basic_parse(self):
        result = parse_constraints("throughput=high,latency=low")
        assert result["throughput"] == "high"
        assert result["latency"] == "low"

    def test_single(self):
        result = parse_constraints("cost=low")
        assert len(result) == 1

    def test_empty(self):
        assert parse_constraints("") == {}
        assert parse_constraints(None) == {}

    def test_ignores_invalid(self):
        result = parse_constraints("noequalssign,valid=yes")
        assert result == {"valid": "yes"}


# ── apply_constraints ────────────────────────────────────────────────

class TestApplyConstraints:
    def test_annotates_results(self):
        rows = [
            {"Name": "A", "Cloud Native": "aws,gcp", "Throughput Tier": "high", "_score": 5.0},
            {"Name": "B", "Cloud Native": "aws", "Throughput Tier": "low", "_score": 3.0},
        ]
        apply_constraints(rows, {"cloud": "gcp", "throughput": "high"})
        assert rows[0]["_constraints"]["cloud"]["match"] is True
        assert rows[0]["_constraints"]["throughput"]["match"] is True
        assert rows[1]["_constraints"]["cloud"]["match"] is False

    def test_sorts_by_satisfied_count(self):
        rows = [
            {"Name": "Bad", "Cloud Native": "azure", "Throughput Tier": "low", "_score": 10.0},
            {"Name": "Good", "Cloud Native": "gcp", "Throughput Tier": "high", "_score": 1.0},
        ]
        apply_constraints(rows, {"cloud": "gcp", "throughput": "high"})
        assert _get_name(rows[0]) == "Good"

    def test_empty_constraints_noop(self):
        rows = [{"Name": "X", "_score": 1.0}]
        result = apply_constraints(rows, {})
        assert "_constraints" not in rows[0]
        assert result is rows

    def test_missing_column_is_unknown(self):
        rows = [{"Name": "X", "_score": 1.0}]
        apply_constraints(rows, {"cloud": "gcp"})
        assert rows[0]["_constraints"]["cloud"]["match"] == "unknown"

    def test_latency_lower_is_better(self):
        rows = [{"Name": "Fast", "Latency Tier": "sub-ms", "_score": 1.0}]
        apply_constraints(rows, {"latency": "low-ms"})
        assert rows[0]["_constraints"]["latency"]["match"] is True  # sub-ms beats low-ms


# ── _parse_scale ─────────────────────────────────────────────────────

class TestParseScale:
    def test_reads_writes(self):
        scales = _parse_scale("100M reads/day, 1M writes/day")
        assert scales["reads_per_day"] == 100_000_000
        assert scales["writes_per_day"] == 1_000_000

    def test_dau(self):
        scales = _parse_scale("10M DAU")
        assert scales["dau"] == 10_000_000

    def test_empty(self):
        assert _parse_scale("no numbers here") == {}


# ── capacity helpers ─────────────────────────────────────────────────

class TestCapacityHelpers:
    def test_qps_from_daily(self):
        result = _qps_from_daily(86400)
        assert result["avg"] == 1.0
        assert result["peak"] == 3.0

    def test_storage_estimate(self):
        result = _storage_estimate(1_000_000)
        assert result["raw_gb"] > 0
        assert result["with_replication_gb"] > result["raw_gb"]
        assert "assumptions" in result


# ── decide ───────────────────────────────────────────────────────────

class TestDecide:
    def test_returns_dict(self):
        result = decide("best database for 50k writes/sec")
        assert isinstance(result, dict)
        assert result["mode"] == "decide"
        assert "candidates" in result

    def test_candidates_list(self):
        result = decide("message queue for event streaming")
        assert isinstance(result["candidates"], list)

    def test_empty_query(self):
        result = decide("")
        assert result["mode"] == "decide"
        assert isinstance(result["candidates"], list)


# ── adr ──────────────────────────────────────────────────────────────

class TestAdr:
    def test_returns_dict(self):
        result = adr("Use PostgreSQL for OLTP", ["database"])
        assert isinstance(result, dict)
        assert "title" in result or "error" in result

    def test_without_domains(self):
        result = adr("Adopt Redis caching", [])
        assert "error" in result

    def test_braces_in_title(self):
        result = adr("Use {Redis} for cache", ["cache"])
        # Should not crash — braces are escaped
        assert "error" in result or "title" in result


# ── design ───────────────────────────────────────────────────────────

class TestDesign:
    def test_returns_dict(self):
        result = design("real-time notification system at 10k msgs/sec")
        assert isinstance(result, dict)
        assert result["mode"] == "design"

    def test_has_sections(self):
        result = design("payment processing pipeline")
        assert "sections" in result

    def test_capacity_math(self):
        result = design("url shortener, 100M reads/day, 1M writes/day")
        assert "read_qps" in result["capacity"]
        assert "write_qps" in result["capacity"]
        assert "storage_1yr" in result["capacity"]


# ── formatters ───────────────────────────────────────────────────────

class TestFormatters:
    def test_format_decide_error(self):
        assert "Error" in format_decide({"error": "test error"})

    def test_format_decide_happy(self):
        result = decide("database for 50k writes/sec")
        output = format_decide(result)
        assert "## Backend Pro Max" in output
        assert "Candidates" in output

    def test_format_adr_error(self):
        assert "Error" in format_adr({"error": "test"})

    def test_format_adr_happy(self):
        result = adr("Use Redis", ["cache"])
        output = format_adr(result)
        assert isinstance(output, str)

    def test_format_design_error(self):
        assert "Error" in format_design({"error": "test"})

    def test_format_design_happy(self):
        result = design("url shortener 100M reads/day")
        output = format_design(result)
        assert "## Backend Pro Max" in output
        assert "Scaffold" in output
