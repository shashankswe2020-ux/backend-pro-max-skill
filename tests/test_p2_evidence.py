"""P2 contracts: no invented compatibility, source binding and whole-unit budgets."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from backendpro.scripts import core, evidence, semantic
from backendpro.scripts.templates import compact_json, format_search_response
from backendpro.scripts.versions import resolve_versions, version_match


def bound(name="retry", scope="patterns.csv", **fields):
    row = {"Name": name, "Solution": "retry safely", "When NOT to Use": "unsafe writes", **fields}
    return {**row, "_evidence": evidence.bind_row(row, scope)}


def payload(*rows):
    return {"query": "retry", "domain": "pattern", "results": list(rows)}


def test_versioned_pilot_is_opt_in_and_exact_release_scoped():
    before = core.search_stack("pydantic", "python-fastapi")
    raw = core.search_stack("pydantic dictionary export", "python-fastapi", max_results=20, evidence=True)
    result = evidence.format_evidence(raw, library_versions={"pydantic": "2.10.6"})
    matches = [unit for unit in result["results"] if unit["version_match"] == "match"]
    assert matches and all(unit["applicability"]["Applies To"] == "==2.10.6" for unit in matches)
    assert result["omissions"]["version_mismatch"] >= 1
    assert core.search_stack("pydantic", "python-fastapi") == before
    assert all("_evidence" not in row for row in before["results"])
    assert all(unit["platform_check"] == "not_evaluated" for unit in matches)


def test_identity_expansion_and_source_integrity():
    raw = core.search_stack("pydantic dictionary", "python-fastapi", max_results=20, evidence=True)
    for row in raw["results"]:
        bound_row = row["_evidence"]
        detail = evidence.evidence_detail(bound_row["id"])
        assert detail == bound_row
        assert detail["binding"]["row_sha256"] == hashlib.sha256(
            json.dumps(detail["fields"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        if detail["fields"].get("Library"):
            evidence.validate_metadata(detail["fields"])
    with pytest.raises(ValueError, match="not found"):
        evidence.evidence_detail("bpme:" + "0" * 64)
    with pytest.raises(ValueError, match="Invalid"):
        evidence.evidence_detail("../../secrets")


def test_identity_ignores_rank_but_changes_with_source_content():
    row = {"Name": "retry", "Solution": "safe"}
    first = evidence.bind_row(row, "patterns.csv")
    assert evidence.bind_row({**row, "_score": 999}, "patterns.csv") == first
    assert evidence.bind_row({**row, "Solution": "changed"}, "patterns.csv")["id"] != first["id"]
    assert evidence.bind_row(row, "other.csv")["id"] != first["id"]


def test_provenance_version_never_becomes_library_compatibility():
    result = evidence.format_evidence(payload(bound(Version="2.10.6")))
    unit = result["results"][0]
    assert unit["version_match"] == "unknown"
    assert unit["applicability"] == {}
    assert "Library" in unit["missing"]
    assert "Version" in unit["omitted_fields"]


def test_packing_skips_oversized_unit_without_slicing_warning():
    raw = payload(bound("large", **{"When NOT to Use": "critical warning " * 2000}), bound("small"))
    before = copy.deepcopy(raw)
    result = evidence.format_evidence(raw)
    assert [unit["title"] for unit in result["results"]] == ["small"]
    assert result["results"][0]["facts"]["When NOT to Use"] == "unsafe writes"
    assert result["omissions"]["budget"] == 1
    assert len(compact_json(result)) <= 6000
    assert raw == before


def test_exact_budget_boundary_and_explicit_omissions():
    raw = payload(bound())
    result = evidence.format_evidence(raw)
    size = len(compact_json(result))
    assert evidence.format_evidence(raw, size)["count"] == 1
    below = evidence.format_evidence(raw, size - 1)
    assert below["count"] == 0 and below["status"] == "budget_exhausted"
    assert below["omitted_count"] == sum(below["omissions"].values()) == 1
    assert len(compact_json(below)) <= size - 1
    with pytest.raises(ValueError, match="metadata exceeds"):
        evidence.format_evidence(raw, 1)


def test_cross_domain_selection_ignores_uncalibrated_scores_and_domain_order():
    raw = {"query": "retry timeout", "results": {
        "pattern": [bound("retry", _score=999999), bound("retry alternative", Solution="alternative retry")],
        "reliability": [bound("timeout", "reliability.csv", Solution="set timeout", _score=0.0001)],
    }}
    result = evidence.format_evidence(raw, 10000)
    assert [u["title"] for u in result["results"]][:2] == ["retry", "timeout"]
    reordered = {**raw, "results": dict(reversed(list(raw["results"].items())))}
    assert evidence.format_evidence(reordered, 10000) == result


def test_duplicates_suppressed_but_different_warnings_retained():
    result = evidence.format_evidence(payload(
        bound(), bound(scope="reliability.csv"), bound(**{"When NOT to Use": "different critical warning"}),
    ))
    assert result["count"] == 2
    assert result["omissions"]["duplicate"] == 1
    assert result["matched_count"] == result["count"] + result["omitted_count"]


@pytest.mark.parametrize("observed, expected", [
    ("==2.10.6", "match"), (">=2,<3", "match"), (">=1,<3", "unknown"),
    ("<2", "mismatch"), (">=3", "mismatch"), ("==2.10.6rc1", "unknown"),
])
def test_range_reasoning_is_conservative(tmp_path, observed, expected):
    (tmp_path / "requirements.txt").write_text("pydantic" + observed)
    context = resolve_versions(str(tmp_path))
    assert version_match(">=2,<3", context["libraries"]["pydantic"]) == expected


def test_conflicting_manifest_lock_and_explicit_pin_not_overridden(tmp_path):
    (tmp_path / "requirements.txt").write_text("pydantic>=1,<2\n")
    context = resolve_versions(str(tmp_path), {"pydantic": "2.10.6"})
    assert context["libraries"]["pydantic"]["status"] == "conflict"
    raw = core.search_stack("pydantic", "python-fastapi", max_results=20, evidence=True)
    result = evidence.format_evidence(raw, project_path=str(tmp_path), library_versions={"pydantic": "2.10.6"})
    assert result["omissions"]["version_conflict"] == 4
    assert not any(unit["applicability"].get("Library") for unit in result["results"])


def test_pep621_and_uv_lock_resolution(tmp_path):
    pytest.importorskip("tomllib")
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["pydantic>=2,<3"]\nrequires-python=">=3.9"\n')
    (tmp_path / "uv.lock").write_text('[[package]]\nname="pydantic"\nversion="2.10.6"\n')
    context = resolve_versions(str(tmp_path))
    assert context["libraries"]["pydantic"]["status"] == "resolved"
    assert context["libraries"]["pydantic"]["observations"][1]["source_sha256"] == hashlib.sha256(
        (tmp_path / "uv.lock").read_bytes()
    ).hexdigest()
    assert context["libraries"]["python"]["status"] == "constrained"
    assert version_match("==2.10.6", context["libraries"]["pydantic"]) == "match"
    (tmp_path / "uv.lock").write_text('[[package]]\nname="pydantic"\nversion="1.10.21"\n')
    assert resolve_versions(str(tmp_path))["libraries"]["pydantic"]["status"] == "conflict"


def test_unknown_markers_includes_and_no_sensitive_values_echoed(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        'pydantic==2.10.6; python_version > "3.9"\n-r private/other.txt\nprivate @ https://user:secret@example.test/wheel\n'
    )
    result = resolve_versions(str(tmp_path), {"pydantic": "2.10.6"})
    assert result["libraries"]["pydantic"]["status"] == "unknown"
    assert result["issues"]
    assert "secret" not in json.dumps(result) and "private/other.txt" not in json.dumps(result)


def test_partial_python_selector_does_not_invent_patch_version(tmp_path):
    (tmp_path / ".python-version").write_text("3.12")
    observation = resolve_versions(str(tmp_path))["libraries"]["python"]
    assert observation["status"] == "constrained"
    assert version_match("==3.12.0", observation) == "unknown"
    assert version_match(">=3.12,<3.13", observation) == "match"


def test_optional_pipfile_entries_are_not_assumed_active(tmp_path):
    (tmp_path / "Pipfile.lock").write_text(json.dumps({
        "default": {"pydantic": {"version": "==2.10.6"}},
        "develop": {"example": {"version": "==1.0"}},
    }))
    context = resolve_versions(str(tmp_path))["libraries"]
    assert context["pydantic"]["status"] == "resolved"
    assert context["example"]["status"] == "unknown"


def test_unconstrained_requirement_does_not_mask_exact_lock(tmp_path):
    (tmp_path / "requirements.txt").write_text("pydantic\n")
    (tmp_path / "Pipfile.lock").write_text(json.dumps({
        "default": {"pydantic": {"version": "==2.10.6"}},
    }))
    context = resolve_versions(str(tmp_path))["libraries"]["pydantic"]
    assert context["status"] == "resolved"
    assert version_match("==2.10.6", context) == "match"


def test_missing_toml_parser_is_explicit_not_a_silent_pin(monkeypatch, tmp_path):
    import builtins
    original = builtins.__import__
    def without_toml(name, *args, **kwargs):
        if name == "tomllib":
            raise ModuleNotFoundError(name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", without_toml)
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies=["pydantic<2"]')
    context = resolve_versions(str(tmp_path), {"pydantic": "2.10.6"})
    assert context["issues"] and context["libraries"]["pydantic"]["status"] == "unknown"


def test_invalid_manifests_and_symlinks_fail_explicitly(tmp_path):
    pytest.importorskip("tomllib")
    (tmp_path / "pyproject.toml").write_text("[invalid")
    with pytest.raises(ValueError, match="Invalid pyproject"):
        resolve_versions(str(tmp_path))
    (tmp_path / "pyproject.toml").unlink()
    (tmp_path / "external.txt").write_text("pydantic==2.10.6")
    (tmp_path / "requirements.txt").symlink_to(tmp_path / "external.txt")
    with pytest.raises(ValueError, match="non-symlink"):
        resolve_versions(str(tmp_path))


def test_source_schema_rejects_incomplete_unpinned_or_empty_ranges():
    row = evidence.supplemental_rows("stacks/python-fastapi.csv")[0]
    for updates in (
        {"Library": ""}, {"Source SHA256": "bad"}, {"Applies To": ">=3,<2"},
        {"Source URL": "https://docs.pydantic.dev/latest/"}, {"Last Verified": "not-a-date"},
    ):
        with pytest.raises(ValueError):
            evidence.validate_metadata({**row, **updates})


@pytest.mark.parametrize("document", [
    [], {"format": "unknown", "records": []},
    {"format": "source-evidence-v1", "records": [{"scope_file": "../private", "fields": {}}]},
    {"format": "source-evidence-v1", "records": [{"scope_file": [], "fields": {}}]},
    {"format": "source-evidence-v1", "records": [{"scope_file": "patterns.csv", "fields": []}]},
])
def test_invalid_supplemental_corpus_fails_cleanly(monkeypatch, tmp_path, document):
    (tmp_path / "evidence.json").write_text(json.dumps(document))
    monkeypatch.setattr(evidence, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError):
        evidence.supplemental_rows("patterns.csv")


def test_version_options_are_not_silently_ignored_on_legacy_formats():
    for mode in ("raw", "compact"):
        with pytest.raises(ValueError, match="require"):
            format_search_response(payload(bound()), mode, library_versions={"pydantic": "2.10.6"})


def test_semantic_cache_includes_supplemental_text(monkeypatch, tmp_path):
    class Model:
        def encode(self, texts, **kwargs):
            return tuple(texts)
    path = tmp_path / "rows.csv"
    path.write_text("Name\nbase\n")
    monkeypatch.setattr(semantic, "_get_model", lambda: Model())
    monkeypatch.setattr(semantic, "_EMBED_CACHE", {})
    monkeypatch.setattr(semantic, "_load_from_disk", lambda key: None)
    monkeypatch.setattr(semantic, "_save_to_disk", lambda *args: None)
    first = semantic.build_index([{"Name": "base"}], ["Name"], path)
    second = semantic.build_index([{"Name": "base"}, {"Name": "supplement"}], ["Name"], path)
    assert first != second
    assert len(semantic._EMBED_CACHE[second]["texts"]) == 2


def test_cli_evidence_and_detail_roundtrip():
    command = [sys.executable, "-m", "backendpro.scripts.search"]
    response = subprocess.run(command + [
        "pydantic dictionary", "--stack", "python-fastapi", "--evidence",
        "--library-version", "pydantic=2.10.6", "--max-chars", "5000", "--intent", "migration",
    ], capture_output=True, text=True, check=True)
    result = json.loads(response.stdout)
    assert len(response.stdout.rstrip("\n")) <= 5000 and result["count"] > 0
    assert result["intent"] == "migration"
    detail = subprocess.run(command + ["--evidence-id", result["results"][0]["id"]],
                            capture_output=True, text=True, check=True)
    assert json.loads(detail.stdout)["id"] == result["results"][0]["id"]


@pytest.mark.parametrize("options", [
    ["--compact", "--evidence"], ["--project-path", "."], ["--evidence", "--jsonl"],
    ["--evidence", "--library-version", "pydantic=latest"], ["--evidence", "--max-chars", "0"],
])
def test_cli_invalid_evidence_options(options):
    result = subprocess.run(
        [sys.executable, "-m", "backendpro.scripts.search", "pydantic", *options],
        capture_output=True, text=True,
    )
    assert result.returncode == 2


def test_exact_token_budget_uses_serialized_output_not_character_estimates():
    raw = payload(bound(Solution="data \u6570\u636e " * 10))
    def counter(text):
        return len(text.encode("utf-8"))
    result = evidence.format_evidence(raw)
    exact = counter(compact_json(result))
    assert evidence.format_evidence(raw, token_counter=counter, max_tokens=exact)["count"] == 1
    below = evidence.format_evidence(raw, token_counter=counter, max_tokens=exact - 1)
    assert below["count"] == 0
    assert counter(compact_json(below)) <= exact - 1


def test_budget_evaluation_reports_retention_and_source_bindings():
    from backendpro.scripts.benchmark import evaluate_evidence
    path = Path(__file__).with_name("evidence-benchmark.json")
    report = evaluate_evidence(json.loads(path.read_text())["queries"], [1000, 6000])
    assert report["budgets"]["1000"]["critical_field_retention"] == 0
    assert report["budgets"]["6000"]["critical_field_retention"] == 1
    assert all(value["all_bindings_valid"] and value["all_omissions_accounted"] for value in report["budgets"].values())
    assert not report["quality_gates_demonstrated"]


def test_tokenizer_is_hash_pinned_and_truncation_disabled(tmp_path):
    tokenizers = pytest.importorskip("tokenizers")
    from backendpro.scripts.benchmark import pinned_token_counter
    tokenizer = tokenizers.Tokenizer(tokenizers.models.WordLevel({"[UNK]": 0}, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = tokenizers.pre_tokenizers.Whitespace()
    tokenizer.enable_truncation(1)
    path = tmp_path / "tokenizer.json"
    tokenizer.save(str(path))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    counter, info = pinned_token_counter(path, digest, "test-fixture")
    assert counter("one two three") == 3
    assert not info["truncation"]
    with pytest.raises(ValueError, match="mismatch"):
        pinned_token_counter(path, "0" * 64, "test-fixture")
