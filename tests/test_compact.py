"""Opt-in compact evidence must stay bounded, grounded, and backwards compatible."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from backendpro.scripts.core import search, search_all, search_stack
from backendpro.scripts.templates import (
    COMPACT_MAX_CHARS,
    compact_json,
    format_compact,
    format_search_response,
)

ROOT = Path(__file__).resolve().parents[1]


def payload(rows):
    return {"query": "how to fix a timeout", "domain": "pattern", "count": len(rows), "results": rows}


def example():
    return {
        "Name": "Example", "Solution": "Retry only idempotent operations.",
        "When to Use": "Transient failures", "When NOT to Use": "Non-idempotent mutations",
        "Failure Mode": "Duplicate side effects", "Verification Method": "Inject a timeout after commit.",
        "_citation": "[BPM:pattern.example]", "Source URL": "https://example.test/guide",
        "Last Updated": "2026-01-01", "_score": 100,
    }


def test_compact_preserves_source_fields_and_does_not_mutate():
    raw = payload([example()])
    before = copy.deepcopy(raw)
    compact = format_compact(raw)
    unit = compact["results"][0]
    assert raw == before
    assert compact["intent"] == "troubleshoot"
    for field, value in unit["facts"].items():
        assert raw["results"][0][field] == value
    assert unit["citation"] == raw["results"][0]["_citation"]
    assert unit["sources"]["Source URL"] == raw["results"][0]["Source URL"]
    assert unit["last_updated"] == "2026-01-01"
    assert "_score" not in json.dumps(compact)
    assert "confidence" not in unit


def test_raw_default_preserves_exact_object_and_error_contract():
    raw = payload([example()])
    assert format_search_response(raw) is raw
    error = {"error": "Unknown domain"}
    assert format_search_response(error) is error
    with pytest.raises(ValueError, match="Unknown domain"):
        format_search_response(error, "compact")
    with pytest.raises(ValueError, match="response_format"):
        format_search_response(raw, "unknown")


def test_missing_guidance_freshness_and_sources_are_explicit():
    result = format_compact(payload([{"Name": "Example", "Solution": "Quoted guidance"}]))
    unit = result["results"][0]
    assert unit["sources"] == {}
    assert unit["last_updated"] is None
    assert unit["citation"] is None
    assert {"verification", "constraints", "sources", "last_updated", "citation"} <= set(unit["missing"])
    assert "verification" not in unit["facts"]


def test_exact_character_limit_and_whole_unit_omission():
    raw = payload([example()])
    size = len(compact_json(format_compact(raw)))
    exact = format_compact(raw, size)
    assert exact["count"] == 1
    below = format_compact(raw, size - 1)
    assert below["count"] == 0
    assert below["omitted_count"] == 1
    assert below["status"] == "budget_exhausted"
    assert below["truncated"]
    assert len(compact_json(below)) <= size - 1


def test_large_facts_are_not_sliced_or_separated_from_citations():
    row = {**example(), "When NOT to Use": "constraint " * 2000}
    result = format_compact(payload([row, example()]))
    assert result["results"] == []
    assert result["matched_count"] == result["omitted_count"] == 2
    assert len(compact_json(result)) <= COMPACT_MAX_CHARS


def test_no_matches_is_not_budget_exhaustion():
    result = format_compact(payload([]))
    assert result["status"] == "no_matches"
    assert not result["truncated"]


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_limits_raise(limit):
    with pytest.raises(ValueError, match="positive integer"):
        format_compact(payload([]), limit)


def test_oversized_query_is_rejected_not_silently_clipped():
    with pytest.raises(ValueError, match="shorten the query"):
        format_compact({**payload([]), "query": "x" * 7000})


def test_unicode_is_bounded_without_changing_source_text():
    row = {**example(), "Solution": "\u6570\u636e" * 500}
    result = format_compact(payload([row]))
    text = compact_json(result)
    assert len(text) <= COMPACT_MAX_CHARS
    assert json.loads(text)["results"][0]["facts"]["Solution"] == row["Solution"]


@pytest.mark.parametrize("raw", [
    search("circuit breaker", domain="pattern"),
    search_stack("error handling", "go"),
    search_all("idempotency"),
])
def test_domain_stack_and_cross_domain_results(raw):
    compact = format_compact(raw)
    assert compact["matched_count"] > 0
    assert compact["count"] > 0
    assert len(compact_json(compact)) <= COMPACT_MAX_CHARS
    rows = raw["results"]
    flattened = [row for group in rows.values() for row in group] if isinstance(rows, dict) else rows
    assert all(unit["citation"] in {row["_citation"] for row in flattened} for unit in compact["results"])


@pytest.mark.parametrize("options", [
    ["--domain", "pattern"], ["--stack", "go"], ["--all"],
    ["--domain", "pattern", "--intent", "incident", "--json"],
])
def test_cli_compact_is_bounded_json(options):
    result = subprocess.run(
        [sys.executable, "-m", "backendpro.scripts.search", "circuit breaker", "--compact", *options],
        capture_output=True, text=True, check=True,
    )
    assert len(result.stdout.rstrip("\n")) <= COMPACT_MAX_CHARS
    value = json.loads(result.stdout)
    assert value["format"] == "compact-v1"
    if "--intent" in options:
        assert value["intent"] == "incident"


@pytest.mark.parametrize("args", [
    ["test", "--jsonl"], ["test", "--decide"], ["test", "--design"], ["--list"],
    ["--interactive"], ["compare", "Kafka", "RabbitMQ"], ["latency"],
    ["--stale", "--domain", "pattern", "--max-age-months", "18"],
])
def test_cli_rejects_incompatible_modes(args):
    result = subprocess.run(
        [sys.executable, "-m", "backendpro.scripts.search", *args, "--compact"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "--compact supports" in result.stderr


def test_retrieval_guidance_matches_all_installed_templates():
    paths = [
        ROOT / ".claude/skills/backend-pro-max/SKILL.md",
        ROOT / "src/backend-pro-max/templates/base/SKILL.md",
        ROOT / "src/backend-pro-max/templates/base/skill-content.md",
    ]
    sections = [path.read_text().split("## Retrieval decision\n", 1)[1].split("\n## ", 1)[0] for path in paths]
    assert sections[0] == sections[1] == sections[2]
    assert "Skip retrieval for typos" in sections[0]
    assert "Never guess a stack" in sections[0]
