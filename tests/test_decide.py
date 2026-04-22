"""Tests for the decide module (Tier 1 – Decision Intelligence)."""
from __future__ import annotations

from core import parse_constraints
from decide import adr, decide, design, extract_constraints

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


# ── adr ──────────────────────────────────────────────────────────────

class TestAdr:
    def test_returns_dict(self):
        result = adr("Use PostgreSQL for OLTP", ["database"])
        assert isinstance(result, dict)
        assert "title" in result or "error" in result

    def test_without_domains(self):
        result = adr("Adopt Redis caching", [])
        assert "error" in result  # requires at least one domain


# ── design ───────────────────────────────────────────────────────────

class TestDesign:
    def test_returns_dict(self):
        result = design("real-time notification system at 10k msgs/sec")
        assert isinstance(result, dict)
        assert result["mode"] == "design"

    def test_has_sections(self):
        result = design("payment processing pipeline")
        assert "sections" in result
