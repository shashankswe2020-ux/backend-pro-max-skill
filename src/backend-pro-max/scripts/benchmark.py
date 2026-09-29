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

MODES = ("bm25", "hybrid", "hybrid-rerank")


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
        "mrr": next((1 / rank for rank, gain in enumerate(gains, 1) if gain), 0.0),
        "ndcg": dcg / ideal,
    }


def validate_cases(cases: list[dict]):
    if not cases:
        raise ValueError("At least one benchmark query is required")
    for case in cases:
        config = core.CSV_CONFIG.get(case.get("domain"))
        if config is None or not isinstance(case.get("query"), str) or not case["query"].strip():
            raise ValueError("Each case needs a known domain and non-empty query")
        relevant = case.get("relevant")
        if not isinstance(relevant, list) or not relevant or not all(isinstance(name, str) for name in relevant):
            raise ValueError("Each case needs relevant row names")
        rows = core._load_csv(core.DATA_DIR / config["file"])
        names = {row[config["output_cols"][0]] for row in rows}
        unknown = set(relevant) - names
        if unknown:
            raise ValueError(f"Unknown relevant rows in {case['domain']}: {sorted(unknown)}")


def evaluate(cases: list[dict], modes=MODES, top_k: int = 5, candidates: int = 20, repeats: int = 3) -> dict:
    validate_cases(cases)
    if top_k < 1 or candidates < top_k or repeats < 1 or not modes or any(mode not in MODES for mode in modes):
        raise ValueError("Invalid modes, top_k, candidate count, or repeat count")
    if any(mode != "bm25" for mode in modes) and semantic._get_model() is None:
        raise RuntimeError("Install backendpro[semantic]; benchmarks must not silently fall back")
    if "hybrid-rerank" in modes and rerank._get_model() is None:
        raise RuntimeError("Install backendpro[rerank]; benchmarks must not silently fall back")

    reports = {}
    for mode in modes:
        details = []
        durations = []
        for case in cases:
            def retrieve(case=case, mode=mode):
                result = core.search(
                    case["query"], domain=case["domain"], max_results=candidates,
                    engine="bm25" if mode == "bm25" else "hybrid",
                )
                if "error" in result:
                    raise RuntimeError(result["error"])
                rows = result["results"]
                if mode == "hybrid-rerank":
                    rows = rerank.rerank(case["query"], rows, top_k=top_k)
                return rows[:top_k]

            retrieve()
            for _repeat in range(repeats):
                started = time.perf_counter()
                rows = retrieve()
                durations.append((time.perf_counter() - started) * 1000)
            name_col = core.CSV_CONFIG[case["domain"]]["output_cols"][0]
            ranked = [row[name_col] for row in rows]
            details.append({
                "query": case["query"], "domain": case["domain"], "ranked": ranked,
                **ranking_metrics(ranked, case["relevant"], top_k),
            })
        reports[mode] = {
            **{metric: statistics.mean(detail[metric] for detail in details) for metric in ("recall", "mrr", "ndcg")},
            "p50_ms": statistics.median(durations),
            "p95_ms": sorted(durations)[math.ceil(len(durations) * 0.95) - 1],
            "queries": details,
        }
    return {"top_k": top_k, "candidates": candidates, "repeats": repeats, "modes": reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidates", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-p95-ms", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.max_p95_ms is not None and (not math.isfinite(args.max_p95_ms) or args.max_p95_ms <= 0):
        parser.error("--max-p95-ms must be finite and positive")
    raw = args.dataset.read_bytes()
    dataset = json.loads(raw)
    try:
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
            domain: hashlib.sha256((core.DATA_DIR / core.CSV_CONFIG[domain]["file"]).read_bytes()).hexdigest()
            for domain in sorted({case["domain"] for case in dataset["queries"]})
        },
        "python": platform.python_version(), "platform": platform.platform(), "packages": packages,
        "models": {"embedding": semantic._MODEL_NAME, "reranker": rerank._MODEL_NAME},
        "latency_scope": "warm queries; model loading, downloads and index building excluded",
        "limitations": dataset.get("limitations", "Relevance labels require independent review"),
    })
    output = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.max_p95_ms is not None and any(mode["p95_ms"] > args.max_p95_ms for mode in report["modes"].values()):
        raise SystemExit("Warm-query p95 latency budget exceeded")


if __name__ == "__main__":
    main()
