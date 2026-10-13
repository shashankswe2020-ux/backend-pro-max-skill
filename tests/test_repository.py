"""Local evidence is explicit, bounded, source-bound and never executable."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest
from backendpro.scripts.repository import Snapshot, editor_context, repository_context
from backendpro.scripts.templates import compact_json


def git(root, *args):
    return subprocess.check_output(
        ["git", "-c", "user.name=BackendPro Test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
        text=True,
    ).strip()


@pytest.fixture
def workspace(tmp_path):
    files = {
        "ops.py": "def retry(attempts):\n    if attempts < 1:\n        raise ValueError('attempts')\n    return attempts\n",
        "service.py": "from ops import retry as invoke\n\n\ndef handle():\n    return invoke(3)\n",
        "test_ops.py": "import pytest\nfrom ops import retry\n\n\ndef test_retry():\n    with pytest.raises(ValueError):\n        retry(0)\n",
        "pyproject.toml": "[tool.pytest.ini_options]\naddopts = '-q'\n",
        "AGENTS.md": "Local convention: retry operations must have an explicit attempt limit.\n",
        ".gitignore": "ignored.py\n",
        "ignored.py": "def retry():\n    return 'ignored'\n",
        ".env": "PASSWORD=not-a-real-secret\n",
        "embedded.py": "api_key = 'not-a-real-secret'\ndef retry():\n    return 1\n",
        "generated.py": "# Automatically generated; do not edit\ndef retry():\n    return 1\n",
    }
    for path, text in files.items():
        (tmp_path / path).write_text(text)
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-f", ".")
    git(tmp_path, "commit", "-qm", "Fixture", "-m",
        "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>")
    (tmp_path / "untracked.py").write_text("def retry():\n    return 'untracked'\n")
    return tmp_path


def test_definitions_references_conventions_and_exact_source_ranges(workspace):
    result = repository_context("retry", ["ops.py", "test_ops.py", "AGENTS.md"], workspace_root=str(workspace))
    assert result["count"] > 0
    assert len(compact_json(result)) <= 6000
    assert result["workspace"]["revision"] == git(workspace, "rev-parse", "HEAD")
    assert {"definition", "syntactic_call", "local_convention"} <= {unit["relationship"] for unit in result["results"]}
    for unit in result["results"]:
        binding = unit["binding"]
        data = (workspace / binding["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == binding["file_sha256"]
        expected = "\n".join(data.decode().splitlines()[binding["start_line"] - 1:binding["end_line"]])
        assert unit["facts"]["excerpt"] == expected
    assert result["verification"] == [{"argv": ["python", "-m", "pytest", "./test_ops.py"], "status": "suggested_not_run"}]


def test_no_results_is_not_agent_activation_measurement(workspace):
    result = repository_context("zzqxvzzqxv", ["ops.py"], workspace_root=str(workspace))
    assert result["count"] == result["matched_count"] == 0
    assert result["status"] == "no_matches"


def test_exclusions_apply_even_to_force_tracked_files(workspace):
    result = repository_context(
        "retry", [".env", "ignored.py", "embedded.py", "generated.py", "untracked.py"],
        workspace_root=str(workspace),
    )
    assert result["count"] == 0 and result["workspace"]["files"] == {}
    assert result["discovery"]["excluded_files"] == {
        "path_policy": 3, "sensitive_content": 1, "generated_content": 1,
    }
    assert "not-a-real-secret" not in compact_json(result)
    assert ".env" not in compact_json(result)


@pytest.mark.parametrize("path", ["../ops.py", "/etc/passwd", "a/../ops.py", "a\\ops.py", ":(glob)**", "."])
def test_invalid_paths_fail_before_read(workspace, path):
    with pytest.raises(ValueError):
        repository_context("retry", [path], workspace_root=str(workspace))


def test_symlink_and_directory_rejected(workspace):
    (workspace / "link.py").symlink_to(workspace / "ops.py")
    git(workspace, "add", "link.py")
    with pytest.raises(ValueError, match="symlinks"):
        repository_context("retry", ["link.py"], workspace_root=str(workspace))
    (workspace / "folder").mkdir()
    with pytest.raises(ValueError, match="files"):
        repository_context("retry", ["folder"], workspace_root=str(workspace))


def test_non_regular_replacement_is_rejected_without_reading(workspace):
    (workspace / "ops.py").unlink()
    os.mkfifo(workspace / "ops.py")
    with pytest.raises(ValueError, match="regular files"):
        repository_context("retry", ["ops.py"], workspace_root=str(workspace))


def test_utf8_bom_does_not_break_python_ast_fallback(workspace):
    path = workspace / "ops.py"
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    result = repository_context("retry", ["ops.py"], workspace_root=str(workspace))
    assert result["count"] == 1
    assert result["results"][0]["facts"]["excerpt"].startswith("\ufeff")


def test_stale_saved_file_same_mtime_and_revision_fail_closed(workspace):
    first = repository_context("retry", ["ops.py"], workspace_root=str(workspace))
    path = workspace / "ops.py"
    original = path.stat().st_mtime_ns
    path.write_text(path.read_text().replace("return attempts", "return attempts + 1"))
    os.utime(path, ns=(original, original))
    with pytest.raises(ValueError, match="Stale file"):
        repository_context("retry", ["ops.py"], workspace_root=str(workspace),
                           expected_files=first["workspace"]["files"])
    second = repository_context("retry", ["ops.py"], workspace_root=str(workspace))
    assert first["workspace"]["snapshot_id"] != second["workspace"]["snapshot_id"]
    git(workspace, "add", "ops.py")
    git(workspace, "commit", "-qm", "Change", "-m",
        "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>")
    with pytest.raises(ValueError, match="revision"):
        repository_context("retry", ["ops.py"], workspace_root=str(workspace),
                           expected_revision=first["workspace"]["revision"])


def test_concurrent_file_change_invalidates_response(workspace, monkeypatch):
    original = Snapshot.validate
    def change_then_validate(self):
        (workspace / "ops.py").write_text("def retry():\n    return 9\n")
        original(self)
    monkeypatch.setattr(Snapshot, "validate", change_then_validate)
    with pytest.raises(ValueError, match="changed during"):
        repository_context("retry", ["ops.py"], workspace_root=str(workspace))


def packet(workspace):
    paths = ["ops.py", "service.py"]
    source = Snapshot(str(workspace), paths).binding()
    return editor_context(
        str(workspace), [
            {"uri": (workspace / "ops.py").as_uri(), "range": {
                "start": {"line": 0, "character": 4}, "end": {"line": 0, "character": 9},
            }},
            {"uri": (workspace / "service.py").as_uri(), "range": {
                "start": {"line": 4, "character": 11}, "end": {"line": 4, "character": 17},
            }},
        ],
        client="fixture-editor", method="textDocument/references",
        expected_revision=source["revision"], expected_files=source["files"],
    )


def test_editor_locations_retain_alias_reference_and_do_not_claim_resolution(workspace):
    editor = packet(workspace)
    result = repository_context("retry", list(editor["files"]), workspace_root=str(workspace), editor=editor)
    assert result["discovery"]["mode"] == "editor_locations"
    assert len(result["results"]) == 2
    assert any("invoke(3)" in unit["facts"]["excerpt"] for unit in result["results"])
    assert all(unit["provenance"] == "editor_reported_saved_file" for unit in result["results"])
    (workspace / "service.py").write_text("invalid saved content\n")
    with pytest.raises(ValueError, match="Stale file"):
        repository_context("retry", list(editor["files"]), workspace_root=str(workspace), editor=editor)


def test_editor_packet_cannot_change_authorized_scope(workspace):
    editor = packet(workspace)
    editor["locations"][0]["path"] = "../private.py"
    with pytest.raises(ValueError):
        repository_context("retry", list(editor["files"]), workspace_root=str(workspace), editor=editor)


def test_editor_packet_is_bound_to_workspace_identity(workspace):
    editor = packet(workspace)
    editor["root_id"] = "0" * 64
    with pytest.raises(ValueError, match="different workspace"):
        repository_context("retry", list(editor["files"]), workspace_root=str(workspace), editor=editor)


def test_native_saved_locations_do_not_require_backend_ast_parse_success(workspace):
    (workspace / "ops.py").write_text("def retry(:\n    pass\n")
    source = Snapshot(str(workspace), ["ops.py"]).binding()
    editor = editor_context(
        str(workspace), [{"uri": (workspace / "ops.py").as_uri(), "range": {
            "start": {"line": 0, "character": 4}, "end": {"line": 0, "character": 9},
        }}], client="fixture", method="textDocument/references",
        expected_revision=source["revision"], expected_files=source["files"],
    )
    result = repository_context("retry", ["ops.py"], workspace_root=str(workspace), editor=editor)
    assert result["count"] == 1
    assert result["analysis_gaps"][0]["path"] == "ops.py"
    with pytest.raises(ValueError, match="parse"):
        repository_context("retry", ["ops.py"], workspace_root=str(workspace))


def test_malformed_editor_ranges_and_unsaved_positions_fail(workspace):
    source = Snapshot(str(workspace), ["ops.py"]).binding()
    for location in (
        {},
        {"uri": (workspace / "ops.py").as_uri(), "range": {}},
        {"uri": (workspace / "ops.py").as_uri(), "range": {
            "start": {"line": 0, "character": 999}, "end": {"line": 0, "character": 1000},
        }},
    ):
        with pytest.raises(ValueError):
            editor_context(str(workspace), [location], client="fixture", method="textDocument/references",
                           expected_revision=source["revision"], expected_files=source["files"])


def test_exclusion_policy_changes_invalidate_existing_evidence(workspace):
    first = repository_context("retry", ["ops.py"], workspace_root=str(workspace))
    (workspace / ".gitignore").write_text("ops.py\n")
    with pytest.raises(ValueError, match="excluded"):
        repository_context("retry", ["ops.py"], workspace_root=str(workspace),
                           expected_files=first["workspace"]["files"])


def test_extraction_limit_is_counted_not_silently_truncated(workspace):
    (workspace / "many.py").write_text("\n".join(f"def retry_{n}():\n    return {n}\n" for n in range(140)))
    git(workspace, "add", "many.py")
    result = repository_context("retry", ["many.py"], workspace_root=str(workspace))
    assert result["matched_count"] == 140
    assert result["omissions"]["candidate_limit"] == 12
    assert result["count"] + result["omitted_count"] == 140


def test_retrieval_telemetry_recognizes_local_identity_and_budget_exhaustion(workspace):
    from backendpro.scripts.retrieval_evidence import describe_payload
    result = repository_context("retry", ["ops.py"], workspace_root=str(workspace))
    description = describe_payload(result)
    assert description["evidence_ids"] == [result["results"][0]["id"]]
    assert description["citations"] == [result["results"][0]["id"]]
    below = repository_context("retry", ["ops.py"], workspace_root=str(workspace), max_chars=len(compact_json(result)) - 1)
    assert describe_payload(below)["status"] == "budget_exhausted"


def test_complete_units_and_exact_character_budget(workspace):
    raw = repository_context("retry", ["ops.py"], workspace_root=str(workspace))
    size = len(compact_json(raw))
    assert repository_context("retry", ["ops.py"], workspace_root=str(workspace), max_chars=size)["count"] == 1
    below = repository_context("retry", ["ops.py"], workspace_root=str(workspace), max_chars=size - 1)
    assert below["count"] == 0
    assert below["omitted_count"] == below["omissions"]["budget"] == 1
    assert below["status"] == "budget_exhausted"
    assert len(compact_json(below)) <= size - 1


def test_curated_and_local_sources_stay_distinct_and_namespace_tension_is_explicit(workspace):
    (workspace / "model.py").write_text("from pydantic.v1 import BaseModel\n\nclass Model(BaseModel):\n    value: int\n")
    git(workspace, "add", "model.py")
    result = repository_context(
        "pydantic dictionary export migration", ["model.py"], workspace_root=str(workspace),
        stack="python-fastapi", library_versions={"pydantic": "2.10.6"}, max_chars=10000,
    )
    assert {unit["kind"] for unit in result["results"]} == {"local", "curated"}
    assert result["tensions"][0]["code"] == "pydantic_compatibility_namespace"
    assert result["count"] + result["omitted_count"] == result["matched_count"]
    assert "Not resolved automatically" in result["reconciliation"]


def test_cli_and_core_agree(workspace):
    result = subprocess.run(
        [sys.executable, "-m", "backendpro.scripts.search", "context", "retry",
         "--workspace-root", str(workspace), "--paths", "ops.py"],
        capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout) == repository_context("retry", ["ops.py"], workspace_root=str(workspace))


def test_actual_mcp_transport_authorized_root_and_invalidation(workspace):
    pytest.importorskip("mcp")
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def exercise():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "backendpro.scripts.mcp_server"],
            env={**os.environ, "BACKENDPRO_WORKSPACE": str(workspace)},
        )
        with anyio.fail_after(30):
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    response = await session.call_tool("repository_context", {"query": "retry", "paths": ["ops.py"]})
                    assert not response.isError
                    assert len(response.content[0].text) <= 6000
                    result = json.loads(response.content[0].text)
                    assert result == repository_context("retry", ["ops.py"], workspace_root=str(workspace))
                    (workspace / "ops.py").write_text("def retry():\n    return 99\n")
                    stale = await session.call_tool("repository_context", {
                        "query": "retry", "paths": ["ops.py"], "expected_files": result["workspace"]["files"],
                    })
                    assert stale.isError
                    escape = await session.call_tool("repository_context", {"query": "retry", "paths": ["../x.py"]})
                    assert escape.isError
    anyio.run(exercise)


def test_repository_budget_evaluator_accounts_for_exact_labeled_lines(workspace):
    from backendpro.scripts.benchmark import evaluate_repository
    report = evaluate_repository(str(workspace), [
        {"query": "retry", "paths": ["ops.py"],
         "relevant": [{"path": "ops.py", "start_line": 1, "end_line": 4}],
         "critical": [{"path": "ops.py", "start_line": 4, "end_line": 4}]},
        {"query": "zzqxvzzqxv", "paths": ["ops.py"], "relevant": [], "critical": []},
    ], [2500, 4000])
    for result in report["budgets"].values():
        assert result["cases"][0]["modes"]["bounded_ast"]["critical_line_retention"] == 1
        assert all(mode["no_match_control_passed"] for mode in result["cases"][1]["modes"].values())
    assert not report["quality_gates_demonstrated"]
    assert not report["agent_activation_measured"]
