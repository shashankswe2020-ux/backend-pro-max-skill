#!/usr/bin/env python3
"""
Conflict detector — surface known architectural tensions between knowledge
base entries across domains.

Usage:
    backendpro conflicts [--domain <domain>] [--json]
    python scripts/conflicts.py [--domain <domain>] [--json]

This is a static-analysis pass. It runs a curated set of tension rules against
the KB and emits warnings for trade-offs that users should be aware of.
"""

from __future__ import annotations

import argparse
import json as _json
import sys

try:
    from .core import search
except ImportError:
    from core import search  # type: ignore[no-redef]


# ============ CONFLICT RULES ============
# Each rule defines a pair of domains/queries that represent a known
# architectural tension. The scanner searches both sides and, if both
# return results, surfaces the tension.

CONFLICT_RULES: list[dict] = [
    {
        "id": "retry-vs-latency",
        "description": "Retries improve reliability but add p99 latency",
        "side_a": {"domain": "reliability", "query": "retry backoff"},
        "side_b": {"domain": "performance", "query": "retry latency"},
    },
    {
        "id": "outbox-vs-cdc",
        "description": "Outbox pattern writes to DB; CDC reads from WAL — different consistency trade-offs",
        "side_a": {"domain": "pattern", "query": "transactional outbox"},
        "side_b": {"domain": "data", "query": "change data capture CDC"},
    },
    {
        "id": "cache-vs-consistency",
        "description": "Caching improves latency but risks serving stale data",
        "side_a": {"domain": "cache", "query": "cache invalidation"},
        "side_b": {"domain": "consistency", "query": "strong consistency"},
    },
    {
        "id": "microservices-vs-complexity",
        "description": "Microservices enable team autonomy but increase operational complexity",
        "side_a": {"domain": "architecture", "query": "microservices"},
        "side_b": {"domain": "reliability", "query": "distributed failure"},
    },
    {
        "id": "event-sourcing-vs-query",
        "description": "Event sourcing preserves history but complicates queries",
        "side_a": {"domain": "pattern", "query": "event sourcing"},
        "side_b": {"domain": "performance", "query": "query complexity"},
    },
    {
        "id": "strong-consistency-vs-availability",
        "description": "Strong consistency reduces availability during partitions (CAP theorem)",
        "side_a": {"domain": "consistency", "query": "linearizable strong"},
        "side_b": {"domain": "reliability", "query": "availability partition"},
    },
    {
        "id": "sharding-vs-joins",
        "description": "Sharding scales writes but makes cross-shard joins expensive",
        "side_a": {"domain": "scaling", "query": "sharding partition"},
        "side_b": {"domain": "database", "query": "join cross-shard"},
    },
    {
        "id": "async-vs-debugging",
        "description": "Async messaging decouples services but makes debugging harder",
        "side_a": {"domain": "messaging", "query": "async decoupling"},
        "side_b": {"domain": "observability", "query": "distributed tracing"},
    },
    {
        "id": "rate-limiting-vs-ux",
        "description": "Rate limiting protects services but can degrade user experience",
        "side_a": {"domain": "security", "query": "rate limiting throttle"},
        "side_b": {"domain": "performance", "query": "latency user experience"},
    },
    {
        "id": "normalization-vs-read-perf",
        "description": "Normalized schemas reduce duplication but require joins that hurt read performance",
        "side_a": {"domain": "database", "query": "normalization"},
        "side_b": {"domain": "performance", "query": "denormalization read"},
    },
    {
        "id": "saga-vs-consistency",
        "description": "Sagas enable distributed transactions but only provide eventual consistency",
        "side_a": {"domain": "pattern", "query": "saga orchestration"},
        "side_b": {"domain": "consistency", "query": "eventual consistency"},
    },
    {
        "id": "caching-layers-vs-memory",
        "description": "Multi-layer caching speeds up reads but increases memory cost and invalidation complexity",
        "side_a": {"domain": "cache", "query": "multi-layer L1 L2"},
        "side_b": {"domain": "cost", "query": "memory cost"},
    },
]


# ============ SCANNER ============
def scan_conflicts(
    domain: str | None = None,
    rules: list[dict] | None = None,
) -> list[dict]:
    """Scan for known tensions. Returns list of triggered conflicts."""
    rules = rules or CONFLICT_RULES
    tensions: list[dict] = []

    for rule in rules:
        # Filter by domain if specified
        if domain:
            side_a_domain = rule["side_a"]["domain"]
            side_b_domain = rule["side_b"]["domain"]
            if domain != side_a_domain and domain != side_b_domain:
                continue

        # Search both sides
        try:
            result_a = search(
                rule["side_a"]["query"],
                domain=rule["side_a"]["domain"],
                max_results=1,
                min_score=0.5,
            )
            result_b = search(
                rule["side_b"]["query"],
                domain=rule["side_b"]["domain"],
                max_results=1,
                min_score=0.5,
            )
        except Exception:  # noqa: BLE001
            continue

        hits_a = result_a.get("results", [])
        hits_b = result_b.get("results", [])

        if hits_a and hits_b:
            row_a = hits_a[0]
            row_b = hits_b[0]
            cite_a = row_a.get("_citation", f"[BPM:{rule['side_a']['domain']}]")
            cite_b = row_b.get("_citation", f"[BPM:{rule['side_b']['domain']}]")
            # Get the name/title of each row
            name_a = next((v for k, v in row_a.items() if k not in ("_score", "_citation") and v), "?")
            name_b = next((v for k, v in row_b.items() if k not in ("_score", "_citation") and v), "?")

            tensions.append({
                "id": rule["id"],
                "description": rule["description"],
                "side_a": {
                    "domain": rule["side_a"]["domain"],
                    "name": name_a,
                    "citation": cite_a,
                },
                "side_b": {
                    "domain": rule["side_b"]["domain"],
                    "name": name_b,
                    "citation": cite_b,
                },
            })

    return tensions


# ============ FORMATTERS ============
def format_tensions(tensions: list[dict]) -> str:
    """Format tensions as human-readable markdown."""
    if not tensions:
        return "✅ No known tensions detected."

    lines = [f"## ⚠ Architectural Tensions ({len(tensions)} found)\n"]
    for t in tensions:
        lines.append(
            f"**⚠ Tension [{t['id']}]:** {t['description']}\n"
            f"  - {t['side_a']['citation']} `{t['side_a']['domain']}` → {t['side_a']['name']}\n"
            f"  - {t['side_b']['citation']} `{t['side_b']['domain']}` → {t['side_b']['name']}\n"
        )
    return "\n".join(lines)


def format_tensions_json(tensions: list[dict]) -> str:
    """Format tensions as JSON."""
    return _json.dumps({"tensions": tensions, "count": len(tensions)}, indent=2)


# ============ CLI ============
def main() -> int:
    parser = argparse.ArgumentParser(description="Backend Pro Max Conflict Detector")
    parser.add_argument("--domain", type=str, default=None,
                        help="Limit scan to tensions involving this domain")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    tensions = scan_conflicts(domain=args.domain)

    if args.json:
        print(format_tensions_json(tensions))
    else:
        print(format_tensions(tensions))

    return 0


if __name__ == "__main__":
    sys.exit(main())
