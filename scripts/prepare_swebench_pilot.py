"""Freeze a SWE-bench Verified pilot; this does not generate or grade patches."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

DATASET = "princeton-nlp/SWE-bench_Verified"
SEED = "backendpro-context7-pilot-v1"
ARMS = ("baseline", "context7", "backendpro", "both")
FIELDS = ("instance_id", "repo", "base_commit")
ROOT = Path(__file__).resolve().parents[1]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def select_tasks(rows: list[dict], count: int = 20) -> list[dict]:
    if len(rows) != 500:
        raise ValueError("Expected the complete 500-instance Verified test split")
    if not 1 <= count <= len(rows):
        raise ValueError("Task count must be between 1 and the population size")
    metadata = []
    seen = set()
    for row in rows:
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in FIELDS):
            raise ValueError("Each instance needs non-empty instance_id, repo and base_commit")
        if row["instance_id"] in seen:
            raise ValueError("Duplicate instance_id in dataset")
        seen.add(row["instance_id"])
        metadata.append({key: row[key] for key in FIELDS})
    return sorted(metadata, key=lambda row: (digest(f"{SEED}:{row['instance_id']}"), row["instance_id"]))[:count]


def schedule(tasks: list[dict]) -> list[dict]:
    attempts = []
    for index, task in enumerate(tasks):
        offset = index % len(ARMS)
        for arm in ARMS[offset:] + ARMS[:offset]:
            attempts.append({"instance_id": task["instance_id"], "arm": arm, "repeat": 1})
    return attempts


def preflight() -> dict:
    credentials = {key: bool(os.environ.get(key)) for key in ("ANTHROPIC_API_KEY", "CONTEXT7_API_KEY")}
    docker = "not installed"
    if shutil.which("docker"):
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.OSType}}/{{.Architecture}}"],
                capture_output=True, text=True, timeout=15, check=False,
            )
            docker = result.stdout.strip() if result.returncode == 0 else f"failed (exit {result.returncode})"
        except subprocess.TimeoutExpired:
            docker = "timed out after 15 seconds"
    return {
        "credentials_present": credentials,
        "docker": docker,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ready_for_generation": False,
        "remaining_gates": [
            "Both credentials must be available to the runner, never stored in artifacts.",
            "Docker must respond and an isolated SWE-bench instance must pass a smoke evaluation.",
            "Verify exact requested model access using the provider model catalog; never substitute a model.",
            "Pin agent, harness, container digests, model parameters and equal per-attempt limits.",
            "Implement and test the four isolated knowledge-tool configurations.",
            "Verify current provider pricing and enforce the aggregate $25 cap before every paid request.",
            "Keep gold patches and grading tests out of agent-visible inputs.",
        ],
    }


def build_manifest(rows: list[dict], revision: str, protocol: dict, checks: dict) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Dataset revision must be an immutable 40-character commit SHA")
    tasks = select_tasks(rows)
    population = sorted(
        ({key: row[key] for key in FIELDS} for row in rows),
        key=lambda row: row["instance_id"],
    )
    corpus = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "src/backend-pro-max/data").rglob("*.csv"))
    }
    return {
        "status": "prepared_not_run",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": DATASET,
        "split": "test",
        "dataset_revision": revision,
        "population_size": len(rows),
        "population_metadata_sha256": digest(json.dumps(population, sort_keys=True)),
        "selection": {"seed": SEED, "method": "lowest SHA256(seed:instance_id), tie-break instance_id"},
        "protocol": protocol,
        "protocol_sha256": digest(json.dumps(protocol, sort_keys=True)),
        "backendpro_csv_sha256": corpus,
        "tasks": tasks,
        "attempt_schedule": schedule(tasks),
        "preflight": checks,
        "completed_attempts": 0,
        "results": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", help="Immutable dataset SHA; default resolves main once")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; frozen selections must not be overwritten")
    revision = args.revision
    if revision is None:
        with urlopen(f"https://huggingface.co/api/datasets/{DATASET}", timeout=30) as response:
            revision = json.load(response)["sha"]
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        parser.error("Dataset revision must be an immutable 40-character commit SHA")

    from datasets import load_dataset

    rows = list(load_dataset(DATASET, revision=revision, split="test"))
    protocol = json.loads((ROOT / "benchmarks/swebench-pilot/protocol.json").read_text(encoding="utf-8"))
    manifest = build_manifest(rows, revision, protocol, preflight())
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(manifest, output, indent=2)
        output.write("\n")
    print(f"Frozen {len(manifest['tasks'])} tasks / {len(manifest['attempt_schedule'])} attempts: {args.output}")
    print("PREPARED ONLY: no model generation, Context7 retrieval or SWE-bench grading has run.")


if __name__ == "__main__":
    main()
