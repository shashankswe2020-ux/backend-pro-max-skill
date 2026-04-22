#!/usr/bin/env python3
"""
Backend Pro Max Search - CLI for the BM25 backend / distributed-systems
knowledge bases.

Usage:
    backendpro "<query>" [--domain <domain>] [-n N]
    backendpro "<query>" --stack <stack> [-n N]
    backendpro "<query>" --all
    backendpro compare "<A>" "<B>" [--domain <domain>]
    backendpro --stale --domain <domain> --max-age-months 18
    backendpro --interactive
    backendpro --list
"""

import argparse
import io
import json
import shlex
import sys

try:
    from .core import (
        AVAILABLE_STACKS,
        CSV_CONFIG,
        MAX_RESULTS,
        compare,
        find_stale,
        search,
        search_all,
        search_stack,
    )
except ImportError:
    from core import (  # type: ignore[no-redef]
        AVAILABLE_STACKS,
        CSV_CONFIG,
        MAX_RESULTS,
        compare,
        find_stale,
        search,
        search_all,
        search_stack,
    )

# Force UTF-8 for stdout/stderr to handle emojis on Windows (cp1252 default).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# ============ FORMATTERS ============
def _confidence_label(score):
    if score >= 4.0:
        return "high"
    if score >= 1.5:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def format_output(result, show_scores=True):
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
        score = row.get("_score")
        header = f"### Result {i}"
        if show_scores and score is not None:
            header += f"  _(score: {score:.2f}, confidence: {_confidence_label(score)})_"
        output.append(header)
        for key, value in row.items():
            if key == "_score":
                continue
            value_str = str(value).strip()
            if not value_str:
                continue
            if len(value_str) > 400:
                value_str = value_str[:400] + "…"
            output.append(f"- **{key}:** {value_str}")
        output.append("")

    return "\n".join(output)


def format_all(result, show_scores=True):
    """Format cross-domain search."""
    output = ["## Backend Pro Max — Cross-Domain Search",
              f"**Query:** {result['query']} | **Matched domains:** {len(result['domains'])}\n"]
    if not result["domains"]:
        output.append("_No matches across any domain._")
        return "\n".join(output)

    for domain, rows in result["results"].items():
        output.append(f"### Domain: `{domain}` ({len(rows)} hit(s))")
        for i, row in enumerate(rows, 1):
            head = next((v for k, v in row.items() if k != "_score"), "?")
            tag = f" _(score {row['_score']:.2f})_" if show_scores and "_score" in row else ""
            output.append(f"- **{i}. {head}**{tag}")
            shown = 0
            head_key = next((k for k in row if k != "_score"), None)
            for key, value in row.items():
                if key == "_score" or key == head_key or shown >= 3:
                    continue
                value_str = str(value).strip()
                if value_str:
                    if len(value_str) > 160:
                        value_str = value_str[:160] + "…"
                    output.append(f"    - {key}: {value_str}")
                    shown += 1
        output.append("")
    return "\n".join(output)


def format_compare(result):
    if "error" in result:
        return f"Error: {result['error']}"
    out = [f"## Backend Pro Max — Compare ({result['domain']})",
           f"**Comparing:** {' vs '.join(result['names'])}\n"]
    cols = result["columns"]
    if not cols:
        out.append("_No entries found for any of the names._")
        return "\n".join(out)

    header = "| Field | " + " | ".join(result["names"]) + " |"
    sep = "| --- |" + "".join(" --- |" for _ in result["names"])
    out.append(header)
    out.append(sep)
    for col in cols:
        cells = []
        for name in result["names"]:
            val = str(result["entries"].get(name, {}).get(col, "")).strip()
            val = val.replace("|", "\\|").replace("\n", " ")
            if len(val) > 180:
                val = val[:180] + "…"
            cells.append(val or "—")
        out.append(f"| **{col}** | " + " | ".join(cells) + " |")
    return "\n".join(out)


def format_stale(result):
    if "error" in result:
        return f"Error: {result['error']}"
    out = [f"## Backend Pro Max — Stale entries in `{result['domain']}`",
           f"**Older than:** {result['older_than_months']} months | **Found:** {result['count']}\n"]
    if result["count"] == 0:
        out.append("_No stale entries (or no `Last Updated` dates set)._")
        return "\n".join(out)
    for row in result["results"]:
        head = next(iter(row.values()), "?")
        out.append(f"- **{head}** — last updated: {row.get('Last Updated', '?')}")
    return "\n".join(out)


def list_domains_and_stacks():
    print("## Domains")
    for d in CSV_CONFIG:
        print(f"  - {d}")
    print("\n## Stacks")
    for s in AVAILABLE_STACKS:
        print(f"  - {s}")


# ============ INTERACTIVE REPL ============
_INTERACTIVE_HELP = """\
Interactive commands:
  <query>                       search (auto-detect domain)
  /d <domain> <query>           search a specific domain
  /s <stack> <query>            search a stack
  /all <query>                  cross-domain search
  /cmp <name1> | <name2> [...]  compare entries (pipe-separated)
  /stale <domain> <months>      list stale entries
  /list                         list domains & stacks
  /help                         this help
  /quit  (or Ctrl-D)            exit
"""


def interactive_loop():
    print("Backend Pro Max — interactive mode. Type /help for commands, /quit to exit.")
    while True:
        try:
            line = input("bpm> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        if line in ("/quit", "/exit", ":q"):
            return
        if line == "/help":
            print(_INTERACTIVE_HELP)
            continue
        if line == "/list":
            list_domains_and_stacks()
            continue
        if line.startswith("/all "):
            print(format_all(search_all(line[5:].strip())))
            continue
        if line.startswith("/d "):
            parts = line[3:].split(None, 1)
            if len(parts) != 2:
                print("usage: /d <domain> <query>")
                continue
            print(format_output(search(parts[1], domain=parts[0])))
            continue
        if line.startswith("/s "):
            parts = line[3:].split(None, 1)
            if len(parts) != 2:
                print("usage: /s <stack> <query>")
                continue
            print(format_output(search_stack(parts[1], parts[0])))
            continue
        if line.startswith("/cmp "):
            names = [n.strip() for n in line[5:].split("|") if n.strip()]
            if len(names) < 2:
                print("usage: /cmp <name1> | <name2> [| <name3> ...]")
                continue
            print(format_compare(compare(names)))
            continue
        if line.startswith("/stale "):
            try:
                _, dom, months = shlex.split(line)
                print(format_stale(find_stale(dom, int(months))))
            except (ValueError, IndexError):
                print("usage: /stale <domain> <months>")
            continue
        # Default: plain search
        print(format_output(search(line)))


# ============ ARG PARSING ============
def _build_parser():
    parser = argparse.ArgumentParser(
        prog="backendpro",
        description="BM25 search across backend / distributed-systems knowledge bases.",
    )
    parser.add_argument("query", nargs="?",
                        help="Search query (or 'compare' to invoke compare mode)")
    parser.add_argument("compare_args", nargs="*",
                        help="When the first positional is 'compare', the remaining names to compare.")

    parser.add_argument("--domain", "-d", choices=list(CSV_CONFIG.keys()),
                        help="Search a specific domain (auto-detected if omitted)")
    parser.add_argument("--stack", "-s", choices=AVAILABLE_STACKS,
                        help=f"Stack-specific search. Available: {', '.join(AVAILABLE_STACKS)}")
    parser.add_argument("--all", action="store_true",
                        help="Cross-domain search across every CSV")
    parser.add_argument("--max-results", "-n", type=int, default=MAX_RESULTS,
                        help=f"Max results per domain (default: {MAX_RESULTS})")
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="Drop results with BM25 score <= this (default 0.0)")
    parser.add_argument("--max-age-months", type=int, default=None,
                        help="Drop results whose `Last Updated` is older than N months")
    parser.add_argument("--no-expand", action="store_true",
                        help="Disable synonym expansion")
    parser.add_argument("--no-scores", action="store_true",
                        help="Hide BM25 confidence scores in markdown output")
    parser.add_argument("--stale", action="store_true",
                        help="List stale entries in --domain (requires --max-age-months)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Start an interactive REPL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list", action="store_true",
                        help="List available domains and stacks then exit")
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.interactive:
        interactive_loop()
        return

    if args.list:
        list_domains_and_stacks()
        return

    if args.stale:
        if not args.domain or args.max_age_months is None:
            parser.error("--stale requires --domain and --max-age-months")
        result = find_stale(args.domain, args.max_age_months)
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else format_stale(result))
        return

    if args.query == "compare":
        names = args.compare_args
        if len(names) < 2:
            parser.error("compare needs at least two names: backendpro compare <A> <B> [...]")
        result = compare(names, domain=args.domain)
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else format_compare(result))
        return

    if not args.query:
        parser.error("a query is required (or pass --list / --interactive)")

    expand = not args.no_expand
    show_scores = not args.no_scores

    if args.all:
        result = search_all(
            args.query, max_results=max(1, args.max_results // 2),
            min_score=args.min_score, expand=expand,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False)
              if args.json else format_all(result, show_scores=show_scores))
        return

    if args.stack:
        result = search_stack(
            args.query, args.stack, args.max_results,
            min_score=args.min_score, expand=expand,
        )
    else:
        result = search(
            args.query, args.domain, args.max_results,
            min_score=args.min_score, max_age_months=args.max_age_months, expand=expand,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False)
          if args.json else format_output(result, show_scores=show_scores))


if __name__ == "__main__":
    main()
