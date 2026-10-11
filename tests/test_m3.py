"""Offline M3 tests. Synthetic observations are never real model evidence."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def m3(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return importlib.import_module("run_m3")


@pytest.fixture
def frozen(m3, tmp_path, monkeypatch):
    def docker(*args, **kwargs):
        if args[:2] == ("image", "inspect"):
            return json.dumps([{"Id": "sha256:synthetic-image", "Os": "linux", "Architecture": "arm64"}])
        if args[0] == "run":
            return json.dumps({
                "python": "3.12.13",
                "packages": {"pydantic": "2.14.0", "starlette": "1.7.0", "httpx": "0.28.1"},
            })
        raise AssertionError(f"Unexpected Docker operation: {args}")

    monkeypatch.setattr(m3, "docker", docker)
    root = tmp_path / "frozen"
    m3.freeze(root, "synthetic")
    return root


def test_balanced_freeze_keeps_gold_out_of_agent_inputs(m3, frozen):
    manifest = m3.load_frozen(frozen)
    assert len(manifest["tasks"]) == 24
    assert not manifest["paid_generation_authorized"]
    for task in manifest["tasks"]:
        public = frozen / "agent" / task["id"]
        private = frozen / "grading" / task["id"]
        assert {path.name for path in public.iterdir()} == {"task.json", "solution.py"}
        assert "source_urls" not in json.loads((public / "task.json").read_text())
        assert (public / "solution.py").read_bytes() != (private / "reference.py").read_bytes()
        compile((public / "solution.py").read_text(), "starter", "exec")
        compile((private / "reference.py").read_text(), "reference", "exec")
        compile((private / "check.py").read_text(), "checks", "exec")
    assert set(manifest["files"]) >= {"optional.protocol.json", "required.protocol.json", "tools.json"}
    optional = json.loads((frozen / "optional.protocol.json").read_text())
    required = json.loads((frozen / "required.protocol.json").read_text())
    assert optional["task_ids"] == required["task_ids"]
    assert optional["limits"] == required["limits"]
    assert optional["id"] != required["id"]


def test_schedule_is_reproducible_balanced_and_not_best_of_n(m3, frozen):
    tasks = m3.load_frozen(frozen)["tasks"]
    schedule = m3.assignments(tasks)
    assert schedule == m3.assignments(tasks)
    assert len(schedule) == len({row["id"] for row in schedule}) == 288
    for track in m3.TRACKS:
        for arm in m3.ARMS:
            assert sum(row["track"] == track and row["arm"] == arm for row in schedule) == 18
    for repeat in (1, 2, 3):
        rows = [row for row in schedule if row["repeat"] == repeat]
        assert len(rows) == 96
        assert set(row["arm"] for row in rows[:4]) == set(m3.ARMS)


def test_freeze_refuses_overwrite_and_detects_tampering(m3, frozen):
    with pytest.raises(ValueError, match="already exists"):
        m3.freeze(frozen, "unused")
    (frozen / "agent/backend-01/solution.py").write_text("modified")
    with pytest.raises(ValueError, match="changed"):
        m3.load_frozen(frozen)


@pytest.mark.parametrize("policy", ["optional", "required"])
def test_baseline_has_no_knowledge_tools(m3, policy):
    workflow = m3.RetrievalWorkflow(policy, "baseline")
    called = []
    with pytest.raises(ValueError, match="unavailable"):
        workflow.retrieve("backendpro_search", {"query": "Kafka"}, lambda *_: called.append(1), "offline_fixture")
    workflow.guard("shell")
    workflow.guard("finish")
    assert called == []


def test_required_both_reserves_budget_for_other_source(m3):
    workflow = m3.RetrievalWorkflow("required", "both")
    with pytest.raises(ValueError, match="missing sources"):
        workflow.guard("shell")
    for _ in range(2):
        workflow.retrieve("backendpro_search", {"query": "retry"}, lambda *_: {"results": []}, "offline_fixture")
    with pytest.raises(ValueError, match="reserved"):
        workflow.retrieve("backendpro_search", {"query": "retry"}, lambda *_: {}, "offline_fixture")
    workflow.retrieve("context7", {"query": "Starlette routing"}, lambda *_: {"results": []}, "offline_fixture")
    workflow.guard("shell")
    with pytest.raises(ValueError, match="three-call"):
        workflow.retrieve("context7", {"query": "again"}, lambda *_: {}, "offline_fixture")
    workflow.guard("finish")
    with pytest.raises(ValueError, match="after finish"):
        workflow.guard("shell")
    assert workflow.calls == 3


def test_failure_and_empty_results_are_retained_not_retried(m3):
    workflow = m3.RetrievalWorkflow("required", "context7")
    called = []

    def failure(*args):
        called.append(1)
        raise TimeoutError("synthetic timeout")

    event = workflow.retrieve("context7", {"query": "docs"}, failure, "offline_fixture")
    assert event["evidence"]["status"] == "error"
    assert event["payload"]["error"] == "synthetic timeout"
    assert len(called) == workflow.calls == 1
    workflow.guard("finish")


def test_bounded_response_remains_parseable_and_hash_bound(m3):
    value = {"results": [{"content": '"\n\u6570' * 12000}]}
    workflow = m3.RetrievalWorkflow("optional", "backendpro")
    event = workflow.retrieve("backendpro_search", {"query": "Kafka"}, lambda *_: value, "offline_fixture")
    assert len(event["output"]) <= 6000
    assert json.loads(event["output"])["truncated"]
    assert event["payload"] == value
    assert event["output_sha256"] == m3.sha(event["output"].encode())
    assert event["relevance"] == event["application"] == "not_reviewed"


def test_schema_and_transport_checks_precede_execution(m3):
    workflow = m3.RetrievalWorkflow("required", "backendpro")
    called = []
    with pytest.raises(ValueError, match="Invalid tool arguments"):
        workflow.retrieve("backendpro_search", {"query": "x", "domain": "wrong"}, lambda *_: called.append(1), "mcp_stdio")
    with pytest.raises(ValueError, match="Transport"):
        workflow.retrieve("backendpro_search", {"query": "x"}, lambda *_: called.append(1), "context7_search_api")
    assert workflow.calls == 0
    assert called == []


def test_replay_retains_rejections_without_executing_shell(m3):
    result = m3.replay("required", "both", [
        {"name": "shell"},
        {"name": "backendpro_search", "arguments": {"query": "retry"}, "fixture": {"results": []}},
        {"name": "finish"},
        {"name": "context7", "arguments": {"query": "docs"}, "fixture": {"error": "unavailable"}},
        {"name": "shell"},
        {"name": "finish"},
    ])
    assert [action["status"] for action in result["trace"]] == [
        "rejected", "attempted", "rejected", "attempted", "allowed", "allowed",
    ]
    assert result["finished"]
    assert all(not action["executed"] for action in result["trace"] if "executed" in action)


def test_real_backendpro_replay_never_uses_context7_network(m3, monkeypatch):
    calls = []

    def local(name, arguments):
        calls.append(name)
        return {"results": [{"_citation": "[BPM:example]"}]}

    monkeypatch.setattr(m3, "backendpro_mcp", local)
    result = m3.replay("required", "both", [
        {"name": "backendpro_search", "arguments": {"query": "retry"}},
        {"name": "context7", "arguments": {"query": "docs"}, "fixture": {"results": []}},
        {"name": "finish"},
    ], real_backendpro=True)
    assert result["finished"]
    assert calls == ["backendpro_search"]
    assert result["trace"][0]["event"]["transport"] == "mcp_stdio"
    assert result["trace"][1]["event"]["transport"] == "offline_fixture"


def test_clustered_statistics_use_tasks_not_repetitions(m3):
    left = {"a": 1, "b": 2 / 3, "c": 0}
    right = {"a": 0, "b": 1 / 3, "c": 1}
    first = m3.clustered_pair(left, right, "test")
    assert first == m3.clustered_pair(left, right, "test")
    assert first["task_clusters"] == 3
    assert first["difference_percentage_points"] == pytest.approx(100 / 9)
    with pytest.raises(ValueError):
        m3.clustered_pair({"a": 1}, {"b": 1}, "test")
    pairs = {str(i): {"sign_flip_p_unadjusted": p} for i, p in enumerate((.01, .02, .5))}
    m3.holm(pairs)
    assert [pairs[str(i)]["holm_p"] for i in range(3)] == pytest.approx([.03, .04, .5])


def observations(m3, frozen, tmp_path, rows, policy="optional"):
    path = tmp_path / "observations.json"
    path.write_bytes(m3.encode({
        "protocol_sha256": m3.sha((frozen / f"{policy}.protocol.json").read_bytes()), "attempts": rows,
    }))
    return path


def record(identifier):
    return {
        "id": identifier, "status": "not_started", "cost_micro_usd": 0, "input_tokens": 0,
        "output_tokens": 0, "generation_seconds": 0, "trace": [],
    }


def test_incomplete_report_retains_every_assignment(m3, frozen, tmp_path):
    path = observations(m3, frozen, tmp_path, [record("backend-01.baseline.r1")])
    result = m3.report(frozen, path, "optional")
    assert result["assigned"] == 288 and result["observed"] == 1
    assert len(result["missing"]) == 287
    assert result["status"] == "incomplete"
    assert result["paired_task_cluster_comparisons"] == {}
    assert result["tracks"]["backend"]["baseline"]["assigned"] == 18
    assert not result["superiority_claim_supported"]


def test_duplicate_and_mixed_policy_inputs_are_rejected(m3, frozen, tmp_path):
    row = record("backend-01.baseline.r1")
    path = observations(m3, frozen, tmp_path, [row, row])
    with pytest.raises(ValueError, match="Duplicate"):
        m3.report(frozen, path, "optional")
    with pytest.raises(ValueError, match="protocol"):
        m3.report(frozen, path, "required")


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, None])
def test_invalid_costs_do_not_become_zero_cost_success(m3, frozen, tmp_path, value):
    row = {**record("backend-01.baseline.r1"), "cost_micro_usd": value}
    path = observations(m3, frozen, tmp_path, [row])
    with pytest.raises(ValueError, match="measurement"):
        m3.report(frozen, path, "optional")


def test_offline_fixture_cannot_be_mislabeled_a_model_result(m3, frozen, tmp_path):
    flow = m3.RetrievalWorkflow("optional", "backendpro")
    event = flow.retrieve("backendpro_search", {"query": "retry"}, lambda *_: {"results": []}, "offline_fixture")
    row = {**record("backend-01.backendpro.r1"), "trace": [{"name": "backendpro_search", "event": event}]}
    path = observations(m3, frozen, tmp_path, [row])
    with pytest.raises(ValueError, match="Offline fixtures"):
        m3.report(frozen, path, "optional")


def test_grade_artifact_must_match_task_environment_and_candidate(m3, frozen, tmp_path):
    manifest = m3.load_frozen(frozen)
    evidence = {
        "task_id": "backend-01", "status": "passed",
        "suite_sha256": m3.sha((frozen / "manifest.json").read_bytes()), "image_id": manifest["image_id"],
        "candidate_sha256": "candidate", "grader_sha256": manifest["files"]["grading/backend-01/check.py"],
    }
    grade_path = tmp_path / "grade.json"
    grade_path.write_bytes(m3.encode(evidence))
    row = {
        **record("backend-01.baseline.r1"), "status": "completed",
        "grade_file": "grade.json", "grade_sha256": m3.sha(grade_path.read_bytes()),
        "candidate_sha256": "different-candidate",
    }
    path = observations(m3, frozen, tmp_path, [row])
    with pytest.raises(ValueError, match="Grade does not match"):
        m3.report(frozen, path, "optional")


def test_complete_report_clusters_repetitions_and_counts_regressions(m3, frozen, tmp_path, monkeypatch):
    manifest = m3.load_frozen(frozen)
    rows = []
    for assignment in m3.assignments(manifest["tasks"]):
        passed = assignment["arm"] == "baseline" or assignment["repeat"] == 1
        filename = assignment["id"] + ".grade.json"
        evidence = {
            "task_id": assignment["task_id"], "status": "passed" if passed else "failed", "passed": passed,
            "suite_sha256": m3.sha((frozen / "manifest.json").read_bytes()), "image_id": manifest["image_id"],
            "candidate_sha256": "synthetic", "exit_code": 0 if passed else 1,
            "grader_sha256": manifest["files"][f"grading/{assignment['task_id']}/check.py"],
            "test_report": {"ran": 1, "passed": passed, "failures": 0 if passed else 1, "errors": 0},
        }
        grade_path = tmp_path / filename
        grade_path.write_bytes(m3.encode(evidence))
        rows.append({
            **record(assignment["id"]), "status": "completed", "candidate_sha256": "synthetic",
            "grade_file": filename, "grade_sha256": m3.sha(grade_path.read_bytes()),
        })
    calls = []

    def cluster(left, right, seed):
        calls.append((left, right))
        assert len(left) == len(right) == 24
        assert all(value in (1, 1 / 3) for value in [*left.values(), *right.values()])
        return {"task_clusters": 24, "sign_flip_p_unadjusted": .5}

    monkeypatch.setattr(m3, "clustered_pair", cluster)
    path = observations(m3, frozen, tmp_path, rows)
    result = m3.report(frozen, path, "optional")
    assert result["status"] == "complete_unreviewed"
    assert result["observed"] == 288 and result["missing"] == []
    assert len(calls) == len(result["paired_task_cluster_comparisons"]) == 6
    assert result["tracks"]["control"]["backendpro"]["regressions_vs_baseline_observed"] == 12
    assert not result["superiority_claim_supported"]
