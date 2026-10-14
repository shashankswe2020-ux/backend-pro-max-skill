"""P0 gates use synthetic fixtures here, never advertised as model evidence."""
from __future__ import annotations

import copy
import importlib
import runpy
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = {"model": "fixture-only", "harness": "fixture", "harness_revision": "test", "parameters": {}}


@pytest.fixture
def p0(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return importlib.import_module("run_p0")


@pytest.fixture
def tasks():
    return runpy.run_path(str(ROOT / "benchmarks/p0/tasks.py"))["TASKS"]


@pytest.fixture
def frozen(p0, monkeypatch, tmp_path):
    def image(_):
        return (
            {"Id": "sha256:fixture", "Architecture": "arm64"},
            {"python": "3.12.13", "packages": {"pydantic": "2.14.0", "starlette": "1.7.0", "httpx": "0.28.1"}},
        )
    monkeypatch.setattr(p0, "inspect_image", image)
    root = tmp_path / "development"
    p0.freeze(root, "fixture", SETTINGS)
    return root


def save(p0, path, value):
    path.write_bytes(p0.m3.encode(value))
    return path


def review_for(p0, tasks, binding):
    return {
        "cohort_sha256": binding, "reviewer": "independent-fixture-reviewer",
        "rubric": "fixture-only", "reviewed_at": "2026-10-12", "independence_attested": True,
        "tasks": {t["id"]: {
            "requirements_discoverable": True, "sources_verified": True, "tests_verified": True,
            "usage_authorized": True, "rationale": "Synthetic unit test, not actual review",
        } for t in tasks},
    }


def grade_record(p0, root, task_id, files, passed, kind=None):
    manifest = p0.m3.load_frozen(root)
    return {
        "task_id": task_id, "suite_sha256": p0.m3.sha((root / "manifest.json").read_bytes()),
        "image_id": manifest["image_id"], "files_sha256": p0.digest(files),
        "candidate_sha256": p0.m3.sha(p0.bundle(files).encode()),
        "grader_sha256": manifest["files"][f"grading/{task_id}/check.py"],
        "status": "passed" if passed else "failed", "passed": passed,
        "kind": kind, "exit_code": 0 if passed else 1,
        "test_report": {"ran": 1, "passed": passed, "errors": 0, "failures": 0 if passed else 1},
    }


def calibration_input(p0, frozen, tmp_path, fraction=.5):
    schedule = [a for a in p0.read(frozen / "assignments.json") if a["arm"] == "baseline"]
    attempts = []
    for index, assigned in enumerate(schedule):
        identifier = assigned["task_id"]
        # Real collection would retain model-generated code, not references.
        files = p0.read(frozen / "grading" / identifier / "reference.json")
        candidate = save(p0, tmp_path / f"{assigned['id']}.candidate.json", files)
        passed = index % 10 < int(fraction * 10)
        artifact = save(p0, tmp_path / f"{assigned['id']}.grade.json",
                        grade_record(p0, frozen, identifier, files, passed))
        attempts.append({
            "id": assigned["id"], "status": "completed", "knowledge_calls": 0,
            "cost_micro_usd": 10, "input_tokens": 1, "output_tokens": 1, "seconds": .1,
            "grade_file": artifact.name, "grade_sha256": p0.m3.sha(artifact.read_bytes()),
            "candidate_file": candidate.name, "candidate_sha256": p0.m3.sha(candidate.read_bytes()),
        })
    return save(p0, tmp_path / "observations.json", {
        "protocol_sha256": p0.m3.sha((frozen / "optional.protocol.json").read_bytes()),
        "collection_kind": "model", "model_settings": SETTINGS, "attempts": attempts,
    })


def validation_summary(p0, frozen, tmp_path):
    output = tmp_path / "selftest"
    output.mkdir()
    manifest = p0.m3.load_frozen(frozen)
    artifacts = {}
    for task in manifest["tasks"]:
        identifier = task["id"]
        public = frozen / "agent" / identifier
        for kind in ("reference", "starter"):
            files = p0.read(frozen / "grading" / identifier / "reference.json") if kind == "reference" else {
                name: (public / name).read_text() for name in p0.read(public / "task.json")["editable_files"]
            }
            path = save(p0, output / f"{identifier}.{kind}.json",
                        grade_record(p0, frozen, identifier, files, kind == "reference", kind))
            artifacts[path.name] = p0.m3.sha(path.read_bytes())
    return save(p0, output / "summary.json", {
        "suite_sha256": p0.m3.sha((frozen / "manifest.json").read_bytes()),
        "status": "passed", "artifacts": artifacts,
    })


def test_corpus_is_multifile_balanced_and_honest_about_family_count(p0, tasks):
    p0.validate_tasks(tasks, "development")
    assert len(tasks) == 40
    assert Counter(t["track"] for t in tasks) == dict.fromkeys(p0.m3.TRACKS, 10)
    assert len({t["family"] for t in tasks}) == 8
    assert all(t["review_status"] == "pending_independent_review" for t in tasks)
    assert all(sum(t["starter"][k] != v for k, v in t["reference"].items()) >= 2 for t in tasks)
    assert all(not t["source_urls"] for t in tasks if t["track"] == "control")


def test_frozen_agent_exports_exclude_gold(p0, frozen):
    manifest = p0.m3.load_frozen(frozen)
    assert len(manifest["tasks"]) == 40
    assert not manifest["paid_generation_authorized"]
    for task in manifest["tasks"]:
        folder = frozen / "agent" / task["id"]
        public = p0.read(folder / "task.json")
        assert set(p.name for p in folder.iterdir()) == set(public["editable_files"]) | {"task.json"}
        assert not {"checks", "reference", "source_urls", "family"} & public.keys()
    assert len(p0.read(frozen / "assignments.json")) == 480
    for policy in ("optional", "required"):
        protocol = p0.read(frozen / f"{policy}.protocol.json")
        assert protocol["seed"] == p0.SEED
        assert protocol["model_settings"] == SETTINGS
        assert "cluster" in protocol["analysis"]["unit"]


def test_frozen_artifacts_cannot_be_reused_or_tampered(p0, frozen):
    with pytest.raises(ValueError, match="already exists"):
        p0.freeze(frozen, "fixture")
    (frozen / "agent/ledger-01/app.py").write_text("modified")
    with pytest.raises(ValueError, match="changed"):
        p0.m3.load_frozen(frozen)


@pytest.mark.parametrize("path", ["../app.py", "/app.py", "a/../../app.py", "a//b.py", "a\\b.py", "x.json"])
def test_candidate_paths_cannot_escape(p0, path):
    with pytest.raises(ValueError, match="Invalid Python file"):
        p0.file_map({"app.py": "", path: ""})


def test_multifile_grading_reuses_isolated_m3_transport(p0, frozen, monkeypatch):
    calls = []
    files = p0.read(frozen / "grading/ledger-01/reference.json")
    def grade(root, task_id, candidate):
        calls.append((root, task_id, candidate.read_text(), candidate))
        return {"passed": True}
    monkeypatch.setattr(p0.m3, "grade", grade)
    result = p0.grade(frozen, "ledger-01", files)
    assert result["files_sha256"] == p0.digest(files)
    assert calls[0][2] == p0.bundle(files)
    assert not calls[0][3].exists()
    with pytest.raises(ValueError, match="exactly"):
        p0.grade(frozen, "ledger-01", {"app.py": ""})


def test_heldout_import_rejects_family_leakage_and_self_review(p0, frozen, tasks, tmp_path):
    evaluation = copy.deepcopy(tasks)
    for task in evaluation:
        task["split"] = "evaluation"
        task["author"] = "external-author"
    cohort = save(p0, tmp_path / "cohort.json", evaluation)
    review = save(p0, tmp_path / "review.json", review_for(p0, evaluation, p0.m3.sha(cohort.read_bytes())))
    with pytest.raises(ValueError, match="overlap"):
        p0.heldout_tasks(cohort, frozen, review)
    for task in evaluation:
        task["id"] = "eval-" + task["id"]
        task["repository"] = "eval-" + task["repository"]
        task["family"] = "eval-" + task["family"]
    save(p0, cohort, evaluation)
    save(p0, review, review_for(p0, evaluation, p0.m3.sha(cohort.read_bytes())))
    with pytest.raises(ValueError, match="Renamed"):
        p0.heldout_tasks(cohort, frozen, review)
    reviewed = review_for(p0, tasks, "binding")
    reviewed["reviewer"] = tasks[0]["author"]
    with pytest.raises(ValueError, match="Independent"):
        p0.validate_review(reviewed, "binding", tasks)


def test_review_requires_full_coverage_and_hash_binding(p0, tasks):
    reviewed = review_for(p0, tasks, "binding")
    with pytest.raises(ValueError, match="bound"):
        p0.validate_review(reviewed, "changed", tasks)
    reviewed["tasks"].pop(tasks[0]["id"])
    with pytest.raises(ValueError, match="every"):
        p0.validate_review(reviewed, "binding", tasks)


def test_calibration_tracks_variants_and_counts_all_assignments(p0, frozen, tmp_path):
    path = calibration_input(p0, frozen, tmp_path)
    result = p0.calibration(frozen, path)
    assert result["assigned"] == 120
    assert result["family_clusters"] == 6
    assert result["status"] == "headroom_observed"
    assert sum(t["assigned"] for t in result["tracks"].values()) == 120
    assert result == p0.calibration(frozen, path)
    assert result["cost_micro_usd"] == 1200


@pytest.mark.parametrize("fraction", [0, 1])
def test_floor_and_ceiling_do_not_establish_headroom(p0, frozen, tmp_path, fraction):
    result = p0.calibration(frozen, calibration_input(p0, frozen, tmp_path, fraction))
    assert result["status"] == "blocked"


@pytest.mark.parametrize("change", ["missing", "duplicate", "fixture", "settings", "retrieval", "negative_cost", "nan"])
def test_invalid_calibration_is_rejected(p0, frozen, tmp_path, change):
    path = calibration_input(p0, frozen, tmp_path)
    value = p0.read(path)
    if change == "missing":
        value["attempts"].pop()
    elif change == "duplicate":
        value["attempts"][1] = value["attempts"][0]
    elif change == "fixture":
        value["collection_kind"] = "fixture"
    elif change == "settings":
        value["model_settings"] = {}
    elif change == "retrieval":
        value["attempts"][0]["knowledge_calls"] = 1
    elif change == "negative_cost":
        value["attempts"][0]["cost_micro_usd"] = -1
    else:
        value["attempts"][0]["seconds"] = float("nan")
    save(p0, path, value)
    with pytest.raises(ValueError):
        p0.calibration(frozen, path)


def test_provider_failure_is_retained_but_blocks_headroom(p0, frozen, tmp_path):
    path = calibration_input(p0, frozen, tmp_path)
    value = p0.read(path)
    value["attempts"][0]["status"] = "provider_error"
    save(p0, path, value)
    result = p0.calibration(frozen, path)
    assert result["assigned"] == 120
    assert result["status"] == "blocked"
    assert not result["infrastructure_complete"]


def test_grade_tampering_is_rejected_even_when_outer_hash_is_updated(p0, frozen, tmp_path):
    path = calibration_input(p0, frozen, tmp_path)
    value = p0.read(path)
    row = value["attempts"][0]
    artifact = tmp_path / row["grade_file"]
    grade = p0.read(artifact)
    grade["test_report"]["ran"] = 0
    save(p0, artifact, grade)
    row["grade_sha256"] = p0.m3.sha(artifact.read_bytes())
    save(p0, path, value)
    with pytest.raises(ValueError, match="Invalid grader"):
        p0.calibration(frozen, path)


def test_readiness_does_not_claim_external_work_is_done(p0, frozen, tmp_path):
    summary = validation_summary(p0, frozen, tmp_path)
    result = p0.readiness(frozen, summary)
    assert result["reference_starter_validation"]
    assert result["status"] == "blocked"
    assert set(result["blockers"]) == {
        "independent_task_source_review", "authorized_development_baseline_calibration",
        "separate_independently_authored_evaluation_cohort",
    }
    assert not result["paid_generation_authorized"]


def test_readiness_recomputes_calibration_not_just_status(p0, frozen, tmp_path):
    summary = validation_summary(p0, frozen, tmp_path)
    observations = calibration_input(p0, frozen, tmp_path)
    report = save(p0, tmp_path / "calibration.json", p0.calibration(frozen, observations))
    assert "authorized_development_baseline_calibration" not in p0.readiness(frozen, summary, report)["blockers"]
    data = p0.read(report)
    data["resolved"] += 1
    save(p0, report, data)
    with pytest.raises(ValueError, match="reproduce"):
        p0.readiness(frozen, summary, report)


def test_pending_external_access_is_fail_closed(p0):
    for identifier in ("contextbench", "swe-context-bench", "swe-bench-verified"):
        with pytest.raises(ValueError, match="pending"):
            p0.check_access(ROOT / "benchmarks/p0/benchmark-access.json", [identifier])


def test_historical_empty_causes_remain_unknown(p0):
    report = p0.historical_audit(ROOT / "benchmarks/m3/results/2026-10-11/retrieval-summary.json")
    assert report["empty_calls"] == 21
    assert report["cause_counts"] == {"unknown": 21}
    assert sum(report["by_track"].values()) == 21


def test_diagnosis_requires_output_binding_and_supporting_artifacts(p0, tmp_path):
    workflow = p0.m3.RetrievalWorkflow("optional", "backendpro")
    event = workflow.retrieve("search", {"query": "x"}, lambda *_: {"results": []}, "offline_fixture")
    observations = save(p0, tmp_path / "observations.json", {
        "attempts": [{"id": "example.backendpro.r1", "trace": [{"event": event}]}],
    })
    assert p0.diagnose(observations)["counts"] == {"unknown": 1}
    evidence = save(p0, tmp_path / "source-check.json", {"note": "Fixture scope inspection"})
    review = save(p0, tmp_path / "review.json", {
        "observations_sha256": p0.m3.sha(observations.read_bytes()),
        "reviewer": "fixture", "rubric": "p0-v1",
        "events": {"example.backendpro.r1:0": {
            "cause": "scope_error", "output_sha256": event["output_sha256"],
            "rationale": "Fixture query was scoped incorrectly",
            "evidence": [{"path": evidence.name, "sha256": p0.m3.sha(evidence.read_bytes())}],
        }},
    })
    assert p0.diagnose(observations, review)["counts"] == {"scope_error": 1}
    evidence.write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        p0.diagnose(observations, review)


def test_source_output_tampering_is_not_diagnosed(p0, tmp_path):
    workflow = p0.m3.RetrievalWorkflow("optional", "backendpro")
    event = workflow.retrieve("search", {"query": "x"}, lambda *_: {"results": []}, "offline_fixture")
    event["output"] = "{}"
    path = save(p0, tmp_path / "observations.json", {
        "attempts": [{"id": "x", "trace": [{"event": event}]}],
    })
    with pytest.raises(ValueError, match="hash mismatch"):
        p0.diagnose(path)


def test_evaluation_intake_and_readiness_require_matching_calibration(p0, frozen, tasks, tmp_path):
    # Synthetic disjoint four-track intake exercises contracts, not independence.
    evaluation = []
    for track in p0.m3.TRACKS:
        task = copy.deepcopy(next(t for t in tasks if t["track"] == track))
        task.update(id="eval-" + task["id"], repository="eval-" + task["repository"],
                    family="eval-" + task["family"], author="external-fixture", split="evaluation")
        for kind in ("reference", "starter"):
            task[kind]["app.py"] += "\nFIXTURE_INTAKE = True\n"
        evaluation.append(task)
    cohort = save(p0, tmp_path / "evaluation.json", evaluation)
    review = save(p0, tmp_path / "evaluation-review.json",
                  review_for(p0, evaluation, p0.m3.sha(cohort.read_bytes())))
    destination = tmp_path / "evaluation-frozen"
    manifest = p0.freeze(destination, "fixture", SETTINGS, cohort, frozen, review)
    assert manifest["split"] == "evaluation"
    observations = calibration_input(p0, frozen, tmp_path)
    calibrated = save(p0, tmp_path / "calibration.json", p0.calibration(frozen, observations))
    validation = validation_summary(p0, destination, tmp_path)
    result = p0.readiness(destination, validation, calibrated, development=frozen)
    assert result["status"] == "ready_for_budget_review"
    assert result["blockers"] == []
    assert not result["paid_generation_authorized"]
    with pytest.raises(ValueError, match="development-only"):
        p0.calibration(destination, observations)
    with pytest.raises(ValueError, match="outside the repository"):
        p0.freeze(ROOT / "benchmarks/p0/private-test", "fixture", SETTINGS, cohort, frozen, review)


@pytest.mark.parametrize("gate", ["requirements_discoverable", "sources_verified", "tests_verified", "usage_authorized"])
def test_review_false_gates_cannot_pass(p0, tasks, gate):
    review = review_for(p0, tasks, "binding")
    review["tasks"][tasks[0]["id"]][gate] = False
    with pytest.raises(ValueError, match="Review gate pending"):
        p0.validate_review(review, "binding", tasks)


def test_verified_access_requires_immutable_revision(p0, tmp_path):
    record = {
        "id": "fixture", "availability": "verified", "usage_authorized": True,
        "license": "MIT", "license_url": "https://example.org/LICENSE",
        "revision": "a" * 40, "reviewer": "fixture", "verified_at": "2026-10-12",
        "permitted_use": "unit-test only",
    }
    path = save(p0, tmp_path / "access.json", [record])
    assert p0.check_access(path, ["fixture"])["selected"] == ["fixture"]
    record["revision"] = "main"
    save(p0, path, [record])
    with pytest.raises(ValueError, match="Immutable"):
        p0.check_access(path, ["fixture"])


def test_candidate_and_support_artifacts_cannot_escape(p0, tmp_path):
    inside = tmp_path / "inside"
    inside.mkdir()
    outside = save(p0, tmp_path / "outside.json", {})
    with pytest.raises(ValueError, match="escapes"):
        p0.bound_artifact(inside, "../outside.json", p0.m3.sha(outside.read_bytes()))
    link = inside / "link.json"
    link.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        p0.bound_artifact(inside, "link.json", p0.m3.sha(outside.read_bytes()))


@pytest.mark.parametrize("resolved,expected", [(26, "blocked"), (27, "headroom_observed"),
                                              (72, "headroom_observed"), (73, "blocked")])
def test_exact_substantive_headroom_boundaries(p0, frozen, tmp_path, resolved, expected):
    path = calibration_input(p0, frozen, tmp_path)
    value = p0.read(path)
    schedule = {a["id"]: a for a in p0.read(frozen / "assignments.json")}
    seen = 0
    for row in value["attempts"]:
        assignment = schedule[row["id"]]
        passed = assignment["track"] == "control"
        if assignment["track"] != "control":
            passed = seen < resolved
            seen += 1
        files = p0.read(tmp_path / row["candidate_file"])
        artifact = save(p0, tmp_path / row["grade_file"],
                        grade_record(p0, frozen, assignment["task_id"], files, passed))
        row["grade_sha256"] = p0.m3.sha(artifact.read_bytes())
    save(p0, path, value)
    result = p0.calibration(frozen, path)
    assert seen == 90
    assert result["substantive_resolved_fraction"] == resolved / 90
    assert result["tracks"]["control"]["resolved"] == 30
    assert result["status"] == expected
