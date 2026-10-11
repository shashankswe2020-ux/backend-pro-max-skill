"""Verify official grading artifacts and publish a descriptive paired pilot report."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import statistics
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from backendpro.scripts.retrieval_evidence import describe_payload

ARMS = ("baseline", "context7", "backendpro", "both")
TERMINAL_MODEL_STATUSES = {"finished", "budget_limit", "time_limit", "turn_limit", "output_limit"}
KNOWLEDGE_TOOLS = {
    "baseline": set(), "context7": {"context7"}, "backendpro": {"backendpro"},
    "both": {"context7", "backendpro"},
}


def retrieval_gate(run: Path, attempts: list[dict], complete: bool, policy: str = "optional") -> dict:
    if policy not in ("optional", "required"):
        raise ValueError("Unknown retrieval policy")
    review_path = run / "evidence-review.json"
    review = json.loads(review_path.read_text()) if review_path.exists() else {}
    reviews = review.get("events", {})
    if review and (not review.get("rubric") or not review.get("reviewer") or not isinstance(reviews, dict)):
        raise ValueError("Evidence review requires a rubric, reviewer, and event mapping")
    seen = set()
    usable_pairs = set()
    events = []
    compliance = {}
    for item in attempts:
        arm = item["arm"]
        available = KNOWLEDGE_TOOLS[arm] | {"shell", "finish"}
        if "available_tools" in item and set(item["available_tools"]) != available:
            raise ValueError("Recorded tool availability disagrees with assigned arm")
        before_coding = True
        retrieved_before_coding = set()
        for index, event in enumerate(item["tool_calls"]):
            name = event["name"]
            if name in ("shell", "finish"):
                before_coding = False
            if name not in ("context7", "backendpro"):
                continue
            if name not in available and not event["is_error"]:
                raise ValueError("Unavailable knowledge tool reported as successful")
            if before_coding and name in available and (
                event.get("evidence") is not None or event.get("failure_type") == "ProviderError"
            ):
                retrieved_before_coding.add(name)
            key = f"{item['instance_id']}.{arm}:{index}"
            seen.add(key)
            status = "error" if event["is_error"] else "unverified"
            evidence = event.get("evidence")
            if evidence is not None:
                artifact = evidence["artifact"]
                if Path(artifact).name != artifact:
                    raise ValueError("Retrieval evidence must be a local artifact filename")
                raw = (run / f"{item['instance_id']}.{arm}" / artifact).read_bytes()
                if hashlib.sha256(raw).hexdigest() != evidence["sha256"]:
                    raise ValueError("Retrieval evidence hash mismatch")
                actual = describe_payload(json.loads(raw))
                if any(evidence.get(field) != value for field, value in actual.items()):
                    raise ValueError("Retrieval evidence metadata disagrees with raw payload")
                status = "error" if event["is_error"] else actual["status"]
                if hashlib.sha256(event["output"].encode()).hexdigest() != event.get("output_sha256"):
                    raise ValueError("Delivered retrieval output hash mismatch")
                if not event["is_error"]:
                    text = json.dumps(json.loads(raw), ensure_ascii=False)
                    truncated = len(text) > 6000
                    if truncated:
                        text = text[:6000] + "\n[Output truncated at 6000 characters]"
                    if event["output"] != text or event.get("truncated") != truncated:
                        raise ValueError("Tool output does not match bounded retrieval evidence")
            assessment = reviews.get(key)
            if assessment is not None:
                if evidence is None or assessment.get("output_sha256") != event.get("output_sha256"):
                    raise ValueError("Evidence review is not bound to verified delivered output")
                if assessment.get("relevance") not in ("relevant", "irrelevant", "unknown"):
                    raise ValueError("Invalid evidence relevance assessment")
                if assessment.get("application") not in ("correct", "incorrect", "not_applied", "unknown"):
                    raise ValueError("Invalid evidence application assessment")
                if not assessment.get("rationale"):
                    raise ValueError("Evidence assessment requires a rationale")
                if status == "returned" and event.get("delivered") and assessment["relevance"] == "relevant":
                    usable_pairs.add((arm, name))
            events.append({
                "event": key, "tool": name, "arm": arm, "status": status,
                "delivered": event.get("delivered"),
                "truncated": event.get("truncated"),
                "seconds": event.get("seconds"),
                "cost_upper_bound_micro_usd": event.get("cost_upper_bound_micro_usd"),
                "evidence_ids": evidence["evidence_ids"] if evidence else [],
                "assessment": assessment,
            })
        if KNOWLEDGE_TOOLS[arm]:
            compliance[f"{item['instance_id']}.{arm}"] = KNOWLEDGE_TOOLS[arm] <= retrieved_before_coding
    required_pairs = {(arm, name) for arm, names in KNOWLEDGE_TOOLS.items() for name in names}
    reasons = []
    if not complete:
        reasons.append("Generation, grading, or accounting is incomplete.")
    if not events:
        reasons.append("No knowledge tool was invoked.")
    missing = required_pairs - usable_pairs
    if missing:
        reasons.append("No verified, reviewer-rated relevant evidence for: "
                       + ", ".join(f"{arm}/{name}" for arm, name in sorted(missing)) + ".")
    if any(event["status"] in ("unverified", "unclassified") for event in events):
        reasons.append("Some retrieval payloads are unverified or unclassified.")
    if any(
        event["status"] == "returned" and (
            event["assessment"] is None or event["assessment"]["relevance"] == "unknown"
            or event["assessment"]["application"] == "unknown"
        )
        for event in events
    ):
        reasons.append("Returned evidence still needs relevance/application review.")
    if reviews.keys() - seen:
        raise ValueError("Evidence review contains unassigned events")
    if policy == "required" and not all(compliance.values()):
        reasons.append("Required retrieval was not attempted before the first shell/finish call in every eligible attempt.")
    return {
        "policy": policy,
        "activation_measured": all(item["status"] in TERMINAL_MODEL_STATUSES for item in attempts),
        "retrieval_comparison_evaluable": not reasons,
        "superiority_claim_supported": False,
        "reasons": reasons,
        "required_use_compliance": compliance if policy == "required" else None,
        "event_statuses": dict(Counter(event["status"] for event in events)),
        "reviewed_events": len(reviews),
        "reviewer": review.get("reviewer"), "rubric": review.get("rubric"),
        "events": events,
    }


def wilson(successes: int, count: int) -> list[float]:
    if not 0 <= successes <= count or count < 1:
        raise ValueError("Invalid success count or denominator")
    z = 1.959963984540054
    proportion = successes / count
    denominator = 1 + z * z / count
    center = (proportion + z * z / (2 * count)) / denominator
    radius = z * math.sqrt(proportion * (1 - proportion) / count + z * z / (4 * count**2)) / denominator
    return [max(0.0, center - radius), min(1.0, center + radius)]


def paired(left: dict[str, bool], right: dict[str, bool]) -> dict:
    if not left or left.keys() != right.keys():
        raise ValueError("Paired comparison requires identical non-empty task sets")
    left_only = sum(left[key] and not right[key] for key in left)
    right_only = sum(right[key] and not left[key] for key in left)
    discordant = left_only + right_only
    probability = min(1.0, 2 * sum(math.comb(discordant, k) for k in range(min(left_only, right_only) + 1))
                      / 2**discordant)
    return {
        "left_only_resolved": left_only, "right_only_resolved": right_only,
        "both_resolved": sum(left[key] and right[key] for key in left),
        "neither_resolved": sum(not left[key] and not right[key] for key in left),
        "difference_percentage_points": (left_only - right_only) / len(left) * 100,
        "exact_mcnemar_p_unadjusted": probability,
    }


def spend(path: Path) -> dict:
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        rows = connection.execute("SELECT provider,reserved,charged FROM charges").fetchall()
    return {
        "accounted_upper_bound_usd": sum(charged if charged is not None else reserved
                                         for _, reserved, charged in rows) / 1_000_000,
        "anthropic_measured_usd": sum(charged or 0 for provider, _, charged in rows
                                      if provider == "anthropic") / 1_000_000,
        "context7_upper_bound_usd": sum(charged if charged is not None else reserved
                                        for provider, reserved, charged in rows
                                        if provider == "context7") / 1_000_000,
        "unsettled_requests": sum(charged is None for _, _, charged in rows),
        "api_requests_including_startup": len(rows),
    }


def build_report(run: Path) -> dict:
    config = json.loads((run / "protocol.json").read_text())
    provenance = json.loads((run / "provenance.json").read_text())
    input_bytes = (run / "inputs.json").read_bytes()
    if hashlib.sha256(input_bytes).hexdigest() != provenance["inputs_sha256"]:
        raise ValueError("Frozen input hash mismatch")
    inputs = json.loads(input_bytes)
    generation = json.loads((run / "generation.json").read_text())
    expected = {(item["instance_id"], item["arm"]) for item in inputs["attempts"]}
    attempts = generation["attempts"]
    if len(attempts) != 72 or len(expected) != 72 or len(inputs["attempts"]) != 72:
        raise ValueError("Expected exactly 72 assigned attempts")
    if {(item["instance_id"], item["arm"]) for item in attempts} != expected:
        raise ValueError("Generation results do not match the assigned cohort")
    arm_reports = {}
    outcomes = {}
    details = []
    complete = True
    for arm in ARMS:
        selected = [item for item in attempts if item["arm"] == arm]
        if len(selected) != 18:
            raise ValueError("Every arm must have exactly 18 assigned tasks")
        model_label = f"claude-opus-5-5-{arm}"
        run_id = f"{run.name}-{arm}"
        summary_path = run / f"{model_label}.{run_id}.json"
        summary_bytes = summary_path.read_bytes()
        summary = json.loads(summary_bytes)
        allowed_ids = {item["instance_id"] for item in selected}
        if not set(summary["submitted_ids"]) <= allowed_ids:
            raise ValueError("Evaluator includes unassigned tasks")
        statuses = Counter()
        decisions = {}
        token_counts = Counter()
        tool_requests = Counter()
        tool_successes = Counter()
        retrieval_attempts = 0
        for item in selected:
            instance = item["instance_id"]
            folder = run / f"{instance}.{arm}"
            patch = folder / "patch.diff"
            if patch.exists() and hashlib.sha256(patch.read_bytes()).hexdigest() != item["patch_sha256"]:
                raise ValueError(f"Patch changed after generation: {instance}/{arm}")
            used_knowledge = False
            for event in item["tool_calls"]:
                if event["name"] in ("context7", "backendpro"):
                    tool_requests[event["name"]] += 1
                    used_knowledge = True
                    if not event["is_error"]:
                        tool_successes[event["name"]] += 1
            retrieval_attempts += used_knowledge
            responses = list(folder.glob("response-*.json"))
            if len(responses) != item["model_turns"]:
                raise ValueError("Missing model-response evidence")
            response_calls = {}
            for response_path in responses:
                response = json.loads(response_path.read_text())
                if response["model"] != config["model"]:
                    raise ValueError("Mixed models in response evidence")
                token_counts.update({key: response["usage"][key] for key in ("input_tokens", "output_tokens")})
                for block in response.get("content", []):
                    if block.get("type") == "tool_use":
                        response_calls[block["id"]] = block
            for event in item["tool_calls"]:
                if "tool_use_id" in event:
                    call = response_calls.get(event["tool_use_id"])
                    if call is None or call["name"] != event["name"] or call["input"] != event["input"]:
                        raise ValueError("Tool trace does not match returned model evidence")
            resolved = False
            grading_hash = None
            if item["status"] not in TERMINAL_MODEL_STATUSES:
                status = "generation_incomplete"
                complete = False
            elif not patch.exists():
                raise ValueError("Terminal attempt lacks its patch artifact")
            elif not patch.read_bytes():
                status = "empty_patch"
                if instance not in summary["empty_patch_ids"]:
                    raise ValueError("Empty patch missing from official evaluator summary")
            elif instance in summary["error_ids"]:
                status = "evaluation_error"
                complete = False
            else:
                evidence = run / "logs/run_evaluation" / run_id / model_label / instance / "report.json"
                evidence_bytes = evidence.read_bytes()
                grading_hash = hashlib.sha256(evidence_bytes).hexdigest()
                raw = json.loads(evidence_bytes)[instance]
                resolved = raw["resolved"]
                if not isinstance(resolved, bool):
                    raise ValueError("Invalid resolved flag")
                if instance not in summary["completed_ids"]:
                    raise ValueError("Per-task report missing from completed evaluator IDs")
                if resolved != (instance in summary["resolved_ids"]):
                    raise ValueError("Evaluator summary disagrees with task evidence")
                status = "resolved" if resolved else "unresolved"
            statuses[status] += 1
            decisions[instance] = resolved
            details.append({
                "instance_id": instance, "arm": arm, "generation_status": item["status"],
                "model_turns": item["model_turns"], "evaluation_status": status, "resolved": resolved,
                "patch_sha256": item.get("patch_sha256"), "used_knowledge_tool": used_knowledge,
                "grading_report_sha256": grading_hash,
            })
        costs = sum(item["cost"]["accounted_upper_bound_micro_usd"] for item in selected) / 1_000_000
        measured = sum(item["cost"]["anthropic_measured_micro_usd"] for item in selected)
        if measured != token_counts["input_tokens"] * 4 + token_counts["output_tokens"] * 20:
            raise ValueError("Attempt costs disagree with returned model token usage")
        times = sorted(item["seconds"] for item in selected)
        resolved = sum(decisions.values())
        arm_reports[arm] = {
            "assigned": 18, "resolved": resolved, "resolved_fraction": resolved / 18,
            "wilson_95_interval": wilson(resolved, 18), "evaluation_statuses": dict(statuses),
            "generation_statuses": dict(Counter(item["status"] for item in selected)),
            "cost_upper_bound_usd": costs,
            "cost_per_resolved_upper_bound_usd": costs / resolved if resolved else None,
            "tokens": dict(token_counts), "knowledge_tool_requests": dict(tool_requests),
            "successful_knowledge_tool_requests": dict(tool_successes),
            "attempts_using_knowledge_tools": retrieval_attempts,
            "generation_p50_seconds": statistics.median(times),
            "generation_p95_seconds": times[math.ceil(len(times) * 0.95) - 1],
            "official_summary_sha256": hashlib.sha256(summary_bytes).hexdigest(),
        }
        outcomes[arm] = decisions
    accounting = spend(Path(provenance["spending_ledger"]))
    if accounting["accounted_upper_bound_usd"] > 25:
        raise ValueError("Authorized aggregate spending ceiling exceeded")
    response_cost = sum(
        arm["tokens"].get("input_tokens", 0) * 4 + arm["tokens"].get("output_tokens", 0) * 20
        for arm in arm_reports.values()
    ) / 1_000_000
    startup_cost = 0
    startup = run / "preflight-model-response.json"
    if startup.exists():
        response = json.loads(startup.read_text())
        if response["model"] != config["model"]:
            raise ValueError("Mixed model in capability preflight")
        startup_cost = (response["usage"]["input_tokens"] * 4 + response["usage"]["output_tokens"] * 20) / 1_000_000
    if not math.isclose(accounting["anthropic_measured_usd"], response_cost + startup_cost, abs_tol=0.000001):
        raise ValueError("Shared ledger disagrees with response-token accounting")
    if accounting["unsettled_requests"]:
        complete = False
    usage = sum(arm["attempts_using_knowledge_tools"] for arm in arm_reports.values())
    gate = retrieval_gate(run, attempts, complete, config.get("retrieval_policy", "optional"))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed" if complete else "incomplete",
        "run_id": run.name, "model": config["model"], "dataset_revision": inputs["dataset_revision"],
        "assigned_tasks_per_arm": 18, "assigned_attempts": 72, "arms": arm_reports,
        "paired_comparisons": {
            f"{left}_vs_{right}": paired(outcomes[left], outcomes[right])
            for left, right in combinations(ARMS, 2)
        } if complete else {},
        "spend": accounting,
        "startup_model_cost_usd": startup_cost,
        "evaluation_gate": gate,
        "readiness": json.loads((run / "readiness.json").read_text())
        if (run / "readiness.json").exists() else {"status": "not_recorded_legacy_run"},
        "excluded_tasks": config["approved_amendments"]["excluded_instances"],
        "interpretation": (
            "No knowledge tool was invoked in any model attempt. These results compare tool availability "
            "only and do not measure the usefulness or quality of Context7 or BackendPro retrieval."
            if usage == 0 else
            "This measures tool availability under the fixed scaffold and budget. Inspect actual retrieval "
            "usage before attributing paired outcome differences to either knowledge source."
        ),
        "limitations": config["limitations"] + [
            "Confidence intervals and paired tests are descriptive; six pairwise p-values are unadjusted for multiplicity.",
            "Do not declare a universal product winner from this small, public Python issue-fixing sample.",
            "Generation latency includes container setup and cleanup, but excludes queueing, dataset loading and grading.",
            "One interrupted conversation was continued with its exact prior messages and patch; completed attempts were not regenerated.",
            "Reviewed dependency pins and file-mode changes from the official images were preserved equally across arms.",
            "Startup/resume overhead is included in generation timings; these timings do not rank retrieval speed.",
            "The initial unsupported-parameter requests produced no model output; their evidence and shared ledger were retained.",
            "Context7 cost is an upper bound at the public overage rate, not the account's actual invoice.",
        ],
        "provenance": {key: value for key, value in provenance.items() if key != "spending_ledger"},
        "resume_provenance": json.loads((run / "resume-provenance.json").read_text())
        if (run / "resume-provenance.json").exists() else None,
        "tasks": details,
    }


def markdown(report: dict) -> str:
    lines = [
        "# BackendPro / Context7: SWE-bench pilot comparison",
        "",
        f"**Status: {report['status']}.** Model: `{report['model']}`. "
        "18 identical tasks per arm, one attempt per task, 72 assigned attempts.",
        "",
        "**This is an exploratory pilot, not a full leaderboard run or a universal product ranking.**",
        "",
        "| Arm | Resolved / 18 | 95% Wilson interval | Cost upper bound | Attempts using knowledge tools |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, arm in report["arms"].items():
        low, high = arm["wilson_95_interval"]
        lines.append(
            f"| {name} | {arm['resolved']}/18 | {low:.1%}-{high:.1%} | "
            f"${arm['cost_upper_bound_usd']:.4f} | {arm['attempts_using_knowledge_tools']}/18 |"
        )
    lines += [
        "", "## Interpretation", "", report["interpretation"], "",
        "## Evaluation gates", "",
        f"- Activation measured: **{report['evaluation_gate']['activation_measured']}**.",
        f"- Retrieval comparison evaluable: **{report['evaluation_gate']['retrieval_comparison_evaluable']}**.",
        "- A passed retrieval gate is not statistical evidence of superiority.",
        *[f"- {reason}" for reason in report["evaluation_gate"]["reasons"]],
        "",
        f"Aggregate API cost upper bound, including startup: **${report['spend']['accounted_upper_bound_usd']:.4f}** "
        "against the authorized $25 cap.", "",
        "Two tasks were excluded equally before generation because their reference-patch evaluations timed out: "
        + ", ".join(f"`{task}`" for task in report["excluded_tasks"]) + ".", "",
        "## Paired outcomes", "",
        "| Comparison | Left only resolved | Right only resolved | Both resolved | Exact paired p (unadjusted) |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, result in report["paired_comparisons"].items():
        lines.append(
            f"| {name} | {result['left_only_resolved']} | {result['right_only_resolved']} | "
            f"{result['both_resolved']} | {result['exact_mcnemar_p_unadjusted']:.4f} |"
        )
    lines += [
        "", "## Method", "",
        "- Official SWE-bench 4.1.0 evaluator; frozen Verified dataset revision "
        f"`{report['dataset_revision']}`.",
        "- Same native-tool scaffold; fresh network-disabled AMD64 containers on Apple Silicon.",
        "- Adaptive thinking with low effort; 16 turns, 2,048 output tokens/turn, $0.34 ceiling per attempt.",
        f"- Retrieval policy: {report['evaluation_gate']['policy']}; knowledge-enabled arms share three retrieval calls.",
        "- Reference patches and grading-only tests were not supplied to the coding model.",
        "- The [approved protocol](comparison-protocol.json) records scope amendments, limits and pricing sources.",
        "", "## Limitations", "",
    ]
    lines += [f"- {limitation}" for limitation in report["limitations"]]
    lines += [
        "", "Full per-task outcomes, token counts, timing, generation exits, cost accounting and hashes "
        "are in [comparison-results.json](comparison-results.json).", "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".md").exists():
        parser.error("Refusing to overwrite an existing report; use a new output path")
    report = build_report(args.run)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(report["status"], report["spend"], report["interpretation"])


if __name__ == "__main__":
    main()
