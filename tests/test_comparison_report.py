"""Checks for paired pilot metrics; no model-generated outcomes are mocked as real evidence."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "comparison_report", Path(__file__).resolve().parents[1] / "scripts/report_swebench_comparison.py",
)
assert SPEC is not None and SPEC.loader is not None
report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report)


def test_wilson_bounds():
    assert report.wilson(0, 18)[0] == pytest.approx(0)
    assert report.wilson(18, 18)[1] == pytest.approx(1)
    low, high = report.wilson(9, 18)
    assert low == pytest.approx(1 - high)
    assert 0 < low < 0.5 < high < 1


@pytest.mark.parametrize("successes,count", [(0, 0), (2, 1), (-1, 18)])
def test_invalid_counts(successes, count):
    with pytest.raises(ValueError):
        report.wilson(successes, count)


def test_identical_paired_outcomes():
    result = report.paired({"a": True, "b": False}, {"a": True, "b": False})
    assert result["difference_percentage_points"] == 0
    assert result["exact_mcnemar_p_unadjusted"] == 1
    assert result["both_resolved"] == result["neither_resolved"] == 1


def test_paired_direction_and_exact_probability():
    result = report.paired(dict.fromkeys("abcdef", True), dict.fromkeys("abcdef", False))
    assert result["left_only_resolved"] == 6
    assert result["right_only_resolved"] == 0
    assert result["difference_percentage_points"] == 100
    assert result["exact_mcnemar_p_unadjusted"] == pytest.approx(2 / 64)


def test_paired_sets_must_match():
    with pytest.raises(ValueError):
        report.paired({"a": True}, {"b": True})


def test_empty_pairs_are_not_a_success():
    with pytest.raises(ValueError):
        report.paired({}, {})


@pytest.fixture
def synthetic_run(tmp_path):
    """Synthetic artifacts stay in pytest's temporary directory, never published as results."""
    config = {
        "model": "claude-opus-5-5",
        "approved_amendments": {"excluded_instances": ["excluded-1", "excluded-2"]},
        "limitations": ["Synthetic test fixture only"],
    }
    (tmp_path / "protocol.json").write_text(json.dumps(config))
    attempts = []
    inputs = []
    for arm in report.ARMS:
        ids = [f"synthetic-{index}" for index in range(18)]
        summary = {"submitted_ids": ids, "completed_ids": ids, "resolved_ids": ids[::2],
                   "error_ids": [], "empty_patch_ids": []}
        model = f"claude-opus-5-5-{arm}"
        run_id = f"{tmp_path.name}-{arm}"
        (tmp_path / f"{model}.{run_id}.json").write_text(json.dumps(summary))
        for index, instance in enumerate(ids):
            patch = b"synthetic patch for unit test only"
            inputs.append({"instance_id": instance, "arm": arm})
            attempt = {
                "instance_id": instance, "arm": arm, "status": "finished", "model_turns": 1,
                "tool_calls": [], "seconds": 1, "patch_sha256": hashlib.sha256(patch).hexdigest(),
                "cost": {"accounted_upper_bound_micro_usd": 800, "anthropic_measured_micro_usd": 800},
            }
            attempts.append(attempt)
            folder = tmp_path / f"{instance}.{arm}"
            folder.mkdir()
            (folder / "patch.diff").write_bytes(patch)
            (folder / "response-00.json").write_text(json.dumps({
                "model": config["model"], "usage": {"input_tokens": 100, "output_tokens": 20},
            }))
            evidence = tmp_path / "logs/run_evaluation" / run_id / model / instance
            evidence.mkdir(parents=True)
            (evidence / "report.json").write_text(json.dumps({instance: {"resolved": index % 2 == 0}}))
    raw = json.dumps({"dataset_revision": "synthetic", "attempts": inputs}).encode()
    (tmp_path / "inputs.json").write_bytes(raw)
    (tmp_path / "generation.json").write_text(json.dumps({"attempts": attempts}))
    ledger = tmp_path / "ledger.db"
    with sqlite3.connect(ledger) as connection:
        connection.execute("CREATE TABLE charges(provider TEXT,reserved INTEGER,charged INTEGER)")
        connection.execute("INSERT INTO charges VALUES('anthropic',57600,57600)")
    (tmp_path / "provenance.json").write_text(json.dumps({
        "inputs_sha256": hashlib.sha256(raw).hexdigest(), "spending_ledger": str(ledger),
    }))
    return tmp_path


def test_report_validates_all_72_and_does_not_claim_unused_tools_helped(synthetic_run):
    result = report.build_report(synthetic_run)
    assert result["status"] == "completed"
    assert all(arm["assigned"] == 18 and arm["resolved"] == 9 for arm in result["arms"].values())
    assert "No knowledge tool was invoked" in result["interpretation"]
    assert len(result["paired_comparisons"]) == 6
    assert result["evaluation_gate"]["activation_measured"]
    assert not result["evaluation_gate"]["retrieval_comparison_evaluable"]
    assert "Retrieval comparison evaluable: **False**" in report.markdown(result)


def test_report_rejects_patch_changes(synthetic_run):
    (synthetic_run / "synthetic-0.baseline/patch.diff").write_text("modified")
    with pytest.raises(ValueError, match="Patch changed"):
        report.build_report(synthetic_run)


def test_report_rejects_token_cost_mismatch(synthetic_run):
    response = synthetic_run / "synthetic-0.baseline/response-00.json"
    value = json.loads(response.read_text())
    value["usage"]["output_tokens"] += 1
    response.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="token usage"):
        report.build_report(synthetic_run)


def test_evaluator_errors_do_not_become_a_complete_comparison(synthetic_run):
    path = synthetic_run / f"claude-opus-5-5-baseline.{synthetic_run.name}-baseline.json"
    summary = json.loads(path.read_text())
    summary["completed_ids"].remove("synthetic-0")
    summary["resolved_ids"].remove("synthetic-0")
    summary["error_ids"] = ["synthetic-0"]
    path.write_text(json.dumps(summary))
    result = report.build_report(synthetic_run)
    assert result["status"] == "incomplete"
    assert result["arms"]["baseline"]["assigned"] == 18
    assert result["paired_comparisons"] == {}


def evidence_attempt(tmp_path, arm, value, *, error=False, delivered=True):
    folder = tmp_path / f"case.{arm}"
    folder.mkdir(exist_ok=True)
    events = []
    for index, name in enumerate(sorted(report.KNOWLEDGE_TOOLS[arm])):
        artifact = folder / f"retrieval-{index}.json"
        raw = json.dumps(value)
        artifact.write_text(raw)
        output = json.dumps(value, ensure_ascii=False)
        truncated = len(output) > 6000
        if truncated:
            output = output[:6000] + "\n[Output truncated at 6000 characters]"
        events.append({
            "name": name, "input": {"query": "test"}, "is_error": error,
            "output": output, "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
            "delivered": delivered, "truncated": truncated,
            "evidence": {
                **report.describe_payload(value), "artifact": artifact.name,
                "sha256": hashlib.sha256(raw.encode()).hexdigest(),
            },
        })
    return {"instance_id": "case", "arm": arm, "status": "finished", "tool_calls": events}


def review_attempts(tmp_path, attempts, relevance="relevant", application="correct"):
    reviews = {}
    for item in attempts:
        for index, event in enumerate(item["tool_calls"]):
            reviews[f"case.{item['arm']}:{index}"] = {
                "output_sha256": event["output_sha256"], "relevance": relevance,
                "application": application, "rationale": "Synthetic reviewer fixture, not real evidence.",
            }
    (tmp_path / "evidence-review.json").write_text(json.dumps({
        "reviewer": "synthetic-test-reviewer", "rubric": "synthetic-v1", "events": reviews,
    }))


@pytest.mark.parametrize("value,status", [
    ({"results": []}, "empty"),
    ({"error": "offline"}, "error"),
    ({"results": [{"text": "unreviewed evidence"}]}, "returned"),
    ({"unexpected": "shape"}, "unclassified"),
])
def test_calls_alone_do_not_pass_retrieval_gate(tmp_path, value, status):
    attempt = evidence_attempt(tmp_path, "both", value, error=status == "error")
    gate = report.retrieval_gate(tmp_path, [attempt], True)
    assert not gate["retrieval_comparison_evaluable"]
    assert gate["event_statuses"] == {status: 2}


@pytest.mark.parametrize("relevance,application,delivered,expected", [
    ("relevant", "correct", True, True),
    ("relevant", "not_applied", True, True),
    ("relevant", "incorrect", True, True),
    ("irrelevant", "not_applied", True, False),
    ("relevant", "unknown", True, False),
    ("relevant", "correct", False, False),
])
def test_reviewed_useful_evidence_is_not_a_superiority_claim(
    tmp_path, relevance, application, delivered, expected,
):
    attempts = [
        evidence_attempt(tmp_path, arm, {"results": [{"text": "test"}]}, delivered=delivered)
        for arm in report.ARMS
    ]
    review_attempts(tmp_path, attempts, relevance, application)
    gate = report.retrieval_gate(tmp_path, attempts, True)
    assert gate["retrieval_comparison_evaluable"] is expected
    assert not gate["superiority_claim_supported"]


def test_required_retrieval_noncompliance_is_retained(tmp_path):
    attempts = [evidence_attempt(tmp_path, arm, {"results": [{"text": "test"}]}) for arm in report.ARMS]
    review_attempts(tmp_path, attempts)
    attempts[1]["tool_calls"].append({"name": "shell"})
    assert report.retrieval_gate(tmp_path, attempts, True, "required")["retrieval_comparison_evaluable"]
    attempts[1]["tool_calls"] = list(reversed(attempts[1]["tool_calls"]))
    (tmp_path / "evidence-review.json").unlink()
    gate = report.retrieval_gate(tmp_path, attempts, True, "required")
    assert not gate["required_use_compliance"]["case.context7"]
    assert any("before the first shell" in reason for reason in gate["reasons"])
    assert len(gate["events"]) == 4


def test_tampered_retrieval_artifact_is_rejected(tmp_path):
    attempt = evidence_attempt(tmp_path, "backendpro", {"results": []})
    (tmp_path / "case.backendpro/retrieval-0.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        report.retrieval_gate(tmp_path, [attempt], True)


def test_review_is_bound_to_model_visible_output(tmp_path):
    attempt = evidence_attempt(tmp_path, "backendpro", {"results": [{"text": "test"}]})
    review_attempts(tmp_path, [attempt])
    attempt["tool_calls"][0]["output"] = "altered"
    with pytest.raises(ValueError, match="output hash"):
        report.retrieval_gate(tmp_path, [attempt], True)


def test_truncated_evidence_is_explicit_and_verified(tmp_path):
    attempt = evidence_attempt(tmp_path, "backendpro", {"results": [{"text": "x" * 8000}]})
    gate = report.retrieval_gate(tmp_path, [attempt], True)
    assert gate["events"][0]["truncated"] is True


def test_startup_model_probe_is_separately_reconciled(synthetic_run):
    (synthetic_run / "preflight-model-response.json").write_text(json.dumps({
        "model": "claude-opus-5-5", "usage": {"input_tokens": 100, "output_tokens": 20},
    }))
    with sqlite3.connect(synthetic_run / "ledger.db") as connection:
        connection.execute("INSERT INTO charges VALUES('anthropic',800,800)")
    result = report.build_report(synthetic_run)
    assert result["startup_model_cost_usd"] == pytest.approx(0.0008)


def test_trace_cannot_invent_model_tool_calls(synthetic_run):
    path = synthetic_run / "generation.json"
    generation = json.loads(path.read_text())
    generation["attempts"][0]["tool_calls"] = [
        {"name": "backendpro", "input": {}, "is_error": True, "tool_use_id": "invented"},
    ]
    path.write_text(json.dumps(generation))
    with pytest.raises(ValueError, match="model evidence"):
        report.build_report(synthetic_run)
