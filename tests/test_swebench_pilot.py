"""Preparation checks only; these tests do not measure coding performance."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_swebench_pilot.py"
SPEC = importlib.util.spec_from_file_location("prepare_swebench_pilot", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


@pytest.fixture
def rows():
    return [
        {
            "instance_id": f"example__repo-{index}", "repo": "example/repo", "base_commit": "a" * 40,
            "patch": "GOLD MUST NOT LEAK", "test_patch": "TEST MUST NOT LEAK",
            "FAIL_TO_PASS": ["secret"], "hints_text": "HINT MUST NOT LEAK",
        }
        for index in range(500)
    ]


def test_selection_is_deterministic_and_input_order_independent(rows):
    selected = pilot.select_tasks(rows)
    assert selected == pilot.select_tasks(list(reversed(rows)))
    assert len(selected) == len({row["instance_id"] for row in selected}) == 20
    assert all(set(row) == set(pilot.FIELDS) for row in selected)


def test_selection_rejects_incomplete_population(rows):
    with pytest.raises(ValueError, match="500"):
        pilot.select_tasks(rows[:-1])


def test_selection_rejects_duplicate_ids(rows):
    rows[-1] = rows[0]
    with pytest.raises(ValueError, match="Duplicate"):
        pilot.select_tasks(rows)


def test_selection_rejects_missing_metadata(rows):
    del rows[0]["base_commit"]
    with pytest.raises(ValueError, match="base_commit"):
        pilot.select_tasks(rows)


@pytest.mark.parametrize("count", [0, 501])
def test_invalid_count(rows, count):
    with pytest.raises(ValueError, match="Task count"):
        pilot.select_tasks(rows, count=count)


def test_schedule_is_paired_and_position_balanced(rows):
    selected = pilot.select_tasks(rows)
    attempts = pilot.schedule(selected)
    assert len(attempts) == 80
    for task in selected:
        matching = [attempt for attempt in attempts if attempt["instance_id"] == task["instance_id"]]
        assert {attempt["arm"] for attempt in matching} == set(pilot.ARMS)
        assert len(matching) == 4
    for position in range(4):
        arms = [attempt["arm"] for attempt in attempts[position::4]]
        assert all(arms.count(arm) == 5 for arm in pilot.ARMS)


def test_manifest_never_claims_results_or_exposes_gold(rows):
    manifest = pilot.build_manifest(rows, "a" * 40, {"model": "unverified"}, {})
    assert manifest["status"] == "prepared_not_run"
    assert manifest["completed_attempts"] == 0
    assert manifest["results"] is None
    assert manifest["backendpro_csv_sha256"]
    assert "MUST NOT LEAK" not in str(manifest)


def test_manifest_requires_pinned_revision(rows):
    with pytest.raises(ValueError, match="immutable"):
        pilot.build_manifest(rows, "main", {}, {})


def test_preflight_reports_absent_credentials_and_docker(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CONTEXT7_API_KEY", raising=False)
    monkeypatch.setattr(pilot.shutil, "which", lambda command: None)
    checks = pilot.preflight()
    assert not any(checks["credentials_present"].values())
    assert checks["docker"] == "not installed"
    assert checks["ready_for_generation"] is False


def test_preflight_reports_docker_timeout(monkeypatch):
    monkeypatch.setattr(pilot.shutil, "which", lambda command: "/docker")

    def timeout(*args, **kwargs):
        raise pilot.subprocess.TimeoutExpired("docker", 15)

    monkeypatch.setattr(pilot.subprocess, "run", timeout)
    assert pilot.preflight()["docker"] == "timed out after 15 seconds"


def test_preflight_reports_docker_failure_without_storing_output(monkeypatch):
    monkeypatch.setattr(pilot.shutil, "which", lambda command: "/docker")
    monkeypatch.setattr(
        pilot.subprocess, "run",
        lambda *args, **kwargs: pilot.subprocess.CompletedProcess("docker", 1, "", "private host details"),
    )
    checks = pilot.preflight()
    assert checks["docker"] == "failed (exit 1)"
    assert "private host details" not in str(checks)


def test_frozen_pilot_matches_protocol_and_balanced_schedule():
    directory = SCRIPT.parents[1] / "benchmarks/swebench-pilot"
    protocol = json.loads((directory / "protocol.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["protocol"] == protocol
    assert manifest["protocol_sha256"] == pilot.digest(json.dumps(protocol, sort_keys=True))
    assert len(manifest["tasks"]) == protocol["tasks"] == 20
    assert len(manifest["attempt_schedule"]) == protocol["attempts"] == 80
    assert manifest["attempt_schedule"] == pilot.schedule(manifest["tasks"])
    assert protocol["budget"]["maximum_total_usd"] == 25
    assert manifest["results"] is None
