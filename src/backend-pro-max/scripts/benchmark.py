"""Compare retrieval pipelines on a JSON file of labeled domain queries."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from . import core, evidence, rerank, semantic, templates, versions
from .templates import compact_json

MODES = ("bm25-no-expand", "bm25", "hybrid", "hybrid-rerank")


def pinned_token_counter(path: Path, sha256: str, identity: str):
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256) or not identity:
        raise ValueError("A tokenizer identity and exact lowercase SHA256 are required")
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
        raise ValueError("Tokenizer SHA256 mismatch")
    try:
        from tokenizers import Tokenizer
    except ImportError as error:
        raise RuntimeError("Install backendpro[tokens] for local pinned-tokenizer accounting") from error
    tokenizer = Tokenizer.from_file(str(path))
    # A tokenizer snapshot may contain truncation/padding configuration; neither is accounting.
    tokenizer.no_truncation()
    tokenizer.no_padding()
    return lambda text: len(tokenizer.encode(text, add_special_tokens=False).ids), {
        "identity": identity, "sha256": sha256, "engine": "tokenizers", "version": version("tokenizers"),
        "add_special_tokens": False, "padding": False, "truncation": False,
    }


def evaluate_evidence(cases: list[dict], budgets: list[int], *, token_counter=None, candidates: int = 20) -> dict:
    if not cases or not budgets or len(set(budgets)) != len(budgets) or any(type(n) is not int or n < 1 for n in budgets):
        raise ValueError("Evidence cases and unique positive budgets are required")
    if type(candidates) is not int or candidates < 1:
        raise ValueError("Positive candidate count required")
    reports = {}
    for budget in budgets:
        details = []
        for case in cases:
            stack = case.get("stack")
            domain = case.get("domain")
            if bool(stack) == bool(domain) or not isinstance(case.get("query"), str) or not case["query"].strip():
                raise ValueError("Evidence cases need one explicit scope and a non-empty query")
            config = core.STACK_CONFIG.get(stack) if stack else core.CSV_CONFIG.get(domain)
            if config is None:
                raise ValueError("Unknown evidence benchmark scope")
            labels = case.get("relevant")
            critical = case.get("critical_fields")
            if (
                not isinstance(labels, list) or not all(isinstance(name, str) for name in labels)
                or len(set(labels)) != len(labels) or not isinstance(critical, list)
                or not all(isinstance(field, str) for field in critical)
            ):
                raise ValueError("Evidence cases need unique relevant names and critical_fields")
            available = core._load_csv(core.DATA_DIR / config["file"]) + evidence.supplemental_rows(config["file"])
            named = {row.get("Guideline") if stack else row.get(config["output_cols"][0]): row for row in available}
            if set(labels) - named.keys() or any(not named[name].get(field) for name in labels for field in critical):
                raise ValueError("Unknown evidence label or critical field")
            raw = (core.search_stack(case["query"], stack, max_results=candidates, evidence=True) if stack
                   else core.search(case["query"], domain, max_results=candidates, evidence=True))
            response = evidence.format_evidence(
                raw, 24000 if token_counter else budget, library_versions=case.get("library_versions"),
                token_counter=token_counter, max_tokens=budget if token_counter else None,
            )
            text = compact_json(response)
            retained = {unit["title"]: unit for unit in response["results"]}
            relevant = set(labels) & retained.keys()
            expected_fields = len(labels) * len(critical)
            intact = sum(
                retained[name]["facts"].get(field) == named[name][field]
                for name in relevant for field in critical
            )
            bindings_valid = all(
                evidence.evidence_detail(unit["id"])["binding"] == unit["binding"]
                for unit in response["results"]
            )
            details.append({
                "query": case["query"], "retained": list(retained), "count": response["count"],
                "relevance_recall": len(relevant) / len(labels) if labels else None,
                "labeled_precision": len(relevant) / response["count"] if response["count"] else None,
                "critical_field_retention": intact / expected_fields if expected_fields else None,
                "version_matches": {unit["title"]: unit["version_match"] for unit in response["results"]},
                "bindings_valid": bindings_valid,
                "omissions_accounted": response["matched_count"] == response["count"] + sum(response["omissions"].values()),
                "omissions": response["omissions"],
                "characters": len(text), "tokens": token_counter(text) if token_counter else None,
                "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            })
        reports[str(budget)] = {
            "queries": details,
            **{
                metric: statistics.mean(values) if values else None
                for metric in ("relevance_recall", "labeled_precision", "critical_field_retention")
                for values in [[item[metric] for item in details if item[metric] is not None]]
            },
            "all_bindings_valid": all(item["bindings_valid"] for item in details),
            "all_omissions_accounted": all(item["omissions_accounted"] for item in details),
        }
    return {
        "budget_unit": "tokens" if token_counter else "characters", "budgets": reports,
        "character_ceiling": 24000 if token_counter else None,
        "quality_gates_demonstrated": False,
        "measurement_scope": "Whole evidence JSON only; excludes transport envelopes, chat templates and generation. Author labels, not independent applicability review or coding outcomes.",
    }


def ranking_metrics(ranked: list[str], relevant: list[str], top_k: int) -> dict:
    if top_k < 1 or not relevant:
        raise ValueError("top_k and the relevant set must be non-empty")
    relevant_set = set(relevant)
    seen = set()
    gains = []
    for name in ranked[:top_k]:
        gains.append(int(name in relevant_set and name not in seen))
        seen.add(name)
    dcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(top_k, len(relevant_set))))
    return {
        "recall": sum(gains) / len(relevant_set),
        "precision": sum(gains) / top_k,
        "mrr": next((1 / rank for rank, gain in enumerate(gains, 1) if gain), 0.0),
        "ndcg": dcg / ideal,
    }


def validate_cases(cases: list[dict]):
    if not cases:
        raise ValueError("At least one benchmark query is required")
    for case in cases:
        stack = case.get("stack")
        config = core.STACK_CONFIG.get(stack) if stack else core.CSV_CONFIG.get(case.get("domain"))
        if config is None or not isinstance(case.get("query"), str) or not case["query"].strip():
            raise ValueError("Each case needs a known scope and non-empty query")
        if stack and case.get("domain"):
            raise ValueError("Use exactly one domain or stack")
        relevant = case.get("relevant")
        answerable = case.get("answerable", True)
        if type(answerable) is not bool or not isinstance(relevant, list) or not all(isinstance(name, str) for name in relevant):
            raise ValueError("Each case needs relevant row names")
        if bool(relevant) != answerable or len(set(relevant)) != len(relevant):
            raise ValueError("Answerable cases require unique relevant labels; unanswerable cases require an empty list")
        rows = core._load_csv(core.DATA_DIR / config["file"])
        name_col = "Guideline" if stack else config["output_cols"][0]
        names = {row[name_col] for row in rows}
        unknown = set(relevant) - names
        if unknown:
            raise ValueError(f"Unknown relevant rows in {stack or case['domain']}: {sorted(unknown)}")


def evaluate(cases: list[dict], modes=MODES, top_k: int = 5, candidates: int = 20, repeats: int = 3) -> dict:
    validate_cases(cases)
    if top_k < 1 or candidates < top_k or repeats < 1 or not modes or any(mode not in MODES for mode in modes):
        raise ValueError("Invalid modes, top_k, candidate count, or repeat count")
    if any(mode.startswith("hybrid") for mode in modes) and semantic._get_model() is None:
        raise RuntimeError("Install backendpro[semantic]; benchmarks must not silently fall back")
    if "hybrid-rerank" in modes and rerank._get_model() is None:
        raise RuntimeError("Install backendpro[rerank]; benchmarks must not silently fall back")

    reports = {}
    for mode in modes:
        details = []
        durations = []
        for case in cases:
            def retrieve(case=case, mode=mode):
                scope = {"stack": case["stack"]} if case.get("stack") else {"domain": case["domain"]}
                search = core.search_stack if case.get("stack") else core.search
                result = search(
                    case["query"], **scope, max_results=top_k, candidate_pool=candidates,
                    engine="hybrid" if mode.startswith("hybrid") else "bm25",
                    rerank=mode == "hybrid-rerank", expand=mode != "bm25-no-expand", diagnostics=True,
                )
                if "error" in result:
                    raise RuntimeError(result["error"])
                if result["retrieval"]["fallbacks"]:
                    raise RuntimeError("Benchmarks must not silently fall back: " + "; ".join(result["retrieval"]["fallbacks"]))
                return result

            retrieve()
            for _repeat in range(repeats):
                started = time.perf_counter()
                result = retrieve()
                durations.append((time.perf_counter() - started) * 1000)
            name_col = "Guideline" if case.get("stack") else core.CSV_CONFIG[case["domain"]]["output_cols"][0]
            ranked = [row[name_col] for row in result["results"]]
            answerable = case.get("answerable", True)
            details.append({
                "query": case["query"], "domain": case.get("domain"), "stack": case.get("stack"),
                "ranked": ranked, "answerable": answerable, "abstained": not ranked,
                "retrieval": result["retrieval"],
                **(ranking_metrics(ranked, case["relevant"], top_k) if answerable else {}),
            })
        answerable_details = [detail for detail in details if detail["answerable"]]
        unanswerable_details = [detail for detail in details if not detail["answerable"]]
        reports[mode] = {
            **{metric: statistics.mean(detail[metric] for detail in answerable_details) if answerable_details else None
               for metric in ("recall", "precision", "mrr", "ndcg")},
            "false_no_match_rate": statistics.mean(d["abstained"] for d in answerable_details) if answerable_details else None,
            "unanswerable_abstention_rate": statistics.mean(d["abstained"] for d in unanswerable_details) if unanswerable_details else None,
            "answerable_cases": len(answerable_details), "unanswerable_cases": len(unanswerable_details),
            "p50_ms": statistics.median(durations),
            "p95_ms": sorted(durations)[math.ceil(len(durations) * 0.95) - 1],
            "queries": details,
        }
    return {
        "top_k": top_k, "candidates": candidates, "repeats": repeats, "modes": reports,
        "quality_gates_demonstrated": False,
        "label_note": "Metrics use supplied labels, not verified completeness or independent applicability review. Incomplete labels undercount precision. Zero returned rows is not relevance.",
        "targets": {"recall_at_5": .90, "reviewed_precision_at_5": .80, "false_no_match_rate": .05},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--top-k", type=int, default=5)
    pools = parser.add_mutually_exclusive_group()
    pools.add_argument("--candidates", type=int, default=20)
    pools.add_argument("--candidate-pools", type=int, nargs="+", help="Matched ablations, e.g. 20 50")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-p95-ms", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--evidence-budgets", nargs="+", type=int,
                        help="Opt-in evidence selection at fixed character budgets, or token budgets with a pinned tokenizer")
    parser.add_argument("--tokenizer-file", type=Path)
    parser.add_argument("--tokenizer-sha256")
    parser.add_argument("--tokenizer-id", help="Auditable target-model/tokenizer identity including source revision")
    args = parser.parse_args()
    if args.max_p95_ms is not None and (not math.isfinite(args.max_p95_ms) or args.max_p95_ms <= 0):
        parser.error("--max-p95-ms must be finite and positive")
    raw = args.dataset.read_bytes()
    dataset = json.loads(raw)
    tokenizer_info = None
    token_counter = None
    try:
        if any((args.tokenizer_file, args.tokenizer_sha256, args.tokenizer_id)):
            if not args.evidence_budgets or not all((args.tokenizer_file, args.tokenizer_sha256, args.tokenizer_id)):
                raise ValueError("Token accounting requires --evidence-budgets and all three --tokenizer-* options")
            token_counter, tokenizer_info = pinned_token_counter(
                args.tokenizer_file, args.tokenizer_sha256, args.tokenizer_id,
            )
        if args.evidence_budgets:
            if (
                args.candidate_pools or args.max_p95_ms is not None or args.top_k != 5
                or args.repeats != 3 or args.modes != list(MODES)
            ):
                raise ValueError("Evidence budgets cannot be combined with ranking-mode, top-k, repeat, pool-sweep or latency options")
            report = evaluate_evidence(
                dataset["queries"], args.evidence_budgets, token_counter=token_counter, candidates=args.candidates,
            )
        elif args.candidate_pools:
            if len(set(args.candidate_pools)) != len(args.candidate_pools):
                raise ValueError("Candidate pools must be unique")
            report = {"candidate_pools": {
                str(pool): evaluate(dataset["queries"], args.modes, args.top_k, pool, args.repeats)
                for pool in args.candidate_pools
            }}
        else:
            report = evaluate(dataset["queries"], args.modes, args.top_k, args.candidates, args.repeats)
    except (ValueError, RuntimeError, OSError) as error:
        parser.error(str(error))
    packages = {}
    for package in ("sentence-transformers", "torch", "numpy"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = None
    report.update({
        "dataset": dataset.get("name", args.dataset.name),
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "corpus_sha256": {
            ("stack:" + case["stack"] if case.get("stack") else case["domain"]): hashlib.sha256(
                (core.DATA_DIR / (core.STACK_CONFIG[case["stack"]] if case.get("stack") else core.CSV_CONFIG[case["domain"]])["file"]).read_bytes()
            ).hexdigest() for case in dataset["queries"]
        },
        "python": platform.python_version(), "platform": platform.platform(), "packages": packages,
        "models": {
            "embedding": {"name": semantic._MODEL_NAME, "revision": semantic._MODEL_REVISION},
            "reranker": {"name": rerank._MODEL_NAME, "revision": rerank._MODEL_REVISION},
        },
        "source_sha256": {
            Path(__file__).name: hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            **{
            Path(module.__file__).name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for module in (core, semantic, rerank)
            },
        },
        "latency_scope": "warm queries; model loading, downloads and index building excluded",
        "measurement_scope": "Ranked raw rows before optional compact packing; not evidence application or coding outcomes.",
        "limitations": dataset.get("limitations", "Relevance labels require independent review"),
    })
    if args.evidence_budgets:
        report.update({
            "tokenizer": tokenizer_info,
            "quality_gates_demonstrated": False,
            "measurement_scope": "Whole evidence JSON only; excludes transport envelopes, chat templates and generation. Author labels, not independent applicability review or coding outcomes.",
            "latency_scope": "not measured",
            "models": {},
        })
        report["corpus_sha256"]["evidence.json"] = hashlib.sha256((evidence.DATA_DIR / "evidence.json").read_bytes()).hexdigest()
        report["source_sha256"].update({
            Path(module.__file__).name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for module in (evidence, templates, versions)
        })
    output = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    measured = report.get("candidate_pools", {"single": report}).values()
    if args.max_p95_ms is not None and any(
        mode["p95_ms"] > args.max_p95_ms for result in measured for mode in result["modes"].values()
    ):
        raise SystemExit("Warm-query p95 latency budget exceeded")


if __name__ == "__main__":
    main()
