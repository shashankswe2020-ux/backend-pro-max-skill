"""Offline P0 cohort preparation and readiness gates; never calls model providers."""
from __future__ import annotations

import argparse
import base64
import json
import math
import random
import re
import runpy
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath

import run_m3 as m3

ROOT = m3.ROOT
SOURCE = ROOT / "benchmarks/p0"
SEED = "backendpro-p0-v1"
inspect_image = m3.image_environment
CAUSES = (
    "scope_error", "corpus_gap", "lexical_miss", "rank_miss",
    "packing_loss", "version_mismatch", "evidence_misapplication",
    "appropriate_abstention", "no_failure", "unknown",
)


def read(path: Path):
    return json.loads(path.read_bytes())


def digest(value) -> str:
    return m3.sha(m3.encode(value))


def require_text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Nonempty {field} required")
    return value


def file_map(files: dict) -> dict:
    if not isinstance(files, dict) or not files or len(files) > 64 or "app.py" not in files:
        raise ValueError("Candidate needs app.py and at most 64 Python files")
    for name, text in files.items():
        path = PurePosixPath(name)
        if (
            path.is_absolute() or str(path) != name or ".." in path.parts
            or not re.fullmatch(r"(?:[A-Za-z_]\w*/)*[A-Za-z_]\w*\.py", name, flags=re.ASCII)
            or not isinstance(text, str)
        ):
            raise ValueError(f"Invalid Python file: {name}")
    if len(m3.encode(files)) > m3.MAX_CANDIDATE_BYTES:
        raise ValueError("Candidate exceeds source-size limit")
    return dict(sorted(files.items()))


def bundle(files: dict) -> str:
    """Adapt a multi-file submission to the existing isolated M3 grader."""
    encoded = base64.b64encode(m3.encode(file_map(files))).decode()
    return (
        "import base64, json, pathlib, sys\n"
        f"_files = json.loads(base64.b64decode({encoded!r}))\n"
        "_root = pathlib.Path('/tmp/p0_workspace')\n"
        "for _name, _source in _files.items():\n"
        "    _path = _root / _name\n"
        "    _path.parent.mkdir(parents=True, exist_ok=True)\n"
        "    _path.write_text(_source, encoding='utf-8')\n"
        "sys.path.insert(0, str(_root))\n"
        "from app import *\n"
    )


def validate_tasks(tasks: list[dict], split: str) -> None:
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Nonempty cohort required")
    identifiers = set()
    for task in tasks:
        identifier = require_text(task.get("id"), "task id")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", identifier) or identifier in identifiers:
            raise ValueError("Invalid or duplicate task id")
        identifiers.add(identifier)
        for field in ("repository", "family", "author", "problem", "license", "checks"):
            require_text(task.get(field), field)
        if task.get("split") != split or task.get("track") not in m3.TRACKS:
            raise ValueError("Invalid task split or track")
        if not isinstance(task.get("source_urls"), list) or any(
            not isinstance(url, str) or not url.startswith("https://") for url in task["source_urls"]
        ):
            raise ValueError("Explicit HTTPS source list required")
        if task["track"] != "control" and not task["source_urls"]:
            raise ValueError("Non-control tasks require source references")
        reference, starter = file_map(task["reference"]), file_map(task["starter"])
        if reference.keys() != starter.keys() or sum(reference[k] != starter[k] for k in reference) < 2:
            raise ValueError("Each task requires seeded faults in at least two files")
        for files in (reference, starter):
            if len(bundle(files).encode()) > m3.MAX_CANDIDATE_BYTES:
                raise ValueError("Bundled candidate exceeds M3 grading limit")
            for name, source in files.items():
                compile(source, name, "exec")
        compile(m3.grader_source(task["checks"]), "check.py", "exec")
    counts = Counter(task["track"] for task in tasks)
    if set(counts) != set(m3.TRACKS):
        raise ValueError("All four tracks are required")
    if split == "development" and not 40 <= len(tasks) <= 60:
        raise ValueError("Development cohort must contain 40-60 tasks")


def validate_review(review: dict, binding: str, tasks: list[dict]) -> None:
    if review.get("cohort_sha256") != binding:
        raise ValueError("Review is not bound to this cohort")
    reviewer = require_text(review.get("reviewer"), "reviewer")
    require_text(review.get("rubric"), "review rubric")
    require_text(review.get("reviewed_at"), "review date")
    if review.get("independence_attested") is not True or reviewer in {t["author"] for t in tasks}:
        raise ValueError("Independent reviewer attestation required")
    if set(review.get("tasks", {})) != {t["id"] for t in tasks}:
        raise ValueError("Review must cover every assigned task")
    for item in review["tasks"].values():
        for field in ("requirements_discoverable", "sources_verified", "tests_verified", "usage_authorized"):
            if item.get(field) is not True:
                raise ValueError(f"Review gate pending: {field}")
        require_text(item.get("rationale"), "review rationale")


def heldout_tasks(cohort: Path, development: Path, review_path: Path) -> list[dict]:
    tasks = read(cohort)
    validate_tasks(tasks, "evaluation")
    dev = m3.load_frozen(development)
    if dev.get("split") != "development":
        raise ValueError("Development snapshot required")
    for field in ("id", "repository", "family"):
        if {t[field] for t in tasks} & {t[field] for t in dev["tasks"]}:
            raise ValueError(f"Development/evaluation overlap: {field}")
    if {t["author"] for t in tasks} & {t["author"] for t in dev["tasks"]}:
        raise ValueError("Held-out tasks need independent authors")
    dev_content = {t["reference_sha256"] for t in dev["tasks"]}
    if any(digest(file_map(t["reference"])) in dev_content for t in tasks):
        raise ValueError("Renamed development reference in evaluation cohort")
    validate_review(read(review_path), m3.sha(cohort.read_bytes()), tasks)
    return tasks


def freeze(output: Path, image: str, settings: dict | None = None, cohort: Path | None = None,
           development: Path | None = None, review_path: Path | None = None) -> dict:
    if output.exists():
        raise ValueError("Frozen output already exists")
    if cohort is None:
        if development is not None or review_path is not None:
            raise ValueError("Review/development arguments require an evaluation cohort")
        tasks = runpy.run_path(str(SOURCE / "tasks.py"))["TASKS"]
        split = "development"
        validate_tasks(tasks, split)
    else:
        if development is None or review_path is None:
            raise ValueError("Evaluation freeze requires development snapshot and independent review")
        tasks = heldout_tasks(cohort, development, review_path)
        split = "evaluation"
        repo = ROOT.resolve()
        if repo == output.resolve() or repo in output.resolve().parents:
            raise ValueError("Held-out exports must stay outside the repository")
    if settings is not None:
        for field in ("model", "harness", "harness_revision"):
            require_text(settings.get(field), field)
        if not isinstance(settings.get("parameters"), dict):
            raise ValueError("Explicit model parameters required")
    info, environment = inspect_image(image)
    output.mkdir(parents=True)
    metadata = []
    for task in tasks:
        public, private = output / "agent" / task["id"], output / "grading" / task["id"]
        public.mkdir(parents=True)
        private.mkdir(parents=True)
        for name, source in task["starter"].items():
            path = public / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
        m3.write_new(public / "task.json", {
            "id": task["id"], "problem": task["problem"], "entrypoint": "app.py",
            "editable_files": sorted(task["starter"]), "environment": environment,
        })
        m3.write_new(private / "reference.json", file_map(task["reference"]))
        (private / "check.py").write_text(m3.grader_source(task["checks"]), encoding="utf-8")
        metadata.append({
            **{key: task[key] for key in (
                "id", "track", "repository", "family", "author", "source_urls", "license",
            )},
            "reference_sha256": digest(file_map(task["reference"])),
            "starter_sha256": digest(file_map(task["starter"])),
            "review_status": "reviewed_attestation" if cohort else "pending_independent_review",
        })
    for policy in ("optional", "required"):
        protocol = m3.protocol(policy, metadata, settings["model"] if settings else None)
        protocol.update(
            id=f"{SEED}-{split}-{policy}", seed=SEED, schedule_seed=m3.SEED, split=split,
            status="frozen_pending_readiness", model_settings=settings,
            primary_outcome="All assigned task outcomes; repository/family clusters, not independent variants.",
            practical_effect_threshold_percentage_points=5,
            required_boundary="Before first code edit or finish; local read-only inspection may precede retrieval.",
            limitations=[
                "Development cases share repository/family fixtures; variants are not independent repositories."
                if split == "development" else "Independent authorship and review are attested, not identity-certified.",
                "Difficulty and coding benefit are unmeasured until an authorized model calibration is imported.",
                "Review attestations are validated structurally, not proof of reviewer identity.",
                "Offline preparation does not authorize model execution or spending.",
            ],
        )
        protocol["limits"].update(model_turns=40, output_tokens_per_turn=4096, generation_seconds=1200)
        protocol["analysis"]["unit"] = "repository/family cluster; report correlated cases explicitly"
        m3.write_new(output / f"{policy}.protocol.json", protocol)
    m3.write_new(output / "assignments.json", m3.assignments(metadata))
    m3.write_new(output / "tools.json", m3.generate())
    m3.write_new(output / "benchmark-access.json", read(SOURCE / "benchmark-access.json"))
    if review_path:
        m3.write_new(output / "cohort-review.json", read(review_path))
    manifest = {
        "format": SEED, "split": split, "status": "frozen_pending_readiness",
        "tasks": metadata, "image_id": info["Id"], "architecture": info["Architecture"],
        "environment": environment, "model_runs": 0, "paid_generation_authorized": False,
        "cohort_sha256": m3.sha(cohort.read_bytes()) if cohort else digest(tasks),
        "development_sha256": m3.sha((development / "manifest.json").read_bytes()) if development else None,
        "files": {str(p.relative_to(output)): m3.sha(p.read_bytes())
                  for p in sorted(output.rglob("*")) if p.is_file()},
        "source_sha256": {
            str(p.relative_to(ROOT)): m3.sha(p.read_bytes())
            for p in [Path(__file__), Path(m3.__file__), SOURCE / "tasks.py",
                      SOURCE / "benchmark-access.json", *sorted((ROOT / "src/backend-pro-max/scripts").glob("*.py")),
                      *sorted((ROOT / "src/backend-pro-max/data").rglob("*.csv")),
                      ROOT / "benchmarks/m3/environment/Dockerfile",
                      ROOT / "benchmarks/m3/environment/requirements.txt"]
        },
    }
    m3.write_new(output / "manifest.json", manifest)
    return manifest


def grade(root: Path, task_id: str, files: dict) -> dict:
    manifest = m3.load_frozen(root)
    if task_id not in {t["id"] for t in manifest["tasks"]}:
        raise ValueError("Unknown task")
    files = file_map(files)
    public = read(root / "agent" / task_id / "task.json")
    if set(files) != set(public["editable_files"]):
        raise ValueError("Candidate must contain exactly the declared editable files")
    with tempfile.TemporaryDirectory(prefix="backendpro-p0-") as temporary:
        candidate = Path(temporary) / "solution.py"
        candidate.write_text(bundle(files), encoding="utf-8")
        result = m3.grade(root, task_id, candidate)
    result.update(
        files_sha256=digest(files),
        file_sha256={name: m3.sha(text.encode()) for name, text in files.items()},
    )
    return result


def self_test(root: Path, output: Path) -> dict:
    manifest = m3.load_frozen(root)
    if output.exists():
        raise ValueError("Self-test output already exists")
    output.mkdir(parents=True)
    results = []
    for task in manifest["tasks"]:
        public = root / "agent" / task["id"]
        paths = read(public / "task.json")["editable_files"]
        for kind, files in (
            ("reference", read(root / "grading" / task["id"] / "reference.json")),
            ("starter", {name: (public / name).read_text(encoding="utf-8") for name in paths}),
        ):
            result = {**grade(root, task["id"], files), "kind": kind}
            m3.write_new(output / f"{task['id']}.{kind}.json", result)
            results.append(result)
            print(task["id"], kind, result["status"], flush=True)
    report = {
        "status": "passed" if all(
            r["status"] == ("passed" if r["kind"] == "reference" else "failed") for r in results
        ) else "failed",
        "suite_sha256": m3.sha((root / "manifest.json").read_bytes()),
        "reference_passed": sum(r["kind"] == "reference" and r["passed"] for r in results),
        "starter_failed": sum(r["kind"] == "starter" and r["status"] == "failed" for r in results),
        "model_attempts": 0, "independent_review": "pending",
        "artifacts": {p.name: m3.sha(p.read_bytes()) for p in sorted(output.glob("*.json"))},
    }
    m3.write_new(output / "summary.json", report)
    return report


def bound_artifact(base: Path, name: str, expected: str) -> dict:
    if not isinstance(name, str) or not name or not isinstance(expected, str):
        raise ValueError("Artifact path and hash required")
    path = base / name
    if path.is_symlink() or base.resolve() not in path.resolve().parents:
        raise ValueError("Artifact path escapes observation directory")
    if m3.sha(path.read_bytes()) != expected:
        raise ValueError(f"Artifact hash mismatch: {name}")
    return read(path)


def validate_grade(result: dict, manifest: dict, suite_hash: str, task_id: str, files_hash: str) -> None:
    if (
        result.get("task_id") != task_id or result.get("suite_sha256") != suite_hash
        or result.get("image_id") != manifest["image_id"]
        or result.get("grader_sha256") != manifest["files"][f"grading/{task_id}/check.py"]
        or result.get("files_sha256") != files_hash
        or not isinstance(files_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", files_hash)
        or result.get("status") not in ("passed", "failed", "timeout", "invalid_report")
        or result.get("passed") is not (result.get("status") == "passed")
    ):
        raise ValueError("Grade binding mismatch")
    if result["status"] in ("passed", "failed"):
        report = result.get("test_report")
        if (
            not isinstance(report, dict) or type(report.get("ran")) is not int or report["ran"] != 1
            or report.get("passed") is not result["passed"]
            or type(report.get("errors")) is not int or report["errors"] < 0
            or type(report.get("failures")) is not int or report["failures"] < 0
            or report["passed"] != (report["errors"] == report["failures"] == 0)
            or result.get("exit_code") != (0 if result["passed"] else 1)
        ):
            raise ValueError("Invalid grader result")


def calibration(root: Path, observations: Path) -> dict:
    manifest = m3.load_frozen(root)
    if manifest.get("split") != "development":
        raise ValueError("Difficulty calibration is development-only")
    data = read(observations)
    protocol_path = root / "optional.protocol.json"
    protocol = read(protocol_path)
    if data.get("protocol_sha256") != m3.sha(protocol_path.read_bytes()):
        raise ValueError("Calibration protocol mismatch")
    if not protocol["model_settings"] or data.get("model_settings") != protocol["model_settings"]:
        raise ValueError("Pinned model/harness settings required")
    if data.get("collection_kind") != "model":
        raise ValueError("Fixture results cannot establish baseline headroom")
    expected = {a["id"]: a for a in read(root / "assignments.json") if a["arm"] == "baseline"}
    attempts = data.get("attempts")
    if not isinstance(attempts, list) or len(attempts) != len(expected):
        raise ValueError("Calibration must retain every assigned baseline attempt")
    seen, results = set(), []
    for row in attempts:
        identifier = row["id"]
        if identifier not in expected or identifier in seen:
            raise ValueError("Unknown or duplicate baseline assignment")
        seen.add(identifier)
        if row.get("status") not in ("completed", "time_limit", "provider_error", "not_started"):
            raise ValueError("Unknown calibration outcome")
        if type(row.get("knowledge_calls")) is not int or row["knowledge_calls"] != 0:
            raise ValueError("Baseline calibration must not use knowledge tools")
        for field in ("cost_micro_usd", "input_tokens", "output_tokens"):
            if type(row.get(field)) is not int or row[field] < 0:
                raise ValueError(f"Invalid calibration accounting: {field}")
        seconds = row.get("seconds")
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Invalid calibration duration")
        passed = False
        if row["status"] == "completed":
            result = bound_artifact(observations.parent, row["grade_file"], row["grade_sha256"])
            task_id = expected[identifier]["task_id"]
            files = file_map(bound_artifact(observations.parent, row["candidate_file"], row["candidate_sha256"]))
            if set(files) != set(read(root / "agent" / task_id / "task.json")["editable_files"]):
                raise ValueError("Calibration candidate does not match editable files")
            validate_grade(result, manifest, m3.sha((root / "manifest.json").read_bytes()), task_id, digest(files))
            if result["candidate_sha256"] != m3.sha(bundle(files).encode()):
                raise ValueError("Candidate wrapper binding mismatch")
            passed = result["status"] == "passed"
            if result["status"] in ("timeout", "invalid_report"):
                row = {**row, "status": "grading_error"}
        results.append({**expected[identifier], "status": row["status"], "passed": passed})
    counts = {}
    for track in m3.TRACKS:
        rows = [r for r in results if r["track"] == track]
        counts[track] = {"assigned": len(rows), "resolved": sum(r["passed"] for r in rows)}
    substantive = [r for r in results if r["track"] != "control"]
    rate = sum(r["passed"] for r in substantive) / len(substantive)
    complete = all(r["status"] in ("completed", "time_limit") for r in results)
    families = {t["id"]: (t["repository"], t["family"]) for t in manifest["tasks"]}
    groups = {}
    for row in substantive:
        groups.setdefault(families[row["task_id"]], []).append(row["passed"])
    rng = random.Random(SEED)
    clusters = list(groups.values())
    samples = []
    for _ in range(2000):
        sample = [outcome for group in rng.choices(clusters, k=len(clusters)) for outcome in group]
        samples.append(sum(sample) / len(sample))
    samples.sort()
    return {
        "status": "headroom_observed" if complete and .30 <= rate <= .80 else "blocked",
        "suite_sha256": m3.sha((root / "manifest.json").read_bytes()),
        "observations_sha256": m3.sha(observations.read_bytes()),
        "observations_file": observations.name,
        "model_settings": protocol["model_settings"], "tracks": counts,
        "assigned": len(results), "resolved": sum(r["passed"] for r in results),
        "substantive_resolved_fraction": rate, "headroom_range": [.30, .80],
        "family_clusters": len(groups), "cluster_bootstrap_95": [samples[49], samples[1949]],
        "infrastructure_complete": complete, "attempts": results,
        "cost_micro_usd": sum(r["cost_micro_usd"] for r in attempts),
        "limitations": [
            "Submitted model observations are hash-bound, not independently certified collector identity.",
            "Headroom is assessed on non-control development tasks only; all four tracks remain reported.",
            "A small number of related families limits generalization; this is not comparative inference.",
            "Never select or remove evaluation tasks based on these outcomes.",
        ],
    }


def diagnose(observations: Path, reviews: Path | None = None) -> dict:
    """Annotate existing M3 trace artifacts without rewriting the original run."""
    data = read(observations)
    supplied = read(reviews) if reviews else None
    if supplied:
        if supplied.get("observations_sha256") != m3.sha(observations.read_bytes()):
            raise ValueError("Diagnosis review belongs to different observations")
        require_text(supplied.get("reviewer"), "diagnosis reviewer")
        require_text(supplied.get("rubric"), "diagnosis rubric")
    reviewed = supplied.get("events", {}) if supplied else {}
    events = {}
    for attempt in data["attempts"]:
        for index, action in enumerate(attempt["trace"]):
            if "event" not in action:
                continue
            event = action["event"]
            identifier = f"{attempt['id']}:{index}"
            if identifier in events:
                raise ValueError("Duplicate trace identity")
            raw = json.dumps(event["payload"], ensure_ascii=False, separators=(",", ":"))
            if m3.sha(raw.encode()) != event["payload_sha256"] or m3.sha(event["output"].encode()) != event["output_sha256"]:
                raise ValueError("Retrieval payload/output hash mismatch")
            label = reviewed.get(identifier, {})
            cause = label.get("cause", "unknown")
            if cause not in CAUSES:
                raise ValueError("Unknown failure taxonomy label")
            if label:
                if label.get("output_sha256") != event["output_sha256"]:
                    raise ValueError("Diagnosis does not bind model-visible output")
                require_text(label.get("rationale"), "diagnosis rationale")
                if cause != "unknown":
                    evidence = label.get("evidence")
                    if not isinstance(evidence, list) or not evidence:
                        raise ValueError("A diagnosed cause needs supporting artifacts")
                    for item in evidence:
                        bound_artifact(reviews.parent, item["path"], item["sha256"])
            events[identifier] = {
                "provider": event["provider"], "arguments": event["arguments"],
                "output_sha256": event["output_sha256"], "payload_sha256": event["payload_sha256"],
                "retrieval_status": m3.describe_payload(event["payload"])["status"],
                "delivered_to_model": action.get("delivered_to_model"),
                "truncated": event["truncated"], "cause": cause,
                "rationale": label.get("rationale", "Not independently diagnosed"),
            }
    if set(reviewed) - set(events):
        raise ValueError("Review includes unknown trace events")
    return {
        "observations_sha256": m3.sha(observations.read_bytes()),
        "review_sha256": m3.sha(reviews.read_bytes()) if reviews else None,
        "counts": dict(Counter(e["cause"] for e in events.values())), "events": events,
        "retrieval_quality_claim_supported": False,
    }


def historical_audit(summary: Path) -> dict:
    data = read(summary)
    count = data["providers"]["backendpro"]["empty"]
    return {
        "source_sha256": m3.sha(summary.read_bytes()), "empty_calls": count,
        "cause_counts": {"unknown": count},
        "status": "raw_observations_not_supplied",
        "reason": "Published aggregates do not identify root causes. Supply retained observations to diagnose.",
        "by_track": data["backendpro_empty_by_track"],
    }


def readiness(root: Path, validation: Path, calibration_path: Path | None = None,
              review_path: Path | None = None, development: Path | None = None) -> dict:
    manifest = m3.load_frozen(root)
    suite_hash = m3.sha((root / "manifest.json").read_bytes())
    checks = read(validation)
    if checks.get("suite_sha256") != suite_hash:
        raise ValueError("Self-test belongs to a different snapshot")
    expected_artifacts = {f"{t['id']}.{kind}.json" for t in manifest["tasks"] for kind in ("reference", "starter")}
    if set(checks.get("artifacts", {})) != expected_artifacts:
        raise ValueError("Self-test must include every reference and starter")
    verified = True
    for name, hash_value in checks["artifacts"].items():
        item = bound_artifact(validation.parent, name, hash_value)
        kind = "reference" if name.endswith(".reference.json") else "starter"
        task = next(t for t in manifest["tasks"] if name == f"{t['id']}.{kind}.json")
        if item.get("kind") != kind:
            raise ValueError("Self-test kind mismatch")
        validate_grade(item, manifest, suite_hash, task["id"], task[f"{kind}_sha256"])
        verified &= item["status"] == ("passed" if item["kind"] == "reference" else "failed")
    blockers = []
    if not verified or checks.get("status") != "passed":
        blockers.append("reference_or_starter_validation")
    if review_path:
        validate_review(read(review_path), manifest["cohort_sha256"], manifest["tasks"])
    elif manifest["split"] != "evaluation":
        blockers.append("independent_task_source_review")
    if calibration_path:
        calibrated = read(calibration_path)
        expected_suite = suite_hash if manifest["split"] == "development" else manifest["development_sha256"]
        if calibrated.get("suite_sha256") != expected_suite:
            raise ValueError("Calibration belongs to a different development snapshot")
        calibration_root = root if manifest["split"] == "development" else development
        if calibration_root is None:
            raise ValueError("Evaluation readiness requires --development for calibration verification")
        if m3.sha((calibration_root / "manifest.json").read_bytes()) != expected_suite:
            raise ValueError("Development snapshot mismatch")
        bound_artifact(calibration_path.parent, calibrated["observations_file"], calibrated["observations_sha256"])
        regenerated = calibration(calibration_root, calibration_path.parent / calibrated["observations_file"])
        if regenerated != calibrated:
            raise ValueError("Calibration report does not reproduce from bound observations")
        target_settings = read(root / "optional.protocol.json")["model_settings"]
        if target_settings != calibrated["model_settings"]:
            raise ValueError("Evaluation settings differ from calibrated model/harness")
        if regenerated["status"] != "headroom_observed":
            blockers.append("baseline_headroom")
    else:
        blockers.append("authorized_development_baseline_calibration")
    if manifest["split"] == "development":
        blockers.append("separate_independently_authored_evaluation_cohort")
    return {
        "suite_sha256": suite_hash, "status": "ready_for_budget_review" if not blockers else "blocked",
        "reference_starter_validation": verified, "blockers": blockers,
        "paid_generation_authorized": False, "superiority_claim_supported": False,
    }


def check_access(path: Path, names: list[str]) -> dict:
    records = read(path)
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate benchmark access records")
    by_id = {r["id"]: r for r in records}
    if not names or len(set(names)) != len(names) or set(names) - set(by_id):
        raise ValueError("Explicit known benchmark selection required")
    for name in names:
        record = by_id[name]
        if record.get("availability") != "verified" or record.get("usage_authorized") is not True:
            raise ValueError(f"Benchmark access/usage pending: {name}")
        for field in ("license", "license_url", "revision", "reviewer", "verified_at", "permitted_use"):
            require_text(record.get(field), f"{name}.{field}")
        if not re.fullmatch(r"(?:[0-9a-f]{40}|(?:sha256:)?[0-9a-f]{64})", record["revision"]):
            raise ValueError(f"Immutable benchmark revision required: {name}")
        if not record["license_url"].startswith("https://"):
            raise ValueError(f"HTTPS license URL required: {name}")
    return {"selected": names, "access_sha256": m3.sha(path.read_bytes()), "paid_generation_authorized": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "self-test", "grade", "calibrate", "diagnose", "historical-audit", "readiness", "check-access"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--image")
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--cohort", type=Path)
    parser.add_argument("--development", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--task")
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--benchmark", action="append")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; evidence must never be overwritten")
    try:
        if args.mode == "freeze":
            if not args.image:
                parser.error("freeze requires --image")
            result = freeze(args.output, args.image, read(args.settings) if args.settings else None,
                            args.cohort, args.development, args.review)
        elif args.mode in ("self-test", "grade", "calibrate", "readiness"):
            if not args.frozen:
                parser.error(f"{args.mode} requires --frozen")
            if args.mode == "self-test":
                result = self_test(args.frozen, args.output)
            elif args.mode == "grade":
                if not args.input or not args.task:
                    parser.error("grade requires --input candidate JSON and --task")
                result = grade(args.frozen, args.task, read(args.input))
            elif args.mode == "calibrate":
                if not args.input:
                    parser.error("calibrate requires --input observations")
                result = calibration(args.frozen, args.input)
            else:
                if not args.validation:
                    parser.error("readiness requires --validation summary")
                result = readiness(args.frozen, args.validation, args.calibration, args.review, args.development)
        else:
            if not args.input:
                parser.error(f"{args.mode} requires --input")
            if args.mode == "diagnose":
                result = diagnose(args.input, args.review)
            elif args.mode == "historical-audit":
                result = historical_audit(args.input)
            else:
                result = check_access(args.input, args.benchmark or [])
        if args.mode not in ("freeze", "self-test"):
            m3.write_new(args.output, result)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, SyntaxError) as error:
        parser.exit(1, f"P0 error: {error}\n")
    print(json.dumps({key: result[key] for key in ("status", "split", "blockers") if key in result}))
    if result.get("status") in ("failed", "blocked", "timeout", "invalid_report"):
        parser.exit(1)


if __name__ == "__main__":
    main()
