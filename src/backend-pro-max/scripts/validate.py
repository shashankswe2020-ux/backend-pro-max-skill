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
  6. If `Source Type` is present, values must be from the allowed enum.
  7. Soft warnings for missing `Source URL` / `Last Updated` (not errors).
  8. `--strict`: fail on rows without `Source URL` + `Last Updated`.
  9. `--check-urls`: verify `Source URL` values return HTTP 200.

Exit code: 0 on success, 1 if any error is found.

Run:
    python -m backendpro.scripts.validate
    python src/backend-pro-max/scripts/validate.py
    python -m backendpro.scripts.validate --strict
    python -m backendpro.scripts.validate --check-urls
"""

from __future__ import annotations

import argparse
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

# Allowed values for the Source Type column.
VALID_SOURCE_TYPES = frozenset({
    "official-docs",
    "paper",
    "postmortem",
    "engineering-blog",
    "book",
    "benchmark",
    "rfc",
})


def _validate_file(
    label: str,
    filepath: Path,
    search_cols,
    output_cols,
    *,
    strict: bool = False,
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    if not filepath.exists():
        return [f"[{label}] missing file: {filepath}"], []

    try:
        with open(filepath, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            rows = list(reader)
    except Exception as exc:  # noqa: BLE001
        return [f"[{label}] failed to parse {filepath.name}: {exc}"], []

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
    has_source_url_col = "Source URL" in header_set
    has_source_type_col = "Source Type" in header_set

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
        # Source Type enum check
        if has_source_type_col:
            src_type = (row.get("Source Type") or "").strip()
            if src_type and src_type not in VALID_SOURCE_TYPES:
                errors.append(
                    f"[{label}] {filepath.name}:L{i}: invalid Source Type '{src_type}' "
                    f"(allowed: {', '.join(sorted(VALID_SOURCE_TYPES))})"
                )
        # Source URL / Last Updated warnings (soft) or errors (strict)
        if has_source_url_col:
            src_url = (row.get("Source URL") or "").strip()
            if not src_url:
                msg = f"[{label}] {filepath.name}:L{i}: missing Source URL"
                if strict:
                    errors.append(msg)
                else:
                    warnings.append(msg)
        if has_updated_col:
            upd = (row.get("Last Updated") or row.get("Updated") or "").strip()
            if not upd:
                msg = f"[{label}] {filepath.name}:L{i}: missing Last Updated"
                if strict:
                    errors.append(msg)
                else:
                    warnings.append(msg)

    return errors, warnings


def check_urls(domain: str | None = None) -> list[str]:
    """Check Source URLs for HTTP 200. Returns list of broken URL messages."""
    import urllib.error
    import urllib.request

    broken: list[str] = []
    configs = {}
    if domain and domain in CSV_CONFIG:
        configs[domain] = CSV_CONFIG[domain]
    else:
        configs = CSV_CONFIG

    for dom, cfg in configs.items():
        filepath = DATA_DIR / cfg["file"]
        if not filepath.exists():
            continue
        with open(filepath, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for i, row in enumerate(rows, start=2):
            url = (row.get("Source URL") or "").strip()
            if not url or not url.startswith(("http://", "https://")):
                continue
            try:
                req = urllib.request.Request(url, method="HEAD")
                req.add_header("User-Agent", "backendpro-validate/1.0")
                resp = urllib.request.urlopen(req, timeout=5)  # noqa: S310
                if resp.status >= 400:
                    broken.append(f"[{dom}] L{i}: HTTP {resp.status} — {url}")
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
                broken.append(f"[{dom}] L{i}: {exc} — {url}")
    return broken


def validate_all(*, strict: bool = False) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) across all CSVs."""
    all_errors: list[str] = []
    all_warnings: list[str] = []
    for domain, cfg in CSV_CONFIG.items():
        errs, warns = _validate_file(
            f"domain:{domain}",
            DATA_DIR / cfg["file"],
            cfg["search_cols"],
            cfg["output_cols"],
            strict=strict,
        )
        all_errors.extend(errs)
        all_warnings.extend(warns)
    for stack, cfg in STACK_CONFIG.items():
        errs, warns = _validate_file(
            f"stack:{stack}",
            DATA_DIR / cfg["file"],
            _STACK_COLS["search_cols"],
            _STACK_COLS["output_cols"],
            strict=strict,
        )
        all_errors.extend(errs)
        all_warnings.extend(warns)
    return all_errors, all_warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Backend Pro Max CSVs")
    parser.add_argument("--strict", action="store_true",
                        help="Fail on rows missing Source URL or Last Updated")
    parser.add_argument("--check-urls", action="store_true",
                        help="Check Source URLs for HTTP 200 (slow)")
    parser.add_argument("--domain", type=str, default=None,
                        help="Limit URL checks to a specific domain")
    args = parser.parse_args()

    errors, warnings = validate_all(strict=args.strict)

    if warnings:
        print(f"⚠️  {len(warnings)} warning(s) (missing Source URL / Last Updated):",
              file=sys.stderr)
        # Show summary, not every line
        from collections import Counter
        by_file: Counter = Counter()
        for w in warnings:
            # Extract file label
            parts = w.split("]", 1)
            label = parts[0].lstrip("[") if parts else "?"
            by_file[label] += 1
        for label, count in sorted(by_file.items()):
            print(f"  - {label}: {count} row(s) missing source info", file=sys.stderr)

    if args.check_urls:
        broken = check_urls(domain=args.domain)
        if broken:
            print(f"\n🔗 {len(broken)} broken URL(s):", file=sys.stderr)
            for b in broken:
                print(f"  - {b}", file=sys.stderr)
            errors.extend(broken)

    if errors:
        print(f"\n❌ CSV validation failed with {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    domain_count = len(CSV_CONFIG)
    stack_count = len(STACK_CONFIG)
    print(f"✅ All CSVs valid ({domain_count} domains + {stack_count} stacks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
