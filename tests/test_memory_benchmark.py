"""Authored chronological controls; synthetic counters are never efficacy evidence."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
import test_memory
from backendpro.scripts import memory, memory_benchmark, repository
from backendpro.scripts.templates import compact_json

workspace = test_memory.workspace
vault = test_memory.vault
summary = test_memory.summary


@pytest.fixture
def protocol():
    tasks = []
    for family, prefix in (("retry", ""), ("orders", "orders-")):
        for ordinal, name in enumerate(("first", "second")):
            tasks.append({
                "id": prefix + name, "sequence": "pilot", "family": family, "ordinal": ordinal,
                "allowed_tasks": [prefix + "first"] if ordinal else [],
                "query": "retry attempts", "library_versions": {"python": "3.12.13"},
            })
    return {
        "format": "memory-sequence-v1", "study": "authored-fixture",
        "preregistered_at": test_memory.stamp(-4), "model_revision": "synthetic-fixture-no-model-called",
        "repetitions": 1, "max_chars": 6000, "tasks": tasks,
    }


def observations(protocol):
    rows = []
    start = datetime.now(timezone.utc) - timedelta(days=2)
    for task in protocol["tasks"]:
        for arm in memory.ARMS:
            rows.append({
                "task": task["id"], "arm": arm, "repetition": 0,
                "protocol_sha256": repository._identity(protocol),
                "started_at": (start + timedelta(minutes=task["ordinal"] * 2)).isoformat().replace("+00:00", "Z"),
                "finished_at": (start + timedelta(minutes=task["ordinal"] * 2 + 1)).isoformat().replace("+00:00", "Z"),
                "status": "completed", "resolved": True,
                "input_tokens": 700 if arm == "verified_memory" else 900,
                "output_tokens": 100, "setup_tokens": 20 if arm == "verified_memory" else 0,
                "source_tasks": [] if arm == "no_memory" else task["allowed_tasks"],
                "context_sha256": "0" * 64, "stale_guidance": False, "contamination": False,
            })
    return rows


def test_arm_reset_and_only_authorized_predecessors(protocol, vault, summary):
    summary["origin"]["sequence"] = memory_benchmark.sequence_scope(protocol, "pilot")
    memory.manage("put", value=summary, approve=True, **vault)
    test_memory.enable(vault)
    recalled = memory_benchmark.context_for_task(protocol, "second", "verified_memory", **vault)
    assert recalled["count"] == 1
    assert len(compact_json(recalled)) <= protocol["max_chars"]
    assert memory_benchmark.context_for_task(protocol, "first", "verified_memory", **vault)["count"] == 0
    assert memory_benchmark.context_for_task(protocol, "orders-second", "verified_memory", **vault)["count"] == 0
    raw = {"first": {"tool_context": "Authored prior tool output: retry takes a positive attempt count.",
                     "approved": True, "source_arm": "raw_prior_context",
                     "scope": memory_benchmark.sequence_scope(protocol, "pilot")}}
    baseline = memory_benchmark.context_for_task(protocol, "second", "raw_prior_context", prior_context=raw, **vault)
    assert baseline["count"] == 1 and baseline["results"][0]["kind"] == "raw_prior_context"
    with pytest.raises(ValueError, match="cross treatment"):
        memory_benchmark.context_for_task(protocol, "second", "verified_memory", prior_context=raw, **vault)
    memory.manage("revoke-gate", **vault)
    assert memory_benchmark.context_for_task(protocol, "second", "no_memory", **vault)["count"] == 0
    with pytest.raises(ValueError, match="disabled"):
        memory_benchmark.context_for_task(protocol, "second", "verified_memory", **vault)
    assert memory.manage("status", **vault)["records"] == 1
    assert "Authored prior tool output" not in (memory.Path(vault["store"]) / "memory.json").read_text()


def test_independent_study_and_repetition_cannot_reuse_state(protocol, vault, summary):
    protocol["repetitions"] = 2
    summary["origin"]["sequence"] = memory_benchmark.sequence_scope(protocol, "pilot", 0)
    memory.manage("put", value=summary, approve=True, **vault)
    test_memory.enable(vault)
    assert memory_benchmark.context_for_task(protocol, "second", "verified_memory", **vault)["count"] == 1
    assert memory_benchmark.context_for_task(protocol, "second", "verified_memory", repetition=1, **vault)["count"] == 0
    protocol["study"] = "independent-study"
    assert memory_benchmark.context_for_task(protocol, "second", "verified_memory", **vault)["count"] == 0


@pytest.mark.parametrize("source", ["second", "orders-first", "unknown"])
def test_future_family_and_unknown_permissions_rejected(protocol, source):
    protocol["tasks"][1]["allowed_tasks"] = [source]
    with pytest.raises(ValueError, match="forbidden"):
        memory_benchmark.validate_protocol(protocol)


def test_raw_context_rejects_wrong_arm_missing_and_unapproved(protocol, vault):
    for raw in ({}, {"first": {"tool_context": "safe", "approved": False, "source_arm": "raw_prior_context"}},
                {"first": {"tool_context": "safe", "approved": True, "source_arm": "verified_memory"}}):
        with pytest.raises(ValueError):
            memory_benchmark.context_for_task(protocol, "second", "raw_prior_context", prior_context=raw, **vault)


def test_measured_setup_tokens_paired_effects_and_uncertainty(protocol):
    result = memory_benchmark.evaluate_sequences(protocol, observations(protocol))
    assert result["assigned_attempts"] == 12 and result["family_clusters"] == 2
    assert result["arm_totals"]["verified_memory"]["tokens"] == 3280
    for row in result["comparisons"].values():
        assert row["token_reduction"] == pytest.approx(0.18)
        assert row["resolution_delta"] == 0
        assert row["resolution_delta_interval"] == [0, 0]
        assert row["diagnostic_thresholds_met"]
    assert result["decision"] == "eligible_for_independent_review"
    assert not result["quality_gates_demonstrated"]


def test_token_threshold_and_failure_denominator(protocol):
    rows = observations(protocol)
    for row in rows:
        if row["arm"] == "verified_memory":
            row["setup_tokens"] = 60
    result = memory_benchmark.evaluate_sequences(protocol, rows)
    assert result["comparisons"]["no_memory"]["token_reduction"] == pytest.approx(0.14)
    assert not result["comparisons"]["no_memory"]["diagnostic_thresholds_met"]
    rows[2]["resolved"] = False
    rows[2]["status"] = "timeout"
    result = memory_benchmark.evaluate_sequences(protocol, rows)
    assert result["arm_totals"]["verified_memory"]["attempts"] == 4
    assert result["arm_totals"]["verified_memory"]["failed_or_timeout"] == 1
    assert result["comparisons"]["no_memory"]["resolution_delta"] == -0.25


@pytest.mark.parametrize("field", ["stale_guidance", "contamination"])
def test_regressions_reject_memory_even_when_counters_look_good(protocol, field):
    rows = observations(protocol)
    rows[2][field] = True
    assert memory_benchmark.evaluate_sequences(protocol, rows)["decision"] == "reject"


def test_one_family_and_zero_tokens_are_inconclusive(protocol):
    protocol["tasks"] = protocol["tasks"][:2]
    rows = observations(protocol)
    for row in rows:
        row["input_tokens"] = row["output_tokens"] = row["setup_tokens"] = 0
    result = memory_benchmark.evaluate_sequences(protocol, rows)
    assert result["decision"] == "inconclusive"
    assert result["comparisons"]["no_memory"]["token_reduction"] is None
    assert result["comparisons"]["no_memory"]["resolution_delta_interval"] is None


@pytest.mark.parametrize("mutation", [
    lambda rows: rows.pop(),
    lambda rows: rows.append(copy.deepcopy(rows[0])),
    lambda rows: rows[0].update(protocol_sha256="1" * 64),
    lambda rows: rows[0].update(source_tasks=["first"]),
    lambda rows: rows[2].update(source_tasks=["second"]),
    lambda rows: rows[0].update(status="failed"),
    lambda rows: rows[0].update(input_tokens=True),
    lambda rows: rows[3].update(started_at=rows[0]["started_at"]),
])
def test_missing_failed_future_unpaired_or_nonchronological_runs_fail(protocol, mutation):
    rows = observations(protocol)
    mutation(rows)
    with pytest.raises(ValueError):
        memory_benchmark.evaluate_sequences(protocol, rows)


def test_report_cli_matches_core_and_preserves_inputs(protocol, tmp_path):
    rows = observations(protocol)
    source, runs, output = (tmp_path / name for name in ("protocol.json", "runs.json", "report.json"))
    source.write_text(json.dumps(protocol))
    runs.write_text(json.dumps(rows))
    command = [sys.executable, "-m", "backendpro.scripts.memory_benchmark", str(source), str(runs), "--output"]
    subprocess.run([*command, str(output)], check=True, capture_output=True, text=True)
    assert json.loads(output.read_text()) == memory_benchmark.evaluate_sequences(protocol, rows)
    denied = subprocess.run([*command, str(source)], capture_output=True, text=True)
    assert denied.returncode == 2 and "must not overwrite" in denied.stderr
    assert json.loads(source.read_text()) == protocol
