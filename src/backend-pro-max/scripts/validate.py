#!/usr/bin/env python3
"""
Validate every CSV in `data/` against its declared schema in `core.py`.

Checks performed:
  1. The file exists and is non-empty.
  2. CSV parses cleanly (no ragged rows).
  3. Every column listed in `search_cols` and `output_cols` is present in
     the CSV header.
  4. Every row has at least one non-empty searchable column.
  5. If a `Last Updated` column exists, every populated value parses as a
     date (YYYY-MM-DD, YYYY/MM/DD, YYYY-MM, or YYYY).

Exit code: 0 on success, 1 if any error is found.

Run:
    python -m backendpro.scripts.validate
    python src/backend-pro-max/scripts/validate.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

try:
    from .core import (
        _STACK_COLS,
        CSV_CONFIG,
        DATA_DIR,
        STACK_CONFIG,
        _parse_date,
    )
except ImportError:
    from core import (  # type: ignore[no-redef]
        _STACK_COLS,
        CSV_CONFIG,
        DATA_DIR,
        STACK_CONFIG,
        _parse_date,
    )


def _validate_file(label: str, filepath: Path, search_cols, output_cols) -> list[str]:
    errors: list[str] = []
    if not filepath.exists():
        return [f"[{label}] missing file: {filepath}"]

    try:
        with open(filepath, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            rows = list(reader)
    except Exception as exc:  # noqa: BLE001
        return [f"[{label}] failed to parse {filepath.name}: {exc}"]

    if not rows:
        errors.append(f"[{label}] {filepath.name}: no data rows")

    header_set = set(header)
    for col in search_cols:
        if col not in header_set:
            errors.append(f"[{label}] {filepath.name}: missing search column '{col}'")
    for col in output_cols:
        if col not in header_set:
            errors.append(f"[{label}] {filepath.name}: missing output column '{col}'")

    has_updated_col = "Last Updated" in header_set or "Updated" in header_set

    for i, row in enumerate(rows, start=2):  # line 1 is header
        # Ragged rows: csv.DictReader gives us None keys for extras
        if None in row:
            errors.append(f"[{label}] {filepath.name}:L{i}: extra/ragged columns")
        # At least one search column must be non-empty
        if not any((row.get(c) or "").strip() for c in search_cols if c in header_set):
            errors.append(f"[{label}] {filepath.name}:L{i}: all search columns empty")
        # Date sanity
        if has_updated_col:
            raw = (row.get("Last Updated") or row.get("Updated") or "").strip()
            if raw and _parse_date(raw) is None:
                errors.append(
                    f"[{label}] {filepath.name}:L{i}: unparseable date '{raw}' "
                    f"(use YYYY-MM-DD, YYYY/MM/DD, YYYY-MM, or YYYY)"
                )

    return errors


def validate_all() -> list[str]:
    errors: list[str] = []
    for domain, cfg in CSV_CONFIG.items():
        errors.extend(_validate_file(
            f"domain:{domain}",
            DATA_DIR / cfg["file"],
            cfg["search_cols"],
            cfg["output_cols"],
        ))
    for stack, cfg in STACK_CONFIG.items():
        errors.extend(_validate_file(
            f"stack:{stack}",
            DATA_DIR / cfg["file"],
            _STACK_COLS["search_cols"],
            _STACK_COLS["output_cols"],
        ))
    return errors


def main() -> int:
    errors = validate_all()
    if errors:
        print(f"❌ CSV validation failed with {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    domain_count = len(CSV_CONFIG)
    stack_count = len(STACK_CONFIG)
    print(f"✅ All CSVs valid ({domain_count} domains + {stack_count} stacks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
