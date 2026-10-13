#!/usr/bin/env python3
"""Generate tools.json — function-calling manifest for Backend Pro Max.

Dual-format: OpenAI ``functions`` and Anthropic ``tools``.
Tool contracts are maintained here; domain/stack enums use the core registries.
The MCP server publishes and validates these same contracts.

Usage:
    python scripts/gen_tools_schema.py            # write tools.json
    python scripts/gen_tools_schema.py --check     # exit 1 if stale
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from .core import CSV_CONFIG, STACK_CONFIG
except ImportError:
    from core import CSV_CONFIG, STACK_CONFIG

# ── Tool definitions ──────────────────────────────────────────────
# Each entry describes one public function.  The schema is maintained here
# (single source of truth) and serialised to both OpenAI and Anthropic formats.

TOOLS = [
    {
        "name": "evidence_detail",
        "description": "Expand a bpme evidence ID returned by evidence-format search into its complete local source row and immutable content binding. No network access. An edited or removed record fails explicitly; repeat the search. This opt-in detail response is not character-packed.",
        "parameters": {
            "type": "object",
            "properties": {"evidence_id": {"type": "string", "pattern": "^bpme:[0-9a-f]{64}$"}},
            "required": ["evidence_id"],
        },
    },
    {
        "name": "search",
        "description": "Retrieve cited backend guidance for transaction boundaries, idempotency, retries, schema migrations, and operational failure handling. Use when external engineering guidance can affect correctness; skip typos, link fixes, and self-contained local edits. Domain is auto-detected if omitted. Raw results are the default; compact returns bounded, source-linked evidence with explicit gaps, not a confidence score.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'circuit breaker', 'exactly once delivery')."},
                "domain": {
                    "type": ["string", "null"],
                    "description": "Knowledge domain. Auto-detected if omitted.",
                    "enum": [*CSV_CONFIG, None],
                    "default": None,
                },
                "max_results": {"type": "integer", "description": "Cap on returned rows (default 5).", "default": 5},
                "min_score": {"type": "number", "description": "Drop results with BM25 score ≤ this (default 0.0).", "default": 0.0},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_all",
        "description": "Retrieve cited guidance across domains when a backend issue spans concerns, such as retry policy plus database consistency. Prefer a focused search when the domain is known; do not call merely because a file is backend code. Use compact for bounded evidence; use raw for complete returned rows.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "max_results": {"type": "integer", "description": "Max results per domain (default 2).", "default": 2},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_stack",
        "description": "Retrieve guidelines for a known supported language/framework, such as transaction handling in Spring or async database access in FastAPI. Search the relevant named stack first when retrieval is warranted; never guess a stack. Confirm version-sensitive APIs against pinned official documentation. Skip trivial local edits. Supports raw or compact evidence.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'error handling', 'connection pooling')."},
                "stack": {
                    "type": "string",
                    "description": "Stack name.",
                    "enum": list(STACK_CONFIG),
                },
                "max_results": {"type": "integer", "description": "Cap on returned rows (default 5).", "default": 5},
            },
            "required": ["query", "stack"],
        },
    },
    {
        "name": "compare",
        "description": "Compare two or more named backend technologies or patterns with citations when the user is making a trade-off decision. Not needed for an already-specified local implementation detail.",
        "parameters": {
            "type": "object",
            "properties": {
                "names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "description": "Names to compare (e.g. ['Kafka', 'RabbitMQ']).",
                },
                "domain": {
                    "type": ["string", "null"], "enum": [*CSV_CONFIG, None], "default": None,
                    "description": "Force a domain (auto-detected if omitted).",
                },
            },
            "required": ["names"],
        },
    },
    {
        "name": "decide",
        "description": "Recommend backend candidates for a requirement with constraints such as consistency, throughput, cloud, and cost. Uses the existing decision engine; check assumptions and trade-offs, not just rank. Use search for a focused fact instead.",
        "parameters": {
            "type": "object",
            "properties": {
                "requirement": {
                    "type": "string",
                    "description": "Natural-language requirement (e.g. 'message broker for 100k msg/s, exactly once, on AWS').",
                },
            },
            "required": ["requirement"],
        },
    },
    {
        "name": "adr",
        "description": "Draft a cited Architecture Decision Record when a backend decision needs documented context and alternatives. Provide relevant context domains; do not generate an ADR for an ordinary code edit.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "ADR title (e.g. 'Adopt outbox pattern')."},
                "context_domains": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(CSV_CONFIG)},
                    "minItems": 1,
                    "description": "Domains to search for context.",
                },
            },
            "required": ["title", "context_domains"],
        },
    },
    {
        "name": "design",
        "description": "Draft a backend system-design scaffold with capacity math when architecture or scale decisions are requested. Verify workload assumptions, consistency, and failure modes; this is not a substitute for repository inspection or measured capacity.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "System description with optional scale numbers (e.g. 'URL shortener serving 10M reads/day').",
                },
            },
            "required": ["description"],
        },
    },
    {
        "name": "find_stale",
        "description": "Audit a domain for stale knowledge-base metadata before relying on potentially outdated guidance. Last Updated is row metadata, not proof that an external source was checked today.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "enum": list(CSV_CONFIG), "description": "Domain to audit."},
                "months": {"type": "integer", "minimum": 0, "description": "Age threshold in months."},
            },
            "required": ["domain", "months"],
        },
    },
]

for _tool in TOOLS:
    _tool["parameters"]["additionalProperties"] = False
    if _tool["name"] in ("search", "search_all", "search_stack"):
        _tool["description"] += " BM25 stays the offline default. Optional hybrid/semantic engines and reranking report requested/effective execution and fallbacks. Explicit scopes are never widened; diagnostics exposes routing hints only."
        _tool["parameters"]["properties"].update({
            "engine": {
                "type": "string", "enum": ["bm25", "hybrid", "semantic"], "default": "bm25",
                "description": "Optional model engines require backendpro[semantic]; missing dependencies fall back explicitly.",
            },
            "rerank": {
                "type": "boolean", "default": False,
                "description": "Cross-encoder candidate reranking, requiring backendpro[rerank].",
            },
            "candidate_pool": {
                "type": ["integer", "null"], "minimum": 1, "default": None,
                "description": "Candidates per scope before final selection; >= max_results. Defaults to max(20,max_results) with reranking, otherwise max_results.",
            },
            "diagnostics": {"type": "boolean", "default": False, "description": "Include engine, scope and candidate diagnostics even for default BM25."},
            "expand": {"type": "boolean", "default": True, "description": "Apply existing synonym expansion to lexical retrieval."},
            "min_score": {"type": "number", "default": 0.0, "description": "Exclude pre-rerank scores <= this: BM25, cosine similarity or RRF, depending on effective engine. Not confidence."},
            "max_age_months": {"type": ["integer", "null"], "minimum": 0, "default": None, "description": "Exclude stale rows before candidate selection; rows with missing dates are kept."},
            "constraints": {"type": ["string", "null"], "default": None, "description": "Existing constraint preferences, e.g. cloud=gcp,cost=low. Prioritize satisfied preferences within the candidate pool; unknown metadata is not a hard exclusion."},
            "max_chars": {"type": "integer", "minimum": 1, "default": 6000, "description": "Evidence-format JSON character budget including metadata, excluding transport envelopes. Whole units only."},
            "project_path": {"type": ["string", "null"], "default": None, "description": "Evidence format only. Explicit local directory for root Python manifest/lockfile inspection; no execution, recursion or network. Omit to avoid workspace reads."},
            "library_versions": {"type": ["object", "null"], "additionalProperties": {"type": "string"}, "default": None, "description": "Evidence format only. Explicit numeric release versions, e.g. pydantic: 2.10.6. Conflicts with local files remain conflicts, never overrides."},
        })
        _tool["parameters"]["properties"]["response_format"] = {
            "type": "string", "enum": ["raw", "compact", "evidence"], "default": "raw",
            "description": "raw preserves returned rows; compact keeps legacy 6000-character packing. Opt-in evidence adds source-bound version metadata, diverse whole-unit selection and omission counts within max_chars. Selection only considers retrieved rows; raise max_results to widen candidates. Unknown versions are not compatibility claims.",
        }
    for _name, _property in _tool["parameters"]["properties"].items():
        if _name == "max_results":
            _property["minimum"] = 1


def _to_openai(tools):
    """OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tools
    ]


def _to_anthropic(tools):
    """Anthropic tool_use format."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        }
        for t in tools
    ]


def generate():
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "_generated": "Auto-generated by scripts/gen_tools_schema.py — do not hand-edit.",
        "openai": _to_openai(TOOLS),
        "anthropic": _to_anthropic(TOOLS),
    }


def main():
    out_path = Path(__file__).resolve().parent.parent.parent.parent / "tools.json"
    new_content = json.dumps(generate(), indent=2, ensure_ascii=False) + "\n"

    if "--check" in sys.argv:
        if not out_path.exists():
            print(f"FAIL: {out_path} does not exist. Run without --check to generate.", file=sys.stderr)
            sys.exit(1)
        existing = out_path.read_text(encoding="utf-8")
        if existing != new_content:
            print(f"FAIL: {out_path} is stale. Regenerate with: python scripts/gen_tools_schema.py", file=sys.stderr)
            sys.exit(1)
        print("OK: tools.json is up to date.")
        sys.exit(0)

    out_path.write_text(new_content, encoding="utf-8")
    print(f"Wrote {out_path} ({len(TOOLS)} tools)")


if __name__ == "__main__":
    main()
