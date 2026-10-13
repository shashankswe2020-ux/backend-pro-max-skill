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

from . import core, rerank, semantic

MODES = ("bm25-no-expand", "bm25", "hybrid", "hybrid-rerank")


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
    args = parser.parse_args()
    if args.max_p95_ms is not None and (not math.isfinite(args.max_p95_ms) or args.max_p95_ms <= 0):
        parser.error("--max-p95-ms must be finite and positive")
    raw = args.dataset.read_bytes()
    dataset = json.loads(raw)
    try:
        if args.candidate_pools:
            if len(set(args.candidate_pools)) != len(args.candidate_pools):
                raise ValueError("Candidate pools must be unique")
            report = {"candidate_pools": {
                str(pool): evaluate(dataset["queries"], args.modes, args.top_k, pool, args.repeats)
                for pool in args.candidate_pools
            }}
        else:
            report = evaluate(dataset["queries"], args.modes, args.top_k, args.candidates, args.repeats)
    except (ValueError, RuntimeError) as error:
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
