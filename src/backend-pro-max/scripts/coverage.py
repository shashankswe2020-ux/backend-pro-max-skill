#!/usr/bin/env python3
"""
Coverage Report — analyse knowledge base completeness per domain.

Compares actual CSV rows against expected categories defined in
``coverage-targets.yml``. Reports gaps, thin categories, and summary stats.

CLI:
    backendpro coverage [--domain D] [--json] [--badge]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from .core import CSV_CONFIG, DATA_DIR, _load_csv
except ImportError:
    from core import CSV_CONFIG, DATA_DIR, _load_csv  # type: ignore[no-redef]

_TARGETS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "coverage-targets.yml"

THIN_THRESHOLD = 3  # categories with fewer rows than this are flagged


# ---------------------------------------------------------------------------
# Coverage targets loader (no PyYAML required)
# ---------------------------------------------------------------------------
def _load_targets() -> dict[str, list[str]]:
    """Load coverage-targets.yml → {domain: [expected categories]}."""
    path = _TARGETS_PATH
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8")
    targets: dict[str, list[str]] = {}
    current_domain: str | None = None

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Domain header: "messaging:" or "  messaging:"
        m = re.match(r'^(\w[\w-]*):\s*$', stripped)
        if m:
            current_domain = m.group(1)
            targets[current_domain] = []
            continue
        # List item under a domain
        m = re.match(r'^-\s+"?([^"]+)"?\s*$', stripped)
        if m and current_domain is not None:
            targets[current_domain].append(m.group(1).strip())
            continue

    return targets


# ---------------------------------------------------------------------------
# Category extraction
# ---------------------------------------------------------------------------
def _category_col(domain: str) -> str:
    """Guess the category column for a domain."""
    config = CSV_CONFIG.get(domain, {})
    output_cols = config.get("output_cols", [])
    for col in output_cols:
        if col.lower() == "category":
            return col
    # Fallback: second column if exists
    return output_cols[1] if len(output_cols) > 1 else "Category"


def _count_by_category(domain: str) -> dict[str, int]:
    """Return {category: row_count} for a domain CSV."""
    config = CSV_CONFIG.get(domain)
    if config is None:
        return {}
    filepath = DATA_DIR / config["file"]
    if not filepath.exists():
        return {}
    rows = _load_csv(filepath)
    cat_col = _category_col(domain)
    counts: dict[str, int] = {}
    for r in rows:
        cat = str(r.get(cat_col, "Uncategorized")).strip()
        if cat:
            counts[cat] = counts.get(cat, 0) + 1
    return counts


def _has_source_url(row: dict) -> bool:
    url = str(row.get("Source URL", "")).strip()
    return bool(url) and url.lower() not in ("", "n/a", "none", "-")


# ---------------------------------------------------------------------------
# Coverage analysis
# ---------------------------------------------------------------------------
def analyse_domain(domain: str, targets: dict[str, list[str]]) -> dict:
    """Analyse coverage for a single domain."""
    config = CSV_CONFIG.get(domain)
    if config is None:
        return {"domain": domain, "error": f"Unknown domain: {domain}"}

    filepath = DATA_DIR / config["file"]
    if not filepath.exists():
        return {"domain": domain, "error": f"File not found: {filepath}"}

    rows = _load_csv(filepath)
    cat_counts = _count_by_category(domain)
    total = len(rows)
    with_source = sum(1 for r in rows if _has_source_url(r))

    expected_cats = targets.get(domain, [])
    actual_cats = set(cat_counts.keys())

    gaps = [c for c in expected_cats if c not in actual_cats]
    thin = {c: n for c, n in cat_counts.items() if n < THIN_THRESHOLD}
    healthy = {c: n for c, n in cat_counts.items() if n >= THIN_THRESHOLD}

    return {
        "domain": domain,
        "total_rows": total,
        "source_url_count": with_source,
        "source_url_pct": round(with_source / total * 100, 1) if total else 0,
        "categories": cat_counts,
        "category_count": len(cat_counts),
        "gaps": gaps,
        "thin": thin,
        "healthy": healthy,
    }


def analyse_all(targets: dict[str, list[str]], domain_filter: str | None = None) -> dict:
    """Run coverage analysis across all (or one) domains."""
    domains = [domain_filter] if domain_filter else list(CSV_CONFIG.keys())
    domain_reports = []
    total_rows = 0
    total_source = 0
    total_gaps = 0
    total_thin = 0

    for d in domains:
        report = analyse_domain(d, targets)
        domain_reports.append(report)
        total_rows += report.get("total_rows", 0)
        total_source += report.get("source_url_count", 0)
        total_gaps += len(report.get("gaps", []))
        total_thin += len(report.get("thin", {}))

    summary = {
        "total_rows": total_rows,
        "domain_count": len(domains),
        "avg_rows_per_domain": round(total_rows / len(domains), 1) if domains else 0,
        "source_url_pct": round(total_source / total_rows * 100, 1) if total_rows else 0,
        "total_gaps": total_gaps,
        "total_thin_categories": total_thin,
    }

    return {"summary": summary, "domains": domain_reports}


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------
def format_coverage(report: dict) -> str:
    lines = ["## Coverage Report\n"]
    summary = report["summary"]
    lines.append(f"**Total rows:** {summary['total_rows']}  |  "
                 f"**Domains:** {summary['domain_count']}  |  "
                 f"**Avg rows/domain:** {summary['avg_rows_per_domain']}  |  "
                 f"**% with Source URL:** {summary['source_url_pct']}%\n")

    for dr in report["domains"]:
        if "error" in dr:
            lines.append(f"### {dr['domain']} — ❌ {dr['error']}\n")
            continue
        lines.append(f"### {dr['domain']} ({dr['total_rows']} rows)")
        for cat, n in sorted(dr.get("healthy", {}).items()):
            lines.append(f"  ✅ {cat}: {n} rows")
        for cat, n in sorted(dr.get("thin", {}).items()):
            lines.append(f"  ⚠️  {cat}: {n} row{'s' if n != 1 else ''} — consider expanding")
        for gap in dr.get("gaps", []):
            lines.append(f"  ⚠️  {gap}: 0 rows — consider adding")
        lines.append("")

    return "\n".join(lines)


def format_coverage_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def format_badge(report: dict) -> str:
    """Generate a shields.io badge URL."""
    total = report["summary"]["total_rows"]
    gaps = report["summary"]["total_gaps"]
    color = "brightgreen" if gaps == 0 else "yellow" if gaps < 5 else "red"
    label = f"KB coverage: {total} rows"
    msg = f"{gaps} gaps" if gaps else "complete"
    url = f"https://img.shields.io/badge/{_badge_escape(label)}-{_badge_escape(msg)}-{color}"
    return url


def _badge_escape(s: str) -> str:
    return s.replace("-", "--").replace("_", "__").replace(" ", "_")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="backendpro coverage",
        description="Knowledge base coverage report.",
    )
    p.add_argument("--domain", "-d", help="Report only this domain")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--badge", action="store_true", help="Print shields.io badge URL")
    return p


def main(argv: list[str] | None = None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    targets = _load_targets()
    report = analyse_all(targets, domain_filter=args.domain)

    if args.badge:
        print(format_badge(report))
    elif args.json:
        print(format_coverage_json(report))
    else:
        print(format_coverage(report))


if __name__ == "__main__":
    main()
