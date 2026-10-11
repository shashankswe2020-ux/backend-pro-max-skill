"""Synthetic-provider tests; never spend or present fixtures as measured evidence."""
from __future__ import annotations

import importlib
import json
from decimal import Decimal
from pathlib import Path

import pytest


@pytest.fixture
def live(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("run_m3_live")


@pytest.fixture
def frozen(live, tmp_path, monkeypatch):
    def docker(*args, **kwargs):
        if args[:2] == ("image", "inspect"):
            return json.dumps([{"Id": "sha256:synthetic", "Os": "linux", "Architecture": "arm64"}])
        if args[0] == "run":
            return json.dumps({"python": "3.12.13", "packages": {
                "pydantic": "2.14.0", "starlette": "1.7.0", "httpx": "0.28.1",
            }})
        raise AssertionError(args)

    monkeypatch.setattr(live.m3, "docker", docker)
    root = tmp_path / "frozen"
    live.m3.freeze(root, "synthetic", live.MODEL, repetitions=1)
    return root


def test_single_repetition_is_explicit_and_balanced(live, frozen):
    schedule = json.loads((frozen / "assignments.json").read_bytes())
    assert len(schedule) == len({row["id"] for row in schedule}) == 96
    assert all(row["repeat"] == 1 for row in schedule)
    assert json.loads((frozen / "required.protocol.json").read_bytes())["repetitions"] == 1
    for arm in live.m3.ARMS:
        assert sum(row["arm"] == arm for row in schedule) == 24
    with pytest.raises(ValueError, match="Repetitions"):
        live.m3.protocol("required", [], repetitions=True)
    with pytest.raises(ValueError, match="Repetitions"):
        live.m3.protocol("required", [], repetitions=2)


def test_tools_preserve_canonical_search_schemas_and_equal_submission(live):
    arms = {arm: live.tools_for(arm) for arm in live.m3.ARMS}
    assert all(tools[0] == arms["baseline"][0] for tools in arms.values())
    assert len(arms["baseline"]) == 1
    for arm in ("backendpro", "both"):
        for entry in arms[arm]:
            if entry["name"] in live.SEARCH_TOOLS:
                assert entry["input_schema"] == live.m3.CONTRACTS[entry["name"]]["parameters"]
    assert {entry["name"] for entry in arms["both"]} == {"finish", "context7", *live.SEARCH_TOOLS}
    requests = [live.payload([{"role": "user", "content": "identical"}], arm) for arm in live.m3.ARMS]
    assert all({k: v for k, v in row.items() if k != "tools"} == {
        k: v for k, v in requests[0].items() if k != "tools"
    } for row in requests)


def test_initial_prompt_contains_no_hidden_solution_or_rubric(live, frozen):
    messages = live.initial_messages(frozen, "backend-01")
    text = messages[0]["content"]
    assert "staged = accounts" in text
    assert "staged = accounts.copy()" not in text
    for forbidden in ("assertRaises", "source_urls", "grading/", "backend-01"):
        assert forbidden not in text


def test_context7_mapping_preserves_both_snippet_types_and_sources(live):
    value = {
        "codeSnippets": [{"codeId": "https://docs.test/code", "codeList": [{"code": "sample"}]}],
        "infoSnippets": [{"pageId": "https://docs.test/page", "content": "guidance"}],
        "libraries": ["example"],
    }
    normalized = live.normalize_context7(value)
    assert len(normalized["results"]) == 2
    assert normalized["results"][0]["codeList"] == value["codeSnippets"][0]["codeList"]
    assert normalized["metadata"] == {"libraries": ["example"]}
    assert live.describe_payload(normalized)["citations"] == ["https://docs.test/code", "https://docs.test/page"]
    assert live.describe_payload(live.normalize_context7({"codeSnippets": [], "infoSnippets": []}))["status"] == "empty"


@pytest.mark.parametrize("value", [
    {}, {"query": "echo"}, {"codeSnippets": "wrong"}, {"codeSnippets": [None]},
    {"infoSnippets": [{"content": "missing URL"}]},
])
def test_unknown_context7_shapes_fail_explicitly(live, value):
    with pytest.raises(ValueError):
        live.normalize_context7(value)


@pytest.fixture
def client(live, tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    value = live.LiveClient(output, {"ANTHROPIC_API_KEY": "synthetic", "CONTEXT7_API_KEY": "synthetic"})
    yield value
    value.ledger.connection.close()


def test_context7_404_is_empty_but_budgeted(live, client, monkeypatch):
    def missing(*args, **kwargs):
        raise live.ProviderError("no_documentation_found", 404)
    monkeypatch.setattr(live, "request_json", missing)
    value = client.context("example", "query")
    assert value["results"] == []
    assert client.ledger.summary()["accounted_upper_bound_micro_usd"] == 5000
    assert not client.blocked


def test_context7_provider_failure_retains_reservation_and_blocks(live, client, monkeypatch):
    def failed(*args, **kwargs):
        raise live.ProviderError("synthetic rate limit", 429)
    monkeypatch.setattr(live, "request_json", failed)
    with pytest.raises(live.ProviderError):
        client.context("example", "query")
    assert client.blocked
    assert client.ledger.summary()["unsettled_requests"] == 1
    with pytest.raises(live.ProviderError, match="blocked"):
        client.context("example", "query")
    assert client.ledger.summary()["requests"] == 1


def test_context7_request_uses_query_and_language_not_hidden_hints(live, client, monkeypatch):
    captured = []
    def request(url, headers):
        captured.append(url)
        return {"codeSnippets": [], "infoSnippets": []}
    monkeypatch.setattr(live, "request_json", request)
    client.context("example", "Pydantic strict model")
    assert "query=Pydantic+strict+model" in captured[0]
    assert "language=Python" in captured[0]
    assert "library=" not in captured[0]
    assert (client.output / "context7-1.json").exists()


def test_context7_budget_denial_makes_no_request(live, client, monkeypatch):
    client.ledger.per_attempt = 4999
    monkeypatch.setattr(live, "request_json", lambda *args: pytest.fail("Must not call provider"))
    with pytest.raises(live.BudgetExceeded):
        client.context("example", "query")
    assert client.context_budget_hit
    assert client.ledger.summary()["requests"] == 0


def tool_response(name, arguments, identifier):
    return {
        "id": f"response-{identifier}", "model": "claude-opus-5-5",
        "usage": {"input_tokens": 10, "output_tokens": 10},
        "content": [{"type": "tool_use", "id": f"call-{identifier}", "name": name, "input": arguments}],
    }


def fake_model(monkeypatch, client, responses):
    pending = iter(responses)
    def message(attempt, payload):
        return next(pending)
    monkeypatch.setattr(client, "message", message)


def fake_grade(live, monkeypatch):
    monkeypatch.setattr(live.m3, "grade", lambda *args: {"status": "passed", "passed": True})


def test_baseline_submits_once_without_retrieval(live, frozen, client, monkeypatch):
    fake_model(monkeypatch, client, [tool_response("finish", {"source": "pass\n"}, 1)])
    fake_grade(live, monkeypatch)
    result = live.attempt(client, frozen, client.output, {"id": "a", "arm": "baseline", "task_id": "backend-01"})
    assert result["status"] == "completed"
    assert result["input_tokens"] == result["output_tokens"] == 10
    assert result["candidate_sha256"] == live.m3.sha(b"pass\n")
    assert [row["name"] for row in result["trace"]] == ["finish"]
    assert json.loads((client.output / "a/attempt.json").read_bytes()) == result


def test_required_retrieval_must_be_delivered_before_finish(live, frozen, client, monkeypatch):
    bundled = tool_response("context7", {"query": "Pydantic"}, 1)
    bundled["content"].append(tool_response("finish", {"source": "premature\n"}, 2)["content"][0])
    fake_model(monkeypatch, client, [bundled, tool_response("finish", {"source": "pass\n"}, 3)])
    monkeypatch.setattr(client, "context", lambda *_: {"results": []})
    fake_grade(live, monkeypatch)
    result = live.attempt(client, frozen, client.output, {"id": "b", "arm": "context7", "task_id": "backend-01"})
    assert result["status"] == "completed"
    assert [row["status"] for row in result["trace"]] == ["attempted", "rejected", "allowed"]
    assert result["trace"][0]["delivered_to_model"]
    assert result["trace"][0]["consuming_model_call_id"] == "response-3"
    assert (client.output / "b/solution.py").read_text() == "pass\n"


def test_both_sources_receive_real_transport_labels(live, frozen, client, monkeypatch):
    fake_model(monkeypatch, client, [
        tool_response("context7", {"query": "Pydantic"}, 1),
        tool_response("search", {"query": "transaction"}, 2),
        tool_response("finish", {"source": "pass\n"}, 3),
    ])
    monkeypatch.setattr(client, "context", lambda *_: {"results": []})
    monkeypatch.setattr(live.m3, "backendpro_mcp", lambda *_: {"results": [{"_citation": "[BPM:test]"}]})
    fake_grade(live, monkeypatch)
    result = live.attempt(client, frozen, client.output, {"id": "c", "arm": "both", "task_id": "backend-01"})
    assert result["status"] == "completed"
    assert [row["event"]["transport"] for row in result["trace"][:2]] == ["context7_search_api", "mcp_stdio"]
    assert all(row["delivered_to_model"] for row in result["trace"][:2])


def test_model_budget_failure_is_persisted_without_inventing_a_candidate(live, frozen, client, monkeypatch):
    def denied(*args):
        raise live.BudgetExceeded("synthetic ceiling")
    monkeypatch.setattr(client, "message", denied)
    result = live.attempt(client, frozen, client.output, {"id": "d", "arm": "baseline", "task_id": "backend-01"})
    assert result["status"] == "budget_limit"
    assert "candidate_file" not in result
    assert not client.blocked


def test_context7_budget_failure_is_not_swallowed_by_workflow(live, frozen, client, monkeypatch):
    fake_model(monkeypatch, client, [tool_response("context7", {"query": "docs"}, 1)])
    client.ledger.per_attempt = 1
    result = live.attempt(client, frozen, client.output, {"id": "e", "arm": "context7", "task_id": "backend-01"})
    assert result["status"] == "budget_limit"
    assert result["trace"][0]["event"]["evidence"]["status"] == "error"
    assert not result["trace"][0]["delivered_to_model"]


def test_grading_failure_stops_and_keeps_candidate(live, frozen, client, monkeypatch):
    fake_model(monkeypatch, client, [tool_response("finish", {"source": "pass\n"}, 1)])
    def failed(*args):
        raise RuntimeError("synthetic Docker failure")
    monkeypatch.setattr(live.m3, "grade", failed)
    result = live.attempt(client, frozen, client.output, {"id": "f", "arm": "baseline", "task_id": "backend-01"})
    assert result["status"] == "client_error"
    assert client.blocked
    assert (client.output / result["candidate_file"]).exists()


@pytest.mark.parametrize(("approved_hash", "budget", "accept"), [
    ("wrong", "35", True), ("expected", "25", True), ("expected", "35", False),
    ("expected", "NaN", True), ("expected", "Infinity", True),
])
def test_spending_requires_all_matching_approvals(live, tmp_path, monkeypatch, approved_hash, budget, accept):
    monkeypatch.setattr(live, "check_prepared", lambda _: ({}, {"protocol_sha256": "expected"}))
    monkeypatch.setattr(live, "credentials", lambda _: pytest.fail("Do not read keys before approval"))
    with pytest.raises(ValueError, match="Explicit matching"):
        live.run(tmp_path, tmp_path / "keys", approved_hash, Decimal(budget), accept)


def test_late_response_is_charged_but_not_submitted(live, frozen, client, monkeypatch):
    fake_model(monkeypatch, client, [tool_response("finish", {"source": "pass\n"}, 1)])
    ticks = iter([0, 0, 601, 601])
    monkeypatch.setattr(live.time, "monotonic", lambda: next(ticks))
    result = live.attempt(client, frozen, client.output, {"id": "g", "arm": "baseline", "task_id": "backend-01"})
    assert result["status"] == "time_limit"
    assert result["reason"] == "late_model_response"
    assert result["input_tokens"] == 10
    assert "candidate_file" not in result


@pytest.fixture
def prepared(live, frozen, tmp_path, monkeypatch):
    def self_test(root, output):
        output.mkdir()
        result = {
            "status": "passed", "reference_passed": 24, "starter_failed": 24,
            "suite_sha256": live.m3.sha((root / "manifest.json").read_bytes()), "artifacts": {},
        }
        live.m3.write_new(output / "summary.json", result)
        return result
    monkeypatch.setattr(live.m3, "self_test", self_test)
    monkeypatch.setattr(live.m3, "backendpro_mcp", lambda *_: {
        "results": [{"title": "Kubernetes Pod termination"}],
    })
    root = tmp_path / "prepared"
    live.prepare(root, "synthetic")
    return root


def test_preparation_freezes_post_m4_sources_and_requires_new_approval(live, prepared):
    manifest, summary = live.check_prepared(prepared)
    assert summary["paid_calls"] == 0
    assert "scripts/run_m3_live.py" in manifest["source_sha256"]
    assert "scripts/run_swebench_comparison.py" in manifest["source_sha256"]
    protocol = json.loads((prepared / "frozen/required.protocol.json").read_bytes())
    assert protocol["pricing_and_budget"]["total_micro_usd"] == 35_000_000
    assert protocol["repetitions"] == 1
    assert protocol["model_settings"]["system"] == live.SYSTEM
    with pytest.raises(ValueError, match="already exists"):
        live.prepare(prepared, "synthetic")
    (prepared / "frozen/agent/backend-01/solution.py").write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        live.check_prepared(prepared)


def test_protocol_drift_blocks_before_spending(live, prepared, monkeypatch):
    monkeypatch.setattr(live, "SYSTEM", "changed prompt")
    with pytest.raises(ValueError, match="does not match"):
        live.check_prepared(prepared)


def test_preflight_failure_retains_all_96_assigned_denominators(live, prepared, monkeypatch):
    monkeypatch.setattr(live, "credentials", lambda _: {"ANTHROPIC_API_KEY": "fake", "CONTEXT7_API_KEY": "fake"})
    def failed(self):
        raise live.ProviderError("synthetic preflight failure")
    monkeypatch.setattr(live.LiveClient, "preflight", failed)
    protocol_hash = json.loads((prepared / "preparation.json").read_bytes())["protocol_sha256"]
    with pytest.raises(live.ProviderError):
        live.run(prepared, Path("unused"), protocol_hash, Decimal(35), True)
    observations = json.loads((prepared / "run/observations.json").read_bytes())
    assert len(observations["attempts"]) == 96
    assert all(row["status"] == "not_started" for row in observations["attempts"])
    assert "synthetic preflight failure" in (prepared / "run/run-error.json").read_text()
    report = live.compile_report(prepared)
    assert report["status"] == "incomplete"
    assert report["assigned"] == 96
    assert report["spending"]["requests"] == 0
    assert report["overall"]["context7"]["assigned"] == 24
    assert report["overall"]["context7"]["resolved"] == 0
    assert "No superiority claim" in live.markdown_report(report)


def test_utf8_byte_limit_rejects_oversized_candidate(live, frozen, client, monkeypatch):
    fake_model(monkeypatch, client, [
        tool_response("finish", {"source": "\u6570" * 22000}, 1),
        tool_response("finish", {"source": "pass\n"}, 2),
    ])
    fake_grade(live, monkeypatch)
    result = live.attempt(client, frozen, client.output, {"id": "h", "arm": "baseline", "task_id": "backend-01"})
    assert result["status"] == "completed"
    assert result["trace"][0]["status"] == "rejected"
    assert "UTF-8 bytes" in result["trace"][0]["error"]


def test_turn_limit_never_submits_starter_as_success(live, frozen, client, monkeypatch):
    fake_model(monkeypatch, client, [{
        "id": f"response-{i}", "usage": {"input_tokens": 10, "output_tokens": 10},
        "content": [{"type": "text", "text": "not a submission"}],
    } for i in range(16)])
    result = live.attempt(client, frozen, client.output, {"id": "i", "arm": "baseline", "task_id": "backend-01"})
    assert result["status"] == "time_limit"
    assert result["reason"] == "model_turn_limit"
    assert result["model_turns"] == 16
    assert "candidate_file" not in result
