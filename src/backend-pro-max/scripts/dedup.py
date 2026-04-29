#!/usr/bin/env python3
"""
Semantic Deduplication — detect near-duplicate rows within and across domains.

Uses pairwise BM25 self-similarity by default (pure stdlib). Optional
embedding-based dedup via ``[semantic]`` extra for higher accuracy.

CLI:
    backendpro dedup [--domain D] [--threshold 0.85] [--cross-domain] [--json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .core import BM25, CSV_CONFIG, DATA_DIR, _load_csv
except ImportError:
    from core import BM25, CSV_CONFIG, DATA_DIR, _load_csv  # type: ignore[no-redef]

DEFAULT_THRESHOLD = 0.85

# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------
_ALLOWLIST_PATH = Path(__file__).resolve().parent.parent.parent.parent / "dedup-allowlist.yml"


def _load_allowlist() -> set[tuple[str, str]]:
    """Load allowlisted pairs from dedup-allowlist.yml. Returns a set of
    frozensets of (name_lower, name_lower) pairs."""
    path = _ALLOWLIST_PATH
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    pairs: set[tuple[str, str]] = set()
    # Simple line-based parser (no PyYAML dependency)
    import re
    current_pair: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        m = re.match(r'^-\s+"?([^"]+)"?\s*$', stripped)
        if m:
            current_pair.append(m.group(1).strip().lower())
            if len(current_pair) == 2:
                a, b = sorted(current_pair)
                pairs.add((a, b))
                current_pair = []
            continue
        # Inline pair: ["A", "B"]
        m = re.match(r'^-\s*\["?([^"]+)"?,\s*"?([^"]+)"?\]', stripped)
        if m:
            a, b = sorted([m.group(1).strip().lower(), m.group(2).strip().lower()])
            pairs.add((a, b))
            continue
    return pairs


def _is_allowlisted(name_a: str, name_b: str, allowlist: set[tuple[str, str]]) -> bool:
    a, b = sorted([name_a.lower(), name_b.lower()])
    return (a, b) in allowlist


# ---------------------------------------------------------------------------
# Name-column extraction
# ---------------------------------------------------------------------------
def _name_col(domain: str) -> str:
    """Return the first output column name for a domain (the 'name' column)."""
    config = CSV_CONFIG.get(domain, {})
    output_cols = config.get("output_cols", [])
    return output_cols[0] if output_cols else "Name"


def _row_name(row: dict, domain: str) -> str:
    col = _name_col(domain)
    return str(row.get(col, next(iter(row.values()), "")))


def _search_text(row: dict, domain: str) -> str:
    """Concatenate search-column values for a row."""
    config = CSV_CONFIG.get(domain, {})
    search_cols = config.get("search_cols", [])
    parts = [str(row.get(c, "")) for c in search_cols]
    return " ".join(parts)


# ---------------------------------------------------------------------------
# BM25 pairwise self-similarity
# ---------------------------------------------------------------------------
def find_duplicates_bm25(
    domain: str,
    threshold: float = DEFAULT_THRESHOLD,
    allowlist: set[tuple[str, str]] | None = None,
) -> list[dict]:
    """Find near-duplicate rows within a single domain using BM25 self-similarity.

    Returns a list of dicts: {row_a, row_b, similarity, domain}.
    """
    if allowlist is None:
        allowlist = set()

    config = CSV_CONFIG.get(domain)
    if config is None:
        return []

    filepath = DATA_DIR / config["file"]
    if not filepath.exists():
        return []

    rows = _load_csv(filepath)
    if len(rows) < 2:
        return []

    # Build search texts
    texts = [_search_text(r, domain) for r in rows]
    names = [_row_name(r, domain) for r in rows]

    # Fit BM25 on all texts
    bm25 = BM25()
    bm25.fit(texts)

    # Compute max possible score (a document scored against itself)
    max_scores = []
    for i, text in enumerate(texts):
        scored = bm25.score(text)
        self_score = next((s for idx, s in scored if idx == i), 0.0)
        max_scores.append(self_score if self_score > 0 else 1.0)

    duplicates: list[dict] = []
    seen: set[tuple[int, int]] = set()

    for i, text in enumerate(texts):
        scored = bm25.score(text)
        for j, raw_score in scored:
            if j <= i:
                continue
            if (i, j) in seen:
                continue
            seen.add((i, j))

            # Normalise by geometric mean of max scores
            normaliser = (max_scores[i] * max_scores[j]) ** 0.5
            similarity = raw_score / normaliser if normaliser > 0 else 0.0

            if similarity >= threshold:
                if not _is_allowlisted(names[i], names[j], allowlist):
                    duplicates.append({
                        "row_a": names[i],
                        "row_b": names[j],
                        "similarity": round(similarity, 4),
                        "domain": domain,
                    })

    duplicates.sort(key=lambda d: d["similarity"], reverse=True)
    return duplicates


def find_duplicates_cross_domain(
    threshold: float = DEFAULT_THRESHOLD,
    allowlist: set[tuple[str, str]] | None = None,
) -> list[dict]:
    """Find near-duplicate rows across all domains."""
    if allowlist is None:
        allowlist = set()

    # Collect all rows with their domain and name
    all_texts: list[str] = []
    all_names: list[str] = []
    all_domains: list[str] = []

    for domain, config in CSV_CONFIG.items():
        filepath = DATA_DIR / config["file"]
        if not filepath.exists():
            continue
        rows = _load_csv(filepath)
        for r in rows:
            all_texts.append(_search_text(r, domain))
            all_names.append(_row_name(r, domain))
            all_domains.append(domain)

    if len(all_texts) < 2:
        return []

    bm25 = BM25()
    bm25.fit(all_texts)

    # Compute self-scores for normalisation
    max_scores = []
    for i, text in enumerate(all_texts):
        scored = bm25.score(text)
        self_score = next((s for idx, s in scored if idx == i), 0.0)
        max_scores.append(self_score if self_score > 0 else 1.0)

    duplicates: list[dict] = []

    for i in range(len(all_texts)):
        scored = bm25.score(all_texts[i])
        for j, raw_score in scored:
            if j <= i:
                continue
            # Only cross-domain
            if all_domains[i] == all_domains[j]:
                continue

            normaliser = (max_scores[i] * max_scores[j]) ** 0.5
            similarity = raw_score / normaliser if normaliser > 0 else 0.0

            if similarity >= threshold:
                if not _is_allowlisted(all_names[i], all_names[j], allowlist):
                    duplicates.append({
                        "row_a": all_names[i],
                        "row_b": all_names[j],
                        "similarity": round(similarity, 4),
                        "domain_a": all_domains[i],
                        "domain_b": all_domains[j],
                    })

    duplicates.sort(key=lambda d: d["similarity"], reverse=True)
    return duplicates


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------
def format_duplicates(duplicates: list[dict], cross_domain: bool = False) -> str:
    if not duplicates:
        return "✅ No near-duplicates found."

    lines = [f"## Potential Duplicates ({len(duplicates)} pairs)\n"]
    lines.append(f"{'Row A':<40} {'Row B':<40} {'Similarity':>10} {'Domain(s)'}")
    lines.append("-" * 100)
    for d in duplicates:
        if cross_domain or "domain_a" in d:
            domains = f"{d.get('domain_a', '?')} ↔ {d.get('domain_b', '?')}"
        else:
            domains = d.get("domain", "?")
        lines.append(
            f"{d['row_a']:<40} {d['row_b']:<40} {d['similarity']:>10.4f} {domains}"
        )
    return "\n".join(lines)


def format_duplicates_json(duplicates: list[dict]) -> str:
    return json.dumps({"duplicates": duplicates, "count": len(duplicates)}, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="backendpro dedup",
        description="Detect near-duplicate rows in the knowledge base.",
    )
    p.add_argument("--domain", "-d", help="Scan only this domain")
    p.add_argument("--threshold", "-t", type=float, default=DEFAULT_THRESHOLD,
                   help=f"Similarity threshold (default {DEFAULT_THRESHOLD})")
    p.add_argument("--cross-domain", action="store_true",
                   help="Compare rows across all domains")
    p.add_argument("--json", action="store_true", help="JSON output")
    return p


def main(argv: list[str] | None = None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    allowlist = _load_allowlist()

    if args.cross_domain:
        dupes = find_duplicates_cross_domain(
            threshold=args.threshold, allowlist=allowlist,
        )
        if args.json:
            print(format_duplicates_json(dupes))
        else:
            print(format_duplicates(dupes, cross_domain=True))
    elif args.domain:
        dupes = find_duplicates_bm25(
            args.domain, threshold=args.threshold, allowlist=allowlist,
        )
        if args.json:
            print(format_duplicates_json(dupes))
        else:
            print(format_duplicates(dupes))
    else:
        # Scan all domains
        all_dupes: list[dict] = []
        for domain in CSV_CONFIG:
            all_dupes.extend(
                find_duplicates_bm25(domain, threshold=args.threshold, allowlist=allowlist)
            )
        if args.json:
            print(format_duplicates_json(all_dupes))
        else:
            print(format_duplicates(all_dupes))


if __name__ == "__main__":
    main()
