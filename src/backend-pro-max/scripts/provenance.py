#!/usr/bin/env python3
"""
Provenance auto-populator — use git blame to fill `Added By` and `Version`
columns in Backend Pro Max CSVs.

Usage:
    python scripts/provenance.py [--dry-run] [--domain <domain>]

Columns populated:
  - Added By:          git author of the commit that first added the row
  - Last Reviewed By:  (manual — not auto-populated)
  - Version:           git tag at or before the commit that added the row
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

try:
    from .core import CSV_CONFIG, DATA_DIR
except ImportError:
    from core import CSV_CONFIG, DATA_DIR  # type: ignore[no-redef]

_SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+")


def git_blame_authors(filepath: Path) -> dict[int, str]:
    """Return {line_number: author_name} from git blame."""
    authors: dict[int, str] = {}
    try:
        result = subprocess.run(
            ["git", "blame", "--line-porcelain", str(filepath)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return authors
        current_line = 0
        for line in result.stdout.splitlines():
            if line.startswith("author "):
                authors[current_line] = line[7:].strip()
            # The line-porcelain format gives us the line number in the original
            parts = line.split()
            if len(parts) >= 3 and parts[0].isalnum() and len(parts[0]) == 40:
                current_line = int(parts[2])
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return authors


def latest_version_tag() -> str:
    """Get the latest semver tag from git."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, timeout=10,
        )
        tag = result.stdout.strip()
        if _SEMVER_RE.match(tag):
            return tag.lstrip("v")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def populate_provenance(
    filepath: Path,
    *,
    dry_run: bool = False,
) -> dict:
    """Add provenance columns and populate from git blame.

    Returns summary dict with counts.
    """
    if not filepath.exists():
        return {"file": str(filepath), "rows_updated": 0, "error": "file not found"}

    with open(filepath, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = list(reader)

    changed = False
    # Ensure provenance columns exist
    for col in ("Added By", "Last Reviewed By", "Version"):
        if col not in header:
            header.append(col)
            for row in rows:
                row[col] = ""
            changed = True

    # Get git blame data
    authors = git_blame_authors(filepath)
    version = latest_version_tag()

    rows_updated = 0
    for i, row in enumerate(rows):
        line_num = i + 2  # 1-indexed, header is line 1
        updated = False

        # Populate Added By from git blame
        if not (row.get("Added By") or "").strip():
            author = authors.get(line_num, "")
            if author and author != "Not Committed Yet":
                row["Added By"] = f"{author} (auto)"
                updated = True

        # Populate Version if empty
        if not (row.get("Version") or "").strip() and version:
            row["Version"] = version
            updated = True

        if updated:
            rows_updated += 1
            changed = True

    if changed and not dry_run:
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)

    return {"file": str(filepath), "rows_updated": rows_updated}


def validate_version(value: str) -> bool:
    """Check if a version string is valid semver."""
    if not value.strip():
        return True  # empty is OK
    return bool(_SEMVER_RE.match(value.strip()))


# ============ CLI ============
def main() -> int:
    parser = argparse.ArgumentParser(description="Backend Pro Max Provenance Populator")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--domain", type=str, default=None, help="Limit to a specific domain")
    args = parser.parse_args()

    configs = {}
    if args.domain and args.domain in CSV_CONFIG:
        configs[args.domain] = CSV_CONFIG[args.domain]
    else:
        configs = dict(CSV_CONFIG)

    total = 0
    for domain, cfg in configs.items():
        filepath = DATA_DIR / cfg["file"]
        result = populate_provenance(filepath, dry_run=args.dry_run)
        n = result["rows_updated"]
        total += n
        if n > 0:
            action = "would update" if args.dry_run else "updated"
            print(f"  {domain}: {action} {n} row(s)")

    print(f"\n{'Would update' if args.dry_run else 'Updated'} {total} total row(s) across {len(configs)} domain(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
