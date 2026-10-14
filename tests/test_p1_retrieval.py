"""P1 candidate selection and observable retrieval contracts."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from backendpro.scripts import core, rerank, semantic
from backendpro.scripts.templates import compact_json, format_compact


@pytest.fixture
def ranked_corpus(monkeypatch):
    identifiers = {config["output_cols"][0] for config in core.CSV_CONFIG.values()} | {"Name", "Guideline"}
    rows = [{name: f"row-{i}" for name in identifiers} for i in range(60)]

    class Index:
        N = len(rows)

        def score(self, query):
            return [(i, float(100 - i)) for i in range(len(rows))]

    class CrossEncoder:
        def predict(self, pairs):
            return [1000 if "row-19 " in text + " " else -index for index, (_, text) in enumerate(pairs)]

    monkeypatch.setattr(core, "_get_index", lambda *args: (rows, Index()))
    monkeypatch.setattr(rerank, "is_available", lambda: True)
    monkeypatch.setattr(rerank, "_get_model", lambda: CrossEncoder())
    return rows


@pytest.mark.parametrize("scope", ["domain", "stack", "all"])
def test_rerank_can_promote_candidate_outside_final_top_five(ranked_corpus, scope):
    if scope == "domain":
        result = core.search("fixture", domain="pattern", max_results=5, candidate_pool=20, rerank=True)
        groups = [result["results"]]
    elif scope == "stack":
        result = core.search_stack("fixture", "go", max_results=5, candidate_pool=20, rerank=True)
        groups = [result["results"]]
    else:
        result = core.search_all("fixture", max_results=5, candidate_pool=20, rerank=True)
        groups = result["results"].values()
    for rows in groups:
        assert len(rows) == 5
        assert rows[0]["_score"] == 81
    assert result["retrieval"]["rerank_applied"]


def test_plain_bm25_contract_unchanged(ranked_corpus):
    result = core.search("fixture", domain="pattern")
    assert set(result) == {"domain", "query", "file", "count", "results"}
    assert [r["Name"] for r in result["results"]] == [f"row-{i}" for i in range(5)]


def test_missing_optional_dependencies_are_visible_in_result(monkeypatch):
    monkeypatch.setattr(semantic, "is_available", lambda: False)
    monkeypatch.setattr(rerank, "is_available", lambda: False)
    result = core.search("saga", domain="pattern", engine="hybrid", rerank=True)
    details = result["retrieval"]
    assert details["requested_engine"] == "hybrid"
    assert details["effective_engine"] == "bm25"
    assert details["rerank_requested"] and not details["rerank_applied"]
    assert len(details["fallbacks"]) == 2
    assert result["results"]


def test_auto_scope_hints_do_not_change_explicit_scope():
    auto = core.search("kafka consistency", diagnostics=True)
    assert auto["retrieval"]["scope"]["mode"] == "auto"
    assert len(auto["retrieval"]["scope"]["candidates"]) <= 3
    explicit = core.search("kafka", domain="auth", diagnostics=True)
    assert explicit["domain"] == "auth"
    assert explicit["retrieval"]["scope"] == {"mode": "explicit", "selected": "auth", "candidates": []}


@pytest.mark.parametrize("options", [
    {"engine": "unknown"}, {"candidate_pool": 4}, {"candidate_pool": True},
    {"candidate_pool": -1}, {"min_score": float("nan")}, {"max_age_months": -1},
])
def test_invalid_retrieval_options_are_rejected(options):
    with pytest.raises(ValueError):
        core.search("fixture", domain="pattern", **options)


def test_cli_and_core_share_all_domain_limit():
    completed = subprocess.run(
        [sys.executable, "-m", "backendpro.scripts.search", "idempotency", "--all",
         "-n", "5", "--diagnostics", "--json"], text=True, capture_output=True, check=True,
    )
    actual = json.loads(completed.stdout)
    expected = core.search_all("idempotency", max_results=5, diagnostics=True)
    assert actual["results"] == expected["results"]
    assert actual["retrieval"] == expected["retrieval"]


def test_expanded_pool_fifty_is_reranked_before_truncation(ranked_corpus, monkeypatch):
    class Model:
        def predict(self, pairs):
            assert len(pairs) == 50
            return [100 if "row-49 " in text + " " else -i for i, (_, text) in enumerate(pairs)]
    monkeypatch.setattr(rerank, "_get_model", lambda: Model())
    result = core.search("fixture", "pattern", max_results=5, candidate_pool=50, rerank=True)
    assert result["results"][0]["_score"] == 51
    assert result["retrieval"]["candidate_count"] == 50
    assert result["retrieval"]["returned_count"] == 5


def test_freshness_filters_before_candidate_cutoff(ranked_corpus):
    for index, row in enumerate(ranked_corpus):
        row["Last Updated"] = "2000-01-01" if index < 30 else "2999-01-01"
    result = core.search("fixture", "pattern", max_results=5, candidate_pool=20, max_age_months=12)
    assert [row["_score"] for row in result["results"]] == [70, 69, 68, 67, 66]
    assert result["retrieval"]["candidate_count"] == 20


def test_constraint_preferences_use_rerank_score_tiebreak(ranked_corpus):
    for row in ranked_corpus:
        row["Cloud Native"] = "gcp"
    result = core.search("fixture", "pattern", rerank=True, constraints="cloud=gcp")
    assert result["results"][0]["_score"] == 81


@pytest.mark.parametrize("expression", ["", "garbage", "cloud=", "unknown=x", "cloud=a,cloud=b", "cloud=a=b"])
def test_invalid_constraint_preferences_are_errors(expression):
    with pytest.raises(ValueError, match="constraint"):
        core.search("saga", "pattern", constraints=expression)


def test_model_execution_errors_do_not_masquerade_as_fallback(monkeypatch):
    monkeypatch.setattr(semantic, "is_available", lambda: True)
    def broken(*args):
        raise OSError("model weights unavailable")
    monkeypatch.setattr(semantic, "build_index", broken)
    with pytest.raises(OSError, match="model weights unavailable"):
        core.search("saga", "pattern", engine="hybrid")


def test_compact_keeps_engine_diagnostics_when_evidence_is_omitted(monkeypatch):
    monkeypatch.setattr(semantic, "is_available", lambda: False)
    result = core.search_all("idempotency", engine="hybrid", diagnostics=True)
    compact = format_compact(result)
    assert len(compact_json(compact)) <= 6000
    assert compact["retrieval"] == result["retrieval"]
    assert compact["retrieval"]["effective_engine"] == "bm25"
    assert compact["retrieval"]["fallbacks"]


def test_empty_jsonl_still_reports_requested_diagnostics():
    from backendpro.scripts.search import format_jsonl
    result = core.search("zzzz-no-terms-qqq", "auth", diagnostics=True)
    output = [json.loads(line) for line in format_jsonl(result).splitlines()]
    assert output == [{"_type": "retrieval_metadata", "retrieval": result["retrieval"]}]


def test_cli_refuses_conflicting_explicit_scopes():
    result = subprocess.run(
        [sys.executable, "-m", "backendpro.scripts.search", "kafka", "--domain", "auth", "--all"],
        text=True, capture_output=True,
    )
    assert result.returncode == 2
    assert "not allowed" in result.stderr


def test_bm25_and_embedding_identity_detect_same_mtime_content_changes(tmp_path, monkeypatch):
    path = tmp_path / "rows.csv"
    path.write_text("Name,Keywords\nA,alpha\n")
    original_time = path.stat().st_mtime_ns
    first_key = semantic._cache_key(path, ["Name"])
    _, first_index = core._get_index(path, ["Name"])
    path.write_text("Name,Keywords\nB,bravo\n")
    os.utime(path, ns=(original_time, original_time))
    assert semantic._cache_key(path, ["Name"]) != first_key
    rows, second_index = core._get_index(path, ["Name"])
    assert second_index is not first_index and rows[0]["Name"] == "B"
    key = semantic._cache_key(path, ["Name"])
    assert semantic._cache_key(path, ["Name", "Keywords"]) != key
    monkeypatch.setattr(semantic, "_MODEL_REVISION", "different-revision")
    assert semantic._cache_key(path, ["Name"]) != key


def test_pinned_snapshot_has_no_executable_remote_files(monkeypatch):
    pytest.importorskip("huggingface_hub")
    import huggingface_hub
    calls = []
    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda **kw: calls.append(kw) or "/cached-model")
    assert semantic.model_snapshot("model", "pinned") == "/cached-model"
    assert calls[0]["revision"] == "pinned"
    assert "*.py" not in calls[0]["allow_patterns"]


@pytest.mark.parametrize("scores", [[1], [1, float("nan")], [1, float("inf")]])
def test_invalid_reranker_output_is_not_truncated_to_success(monkeypatch, scores):
    class Broken:
        def predict(self, pairs):
            return scores
    monkeypatch.setattr(rerank, "_get_model", lambda: Broken())
    with pytest.raises(ValueError, match="invalid number"):
        rerank.rerank("query", [{"Name": "A"}, {"Name": "B"}], strict=True)


def test_cache_corruption_is_reported_and_not_used(tmp_path, monkeypatch, capsys):
    np = pytest.importorskip("numpy")
    monkeypatch.setattr(semantic, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(semantic, "_np", np)
    monkeypatch.setattr(semantic, "_load_deps", lambda: True)
    np.save(tmp_path / "embed_test.npy", np.array([[float("nan")]]))
    (tmp_path / "embed_test.json").write_text('["one"]')
    assert semantic._load_from_disk("test") is None
    assert "invalid embedding cache" in capsys.readouterr().err
