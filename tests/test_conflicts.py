"""Tests for the conflict detector."""
from __future__ import annotations

import json

import conflicts


def test_conflict_rules_count():
    """At least 10 conflict rules must be defined."""
    assert len(conflicts.CONFLICT_RULES) >= 10


def test_conflict_rules_structure():
    """Each rule must have the required keys."""
    for rule in conflicts.CONFLICT_RULES:
        assert "id" in rule
        assert "description" in rule
        assert "side_a" in rule
        assert "side_b" in rule
        assert "domain" in rule["side_a"]
        assert "query" in rule["side_a"]
        assert "domain" in rule["side_b"]
        assert "query" in rule["side_b"]


def test_conflict_rule_domains_exist():
    """All domains referenced in rules must exist in CSV_CONFIG."""
    from core import CSV_CONFIG
    valid_domains = set(CSV_CONFIG.keys())
    for rule in conflicts.CONFLICT_RULES:
        assert rule["side_a"]["domain"] in valid_domains, (
            f"Rule '{rule['id']}' side_a domain '{rule['side_a']['domain']}' not in CSV_CONFIG"
        )
        assert rule["side_b"]["domain"] in valid_domains, (
            f"Rule '{rule['id']}' side_b domain '{rule['side_b']['domain']}' not in CSV_CONFIG"
        )


def test_scan_conflicts_returns_list():
    """scan_conflicts must return a list."""
    tensions = conflicts.scan_conflicts()
    assert isinstance(tensions, list)


def test_scan_conflicts_with_domain_filter():
    """Filtering by domain should only return tensions involving that domain."""
    tensions = conflicts.scan_conflicts(domain="cache")
    for t in tensions:
        domains = {t["side_a"]["domain"], t["side_b"]["domain"]}
        assert "cache" in domains, f"Tension {t['id']} doesn't involve cache"


def test_scan_conflicts_tension_structure():
    """Each tension must have the expected structure."""
    tensions = conflicts.scan_conflicts()
    for t in tensions:
        assert "id" in t
        assert "description" in t
        assert "side_a" in t
        assert "side_b" in t
        assert "domain" in t["side_a"]
        assert "name" in t["side_a"]
        assert "citation" in t["side_a"]


def test_format_tensions_empty():
    result = conflicts.format_tensions([])
    assert "No known tensions" in result


def test_format_tensions_with_data():
    tensions = [{
        "id": "test",
        "description": "Test tension",
        "side_a": {"domain": "a", "name": "X", "citation": "[BPM:a.1]"},
        "side_b": {"domain": "b", "name": "Y", "citation": "[BPM:b.1]"},
    }]
    result = conflicts.format_tensions(tensions)
    assert "Tension" in result
    assert "Test tension" in result
    assert "[BPM:a.1]" in result


def test_format_tensions_json():
    tensions = [{
        "id": "test",
        "description": "Test tension",
        "side_a": {"domain": "a", "name": "X", "citation": "[BPM:a.1]"},
        "side_b": {"domain": "b", "name": "Y", "citation": "[BPM:b.1]"},
    }]
    result = conflicts.format_tensions_json(tensions)
    parsed = json.loads(result)
    assert parsed["count"] == 1
    assert len(parsed["tensions"]) == 1


def test_scan_finds_known_tensions():
    """At least some of the curated conflict rules should fire."""
    tensions = conflicts.scan_conflicts()
    # We expect at least a few tensions to fire — the KB has enough data
    assert len(tensions) >= 1, "Expected at least 1 tension to fire"


def test_scan_with_custom_rules():
    """Custom rules can be passed to scan_conflicts."""
    # Use a rule that should always fire (broad queries)
    custom = [{
        "id": "custom-test",
        "description": "Custom test tension",
        "side_a": {"domain": "database", "query": "postgres"},
        "side_b": {"domain": "cache", "query": "redis"},
    }]
    tensions = conflicts.scan_conflicts(rules=custom)
    assert len(tensions) == 1
    assert tensions[0]["id"] == "custom-test"


def test_scan_nonexistent_domain_returns_empty():
    """Filtering by a non-matching domain returns no tensions."""
    tensions = conflicts.scan_conflicts(domain="nonexistent-domain-xyz")
    assert tensions == []
