#!/usr/bin/env python3
"""
Backend Pro Max Export — render KB to Obsidian, Notion CSV, or Org-mode.

Pure standard-library. No external dependencies.

Public API:
    export_obsidian(out_dir, *, domain=None)
    export_notion(out_dir, *, domain=None)
    export_org(out_dir, *, domain=None)
"""
from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

try:
    from .core import CSV_CONFIG
except ImportError:
    from core import CSV_CONFIG  # type: ignore[no-redef]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_csv(filepath: Path) -> list[dict[str, str]]:
    """Load a CSV into a list of dicts."""
    if not filepath.exists():
        return []
    with open(filepath, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[\s_]+", "-", s).strip("-")


def _name_col(cfg: dict) -> str:
    """Get the primary name column from CSV config."""
    out = cfg.get("output_cols", [])
    for candidate in ("Name", "Topic", "Service", "Category", "Guideline"):
        if candidate in out:
            return candidate
    return out[0] if out else "Name"


def _all_domain_rows(domain_filter: str | None = None) -> list[tuple[str, str, dict[str, str]]]:
    """Yield (domain, name_col, row) for all matching domains."""
    results = []
    configs = CSV_CONFIG
    if domain_filter:
        configs = {k: v for k, v in configs.items() if k == domain_filter}
    for domain, cfg in sorted(configs.items()):
        filepath = DATA_DIR / cfg["file"]
        name_col = _name_col(cfg)
        for row in _load_csv(filepath):
            results.append((domain, name_col, row))
    return results


# ---------------------------------------------------------------------------
# Obsidian export
# ---------------------------------------------------------------------------

def _obsidian_frontmatter(domain: str, row: dict[str, str], name_col: str) -> str:
    """Generate YAML frontmatter for an Obsidian note."""
    lines = ["---"]
    lines.append(f"domain: {domain}")
    for k, v in row.items():
        if k == name_col or not v.strip():
            continue
        # Truncate very long values in frontmatter
        safe_v = v.replace("\n", " ").strip()
        if len(safe_v) > 200:
            safe_v = safe_v[:200] + "…"
        # Escape YAML special chars
        if any(c in safe_v for c in ":{}\n[]#&*!|>',\""):
            safe_v = f'"{safe_v}"' if '"' not in safe_v else f"'{safe_v}'"
        lines.append(f"{_slugify(k)}: {safe_v}")
    lines.append(f"citation: \"[BPM:{domain}.{_slugify(row.get(name_col, 'unknown'))}]\"")
    lines.append("---")
    return "\n".join(lines)


def _obsidian_body(domain: str, row: dict[str, str], name_col: str) -> str:
    """Generate the body of an Obsidian note."""
    name = row.get(name_col, "Unknown")
    lines = [f"# {name}", ""]

    for k, v in row.items():
        if k == name_col or not v.strip():
            continue
        lines.append(f"## {k}")
        lines.append(v.strip())
        lines.append("")

    # Add wikilinks for related items
    related_fields = ("Related Patterns", "Alternatives", "Related")
    for field in related_fields:
        if field in row and row[field].strip():
            items = [i.strip() for i in row[field].split(",") if i.strip()]
            if items:
                lines.append("## Related")
                for item in items:
                    lines.append(f"- [[{item}]]")
                lines.append("")
                break

    return "\n".join(lines)


def export_obsidian(out_dir: str, *, domain: str | None = None) -> dict:
    """Export KB to an Obsidian vault (one .md per row + _Index.md)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows = _all_domain_rows(domain)
    file_count = 0
    index_entries: dict[str, list[str]] = {}

    for dom, name_col, row in rows:
        name = row.get(name_col, "Unknown").strip()
        if not name:
            continue
        slug = _slugify(name)
        filename = f"{slug}.md"

        frontmatter = _obsidian_frontmatter(dom, row, name_col)
        body = _obsidian_body(dom, row, name_col)
        content = f"{frontmatter}\n\n{body}"

        (out / filename).write_text(content, encoding="utf-8")
        file_count += 1

        index_entries.setdefault(dom, []).append(f"- [[{name}]]")

    # Generate _Index.md (Map of Content)
    index_lines = ["# Backend Pro Max — Knowledge Base Index", ""]
    for dom in sorted(index_entries.keys()):
        index_lines.append(f"## {dom.replace('-', ' ').title()}")
        for entry in sorted(index_entries[dom]):
            index_lines.append(entry)
        index_lines.append("")

    (out / "_Index.md").write_text("\n".join(index_lines), encoding="utf-8")
    file_count += 1

    return {"format": "obsidian", "files": file_count, "out_dir": str(out)}


# ---------------------------------------------------------------------------
# Notion export
# ---------------------------------------------------------------------------

def export_notion(out_dir: str, *, domain: str | None = None) -> dict:
    """Export KB as Notion-importable CSVs (one per domain)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    configs = CSV_CONFIG
    if domain:
        configs = {k: v for k, v in configs.items() if k == domain}

    file_count = 0
    for dom, cfg in sorted(configs.items()):
        filepath = DATA_DIR / cfg["file"]
        rows = _load_csv(filepath)
        if not rows:
            continue

        out_file = out / f"{dom}.csv"
        # Notion expects: Name (title), plus multi-select and URL columns
        fieldnames = list(rows[0].keys())
        with open(out_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        file_count += 1

    return {"format": "notion", "files": file_count, "out_dir": str(out)}


# ---------------------------------------------------------------------------
# Org-mode export
# ---------------------------------------------------------------------------

def _org_entry(row: dict[str, str], name_col: str, domain: str) -> str:
    """Generate an Org-mode entry for a row."""
    name = row.get(name_col, "Unknown").strip()
    lines = [f"** {name}"]
    lines.append("   :PROPERTIES:")
    lines.append(f"   :DOMAIN: {domain}")
    citation = f"[BPM:{domain}.{_slugify(name)}]"
    lines.append(f"   :CITATION: {citation}")
    if row.get("Source URL"):
        lines.append(f"   :SOURCE: [[{row['Source URL']}]]")
    lines.append("   :END:")

    for k, v in row.items():
        if k == name_col or not v.strip():
            continue
        if k in ("Source URL", "Source Type", "Last Updated", "Keywords"):
            continue
        lines.append(f"*** {k}")
        lines.append(f"    {v.strip()}")

    return "\n".join(lines)


def export_org(out_dir: str, *, domain: str | None = None) -> dict:
    """Export KB as Org-mode files (one .org per domain)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    configs = CSV_CONFIG
    if domain:
        configs = {k: v for k, v in configs.items() if k == domain}

    file_count = 0
    for dom, cfg in sorted(configs.items()):
        filepath = DATA_DIR / cfg["file"]
        rows = _load_csv(filepath)
        if not rows:
            continue

        name_col = _name_col(cfg)
        lines = [
            f"#+TITLE: Backend Pro Max — {dom.replace('-', ' ').title()}",
            f"#+DATE: {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"* {dom.replace('-', ' ').title()}",
        ]

        for row in rows:
            lines.append(_org_entry(row, name_col, dom))
            lines.append("")

        out_file = out / f"{dom}.org"
        out_file.write_text("\n".join(lines), encoding="utf-8")
        file_count += 1

    return {"format": "org", "files": file_count, "out_dir": str(out)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list | None = None):
    """CLI: backendpro export --format obsidian|notion|org --out <path> [--domain D]"""
    parser = argparse.ArgumentParser(prog="backendpro export", description="Export KB to Obsidian, Notion, or Org-mode.")
    parser.add_argument("--format", "-f", required=True, choices=["obsidian", "notion", "org"], dest="fmt")
    parser.add_argument("--out", "-o", required=True, help="Output directory")
    parser.add_argument("--domain", "-d", default=None, help="Export only this domain")
    args = parser.parse_args(argv)

    exporters = {
        "obsidian": export_obsidian,
        "notion": export_notion,
        "org": export_org,
    }

    result = exporters[args.fmt](args.out, domain=args.domain)
    print(f"✅ Exported {result['files']} files to {result['out_dir']} ({result['format']})")


if __name__ == "__main__":
    main()
