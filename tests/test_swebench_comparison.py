"""Offline checks for isolation policy, arm parity and pre-request spending limits."""
from __future__ import annotations

import importlib.util
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_swebench_comparison.py"
SPEC = importlib.util.spec_from_file_location("run_swebench_comparison", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
comparison = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(comparison)


def test_arms_differ_only_in_knowledge_tools():
    arms = {arm: comparison.tools_for(arm) for arm in ("baseline", "context7", "backendpro", "both")}
    assert all(value[:2] == arms["baseline"] for value in arms.values())
    assert {tool["name"] for tool in arms["both"]} == {"shell", "finish", "context7", "backendpro"}
    for arm in ("context7", "backendpro"):
        assert arms[arm][-1] in arms["both"]


def test_unknown_arm_is_rejected():
    with pytest.raises(ValueError, match="Unknown arm"):
        comparison.tools_for("unknown")


def test_reservation_includes_output_and_utf8_input():
    payload = {"max_tokens": 1024, "messages": [{"role": "user", "content": "test"}]}
    assert comparison.message_reservation(payload) == (len(json.dumps(payload).encode()) + 8192) * 4 + 1024 * 20


def test_exact_budget_threshold(tmp_path):
    ledger = comparison.Ledger(tmp_path / "ledger.db", total=100, per_attempt=100)
    ledger.reserve("a", "anthropic", 100)
    with pytest.raises(comparison.BudgetExceeded):
        ledger.reserve("a", "anthropic", 1)


def test_per_attempt_budget_cannot_borrow(tmp_path):
    ledger = comparison.Ledger(tmp_path / "ledger.db", total=100, per_attempt=40)
    ledger.reserve("a", "anthropic", 40)
    ledger.reserve("b", "anthropic", 40)
    with pytest.raises(comparison.BudgetExceeded):
        ledger.reserve("a", "anthropic", 1)


def test_settlement_releases_only_unused_reservation(tmp_path):
    ledger = comparison.Ledger(tmp_path / "ledger.db", total=100, per_attempt=100)
    request = ledger.reserve("a", "anthropic", 100)
    ledger.settle(request, 30)
    ledger.reserve("b", "anthropic", 70)
    assert ledger.summary()["accounted_upper_bound_micro_usd"] == 100
    assert ledger.summary()["unsettled_requests"] == 1
    assert ledger.summary()["anthropic_measured_micro_usd"] == 30


def test_unsettled_requests_survive_restart(tmp_path):
    path = tmp_path / "ledger.db"
    original = comparison.Ledger(path, total=100, per_attempt=100)
    original.reserve("a", "anthropic", 100)
    restarted = comparison.Ledger(path, total=100, per_attempt=100)
    with pytest.raises(comparison.BudgetExceeded):
        restarted.reserve("b", "anthropic", 1)


def test_concurrent_requests_cannot_overspend(tmp_path):
    ledger = comparison.Ledger(tmp_path / "ledger.db", total=100, per_attempt=100)
    barrier = threading.Barrier(2)

    def reserve(name):
        barrier.wait()
        try:
            ledger.reserve(name, "anthropic", 60)
        except comparison.BudgetExceeded:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, ("a", "b")))
    assert sum(outcomes) == 1
    assert ledger.summary()["accounted_upper_bound_micro_usd"] == 60


@pytest.mark.parametrize("amount", [-1, 0])
def test_invalid_reservation(tmp_path, amount):
    ledger = comparison.Ledger(tmp_path / "ledger.db")
    with pytest.raises(ValueError):
        ledger.reserve("a", "anthropic", amount)


def test_overage_or_double_settlement_stops(tmp_path):
    ledger = comparison.Ledger(tmp_path / "ledger.db")
    request = ledger.reserve("a", "anthropic", 10)
    with pytest.raises(RuntimeError):
        ledger.settle(request, 11)
    ledger.settle(request, 10)
    with pytest.raises(RuntimeError):
        ledger.settle(request, 10)


def test_credentials_require_owner_only_regular_file(tmp_path):
    path = tmp_path / "keys.json"
    path.write_text(json.dumps({"ANTHROPIC_API_KEY": "fake-test-key", "CONTEXT7_API_KEY": "fake-test-key"}))
    path.chmod(0o644)
    with pytest.raises(ValueError, match="owner-only"):
        comparison.credentials(path)
    path.chmod(0o600)
    assert len(comparison.credentials(path)) == 2
    link = tmp_path / "link.json"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="regular"):
        comparison.credentials(link)


@pytest.mark.parametrize("command", [
    "", "eval \"$x\"", "echo ${!x}", "echo ${x@P}", "pkill python", "sudo sh",
    "rm -rf /testbed", "git reset --hard", "git checkout -- .",
])
def test_unsafe_commands_are_not_executed(command):
    with pytest.raises(ValueError):
        comparison.safe_command(command)


def test_normal_commands_are_accepted():
    comparison.safe_command("python -m pytest tests/test_example.py")


def test_context_no_match_is_not_a_provider_outage(tmp_path, monkeypatch):
    runner = comparison.Runner(tmp_path, {"CONTEXT7_API_KEY": "fake-test-key"}, {})

    def no_docs(*args, **kwargs):
        raise comparison.ProviderError("no docs", 404)

    monkeypatch.setattr(comparison, "request_json", no_docs)
    result = runner.context("attempt", "question", "django/django")
    assert result["status"] == 404
    assert result["error"]
    assert runner.ledger.summary()["context7_upper_bound_micro_usd"] == 5000
    assert not runner.stop.is_set()


def test_provider_error_retains_reservation(tmp_path, monkeypatch):
    runner = comparison.Runner(tmp_path, {"CONTEXT7_API_KEY": "fake-test-key"}, {})

    def outage(*args, **kwargs):
        raise comparison.ProviderError("unavailable", 503)

    monkeypatch.setattr(comparison, "request_json", outage)
    with pytest.raises(comparison.ProviderError):
        runner.context("attempt", "question", "django/django")
    assert runner.ledger.summary()["accounted_upper_bound_micro_usd"] == 5000
    assert runner.ledger.summary()["unsettled_requests"] == 1


def test_message_checks_budget_before_sending(tmp_path, monkeypatch):
    runner = comparison.Runner(tmp_path, {}, {})
    called = []
    monkeypatch.setattr(comparison, "request_json", lambda *args: called.append(args))
    with pytest.raises(comparison.BudgetExceeded):
        runner.message("attempt", {"max_tokens": 100000})
    assert called == []


def test_model_usage_is_reconciled(tmp_path, monkeypatch):
    runner = comparison.Runner(
        tmp_path, {"ANTHROPIC_API_KEY": "fake-test-key"}, {"model": "claude-opus-5-5"},
    )
    response = {"model": "claude-opus-5-5", "usage": {"input_tokens": 100, "output_tokens": 10}}
    monkeypatch.setattr(comparison, "request_json", lambda *args: response)
    assert runner.message("attempt", {"max_tokens": 1024}) == response
    assert runner.ledger.summary()["anthropic_measured_micro_usd"] == 600


def test_model_substitution_is_rejected(tmp_path, monkeypatch):
    runner = comparison.Runner(
        tmp_path, {"ANTHROPIC_API_KEY": "fake-test-key"}, {"model": "claude-opus-5-5"},
    )
    response = {"model": "wrong-model", "usage": {"input_tokens": 100, "output_tokens": 10}}
    monkeypatch.setattr(comparison, "request_json", lambda *args: response)
    with pytest.raises(comparison.ProviderError, match="different model"):
        runner.message("attempt", {"max_tokens": 1024})


def test_capability_probe_uses_generation_settings_and_accounts_cost(tmp_path, monkeypatch):
    runner = comparison.Runner(
        tmp_path, {"ANTHROPIC_API_KEY": "fake", "CONTEXT7_API_KEY": "fake"},
        {"model": "claude-opus-5-5"},
    )
    requests = []

    def provider(url, headers, payload=None):
        requests.append(payload)
        if payload is None:
            return {"results": [{"content": "Django model field reference"}]}
        return {
            "model": "claude-opus-5-5", "usage": {"input_tokens": 100, "output_tokens": 10},
            "content": [{"type": "tool_use", "name": "finish", "input": {}}],
        }

    monkeypatch.setattr(comparison, "request_json", provider)
    result = runner.provider_preflight()
    assert result["model_tool_call"] == "passed"
    assert requests[0] == comparison.model_payload(
        runner.config["model"], requests[0]["messages"], "both",
    )
    assert runner.ledger.summary()["accounted_upper_bound_micro_usd"] == 5600
    assert (tmp_path / "preflight-model-response.json").exists()
    assert (tmp_path / "preflight-context7-response.json").exists()


@pytest.mark.parametrize("value", [
    {"results": []}, {"error": "no docs"}, {"results": [{"text": "unrelated"}]},
    {"unknown": "Django"},
    {"query": "Django", "results": [{"text": "unrelated"}]},
])
def test_readiness_rejects_success_shaped_context_results(tmp_path, monkeypatch, value):
    runner = comparison.Runner(tmp_path, {}, {"model": "claude-opus-5-5"})
    monkeypatch.setattr(runner, "message", lambda *args: {
        "content": [{"type": "tool_use", "name": "finish", "input": {}}],
    })
    monkeypatch.setattr(runner, "context", lambda *args: value)
    with pytest.raises(comparison.ProviderError, match="recognizable Django"):
        runner.provider_preflight()


def test_preflight_blocks_unsettled_ledger_before_request(tmp_path, monkeypatch):
    runner = comparison.Runner(tmp_path, {}, {})
    runner.ledger.reserve("previous", "anthropic", 1)
    called = []
    monkeypatch.setattr(comparison, "request_json", lambda *args: called.append(args))
    with pytest.raises(ValueError, match="Unsettled"):
        runner.provider_preflight()
    assert called == []


def test_preflight_rejects_model_without_tool_call(tmp_path, monkeypatch):
    runner = comparison.Runner(tmp_path, {}, {"model": "claude-opus-5-5"})
    monkeypatch.setattr(runner, "message", lambda *args: {"content": [{"type": "text", "text": "done"}]})
    with pytest.raises(comparison.ProviderError, match="native tool call"):
        runner.provider_preflight()


def test_product_readiness_failure_blocks_paid_generation(tmp_path, monkeypatch):
    def failure():
        raise ValueError("MCP schema mismatch")

    monkeypatch.setattr(comparison, "check_stdio", failure)
    called = []
    monkeypatch.setattr(comparison, "request_json", lambda *args: called.append(args))
    output = tmp_path / "new-run"
    with pytest.raises(ValueError, match="MCP schema"):
        comparison.generate(output, {}, {})
    assert called == []
    assert json.loads((output / "state.json").read_text())["status"] == "preflight_blocked"


@pytest.fixture
def fake_docker(monkeypatch):
    class DockerFailure(Exception):
        pass

    class Container:
        id = "synthetic-container"
        attrs = {"Mounts": [], "Config": {"NetworkDisabled": True}}
        removed = False
        delta = b""

        def exec_run(self, command, **kwargs):
            if command[:2] == ["git", "diff"]:
                return SimpleNamespace(exit_code=0, output=self.delta)
            return SimpleNamespace(exit_code=0, output=b"")

        def remove(self, **kwargs):
            self.removed = True

    container = Container()
    client = SimpleNamespace(
        containers=SimpleNamespace(run=lambda *args, **kwargs: container, get=lambda *args: container),
        close=lambda: None,
    )
    monkeypatch.setitem(sys.modules, "docker", SimpleNamespace(
        from_env=lambda **kwargs: client, errors=SimpleNamespace(DockerException=DockerFailure),
    ))
    return container


def test_readonly_image_preflight_rejects_unreviewed_source_and_cleans_up(fake_docker):
    fake_docker.delta = b"unreviewed source change"
    with pytest.raises(ValueError, match="Unreviewed"):
        comparison.check_image_sources(
            [{"image_id": "image", "instance_id": "case", "base_commit": "base"}], {},
        )
    assert fake_docker.removed


@pytest.mark.parametrize("consume", [True, False])
def test_retrieval_trace_records_actual_consumption(tmp_path, monkeypatch, fake_docker, consume):
    runner = comparison.Runner(tmp_path, {}, {"model": "test-model"})
    retrieval = {"type": "tool_use", "id": "search-1", "name": "backendpro",
                 "input": {"query": "Kafka", "domain": "messaging"}}
    finish = {"type": "tool_use", "id": "finish-1", "name": "finish", "input": {}}
    responses = iter([
        {"content": [retrieval] if consume else [retrieval, finish]},
        {"content": [finish]},
    ])
    monkeypatch.setattr(runner, "message", lambda *args: next(responses))
    result = runner.attempt({
        "instance_id": "case", "arm": "backendpro", "repo": "synthetic/repo",
        "image_id": "image", "base_commit": "base", "index": 0, "problem_statement": "Synthetic test",
    })
    assert result["status"] == "finished"
    event = result["tool_calls"][0]
    assert event["delivered"] is consume
    assert event["evidence"]["status"] == "returned"
    assert event["seconds"] >= 0
    assert event["cost_upper_bound_micro_usd"] == 0
    assert event["tool_use_id"] == "search-1"
    assert fake_docker.removed


def test_provider_failure_is_retained_in_tool_trace(tmp_path, monkeypatch, fake_docker):
    runner = comparison.Runner(tmp_path, {}, {"model": "test-model"})
    monkeypatch.setattr(runner, "message", lambda *args: {
        "content": [{"type": "tool_use", "id": "search-1", "name": "context7", "input": {"query": "Django"}}],
    })

    def outage(*args):
        raise comparison.ProviderError("synthetic outage")

    monkeypatch.setattr(runner, "context", outage)
    result = runner.attempt({
        "instance_id": "case", "arm": "context7", "repo": "synthetic/repo",
        "image_id": "image", "base_commit": "base", "index": 0, "problem_statement": "Synthetic test",
    })
    assert result["status"] == "provider_error"
    assert result["tool_calls"][0]["failure_type"] == "ProviderError"
    assert result["tool_calls"][0]["is_error"]
    assert not result["tool_calls"][0]["delivered"]


def test_invalid_request_does_not_become_a_measured_model_charge(tmp_path, monkeypatch):
    runner = comparison.Runner(tmp_path, {"ANTHROPIC_API_KEY": "fake-test-key"}, {})

    def invalid(*args, **kwargs):
        raise comparison.ProviderError("unsupported parameter", 400)

    monkeypatch.setattr(comparison, "request_json", invalid)
    with pytest.raises(comparison.ProviderError):
        runner.message("attempt", {"max_tokens": 2048})
    assert runner.ledger.summary()["accounted_upper_bound_micro_usd"] == 0
    assert runner.ledger.summary()["unsettled_requests"] == 0


def test_shared_ledger_preserves_previous_run_spend(tmp_path):
    first = comparison.Runner(tmp_path, {}, {})
    request = first.ledger.reserve("preflight", "context7", 5000)
    first.ledger.settle(request, 5000)
    second = comparison.Runner(tmp_path / "different-output", {}, {}, tmp_path / "spending.sqlite3")
    assert second.ledger.summary()["accounted_upper_bound_micro_usd"] == 5000


def test_resume_replays_exact_tool_results_without_new_model_calls(tmp_path):
    content = [{"type": "tool_use", "id": "original-id", "name": "shell", "input": {"command": "pwd"}}]
    (tmp_path / "response-00.json").write_text(json.dumps({"content": content}))
    previous = {
        "model_turns": 1,
        "tool_calls": [{"name": "shell", "input": {"command": "pwd"}, "output": "/testbed\n", "is_error": False}],
    }
    messages = comparison.restore_messages(tmp_path, {"problem_statement": "issue"}, previous)
    assert messages == [
        {"role": "user", "content": "issue"},
        {"role": "assistant", "content": content},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "original-id", "content": "/testbed\n", "is_error": False},
        ]},
    ]
    previous["tool_calls"][0]["input"]["command"] = "different"
    with pytest.raises(ValueError, match="disagree"):
        comparison.restore_messages(tmp_path, {"problem_statement": "issue"}, previous)


def test_approved_protocol_matches_fixed_runner_limits():
    protocol = json.loads((SCRIPT.parents[1] / "benchmarks/swebench-pilot/comparison-protocol.json").read_text())
    assert protocol["attempts"] == 72
    assert protocol["model"] == "claude-opus-5-5"
    assert protocol["limits"]["per_attempt_micro_usd"] * 72 + 5000 < protocol["limits"]["total_micro_usd"]
    assert protocol["limits"]["max_output_tokens_per_turn"] == 2048
    assert protocol["limits"]["max_retrieval_calls_per_attempt"] == 3
