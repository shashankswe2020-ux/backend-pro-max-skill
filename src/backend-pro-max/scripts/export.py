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
import json
from datetime import datetime
from pathlib import Path

try:
    from .core import CSV_CONFIG, BM25
except ImportError:
    from core import CSV_CONFIG, BM25  # type: ignore[no-redef]

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
    lines.append(f"tags:")
    lines.append(f"  - domain/{domain}")
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


def _obsidian_body(domain: str, row: dict[str, str], name_col: str,
                   bm25_links: list[tuple[str, float]] | None = None) -> str:
    """Generate the body of an Obsidian note."""
    name = row.get(name_col, "Unknown")
    lines = [f"# {name}", ""]

    for k, v in row.items():
        if k == name_col or not v.strip():
            continue
        lines.append(f"## {k}")
        lines.append(v.strip())
        lines.append("")

    # Add wikilinks for related items (use slug for link target, display name as alias)
    related_fields = ("Related Patterns", "Alternatives", "Related")
    for field in related_fields:
        if field in row and row[field].strip():
            items = [i.strip() for i in row[field].split(",") if i.strip()]
            if items:
                lines.append("## Related")
                for item in items:
                    lines.append(f"- [[{_slugify(item)}|{item}]]")
                lines.append("")
                break

    # Add BM25-computed cross-domain links
    if bm25_links:
        lines.append("## 🔍 BM25 Related")
        lines.append("> *Auto-generated from BM25 index similarity scores*")
        lines.append("")
        for related_slug, score in bm25_links:
            parts = related_slug.split("/", 1)
            display_domain = parts[0].replace("-", " ").title() if len(parts) > 1 else ""
            entry_slug = parts[1] if len(parts) > 1 else parts[0]
            display_name = entry_slug.replace("-", " ").title()
            score_pct = min(int(score * 20), 5)  # normalize to 0-5 bars
            score_bar = "█" * score_pct + "░" * max(0, 5 - score_pct)
            lines.append(f"- [[{related_slug}|{display_name}]] `{score_bar} {score:.1f}` _{display_domain}_")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# BM25 similarity graph
# ---------------------------------------------------------------------------

def _build_bm25_links(
    rows: list[tuple[str, str, dict[str, str]]],
    top_k: int = 5,
    min_score: float = 0.5,
) -> dict[str, list[tuple[str, float]]]:
    """Compute BM25 similarity between all entries → {dom/slug: [(related, score)]}."""
    slugs: list[str] = []
    documents: list[str] = []
    for dom, name_col, row in rows:
        name = row.get(name_col, "Unknown").strip()
        if not name:
            continue
        slugs.append(f"{dom}/{_slugify(name)}")
        documents.append(" ".join(v.strip() for v in row.values() if v.strip()))

    if not documents:
        return {}

    engine = BM25()
    engine.fit(documents)

    links: dict[str, list[tuple[str, float]]] = {}
    for i, (dom, name_col, row) in enumerate(rows):
        name = row.get(name_col, "Unknown").strip()
        if not name:
            continue
        slug = slugs[i]
        query = name
        for extra in ("Keywords", "Use Case", "Description"):
            if row.get(extra, "").strip():
                query += " " + row[extra].strip()
                break

        scored = engine.score(query)
        related: list[tuple[str, float]] = []
        for idx, score in scored:
            if idx == i or score < min_score:
                continue
            # Prefer cross-domain links
            related.append((slugs[idx], score))
            if len(related) >= top_k:
                break
        links[slug] = related

    return links


# 34 distinct hues spread across the color wheel for domain groups
_DOMAIN_COLORS = [
    "#ef4444", "#f97316", "#f59e0b", "#eab308", "#84cc16",
    "#22c55e", "#10b981", "#14b8a6", "#06b6d4", "#0ea5e9",
    "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7", "#d946ef",
    "#ec4899", "#f43f5e", "#fb923c", "#fbbf24", "#a3e635",
    "#34d399", "#2dd4bf", "#22d3ee", "#38bdf8", "#818cf8",
    "#a78bfa", "#c084fc", "#e879f9", "#f472b6", "#fb7185",
    "#fdba74", "#fcd34d", "#bef264", "#6ee7b7",
]


def _write_obsidian_graph_config(vault_dir: Path, domains: list[str]) -> None:
    """Write .obsidian/workspace.json with color-coded tag groups per domain."""
    obsidian_dir = vault_dir / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    groups = []
    for i, dom in enumerate(domains):
        color = _DOMAIN_COLORS[i % len(_DOMAIN_COLORS)]
        rgb = int(color.lstrip("#"), 16)
        groups.append({
            "query": f"tag:#domain/{dom}",
            "color": {"a": 1, "rgb": rgb},
        })

    # Workspace with a graph leaf that has colorGroups baked in
    workspace = {
        "main": {
            "id": "main",
            "type": "split",
            "children": [
                {
                    "id": "graph-leaf",
                    "type": "leaf",
                    "state": {
                        "type": "graph",
                        "state": {
                            "options": {
                                "colorGroups": groups,
                                "showTags": False,
                                "showOrphans": True,
                                "showAttachments": False,
                            }
                        },
                    },
                }
            ],
            "direction": "vertical",
        },
        "active": "graph-leaf",
    }

    (obsidian_dir / "workspace.json").write_text(
        json.dumps(workspace, indent=2), encoding="utf-8"
    )


def export_obsidian(out_dir: str, *, domain: str | None = None) -> dict:
    """Export KB to an Obsidian vault with domain subfolders + _Index.md."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows = _all_domain_rows(domain)
    file_count = 0
    index_entries: dict[str, list[tuple[str, str]]] = {}

    # Build BM25 similarity links across all entries
    bm25_links = _build_bm25_links(rows)

    for dom, name_col, row in rows:
        name = row.get(name_col, "Unknown").strip()
        if not name:
            continue
        slug = _slugify(name)
        full_slug = f"{dom}/{slug}"
        dom_dir = out / dom
        dom_dir.mkdir(parents=True, exist_ok=True)

        frontmatter = _obsidian_frontmatter(dom, row, name_col)
        entry_links = bm25_links.get(full_slug, [])
        body = _obsidian_body(dom, row, name_col, bm25_links=entry_links)
        content = f"{frontmatter}\n\n{body}"

        (dom_dir / f"{slug}.md").write_text(content, encoding="utf-8")
        file_count += 1

        index_entries.setdefault(dom, []).append((slug, name))

    # Generate per-domain _Index.md inside each folder
    for dom in sorted(index_entries.keys()):
        dom_title = dom.replace("-", " ").title()
        dom_lines = [f"# {dom_title}", ""]
        for slug, display_name in sorted(index_entries[dom], key=lambda x: x[1]):
            dom_lines.append(f"- [[{slug}|{display_name}]]")
        dom_lines.append("")
        (out / dom / "_Index.md").write_text("\n".join(dom_lines), encoding="utf-8")
        file_count += 1

    # Generate root _Index.md (Map of Content) linking to domain indexes
    index_lines = ["# Backend Pro Max — Knowledge Base Index", ""]
    for dom in sorted(index_entries.keys()):
        dom_title = dom.replace("-", " ").title()
        count = len(index_entries[dom])
        index_lines.append(f"- [[{dom}/_Index|{dom_title}]] ({count} entries)")
    index_lines.append("")

    (out / "_Index.md").write_text("\n".join(index_lines), encoding="utf-8")
    file_count += 1

    # Generate .obsidian/graph.json with color-coded domain groups
    _write_obsidian_graph_config(out, sorted(index_entries.keys()))

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
