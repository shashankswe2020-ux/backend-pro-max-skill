"""Synthetic operator attestations exercise infrastructure, not P4 outcome gates."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
import test_repository
from backendpro.scripts import memory
from backendpro.scripts.repository import Snapshot
from backendpro.scripts.templates import compact_json

git = test_repository.git
workspace = test_repository.workspace


def stamp(offset=0):
    return (datetime.now(timezone.utc) + timedelta(days=offset)).isoformat().replace("+00:00", "Z")


@pytest.fixture
def vault(workspace, tmp_path_factory):
    store = tmp_path_factory.mktemp("memory-vault")
    store.chmod(0o700)
    memory.manage("init", workspace_root=str(workspace), store=str(store))
    return {"workspace_root": str(workspace), "store": str(store)}


@pytest.fixture
def summary(workspace):
    binding = Snapshot(str(workspace), ["ops.py", "test_ops.py"]).binding()
    return {
        "problem": "Retry attempt limits must reject zero attempts",
        "decision": "Validate a positive attempt limit before invoking the operation.",
        "failure_conditions": ["Does not establish safety for retries of non-idempotent operations."],
        "library_versions": {"python": "3.12.13"}, "binding": binding,
        "origin": {"sequence": "pilot", "family": "retry", "task": "first", "ordinal": 0,
                   "split": "development", "arm": "verified_memory"},
        "verification": {"argv": ["python", "-m", "pytest", "./test_ops.py"], "exit_code": 0,
                         "artifact_sha256": hashlib.sha256(b"authored-test-fixture").hexdigest(),
                         "snapshot_id": binding["snapshot_id"], "verified_at": stamp(-2)},
        "approval": {"reviewer": "fixture-reviewer", "reviewed_at": stamp(-1), "summary_only": True},
        "expires_at": stamp(7),
    }


def enable(vault):
    status = memory.manage("status", **vault)
    gate = {
        "root_id": status["root_id"], "revision": status["revision"],
        "reviewer": "fixture-reviewer", "reviewed_at": stamp(-1), "expires_at": stamp(7),
        "pattern": "Authored repeated retry fixture, not real trace evidence",
        "traces": [{"task": str(i), "sha256": hashlib.sha256(str(i).encode()).hexdigest()} for i in range(2)],
    }
    memory.manage("approve-gate", value=gate, approve=True, **vault)
    return gate


def query(vault, **overrides):
    args = {"query": "retry attempts", "sequence": "pilot", "family": "retry", "task": "second",
            "ordinal": 1, "allowed_tasks": ["first"], "library_versions": {"python": "3.12.13"}}
    return memory.memory_context(**{**args, **overrides}, **vault)


def test_gated_default_and_explicit_approval(vault, summary):
    with pytest.raises(ValueError, match="approval"):
        memory.manage("put", value=summary, **vault)
    saved = memory.manage("put", value=summary, approve=True, **vault)
    assert saved["records"] == 1 and not saved["reuse_enabled"]
    with pytest.raises(ValueError, match="disabled"):
        query(vault)
    enable(vault)
    result = query(vault)
    assert result["count"] == 1
    assert result["results"][0]["facts"] == summary
    assert not result["quality_gates_demonstrated"]
    assert len(compact_json(result)) <= 6000
    memory.manage("revoke-gate", **vault)
    with pytest.raises(ValueError, match="disabled"):
        query(vault)


@pytest.mark.parametrize("mutation", [
    lambda s: s.update(conversation="raw content"),
    lambda s: s["origin"].update(split="held_out"),
    lambda s: s["origin"].update(arm="no_memory"),
    lambda s: s["verification"].update(exit_code=1),
    lambda s: s["verification"].update(exit_code=False),
    lambda s: s["verification"].update(snapshot_id="0" * 64),
    lambda s: s["approval"].update(summary_only=False),
    lambda s: s.update(expires_at=stamp(100)),
    lambda s: s["approval"].update(reviewed_at=stamp(2)),
    lambda s: s.update(library_versions={"python": ">=3.12"}),
    lambda s: s.update(decision="api_key = 'not-a-real-credential'"),
    lambda s: s.update(decision="one\nraw transcript"),
])
def test_reject_unsafe_unverified_or_unsupported_summaries(vault, summary, mutation):
    mutation(summary)
    with pytest.raises(ValueError):
        memory.manage("put", value=summary, approve=True, **vault)
    assert memory.manage("status", **vault)["records"] == 0


def test_correct_delete_and_idempotent_put(vault, summary):
    original = memory.manage("put", value=summary, approve=True, **vault)["record_id"]
    assert memory.manage("put", value=summary, approve=True, **vault)["records"] == 1
    revised = copy.deepcopy(summary)
    revised["decision"] = "Validate retry limits before entering a retry loop."
    replacement = memory.manage("correct", value=revised, record_id=original, approve=True, **vault)
    assert replacement["record_id"] != original and replacement["records"] == 1
    with pytest.raises(ValueError, match="unknown"):
        memory.manage("delete", record_id=original, **vault)
    assert memory.manage("delete", record_id=replacement["record_id"], **vault)["records"] == 0
    assert summary["decision"] not in (memory.Path(vault["store"]) / "memory.json").read_text()


def test_chronology_family_permissions_and_versions(vault, summary):
    memory.manage("put", value=summary, approve=True, **vault)
    enable(vault)
    for options in ({"family": "different"}, {"sequence": "different"}, {"allowed_tasks": []}, {"ordinal": 0}):
        result = query(vault, **options)
        assert result["count"] == 0 and result["ineligible"]["scope_or_chronology"] == 1
    result = query(vault, library_versions={"python": "3.13.0"})
    assert result["count"] == 0 and result["ineligible"]["version"] == 1
    with pytest.raises(ValueError):
        query(vault, allowed_tasks=["second"])


def test_dirty_files_and_revision_invalidate(vault, summary, workspace):
    memory.manage("put", value=summary, approve=True, **vault)
    enable(vault)
    path = workspace / "ops.py"
    path.write_text(path.read_text() + "\n")
    result = query(vault)
    assert result["count"] == 0 and result["ineligible"]["source_invalid"] == 1
    git(workspace, "add", "ops.py")
    git(workspace, "commit", "-qm", "Revision change", "-m",
        "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>")
    with pytest.raises(ValueError, match="disabled"):
        query(vault)
    enable(vault)
    assert query(vault)["ineligible"]["source_invalid"] == 1


def test_expiry_invalidates_without_deleting_and_needs_review(vault, summary, monkeypatch):
    memory.manage("put", value=summary, approve=True, **vault)
    gate = enable(vault)
    gate["expires_at"] = stamp(30)
    memory.manage("approve-gate", value=gate, approve=True, **vault)
    real_datetime = datetime

    class Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.now(tz) + timedelta(days=8)

    monkeypatch.setattr(memory, "datetime", Later)
    result = query(vault)
    assert result["count"] == 0 and result["ineligible"]["expired"] == 1
    assert memory.manage("status", **vault)["records"] == 1


def test_exact_budget_preserves_whole_units(vault, summary):
    memory.manage("put", value=summary, approve=True, **vault)
    enable(vault)
    full = query(vault)
    size = len(compact_json(full))
    assert query(vault, max_chars=size) == full
    smaller = query(vault, max_chars=size - 1)
    assert smaller["count"] == 0 and smaller["omissions"]["budget"] == 1
    assert smaller["status"] == "budget_exhausted"
    with pytest.raises(ValueError, match="metadata"):
        query(vault, max_chars=1)


def test_scope_permissions_corruption_and_link_rejection(vault, workspace, tmp_path):
    store = memory.Path(vault["store"])
    store.chmod(0o755)
    with pytest.raises(ValueError, match="owner-only"):
        memory.manage("status", **vault)
    store.chmod(0o700)
    original = (store / "memory.json").read_bytes()
    (store / "memory.json").write_text("not JSON")
    with pytest.raises(ValueError):
        memory.manage("status", **vault)
    (store / "memory.json").unlink()
    target = tmp_path / "outside.json"
    target.write_bytes(original)
    (store / "memory.json").symlink_to(target)
    with pytest.raises(OSError):
        memory.manage("status", **vault)
    assert target.read_bytes() == original
    with pytest.raises(ValueError, match="outside"):
        memory.manage("init", workspace_root=str(workspace), store=str(workspace))


def test_lock_conflict_does_not_lose_data(vault, summary):
    with memory._vault(vault["workspace_root"], vault["store"], write=True):
        with pytest.raises(ValueError, match="busy"):
            memory.manage("put", value=summary, approve=True, **vault)
    assert memory.manage("status", **vault)["records"] == 0
    memory.manage("put", value=summary, approve=True, **vault)
    assert memory.manage("status", **vault)["records"] == 1


def test_atomic_write_failure_preserves_previous_state(vault, summary, monkeypatch):
    store = memory.Path(vault["store"])
    before = (store / "memory.json").read_bytes()

    def fail(*args, **kwargs):
        raise OSError("injected replacement failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="injected"):
        memory.manage("put", value=summary, approve=True, **vault)
    assert (store / "memory.json").read_bytes() == before
    assert sorted(path.name for path in store.iterdir()) == ["memory.json", "memory.lock"]


def test_gate_requires_distinct_traces_and_current_review(vault):
    gate = enable(vault)
    memory.manage("revoke-gate", **vault)
    gate["traces"][1] = dict(gate["traces"][0])
    with pytest.raises(ValueError, match="distinct"):
        memory.manage("approve-gate", value=gate, approve=True, **vault)
    assert not memory.manage("status", **vault)["reuse_enabled"]


def test_correction_cannot_relabel_origin(vault, summary):
    identity = memory.manage("put", value=summary, approve=True, **vault)["record_id"]
    summary["origin"]["ordinal"] = 2
    with pytest.raises(ValueError, match="preserve task origin"):
        memory.manage("correct", record_id=identity, value=summary, approve=True, **vault)
    assert memory.manage("status", **vault)["records"] == 1


def test_store_rejects_another_repository(vault, tmp_path_factory):
    other = tmp_path_factory.mktemp("independent-repository")
    git(other, "init", "-q")
    (other / "source.py").write_text("value = 1\n")
    git(other, "add", "source.py")
    git(other, "commit", "-qm", "Independent fixture", "-m",
        "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>")
    with pytest.raises(ValueError, match="different repository"):
        memory.manage("status", workspace_root=str(other), store=vault["store"])


def test_memory_telemetry_retains_ids_and_budget_exhaustion(vault, summary):
    from backendpro.scripts.retrieval_evidence import describe_payload
    identity = memory.manage("put", value=summary, approve=True, **vault)["record_id"]
    enable(vault)
    result = query(vault)
    description = describe_payload(result)
    assert description["evidence_ids"] == description["citations"] == [identity]
    limited = query(vault, max_chars=len(compact_json(result)) - 1)
    assert describe_payload(limited)["status"] == "budget_exhausted"


def test_cli_query_parity(vault, summary, tmp_path):
    memory.manage("put", value=summary, approve=True, **vault)
    enable(vault)
    args = {"query": "retry attempts", "sequence": "pilot", "family": "retry", "task": "second",
            "ordinal": 1, "allowed_tasks": ["first"], "library_versions": {"python": "3.12.13"}, "max_chars": 6000}
    input_path = tmp_path / "query.json"
    input_path.write_text(json.dumps(args))
    reply = subprocess.run(
        [sys.executable, "-m", "backendpro.scripts.search", "memory", "query", "--input", str(input_path),
         "--workspace-root", vault["workspace_root"], "--store", vault["store"]],
        capture_output=True, text=True, check=True,
    )
    assert json.loads(reply.stdout) == query(vault)


def test_actual_mcp_parity_and_mutation_not_exposed(vault, summary):
    pytest.importorskip("mcp")
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    memory.manage("put", value=summary, approve=True, **vault)
    enable(vault)
    expected = query(vault)
    args = {"query": "retry attempts", "sequence": "pilot", "family": "retry", "task": "second",
            "ordinal": 1, "allowed_tasks": ["first"], "library_versions": {"python": "3.12.13"}}

    async def exercise():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "backendpro.scripts.mcp_server"],
            env={**os.environ, "BACKENDPRO_WORKSPACE": vault["workspace_root"], "BACKENDPRO_MEMORY_STORE": vault["store"]},
        )
        with anyio.fail_after(30):
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    names = {tool.name for tool in (await session.list_tools()).tools}
                    assert "memory_context" in names and "approve-gate" not in names
                    reply = await session.call_tool("memory_context", args)
                    assert not reply.isError
                    assert reply.content[0].text == compact_json(expected)
                    assert len(reply.content[0].text) <= 6000
                    unauthorized = await session.call_tool("memory_context", {**args, "store": "/tmp/elsewhere"})
                    assert unauthorized.isError
                    memory.manage("revoke-gate", **vault)
                    disabled = await session.call_tool("memory_context", args)
                    assert disabled.isError

    anyio.run(exercise)
