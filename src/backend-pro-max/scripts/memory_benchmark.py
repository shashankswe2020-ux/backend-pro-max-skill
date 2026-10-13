"""Chronological P4 context arms and offline analysis of externally measured runs."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from . import evidence, memory, repository


def validate_protocol(protocol):
    memory._object(protocol, "format study preregistered_at model_revision repetitions max_chars tasks", "sequence protocol")
    if protocol["format"] != "memory-sequence-v1":
        raise ValueError("Unsupported sequence protocol")
    memory._slug(protocol["study"])
    memory._text(protocol["model_revision"], 200)
    memory._time(protocol["preregistered_at"])
    if type(protocol["repetitions"]) is not int or not 1 <= protocol["repetitions"] <= 10:
        raise ValueError("Declare 1-10 repetitions before collection")
    if type(protocol["max_chars"]) is not int or not 1 <= protocol["max_chars"] <= 100000:
        raise ValueError("Declare an explicit character budget <=100000")
    if not isinstance(protocol["tasks"], list) or not 1 <= len(protocol["tasks"]) <= 500:
        raise ValueError("Declare 1-500 development tasks")
    tasks, positions = {}, set()
    for task in protocol["tasks"]:
        memory._object(task, "id sequence family ordinal allowed_tasks query library_versions", "sequence task")
        for key in ("id", "sequence", "family"):
            memory._slug(task[key])
        memory._text(task["query"])
        memory._versions(task["library_versions"])
        if type(task["ordinal"]) is not int or task["ordinal"] < 0:
            raise ValueError("Task ordinals must be nonnegative integers")
        position = (task["sequence"], task["family"], task["ordinal"])
        if task["id"] in tasks or position in positions:
            raise ValueError("Task IDs and within-family sequence positions must be unique")
        tasks[task["id"]] = task
        positions.add(position)
    for task in tasks.values():
        allowed = task["allowed_tasks"]
        if (
            not isinstance(allowed, list) or len(allowed) > memory.MAX_RECORDS
            or any(not isinstance(item, str) for item in allowed) or len(set(allowed)) != len(allowed)
        ):
            raise ValueError("Declare unique preceding-task permissions")
        for identity in allowed:
            prior = tasks.get(identity)
            if (
                prior is None or prior["sequence"] != task["sequence"] or prior["family"] != task["family"]
                or prior["ordinal"] >= task["ordinal"]
            ):
                raise ValueError("Future, current, unknown or cross-family/sequence context is forbidden")
    return tasks


def sequence_scope(protocol: dict, sequence: str, repetition: int = 0) -> str:
    tasks = validate_protocol(protocol)
    if (
        type(repetition) is not int or not 0 <= repetition < protocol["repetitions"]
        or sequence not in {task["sequence"] for task in tasks.values()}
    ):
        raise ValueError("Unknown sequence or repetition")
    return repository._identity({"protocol": protocol, "sequence": sequence, "repetition": repetition})


def context_for_task(protocol: dict, task_id: str, arm: str, *, workspace_root: str,
                     store: str, prior_context: dict | None = None, repetition: int = 0) -> dict:
    """Each call starts empty; raw tool context is caller-owned and never persisted here."""
    tasks = validate_protocol(protocol)
    if task_id not in tasks or arm not in memory.ARMS:
        raise ValueError("Unknown task or treatment")
    task = tasks[task_id]
    scope = sequence_scope(protocol, task["sequence"], repetition)
    units, prior_omissions = [], 0
    ineligible = {}
    if arm != "raw_prior_context" and prior_context:
        raise ValueError("Raw prior context cannot cross treatment arms")
    if arm == "verified_memory":
        recalled = memory.memory_context(
            task["query"], scope, task["family"], task_id, task["ordinal"],
            task["allowed_tasks"], task["library_versions"], workspace_root=workspace_root,
            store=store, max_chars=protocol["max_chars"],
        )
        units = recalled["results"]
        prior_omissions = recalled["omissions"]["budget"]
        ineligible = recalled["ineligible"]
        for unit in units:
            origin = unit["facts"]["origin"]
            expected = tasks[origin["task"]]
            if origin["sequence"] != scope or any(origin[key] != expected[key] for key in ("family", "ordinal")):
                raise ValueError("Memory origin disagrees with the frozen task schedule")
    elif arm == "raw_prior_context":
        if not isinstance(prior_context, dict) or set(prior_context) != set(task["allowed_tasks"]):
            raise ValueError("Provide only explicitly permitted preceding raw tool contexts")
        for identity in sorted(task["allowed_tasks"], key=lambda item: tasks[item]["ordinal"]):
            value = prior_context[identity]
            memory._object(value, "tool_context approved source_arm scope", "raw tool context")
            text = value["tool_context"]
            if (
                value["approved"] is not True or value["source_arm"] != "raw_prior_context" or value["scope"] != scope
                or not isinstance(text, str) or not text.strip() or len(text) > 200000
                or repository._SENSITIVE.search(text)
            ):
                raise ValueError("Only approved, bounded, non-sensitive raw-arm tool context is allowed; never conversations")
            units.append({
                "id": "raw:" + repository._identity({"task": identity, "text": text}),
                "kind": "raw_prior_context", "title": tasks[identity]["query"], "domain": "prior_tool_context",
                "version_match": "unknown", "facts": {"task": identity, "tool_context": text},
            })
    return evidence.pack_units({
        "format": "memory-sequence-context-v1", "protocol_sha256": repository._identity(protocol),
        "task": task_id, "arm": arm, "repetition": repetition, "query": task["query"], "results": [],
        "matched_count": len(units) + prior_omissions, "omissions": {"budget": len(units) + prior_omissions},
        "ineligible": ineligible, "quality_gates_demonstrated": False,
    }, list(enumerate(units)), protocol["max_chars"])


def _percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def evaluate_sequences(protocol: dict, observations: list[dict]) -> dict:
    """All assigned attempts count; imported measurements are not independently authenticated."""
    tasks = validate_protocol(protocol)
    digest = repository._identity(protocol)
    indexed = {}
    for row in observations:
        memory._object(row, "task arm repetition protocol_sha256 started_at finished_at status resolved input_tokens output_tokens setup_tokens source_tasks context_sha256 stale_guidance contamination", "observation")
        if row["task"] not in tasks or row["arm"] not in memory.ARMS:
            raise ValueError("Observation belongs to an unassigned task or arm")
        if type(row["repetition"]) is not int or not 0 <= row["repetition"] < protocol["repetitions"]:
            raise ValueError("Observation repetition outside frozen assignment")
        if row["protocol_sha256"] != digest:
            raise ValueError("Observation protocol hash mismatch")
        start, end = memory._time(row["started_at"]), memory._time(row["finished_at"])
        if not memory._time(protocol["preregistered_at"]) < start <= end:
            raise ValueError("Protocol must precede collection and finish cannot precede start")
        if (
            row["status"] not in ("completed", "failed", "timeout")
            or any(type(row[key]) is not bool for key in ("resolved", "stale_guidance", "contamination"))
            or (row["status"] != "completed" and row["resolved"])
        ):
            raise ValueError("Failed/timed-out attempts must count as unresolved")
        for key in ("input_tokens", "output_tokens", "setup_tokens"):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError("Actual nonnegative token measurements, including setup, are required")
        sources = row["source_tasks"]
        if (
            not isinstance(sources, list) or any(not isinstance(item, str) for item in sources)
            or len(set(sources)) != len(sources) or set(sources) - set(tasks[row["task"]]["allowed_tasks"])
            or (row["arm"] == "no_memory" and sources)
        ):
            raise ValueError("Observed context violates preceding-task permissions or treatment isolation")
        memory._hash(row["context_sha256"])
        key = (row["task"], row["arm"], row["repetition"])
        if key in indexed:
            raise ValueError("Duplicate assigned observation")
        indexed[key] = row
    expected = {(task, arm, repeat) for task in tasks for arm in memory.ARMS for repeat in range(protocol["repetitions"])}
    if set(indexed) != expected:
        raise ValueError("Report every assigned task/arm/repetition, including failed and empty attempts")
    for (task_id, arm, repeat), row in indexed.items():
        task = tasks[task_id]
        for earlier in tasks.values():
            if (
                earlier["sequence"] == task["sequence"] and earlier["family"] == task["family"]
                and earlier["ordinal"] < task["ordinal"]
                and memory._time(indexed[(earlier["id"], arm, repeat)]["finished_at"]) > memory._time(row["started_at"])
            ):
                raise ValueError("Task sequence is not chronological within its arm and repetition")
    families = sorted({task["family"] for task in tasks.values()})
    totals = {}
    for family in families:
        totals[family] = {}
        for arm in memory.ARMS:
            rows = [row for row in observations if tasks[row["task"]]["family"] == family and row["arm"] == arm]
            totals[family][arm] = (
                sum(row["input_tokens"] + row["output_tokens"] + row["setup_tokens"] for row in rows),
                sum(row["resolved"] for row in rows), len(rows),
            )

    def effect(sample, baseline):
        baseline_tokens = sum(totals[family][baseline][0] for family in sample)
        memory_tokens = sum(totals[family]["verified_memory"][0] for family in sample)
        count = sum(totals[family][baseline][2] for family in sample)
        delta = sum(totals[family]["verified_memory"][1] - totals[family][baseline][1] for family in sample) / count
        return (1 - memory_tokens / baseline_tokens if baseline_tokens else None), delta

    comparisons = {}
    for baseline in memory.ARMS[:2]:
        point = effect(families, baseline)
        intervals = [None, None]
        if len(families) >= 2:
            randomizer = random.Random(0)
            samples = [effect(randomizer.choices(families, k=len(families)), baseline) for _ in range(2000)]
            for column in range(2):
                values = [sample[column] for sample in samples]
                if all(value is not None for value in values):
                    intervals[column] = [_percentile(values, 0.00625), _percentile(values, 0.99375)]
        comparisons[baseline] = {
            "token_reduction": point[0], "resolution_delta": point[1],
            "token_reduction_interval": intervals[0], "resolution_delta_interval": intervals[1],
            "diagnostic_thresholds_met": bool(
                point[0] is not None and point[0] >= 0.15 and intervals[0] and intervals[0][0] > 0
                and intervals[1] and intervals[1][0] >= -0.02
            ),
        }
    regressions = sum(row["stale_guidance"] or row["contamination"] for row in observations if row["arm"] == "verified_memory")
    return {
        "format": "memory-sequence-report-v1", "protocol_sha256": digest,
        "assigned_attempts": len(expected), "family_clusters": len(families), "comparisons": comparisons,
        "arm_totals": {
            arm: {
                "tokens": sum(totals[family][arm][0] for family in families),
                "resolved": sum(totals[family][arm][1] for family in families),
                "attempts": sum(totals[family][arm][2] for family in families),
                "failed_or_timeout": sum(row["status"] != "completed" for row in observations if row["arm"] == arm),
            } for arm in memory.ARMS
        },
        "memory_regressions": regressions,
        "decision": "reject" if regressions else (
            "eligible_for_independent_review" if all(row["diagnostic_thresholds_met"] for row in comparisons.values()) else "inconclusive"
        ),
        "quality_gates_demonstrated": False,
        "method": "Paired family-cluster percentile bootstrap, 2000 draws, seed 0; Bonferroni 98.75% intervals for four endpoints (95% familywise nominal). Repetitions stay in family clusters. Fewer than two clusters or undefined ratios yield no interval.",
        "limitations": "Imported measurements and source-context hashes are not authenticated execution. Few clusters and percentile intervals can be unreliable. Count summary creation/review in setup tokens. No memory gate is automatically enabled; independent review and sufficient study power remain required.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("observations", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.protocol.resolve(), args.observations.resolve()):
        parser.error("Report output must not overwrite protocol or observations")
    try:
        report = evaluate_sequences(json.loads(args.protocol.read_text()), json.loads(args.observations.read_text()))
    except (ValueError, OSError) as error:
        parser.error(str(error))
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
