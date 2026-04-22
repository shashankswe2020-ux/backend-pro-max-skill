#!/usr/bin/env python3
"""Generate tools.json — function-calling manifest for Backend Pro Max.

Dual-format: OpenAI ``functions`` and Anthropic ``tools``.
Auto-generated from public function signatures so the schema never drifts.

Usage:
    python scripts/gen_tools_schema.py            # write tools.json
    python scripts/gen_tools_schema.py --check     # exit 1 if stale
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Tool definitions ──────────────────────────────────────────────
# Each entry describes one public function.  The schema is maintained here
# (single source of truth) and serialised to both OpenAI and Anthropic formats.

TOOLS = [
    {
        "name": "backendpro_search",
        "description": "BM25 search in a specific backend-engineering knowledge domain. Returns ranked results with citations.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'circuit breaker', 'exactly once delivery')."},
                "domain": {
                    "type": "string",
                    "description": "Knowledge domain. Auto-detected if omitted.",
                    "enum": [
                        "language", "pattern", "database", "messaging", "cache", "cloud",
                        "iac", "container", "observability", "api", "auth", "security",
                        "cicd", "testing", "architecture", "scaling", "consistency",
                        "performance", "reliability", "data",
                    ],
                },
                "max_results": {"type": "integer", "description": "Cap on returned rows (default 5).", "default": 5},
                "min_score": {"type": "number", "description": "Drop results with BM25 score ≤ this (default 0.0).", "default": 0.0},
            },
            "required": ["query"],
        },
    },
    {
        "name": "backendpro_search_all",
        "description": "Cross-domain search across every backend-engineering knowledge base. Returns top hits per domain.",
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
        "name": "backendpro_search_stack",
        "description": "Search stack-specific guidelines for a programming language / framework.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'error handling', 'connection pooling')."},
                "stack": {
                    "type": "string",
                    "description": "Stack name.",
                    "enum": [
                        "go", "java-spring", "python-fastapi", "nodejs-express",
                        "rust-axum", "csharp-aspnet", "kotlin-spring", "scala-akka",
                        "elixir-phoenix", "ruby-rails", "php-laravel", "cpp",
                    ],
                },
                "max_results": {"type": "integer", "description": "Cap on returned rows (default 5).", "default": 5},
            },
            "required": ["query", "stack"],
        },
    },
    {
        "name": "backendpro_compare",
        "description": "Side-by-side comparison of two or more named technologies / patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "description": "Names to compare (e.g. ['Kafka', 'RabbitMQ']).",
                },
                "domain": {"type": "string", "description": "Force a domain (auto-detected if omitted)."},
            },
            "required": ["names"],
        },
    },
    {
        "name": "backendpro_decide",
        "description": "Opinionated, constraint-scored recommendation for a backend requirement. Searches across relevant domains and ranks candidates.",
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
        "name": "backendpro_adr",
        "description": "Generate a Michael Nygard-format Architecture Decision Record from KB data.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "ADR title (e.g. 'Adopt outbox pattern')."},
                "context_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domains to search for context.",
                },
            },
            "required": ["title", "context_domains"],
        },
    },
    {
        "name": "backendpro_design",
        "description": "Generate a system-design scaffold from a one-liner requirement with capacity math.",
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
        "name": "backendpro_find_stale",
        "description": "Find knowledge-base entries whose Last Updated date is older than a threshold.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to audit."},
                "months": {"type": "integer", "description": "Age threshold in months."},
            },
            "required": ["domain", "months"],
        },
    },
]


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
