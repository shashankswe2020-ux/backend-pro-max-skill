#!/usr/bin/env python3
"""
Backend Pro Max Linter — scans source files for backend anti-patterns.

Uses regex-based rules from lint-rules.yml. Each finding includes a BPM
citation linking to the knowledge base. Pure standard-library (except PyYAML
parsed manually — we use a minimal YAML subset parser to stay zero-dep).

Public API:
    load_rules(path=None) -> list[dict]
    lint_file(filepath, rules) -> list[Finding]
    lint_paths(paths, rules, *, severity_filter=None) -> list[Finding]
    format_human(findings) -> str
    format_json(findings) -> str
    format_sarif(findings) -> str
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

# ---------------------------------------------------------------------------
# YAML-subset parser (avoids PyYAML dependency)
# Handles the flat structure of lint-rules.yml: top-level list of dicts
# with string values and list-of-string values.
# ---------------------------------------------------------------------------

_RULES_DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent.parent / "lint-rules.yml"

# Extension → language mapping (lowercase, no dot)
_EXT_LANG = {
    "py": "py", "pyw": "py",
    "go": "go",
    "java": "java",
    "kt": "kt", "kts": "kt",
    "js": "js", "jsx": "js", "mjs": "js", "cjs": "js",
    "ts": "ts", "tsx": "ts", "mts": "ts",
    "rs": "rs",
    "rb": "rb",
    "env": "env",
    "cs": "cs",
    "scala": "scala", "sc": "scala",
    "ex": "ex", "exs": "ex",
    "php": "php",
    "cpp": "cpp", "cc": "cpp", "cxx": "cpp", "c": "cpp", "h": "cpp", "hpp": "cpp",
}


def _detect_lang(filepath: str) -> str:
    """Return language key from file extension."""
    name = os.path.basename(filepath)
    if name.startswith(".env"):
        return "env"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return _EXT_LANG.get(ext, "")


# ---------------------------------------------------------------------------
# Minimal YAML parser for lint-rules.yml
# ---------------------------------------------------------------------------

def _parse_yaml_rules(text: str) -> list:
    """Parse our lint-rules.yml subset into a list of rule dicts."""
    rules: list = []
    current: dict = {}
    in_rules_block = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level key "rules:" triggers list parsing
        if stripped == "rules:":
            in_rules_block = True
            continue

        if not in_rules_block:
            continue

        # New list item
        if stripped.startswith("- "):
            if current:
                rules.append(current)
            current = {}
            stripped = stripped[2:].strip()
            if not stripped:
                continue

        # key: value
        if ":" in stripped:
            colon_idx = stripped.index(":")
            key = stripped[:colon_idx].strip()
            val_raw = stripped[colon_idx + 1:].strip()

            if val_raw == "":
                # Could be a block value — skip for now
                continue
            elif val_raw.startswith("[") and val_raw.endswith("]"):
                # Inline list: [go, py, java]
                items = [v.strip().strip("'\"") for v in val_raw[1:-1].split(",") if v.strip()]
                current[key] = items
            elif val_raw.startswith(("'", '"')):
                # Quoted string
                current[key] = val_raw.strip("'\"")
            else:
                current[key] = val_raw

    if current:
        rules.append(current)
    return rules


def load_rules(path: str | None = None) -> list[dict[str, Any]]:
    """Load lint rules from YAML file."""
    p = Path(path) if path else _RULES_DEFAULT_PATH
    if not p.exists():
        raise FileNotFoundError(f"Lint rules file not found: {p}")
    text = p.read_text(encoding="utf-8")
    rules = _parse_yaml_rules(text)
    # Compile patterns
    for r in rules:
        r["_pattern"] = re.compile(r.get("pattern", ""), re.IGNORECASE)
        if r.get("negative_pattern"):
            r["_neg_pattern"] = re.compile(r["negative_pattern"], re.IGNORECASE)
        else:
            r["_neg_pattern"] = None
        # Normalise languages to a list
        if isinstance(r.get("languages"), str):
            r["languages"] = [r["languages"]] if r["languages"] else []
        elif r.get("languages") is None:
            r["languages"] = []
    return rules


# ---------------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    col: int
    rule_id: str
    rule_name: str
    severity: str
    message: str
    fix: str
    citation: str
    matched_text: str = ""


# ---------------------------------------------------------------------------
# Linting engine
# ---------------------------------------------------------------------------

def _applies_to(rule: dict, lang: str) -> bool:
    """Check if a rule applies to the given language."""
    langs = rule.get("languages", [])
    if not langs:
        return True  # empty = all languages
    return lang in langs


def lint_file(filepath: str, rules: list[dict[str, Any]]) -> list[Finding]:
    """Lint a single file and return findings."""
    lang = _detect_lang(filepath)
    if not lang:
        return []

    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return []

    lines = content.splitlines()
    findings: list[Finding] = []

    applicable_rules = [r for r in rules if _applies_to(r, lang)]

    for rule in applicable_rules:
        match_mode = rule.get("match_mode", "line")
        pat = rule["_pattern"]
        rule.get("_neg_pattern")

        if match_mode == "async_block":
            # Special: find async def blocks that contain sync calls
            _lint_async_block(filepath, content, lines, rule, findings)
        elif match_mode == "func_missing":
            # Special: find Go funcs missing context.Context
            _lint_func_missing(filepath, lines, rule, findings)
        elif match_mode in ("line_without", "block_without"):
            _lint_line_without(filepath, lines, rule, findings)
        else:
            # Default: per-line matching
            for i, line_text in enumerate(lines, 1):
                m = pat.search(line_text)
                if m:
                    findings.append(Finding(
                        file=filepath, line=i, col=m.start() + 1,
                        rule_id=rule["id"], rule_name=rule["name"],
                        severity=rule.get("severity", "warning"),
                        message=rule.get("message", ""),
                        fix=rule.get("fix", ""),
                        citation=rule.get("citation", ""),
                        matched_text=m.group(0),
                    ))

    return findings


def _lint_line_without(filepath: str, lines: list, rule: dict, findings: list):
    """Match lines that have the pattern but NOT the negative pattern."""
    pat = rule["_pattern"]
    neg = rule["_neg_pattern"]
    for i, line_text in enumerate(lines, 1):
        m = pat.search(line_text)
        if m:
            # Check negative pattern on same line
            if neg and neg.search(line_text):
                continue
            findings.append(Finding(
                file=filepath, line=i, col=m.start() + 1,
                rule_id=rule["id"], rule_name=rule["name"],
                severity=rule.get("severity", "warning"),
                message=rule.get("message", ""),
                fix=rule.get("fix", ""),
                citation=rule.get("citation", ""),
                matched_text=m.group(0),
            ))


def _lint_async_block(filepath: str, content: str, lines: list, rule: dict, findings: list):
    """Find async def blocks that contain sync calls (e.g. requests.*)."""
    # Find all 'async def' and check the function body for sync patterns
    async_re = re.compile(r"async\s+def\s+\w+")
    sync_re = rule["_pattern"]  # e.g. requests\.(get|post|...)

    for i, line_text in enumerate(lines, 1):
        if async_re.search(line_text):
            # Scan the function body (indented block below)
            base_indent = len(line_text) - len(line_text.lstrip())
            for j in range(i, min(i + 50, len(lines))):
                body_line = lines[j]
                if body_line.strip() == "":
                    continue
                body_indent = len(body_line) - len(body_line.lstrip())
                if j > i and body_indent <= base_indent and body_line.strip():
                    break
                m = sync_re.search(body_line)
                if m:
                    findings.append(Finding(
                        file=filepath, line=j + 1, col=m.start() + 1,
                        rule_id=rule["id"], rule_name=rule["name"],
                        severity=rule.get("severity", "warning"),
                        message=rule.get("message", ""),
                        fix=rule.get("fix", ""),
                        citation=rule.get("citation", ""),
                        matched_text=m.group(0),
                    ))


def _lint_func_missing(filepath: str, lines: list, rule: dict, findings: list):
    """Find Go functions missing context.Context parameter."""
    func_re = re.compile(r"^func\s+(\w+)\(([^)]*)\)")
    skip_re = re.compile(r"(main|init|Test\w+|Benchmark\w+|Example\w+)")
    for i, line_text in enumerate(lines, 1):
        m = func_re.match(line_text)
        if m:
            func_name = m.group(1)
            params = m.group(2)
            # Skip non-exported, main, init, test functions
            if not func_name[0].isupper() or skip_re.match(func_name):
                continue
            if "context.Context" not in params and "ctx " not in params:
                findings.append(Finding(
                    file=filepath, line=i, col=1,
                    rule_id=rule["id"], rule_name=rule["name"],
                    severity=rule.get("severity", "warning"),
                    message=rule.get("message", ""),
                    fix=rule.get("fix", ""),
                    citation=rule.get("citation", ""),
                    matched_text=func_name,
                ))


def lint_paths(
    paths: Sequence[str],
    rules: list[dict[str, Any]],
    *,
    severity_filter: str | None = None,
) -> list[Finding]:
    """Lint one or more files/directories. Returns sorted findings."""
    all_findings: list[Finding] = []
    severity_order = {"error": 0, "warning": 1, "info": 2}
    min_sev = severity_order.get(severity_filter, 2) if severity_filter else 2

    for p in paths:
        path = Path(p)
        if path.is_file():
            all_findings.extend(lint_file(str(path), rules))
        elif path.is_dir():
            for root, _dirs, files in os.walk(path):
                # Skip hidden dirs and common non-source dirs
                base = os.path.basename(root)
                if base.startswith(".") or base in (
                    "node_modules", "__pycache__", ".git", "venv", ".venv",
                    "vendor", "dist", "build", "target",
                ):
                    _dirs.clear()
                    continue
                for fname in sorted(files):
                    fpath = os.path.join(root, fname)
                    all_findings.extend(lint_file(fpath, rules))

    # Filter by severity
    all_findings = [f for f in all_findings if severity_order.get(f.severity, 2) <= min_sev]

    # Sort: file, line, severity
    all_findings.sort(key=lambda f: (f.file, f.line, severity_order.get(f.severity, 2)))
    return all_findings


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

_SEVERITY_ICONS = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}


def format_human(findings: list[Finding]) -> str:
    """Format findings for terminal display."""
    if not findings:
        return "✅ No issues found."

    lines = []
    current_file = ""
    for f in findings:
        if f.file != current_file:
            current_file = f.file
            lines.append(f"\n{current_file}")
        icon = _SEVERITY_ICONS.get(f.severity, "?")
        lines.append(
            f"  {icon} {f.line}:{f.col}  {f.rule_id} {f.severity}  {f.message}"
        )
        if f.fix:
            lines.append(f"     💡 Fix: {f.fix}")
        if f.citation:
            lines.append(f"     📖 {f.citation}")

    counts = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary_parts = [f"{v} {k}{'s' if v != 1 else ''}" for k, v in sorted(counts.items())]
    lines.append(f"\n{'  '.join(summary_parts)}  ({len(findings)} total)")
    return "\n".join(lines)


def format_json(findings: list[Finding]) -> str:
    """Format findings as JSON."""
    return json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False)


def format_sarif(findings: list[Finding]) -> str:
    """Format findings as SARIF v2.1.0 for GitHub Code Scanning."""
    rules_map: dict[str, int] = {}
    rule_objects = []
    results = []

    for f in findings:
        if f.rule_id not in rules_map:
            idx = len(rule_objects)
            rules_map[f.rule_id] = idx
            rule_objects.append({
                "id": f.rule_id,
                "name": f.rule_name,
                "shortDescription": {"text": f.message},
                "helpUri": "",
                "properties": {"citation": f.citation},
                "defaultConfiguration": {
                    "level": "error" if f.severity == "error" else (
                        "warning" if f.severity == "warning" else "note"
                    )
                },
            })

        results.append({
            "ruleId": f.rule_id,
            "ruleIndex": rules_map[f.rule_id],
            "level": "error" if f.severity == "error" else (
                "warning" if f.severity == "warning" else "note"
            ),
            "message": {"text": f"{f.message}\n💡 Fix: {f.fix}\n📖 {f.citation}"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f.file},
                    "region": {"startLine": f.line, "startColumn": f.col},
                }
            }],
        })

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "backendpro-lint",
                    "version": "0.6.0",
                    "informationUri": "https://github.com/shashankswe2020-ux/backend-pro-max-skill",
                    "rules": rule_objects,
                }
            },
            "results": results,
        }],
    }
    return json.dumps(sarif, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None):
    """CLI: backendpro lint <path> [--format human|json|sarif] [--severity warning]"""
    import argparse

    parser = argparse.ArgumentParser(prog="backendpro lint", description="Scan source files for backend anti-patterns.")
    parser.add_argument("paths", nargs="*", default=["."], help="Files or directories to scan")
    parser.add_argument("--format", "-f", choices=["human", "json", "sarif"], default="human", dest="fmt")
    parser.add_argument("--severity", "-s", choices=["error", "warning", "info"], default=None,
                        help="Minimum severity to report (default: all)")
    parser.add_argument("--rules", "-r", default=None, help="Path to lint-rules.yml")
    args = parser.parse_args(argv)

    try:
        rules = load_rules(args.rules)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    findings = lint_paths(args.paths, rules, severity_filter=args.severity)

    if args.fmt == "json":
        print(format_json(findings))
    elif args.fmt == "sarif":
        print(format_sarif(findings))
    else:
        print(format_human(findings))

    # Exit code: 1 if any errors, 0 otherwise
    has_errors = any(f.severity == "error" for f in findings)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
