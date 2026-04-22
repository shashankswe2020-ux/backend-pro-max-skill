"""Tests for intent classification (Tier 2 — Task 2.1)."""
from __future__ import annotations

import json
import subprocess
import sys

from core import Intent, classify_intent


class TestClassifyIntentDefinition:
    """Intent.DEFINITION detection."""

    def test_what_is(self):
        assert classify_intent("what is a saga") == Intent.DEFINITION

    def test_explain(self):
        assert classify_intent("explain CQRS") == Intent.DEFINITION

    def test_define(self):
        assert classify_intent("define circuit breaker") == Intent.DEFINITION

    def test_what_are(self):
        assert classify_intent("what are bounded contexts") == Intent.DEFINITION

    def test_how_does_work(self):
        assert classify_intent("how does raft consensus work") == Intent.DEFINITION


class TestClassifyIntentComparison:
    """Intent.COMPARISON detection."""

    def test_vs(self):
        assert classify_intent("kafka vs rabbitmq") == Intent.COMPARISON

    def test_versus(self):
        assert classify_intent("redis versus memcached") == Intent.COMPARISON

    def test_compare(self):
        assert classify_intent("compare postgres and mysql") == Intent.COMPARISON

    def test_difference_between(self):
        assert classify_intent("difference between saga and 2pc") == Intent.COMPARISON


class TestClassifyIntentTroubleshoot:
    """Intent.TROUBLESHOOT detection."""

    def test_consumer_lag(self):
        assert classify_intent("kafka consumer lag fix") == Intent.TROUBLESHOOT

    def test_timeout(self):
        assert classify_intent("connection timeout to database") == Intent.TROUBLESHOOT

    def test_high_latency(self):
        assert classify_intent("high latency on API endpoint") == Intent.TROUBLESHOOT

    def test_out_of_memory(self):
        assert classify_intent("out of memory in production") == Intent.TROUBLESHOOT

    def test_slow(self):
        assert classify_intent("slow query in postgres") == Intent.TROUBLESHOOT

    def test_connection_pool_exhausted(self):
        assert classify_intent("connection pool exhausted") == Intent.TROUBLESHOOT


class TestClassifyIntentMigration:
    """Intent.MIGRATION detection."""

    def test_migrate_from(self):
        assert classify_intent("migrate from mysql to postgres") == Intent.MIGRATION

    def test_move_from(self):
        assert classify_intent("move from monolith to microservices") == Intent.MIGRATION

    def test_switch_from(self):
        assert classify_intent("switch from REST to gRPC") == Intent.MIGRATION


class TestClassifyIntentDesign:
    """Intent.DESIGN detection."""

    def test_design(self):
        assert classify_intent("design a URL shortener") == Intent.DESIGN

    def test_system_design(self):
        assert classify_intent("system design for chat app") == Intent.DESIGN

    def test_how_to_build(self):
        assert classify_intent("how to build a rate limiter") == Intent.DESIGN


class TestClassifyIntentIncident:
    """Intent.INCIDENT detection."""

    def test_outage(self):
        assert classify_intent("database outage response") == Intent.INCIDENT

    def test_failover(self):
        assert classify_intent("broker failover procedure") == Intent.INCIDENT

    def test_postmortem(self):
        assert classify_intent("write a postmortem") == Intent.INCIDENT

    def test_runbook(self):
        assert classify_intent("runbook for redis failover") == Intent.INCIDENT


class TestClassifyIntentGeneral:
    """Intent.GENERAL fallback."""

    def test_plain_topic(self):
        assert classify_intent("circuit breaker") == Intent.GENERAL

    def test_empty(self):
        assert classify_intent("") == Intent.GENERAL

    def test_weak_signal_only(self):
        # "or" alone is too weak to trigger COMPARISON
        assert classify_intent("caching or something") == Intent.GENERAL


class TestIntentOverride:
    """--intent flag forces a specific intent."""

    def test_forced_intent_in_json(self):
        search_py = str(
            __import__("pathlib").Path(__file__).resolve().parent.parent
            / "src" / "backend-pro-max" / "scripts" / "search.py"
        )
        result = subprocess.run(
            [sys.executable, search_py,
             "circuit breaker", "--domain", "pattern",
             "--intent", "definition", "--json"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data.get("intent") == "definition"

    def test_auto_intent_in_json(self):
        search_py = str(
            __import__("pathlib").Path(__file__).resolve().parent.parent
            / "src" / "backend-pro-max" / "scripts" / "search.py"
        )
        result = subprocess.run(
            [sys.executable, search_py,
             "what is a saga", "--domain", "pattern", "--json"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data.get("intent") == "definition"


class TestIntentTemplateOutput:
    """Verify intent-specific templates produce structured output."""

    def test_troubleshoot_template_has_sections(self):
        from templates import format_troubleshoot
        result = {
            "domain": "performance",
            "query": "n+1 query",
            "count": 1,
            "results": [{
                "Topic": "N+1 query",
                "Symptom": "Many tiny SELECTs",
                "Root Cause": "ORM lazy loading",
                "Fix": "Eager-load",
                "_score": 5.0,
            }],
        }
        output = format_troubleshoot(result)
        assert "Troubleshooting" in output
        assert "Symptom" in output
        assert "Root Cause" in output
        assert "Fix" in output

    def test_definition_template_has_sections(self):
        from templates import format_definition
        result = {
            "domain": "pattern",
            "query": "saga",
            "count": 1,
            "results": [{
                "Name": "Saga",
                "Problem": "Distributed transactions",
                "Solution": "Choreography or orchestration",
                "When to Use": "Cross-service workflows",
                "_score": 4.0,
            }],
        }
        output = format_definition(result)
        assert "Definition" in output
        assert "Saga" in output
        assert "When to Use" in output  # exact column name preserved

    def test_migration_template_has_sections(self):
        from templates import format_migration
        result = {
            "domain": "database",
            "query": "migrate to postgres",
            "count": 1,
            "results": [{
                "Name": "PostgreSQL",
                "Use Case": "OLTP",
                "Strengths": "Extensible",
                "_score": 3.0,
            }],
        }
        output = format_migration(result)
        assert "Migration" in output

    def test_format_by_intent_returns_none_for_general(self):
        from templates import format_by_intent
        result = {"domain": "pattern", "query": "test", "count": 0, "results": []}
        assert format_by_intent("general", result) is None

    def test_format_by_intent_dispatches_troubleshoot(self):
        from templates import format_by_intent
        result = {"domain": "perf", "query": "slow", "count": 0, "results": []}
        output = format_by_intent("troubleshoot", result)
        assert output is not None
        assert "Troubleshooting" in output
