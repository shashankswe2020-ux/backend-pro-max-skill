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
        _tool["parameters"]["properties"]["response_format"] = {
            "type": "string", "enum": ["raw", "compact"], "default": "raw",
            "description": "raw preserves returned rows; compact bounds JSON text to 6000 characters by omitting whole trailing evidence units.",
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
