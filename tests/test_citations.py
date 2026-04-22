"""Tests for Tier 3.4 — Citation tokens.

Every search result should carry a stable, greppable `_citation` field
of the form `[BPM:<domain>.<name_slug>]`.
"""
from __future__ import annotations

import re

# Import the citation helper directly for unit tests.
from core import _make_citation, compare, search, search_all, search_stack

# ────────────────────────────────────────────────────────────────
# Unit tests for _make_citation helper
# ────────────────────────────────────────────────────────────────

CITATION_RE = re.compile(r"^\[BPM:[a-z0-9_-]+\.[a-z0-9_-]+\]$")


class TestMakeCitation:
    """_make_citation(domain, row, column=None) → '[BPM:domain.slug]'"""

    def test_basic(self):
        assert _make_citation("messaging", {"Name": "Kafka"}) == "[BPM:messaging.kafka]"

    def test_spaces_become_hyphens(self):
        c = _make_citation("pattern", {"Name": "Circuit Breaker"})
        assert c == "[BPM:pattern.circuit-breaker]"

    def test_special_chars_stripped(self):
        c = _make_citation("database", {"Name": "Cosmos DB (Azure)"})
        assert c == "[BPM:database.cosmos-db-azure]"

    def test_case_insensitive_slug(self):
        c = _make_citation("cache", {"Name": "Memcached"})
        assert c == "[BPM:cache.memcached]"

    def test_with_column(self):
        c = _make_citation("messaging", {"Name": "Kafka"}, column="Exactly Once")
        assert c == "[BPM:messaging.kafka.exactly-once]"

    def test_max_slug_length(self):
        long_name = "A" * 100
        c = _make_citation("database", {"Name": long_name})
        # Slug portion should be at most 40 chars
        slug_part = c[len("[BPM:database."):-1]
        assert len(slug_part) <= 40

    def test_unicode_handled(self):
        c = _make_citation("api", {"Name": "gRPC/Protobüf"})
        assert CITATION_RE.match(c), f"Citation {c!r} does not match expected format"

    def test_fallback_keys(self):
        """Row without 'Name' falls back to 'Service', 'Technology', etc."""
        c = _make_citation("cloud", {"Service": "Lambda"})
        assert c == "[BPM:cloud.lambda]"

    def test_empty_name_fallback(self):
        c = _make_citation("cache", {"Name": "", "Category": "CDN"})
        assert "cdn" in c.lower()

    def test_format_matches_regex(self):
        c = _make_citation("messaging", {"Name": "RabbitMQ"})
        assert CITATION_RE.match(c)


# ────────────────────────────────────────────────────────────────
# Integration: citations present in search results
# ────────────────────────────────────────────────────────────────

class TestSearchCitations:
    def test_search_results_have_citation(self):
        result = search("kafka", domain="messaging")
        assert result.get("results"), "Expected at least one result"
        for row in result["results"]:
            assert "_citation" in row, f"Missing _citation in row: {row}"
            assert row["_citation"].startswith("[BPM:messaging.")

    def test_search_all_results_have_citation(self):
        result = search_all("circuit breaker", max_results=1)
        for domain, rows in result.get("results", {}).items():
            for row in rows:
                assert "_citation" in row, f"Missing _citation in {domain} row"
                assert row["_citation"].startswith(f"[BPM:{domain}.")

    def test_search_stack_results_have_citation(self):
        result = search_stack("error handling", "go")
        for row in result.get("results", []):
            assert "_citation" in row

    def test_compare_entries_have_citation(self):
        result = compare(["Kafka", "RabbitMQ"], domain="messaging")
        for name, entry in result.get("entries", {}).items():
            if entry:  # non-empty (not a missing entry)
                assert "_citation" in entry, f"Missing _citation for {name}"

    def test_citation_stability(self):
        """Same query twice → same citation strings."""
        r1 = search("kafka", domain="messaging")
        r2 = search("kafka", domain="messaging")
        c1 = [row["_citation"] for row in r1["results"]]
        c2 = [row["_citation"] for row in r2["results"]]
        assert c1 == c2

    def test_citations_unique_within_domain(self):
        """No two rows in a single search should share a citation."""
        result = search("database", domain="database", max_results=20)
        citations = [r["_citation"] for r in result["results"]]
        assert len(citations) == len(set(citations)), f"Duplicate citations: {citations}"

    def test_citation_format_all_results(self):
        """Every citation matches the expected regex pattern."""
        result = search("cache", domain="cache", max_results=10)
        pattern = re.compile(r"^\[BPM:[a-z0-9_-]+\.[a-z0-9_-]+(?:\.[a-z0-9_-]+)?\]$")
        for row in result["results"]:
            assert pattern.match(row["_citation"]), \
                f"Bad citation format: {row['_citation']}"
