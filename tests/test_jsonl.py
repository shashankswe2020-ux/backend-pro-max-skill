"""Tests for Tier 3.2 — Streaming JSON Lines (--jsonl) output."""
from __future__ import annotations

import json

from core import compare, search, search_all
from search import (
    format_jsonl,
    format_jsonl_all,
    format_jsonl_compare,
)


class TestFormatJsonl:
    def test_single_domain_one_line_per_result(self):
        result = search("kafka", domain="messaging")
        lines = format_jsonl(result).strip().split("\n")
        assert len(lines) == result["count"]

    def test_each_line_is_valid_json(self):
        result = search("kafka", domain="messaging")
        for line in format_jsonl(result).strip().split("\n"):
            obj = json.loads(line)
            assert "_index" in obj
            assert "_domain" in obj or "_score" in obj

    def test_no_trailing_comma_or_array(self):
        result = search("kafka", domain="messaging")
        text = format_jsonl(result)
        assert not text.strip().startswith("[")
        assert not text.strip().endswith(",")

    def test_includes_citation(self):
        result = search("kafka", domain="messaging")
        for line in format_jsonl(result).strip().split("\n"):
            obj = json.loads(line)
            assert "_citation" in obj

    def test_empty_results(self):
        result = {"domain": "messaging", "query": "zzzznothing", "file": "messaging.csv",
                  "count": 0, "results": []}
        text = format_jsonl(result)
        assert text.strip() == ""


class TestFormatJsonlAll:
    def test_cross_domain_includes_domain_field(self):
        result = search_all("circuit breaker", max_results=1)
        text = format_jsonl_all(result).strip()
        if not text:
            return  # no results to check
        for line in text.split("\n"):
            obj = json.loads(line)
            assert "_domain" in obj

    def test_each_line_valid_json(self):
        result = search_all("kafka", max_results=1)
        for line in format_jsonl_all(result).strip().split("\n"):
            if line:
                json.loads(line)


class TestFormatJsonlCompare:
    def test_per_field_lines(self):
        result = compare(["Kafka", "RabbitMQ"], domain="messaging")
        text = format_jsonl_compare(result).strip()
        assert text  # should have some output
        for line in text.split("\n"):
            obj = json.loads(line)
            assert "_field" in obj

    def test_each_line_valid_json(self):
        result = compare(["Kafka", "RabbitMQ"], domain="messaging")
        for line in format_jsonl_compare(result).strip().split("\n"):
            if line:
                json.loads(line)
