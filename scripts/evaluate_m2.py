"""Offline M2 evidence bundles and scoring of externally collected MCP observations.

No provider/client execution, credentials, or network access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import statistics
from pathlib import Path

from backendpro.scripts.core import CSV_CONFIG, DATA_DIR, STACK_CONFIG, classify_intent, search, search_stack
from backendpro.scripts.gen_tools_schema import TOOLS
from backendpro.scripts.search import format_output
from backendpro.scripts.templates import COMPACT_MAX_CHARS, compact_json, format_by_intent, format_compact
from report_swebench_comparison import wilson

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "benchmarks/m2/suite.json"


def encoded(value: dict) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_suite(path: Path) -> dict:
    suite = json.loads(path.read_text())
    if suite.get("version") != 1 or suite.get("review_status") != "pending_independent_review":
        raise ValueError("Expected the version-1 draft suite; reviewed studies need a separately locked protocol")
    cases = suite["activation"]
    if any(
        not isinstance(case.get("id"), str) or re.fullmatch(r"[a-z][a-z0-9-]*", case["id"]) is None
        for case in [*cases, *suite["retrieval"]]
    ):
        raise ValueError("Case identifiers must contain only lowercase letters, digits, and hyphens")
    if len(cases) != 40 or len({case["id"] for case in cases}) != 40:
        raise ValueError("Activation suite must have 40 unique cases")
    if any(
        case.get("split") not in ("development", "evaluation")
        or type(case.get("retrieve")) is not bool or not case.get("prompt", "").strip()
        for case in cases
    ):
        raise ValueError("Invalid activation labels or prompt")
    for split in ("development", "evaluation"):
        selected = [case for case in cases if case["split"] == split]
        if len(selected) != 20 or sum(case["retrieve"] for case in selected) != 10:
            raise ValueError("Each split must contain ten positive and ten negative controls")
    retrieval = suite["retrieval"]
    if len(retrieval) != 20 or len({case["id"] for case in retrieval}) != 20:
        raise ValueError("Retrieval suite must have 20 unique cases")
    for case in retrieval:
        if not case["query"].strip() or ("domain" in case) == ("stack" in case):
            raise ValueError("Each retrieval case needs a query and exactly one domain or stack")
        if "domain" in case and case["domain"] not in CSV_CONFIG:
            raise ValueError("Unknown retrieval domain")
        if "stack" in case and case["stack"] not in STACK_CONFIG:
            raise ValueError("Unknown retrieval stack")
    return suite


def bundle(suite_path: Path, output: Path) -> dict:
    suite = load_suite(suite_path)
    if output.exists():
        raise ValueError("Refusing to overwrite an existing M2 bundle")
    output.mkdir(parents=True)
    (output / "suite.json").write_bytes(suite_path.read_bytes())
    records = []
    for case in suite["retrieval"]:
        if "stack" in case:
            raw = search_stack(case["query"], case["stack"], max_results=3, engine="bm25", expand=True)
        else:
            raw = search(case["query"], domain=case["domain"], max_results=3, engine="bm25", expand=True)
        if "error" in raw:
            raise ValueError(f"{case['id']}: {raw['error']}")
        intent = classify_intent(case["query"]).value
        with_intent = {**raw, "intent": intent}
        compact = format_compact(with_intent)
        existing = format_by_intent(intent, with_intent)
        if existing is None:
            existing = format_output(with_intent)
        artifact = {
            "case": case, "raw": raw, "existing_intent_output": existing, "compact": compact,
            "review": {
                "source_verification": "pending", "applicability": "pending",
                "correct_application": "not_measured",
            },
        }
        filename = f"{case['id']}.json"
        (output / filename).write_text(encoded(artifact) + "\n")
        records.append({
            "case_id": case["id"], "artifact": filename, "sha256": digest(output / filename),
            "raw_json_characters": len(encoded(raw)),
            "raw_minified_json_characters": len(compact_json(raw)),
            "existing_intent_characters": len(existing),
            "compact_json_characters": len(compact_json(compact)),
            "matched_count": compact["matched_count"], "returned_count": compact["count"],
            "omitted_count": compact["omitted_count"], "status": compact["status"],
        })
    code_files = [
        "src/backend-pro-max/scripts/core.py", "src/backend-pro-max/scripts/templates.py",
        "src/backend-pro-max/scripts/search.py", "src/backend-pro-max/scripts/mcp_server.py",
        "src/backend-pro-max/scripts/gen_tools_schema.py", "scripts/evaluate_m2.py",
        "src/backend-pro-max/templates/base/SKILL.md",
        "src/backend-pro-max/templates/base/skill-content.md",
        ".claude/skills/backend-pro-max/SKILL.md", "tools.json",
    ]
    report = {
        "status": "offline_structural_checks_only", "suite_sha256": digest(suite_path),
        "independent_review": "pending", "model_experiments": "not_run",
        "python": platform.python_version(),
        "search_settings": {"engine": "bm25", "max_results": 3, "expand": True},
        "activation_cases": len(suite["activation"]), "retrieval_cases": len(records),
        "compact_limit_characters": COMPACT_MAX_CHARS,
        "compact_bound_passed": all(row["compact_json_characters"] <= COMPACT_MAX_CHARS for row in records),
        "compact_smaller_than_raw_cases": sum(
            row["compact_json_characters"] < row["raw_json_characters"] for row in records
        ),
        "compact_smaller_than_minified_raw_cases": sum(
            row["compact_json_characters"] < row["raw_minified_json_characters"] for row in records
        ),
        "median_raw_json_characters": statistics.median(row["raw_json_characters"] for row in records),
        "median_raw_minified_json_characters": statistics.median(
            row["raw_minified_json_characters"] for row in records
        ),
        "median_compact_json_characters": statistics.median(row["compact_json_characters"] for row in records),
        "zero_match_cases": [row["case_id"] for row in records if row["matched_count"] == 0],
        "budget_exhausted_cases": [row["case_id"] for row in records if row["status"] == "budget_exhausted"],
        "records": records,
        "code_and_guidance_sha256": {name: digest(ROOT / name) for name in code_files},
        "corpus_sha256": {
            str(path.relative_to(DATA_DIR)): digest(path)
            for path in sorted(DATA_DIR.rglob("*.csv"))
        },
        "limitations": [
            "Draft author-constructed cases; not independently reviewed or held out from development.",
            "Character lengths measure representation size, not tokens, relevance, or agent performance.",
            "Compare minified raw as well as default pretty raw to separate whitespace savings from field selection.",
            "No external URLs were visited; copied source URLs and timestamps are not source verification.",
            "Whole-unit omission can remove useful evidence. Smaller output is not automatically better.",
            "Activation, 80%/10% targets, and 90% applicability have not been evaluated.",
        ],
    }
    (output / "summary.json").write_text(encoded(report) + "\n")
    return report


def score_activation(suite_path: Path, observations_path: Path) -> dict:
    suite = load_suite(suite_path)
    supplied = json.loads(observations_path.read_text())
    if supplied.get("suite_sha256") != digest(suite_path):
        raise ValueError("Observations do not match the frozen suite")
    if supplied.get("surface") != "mcp":
        raise ValueError("This scorer accepts real MCP-client observations only; do not mix skill/native surfaces")
    for key in ("client", "client_version", "model"):
        if not isinstance(supplied.get(key), str) or not supplied[key].strip():
            raise ValueError(f"Missing experiment metadata: {key}")
    if not isinstance(supplied.get("settings"), dict):
        raise ValueError("Explicit model/client settings are required")
    manifest_hash = supplied.get("tool_manifest_sha256")
    if not isinstance(manifest_hash, str) or re.fullmatch(r"[a-f0-9]{64}", manifest_hash) is None:
        raise ValueError("Record the SHA-256 of the exact tool manifest exposed to the model")
    repetitions = supplied.get("repetitions")
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError("Repetitions must be a positive integer")
    cases = {case["id"]: case for case in suite["activation"]}
    known = {tool["name"] for tool in TOOLS}
    seen = {}
    for observation in supplied["observations"]:
        case_id, repeat = observation["case_id"], observation["repeat"]
        key = (case_id, repeat)
        if case_id not in cases or type(repeat) is not int or not 0 <= repeat < repetitions or key in seen:
            raise ValueError("Unassigned or duplicate activation observation")
        if observation.get("status") not in ("completed", "client_error"):
            raise ValueError("Invalid activation status")
        calls = observation.get("tool_calls")
        if not isinstance(calls, list):
            raise ValueError("Tool calls must be an explicit list (empty means no calls)")
        for call in calls:
            if not isinstance(call.get("name"), str) or type(call.get("is_error")) is not bool:
                raise ValueError("Each tool call needs a name and an explicit error flag")
            if call["name"].startswith("backendpro") and call["name"] not in known:
                raise ValueError("Unrecognized BackendPro tool name; normalize the actual MCP trace")
        seen[key] = observation
    reports = []
    for split in ("development", "evaluation"):
        selected = [case for case in cases.values() if case["split"] == split]
        for repeat in range(repetitions):
            positives = negatives = missing = errors = failed_calls = 0
            for case in selected:
                observation = seen.get((case["id"], repeat))
                if observation is None:
                    missing += 1
                    continue
                calls = [call for call in observation["tool_calls"] if call["name"] in known]
                failed_calls += sum(call["is_error"] for call in calls)
                errors += observation["status"] != "completed"
                if calls:
                    if case["retrieve"]:
                        positives += 1
                    else:
                        negatives += 1
            complete = missing == errors == failed_calls == 0
            reports.append({
                "split": split, "repeat": repeat, "positive_cases": 10, "negative_cases": 10,
                "positive_activated": positives, "negative_activated": negatives,
                "appropriate_activation_rate": positives / 10,
                "unnecessary_activation_rate": negatives / 10,
                "positive_wilson_95": wilson(positives, 10) if missing == 0 else None,
                "negative_wilson_95": wilson(negatives, 10) if missing == 0 else None,
                "missing_observations": missing, "client_errors": errors, "failed_knowledge_calls": failed_calls,
                "engineering_thresholds_met": complete and positives >= 8 and negatives <= 1,
            })
    evaluation = [row for row in reports if row["split"] == "evaluation"]
    return {
        "status": "independent_review_pending", "suite_sha256": digest(suite_path),
        "observations_sha256": digest(observations_path),
        "provenance": {
            key: supplied[key]
            for key in ("surface", "client", "client_version", "model", "settings", "tool_manifest_sha256")
        },
        "repetitions": repetitions, "per_repeat": reports,
        "all_evaluation_repeats_meet_targets": all(row["engineering_thresholds_met"] for row in evaluation),
        "minimum_three_repeats_met": repetitions >= 3,
        "evaluation_activation_rate_range": [
            min(row["appropriate_activation_rate"] for row in evaluation),
            max(row["appropriate_activation_rate"] for row in evaluation),
        ],
        "acceptance_verified": False,
        "limitations": [
            "External observations are supplied by the caller; this scorer does not execute or certify a client.",
            "Draft labels still require independent review before a separately frozen evaluation.",
            "Intervals are per repeat; repeated observations of one task are not independent samples.",
            "Tool invocation does not establish relevant evidence or correct application.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("bundle", "activation"))
    parser.add_argument("--suite", type=Path, default=SUITE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observations", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new path")
    try:
        if args.mode == "bundle":
            if args.observations is not None:
                parser.error("--observations is only used in activation mode")
            result = bundle(args.suite, args.output)
        else:
            if args.observations is None:
                parser.error("activation requires --observations")
            result = score_activation(args.suite, args.observations)
            args.output.write_text(encoded(result) + "\n")
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.error(str(error))
    print(result["status"])


if __name__ == "__main__":
    main()
