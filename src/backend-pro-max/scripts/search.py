#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Pro Max Search - CLI for the BM25 backend / distributed-systems
knowledge bases.

Usage:
    python search.py "<query>" [--domain <domain>] [-n N]
    python search.py "<query>" --stack <stack> [-n N]
    python search.py "<query>" --all
    python search.py --list

Domains:
    language, pattern, database, messaging, cache, cloud, iac, container,
    observability, api, auth, security, cicd, testing, architecture,
    scaling, consistency, performance, reliability, data

Stacks:
    go, java-spring, python-fastapi, nodejs-express, rust-axum, csharp-aspnet,
    kotlin-spring, scala-akka, elixir-phoenix, ruby-rails, php-laravel, cpp
"""

import argparse
import io
import json
import sys

from core import (
    CSV_CONFIG, AVAILABLE_STACKS, MAX_RESULTS,
    search, search_stack, search_all,
)

# Force UTF-8 for stdout/stderr to handle emojis on Windows (cp1252 default).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def format_output(result):
    """Format results for AI/CLI consumption (token-optimized)."""
    if "error" in result:
        return f"Error: {result['error']}"

    output = []
    if result.get("stack"):
        output.append("## Backend Pro Max Stack Guidelines")
        output.append(f"**Stack:** {result['stack']} | **Query:** {result['query']}")
    else:
        output.append("## Backend Pro Max Search Results")
        output.append(f"**Domain:** {result['domain']} | **Query:** {result['query']}")
    output.append(f"**Source:** {result['file']} | **Found:** {result['count']} results\n")

    if result["count"] == 0:
        output.append("_No matches. Try a broader query, --all, or another --domain._")

    for i, row in enumerate(result["results"], 1):
        output.append(f"### Result {i}")
        for key, value in row.items():
            value_str = str(value).strip()
            if not value_str:
                continue
            if len(value_str) > 400:
                value_str = value_str[:400] + "…"
            output.append(f"- **{key}:** {value_str}")
        output.append("")

    return "\n".join(output)


def format_all(result):
    """Format cross-domain search."""
    output = ["## Backend Pro Max — Cross-Domain Search",
              f"**Query:** {result['query']} | **Matched domains:** {len(result['domains'])}\n"]
    if not result["domains"]:
        output.append("_No matches across any domain._")
        return "\n".join(output)

    for domain, rows in result["results"].items():
        output.append(f"### Domain: `{domain}` ({len(rows)} hit(s))")
        for i, row in enumerate(rows, 1):
            head = next(iter(row.values()), "?")
            output.append(f"- **{i}. {head}**")
            for key, value in list(row.items())[1:4]:
                value_str = str(value).strip()
                if value_str:
                    if len(value_str) > 160:
                        value_str = value_str[:160] + "…"
                    output.append(f"    - {key}: {value_str}")
        output.append("")
    return "\n".join(output)


def list_domains_and_stacks():
    print("## Domains")
    for d in CSV_CONFIG:
        print(f"  - {d}")
    print("\n## Stacks")
    for s in AVAILABLE_STACKS:
        print(f"  - {s}")


def main():
    parser = argparse.ArgumentParser(
        prog="backend-pro-max-search",
        description="BM25 search across backend / distributed-systems knowledge bases.",
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--domain", "-d", choices=list(CSV_CONFIG.keys()),
                        help="Search a specific domain (auto-detected if omitted)")
    parser.add_argument("--stack", "-s", choices=AVAILABLE_STACKS,
                        help=f"Stack-specific search. Available: {', '.join(AVAILABLE_STACKS)}")
    parser.add_argument("--all", action="store_true",
                        help="Cross-domain search across every CSV")
    parser.add_argument("--max-results", "-n", type=int, default=MAX_RESULTS,
                        help=f"Max results per domain (default: {MAX_RESULTS})")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list", action="store_true",
                        help="List available domains and stacks then exit")

    args = parser.parse_args()

    if args.list:
        list_domains_and_stacks()
        return

    if not args.query:
        parser.error("a query is required (or pass --list)")

    if args.all:
        result = search_all(args.query, max_results=max(1, args.max_results // 2))
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else format_all(result))
        return

    if args.stack:
        result = search_stack(args.query, args.stack, args.max_results)
    else:
        result = search(args.query, args.domain, args.max_results)

    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else format_output(result))


if __name__ == "__main__":
    main()
