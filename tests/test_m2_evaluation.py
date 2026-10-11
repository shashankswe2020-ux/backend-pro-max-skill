"""M2 scoring fixtures are synthetic and never presented as client/model results."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def evaluation(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return importlib.import_module("evaluate_m2")


@pytest.fixture
def observations(evaluation, tmp_path):
    suite = evaluation.load_suite(evaluation.SUITE)
    value = {
        "suite_sha256": evaluation.digest(evaluation.SUITE),
        "surface": "mcp", "client": "synthetic", "client_version": "test-only", "model": "not-a-real-run",
        "settings": {}, "tool_manifest_sha256": "0" * 64, "repetitions": 3,
        "observations": [
            {
                "case_id": case["id"], "repeat": repeat, "status": "completed",
                "tool_calls": [{"name": "backendpro_search", "is_error": False}] if case["retrieve"] else [],
            }
            for repeat in range(3) for case in suite["activation"]
        ],
    }
    path = tmp_path / "synthetic-observations.json"
    path.write_text(json.dumps(value))
    return path, value


def test_offline_bundle_freezes_inputs_and_measures_not_grades(evaluation, tmp_path):
    output = tmp_path / "bundle"
    result = evaluation.bundle(evaluation.SUITE, output)
    assert result["activation_cases"] == 40
    assert result["retrieval_cases"] == 20
    assert result["compact_bound_passed"]
    assert result["model_experiments"] == "not_run"
    assert result["independent_review"] == "pending"
    assert len(result["records"]) == 20
    assert (output / "suite.json").read_bytes() == evaluation.SUITE.read_bytes()
    for row in result["records"]:
        path = output / row["artifact"]
        assert evaluation.digest(path) == row["sha256"]
        artifact = json.loads(path.read_text())
        assert artifact["review"]["source_verification"] == "pending"
        assert row["compact_json_characters"] == len(evaluation.compact_json(artifact["compact"]))
        assert row["raw_json_characters"] == len(evaluation.encoded(artifact["raw"]))
        assert row["raw_minified_json_characters"] == len(evaluation.compact_json(artifact["raw"]))
        assert row["returned_count"] + row["omitted_count"] == row["matched_count"]
    with pytest.raises(ValueError, match="overwrite"):
        evaluation.bundle(evaluation.SUITE, output)


def test_scores_are_per_repeat_and_never_certify_draft_acceptance(evaluation, observations):
    path, _ = observations
    result = evaluation.score_activation(evaluation.SUITE, path)
    assert len(result["per_repeat"]) == 6
    assert result["all_evaluation_repeats_meet_targets"]
    assert result["minimum_three_repeats_met"]
    assert not result["acceptance_verified"]
    assert result["status"] == "independent_review_pending"
    for row in result["per_repeat"]:
        assert row["positive_cases"] == row["negative_cases"] == 10
        assert row["positive_activated"] == 10
        assert row["negative_activated"] == 0
        assert row["positive_wilson_95"] == evaluation.wilson(10, 10)


def test_exact_prospective_activation_thresholds(evaluation, observations):
    path, value = observations
    for row in value["observations"]:
        if row["repeat"] == 0 and row["case_id"] in ("activate-11", "activate-12"):
            row["tool_calls"] = []
        if row["repeat"] == 0 and row["case_id"] == "control-11":
            row["tool_calls"] = [{"name": "backendpro_search", "is_error": False}]
    path.write_text(json.dumps(value))
    result = evaluation.score_activation(evaluation.SUITE, path)
    assert result["all_evaluation_repeats_meet_targets"]
    assert result["evaluation_activation_rate_range"] == [0.8, 1.0]
    for row in value["observations"]:
        if row["repeat"] == 0 and row["case_id"] == "activate-13":
            row["tool_calls"] = []
    path.write_text(json.dumps(value))
    assert not evaluation.score_activation(evaluation.SUITE, path)["all_evaluation_repeats_meet_targets"]


@pytest.mark.parametrize("problem", ["missing", "client_error", "tool_error"])
def test_missing_and_failed_observations_cannot_pass(evaluation, observations, problem):
    path, value = observations
    row = next(row for row in value["observations"] if row["case_id"] == "activate-11")
    if problem == "missing":
        value["observations"].remove(row)
    elif problem == "client_error":
        row["status"] = "client_error"
    else:
        row["tool_calls"][0]["is_error"] = True
    path.write_text(json.dumps(value))
    result = evaluation.score_activation(evaluation.SUITE, path)
    assert not result["all_evaluation_repeats_meet_targets"]
    scored = next(row for row in result["per_repeat"] if row["split"] == "evaluation" and row["repeat"] == 0)
    assert scored[{"missing": "missing_observations", "client_error": "client_errors",
                   "tool_error": "failed_knowledge_calls"}[problem]] == 1


@pytest.mark.parametrize("problem", ["hash", "surface", "duplicate", "unknown_tool", "missing_calls", "repeat"])
def test_invalid_observations_are_rejected(evaluation, observations, problem):
    path, value = observations
    if problem == "hash":
        value["suite_sha256"] = "changed"
    elif problem == "surface":
        value["surface"] = "native"
    elif problem == "duplicate":
        value["observations"].append(value["observations"][0])
    elif problem == "unknown_tool":
        value["observations"][0]["tool_calls"][0]["name"] = "backendpro_misspelled"
    elif problem == "missing_calls":
        del value["observations"][0]["tool_calls"]
    else:
        value["observations"][0]["repeat"] = True
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        evaluation.score_activation(evaluation.SUITE, path)


def test_case_identifiers_cannot_escape_bundle_directory(evaluation, tmp_path):
    suite = json.loads(evaluation.SUITE.read_text())
    suite["retrieval"][0]["id"] = "../outside"
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite))
    with pytest.raises(ValueError, match="identifiers"):
        evaluation.bundle(path, tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()


def test_reviewed_suite_requires_separate_protocol(evaluation, tmp_path):
    suite = json.loads(evaluation.SUITE.read_text())
    suite["review_status"] = "approved"
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite))
    with pytest.raises(ValueError, match="separately locked protocol"):
        evaluation.load_suite(path)
