#!/usr/bin/env python3
"""
Freshness scanner — find stale rows and broken Source URLs across all
Backend Pro Max knowledge bases.

Usage:
    python scripts/freshness.py --dry-run [--domain <domain>]
    python scripts/freshness.py --open-issues [--domain <domain>]

Designed to run as a weekly GitHub Action (see .github/workflows/freshness.yml).
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

try:
    from .core import CSV_CONFIG, DATA_DIR, STACK_CONFIG, _parse_date
except ImportError:
    from core import CSV_CONFIG, DATA_DIR, STACK_CONFIG, _parse_date  # type: ignore[no-redef]


# ============ CONFIGURATION ============
DEFAULT_MAX_AGE_MONTHS = 18
URL_TIMEOUT = 5
URL_MAX_RETRIES = 3
URL_CONCURRENCY = 5


# ============ STALE DETECTION ============
def find_stale_rows(filepath: Path, max_age_months: int = DEFAULT_MAX_AGE_MONTHS) -> list[dict]:
    """Return rows with Last Updated older than max_age_months."""
    if not filepath.exists():
        return []
    cutoff = datetime.now()
    stale = []
    with open(filepath, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            raw = (row.get("Last Updated") or row.get("Updated") or "").strip()
            if not raw:
                continue
            dt = _parse_date(raw)
            if dt is None:
                continue
            age_months = (cutoff.year - dt.year) * 12 + (cutoff.month - dt.month)
            if age_months > max_age_months:
                name = row.get("Name") or row.get("Topic") or row.get("Tool") or row.get("Service") or row.get("Operation") or row.get("Model") or row.get("Technique") or row.get("Style") or row.get("Category") or "?"
                stale.append({
                    "line": i,
                    "name": name,
                    "last_updated": raw,
                    "age_months": age_months,
                })
    return stale


# ============ URL CHECKING ============
def check_url(url: str, retries: int = URL_MAX_RETRIES, timeout: int = URL_TIMEOUT) -> dict:
    """Check a single URL. Returns dict with status."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "backendpro-freshness/1.0")
            resp = urllib.request.urlopen(req, timeout=timeout)  # noqa: S310
            return {"url": url, "status": resp.status, "ok": resp.status < 400}
        except urllib.error.HTTPError as exc:
            if attempt == retries - 1:
                return {"url": url, "status": exc.code, "ok": False, "error": str(exc)}
        except (urllib.error.URLError, OSError) as exc:
            if attempt == retries - 1:
                return {"url": url, "status": 0, "ok": False, "error": str(exc)}
    return {"url": url, "status": 0, "ok": False, "error": "max retries"}


def check_urls_in_file(filepath: Path) -> list[dict]:
    """Check all Source URLs in a CSV. Returns list of broken entries."""
    if not filepath.exists():
        return []
    urls_to_check = []
    with open(filepath, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            url = (row.get("Source URL") or "").strip()
            if url and url.startswith(("http://", "https://")):
                name = row.get("Name") or row.get("Topic") or row.get("Tool") or "?"
                urls_to_check.append((i, name, url))

    broken = []
    with ThreadPoolExecutor(max_workers=URL_CONCURRENCY) as executor:
        future_to_info = {
            executor.submit(check_url, url): (line, name, url)
            for line, name, url in urls_to_check
        }
        for future in as_completed(future_to_info):
            line, name, url = future_to_info[future]
            result = future.result()
            if not result["ok"]:
                broken.append({
                    "line": line,
                    "name": name,
                    "url": url,
                    "status": result.get("status", 0),
                    "error": result.get("error", ""),
                })
    return broken


# ============ SCANNING ============
def scan_domain(domain: str, cfg: dict, max_age_months: int = DEFAULT_MAX_AGE_MONTHS, check_urls: bool = True) -> dict:
    """Scan a single domain for stale rows and broken URLs."""
    filepath = DATA_DIR / cfg["file"]
    stale = find_stale_rows(filepath, max_age_months)
    broken = check_urls_in_file(filepath) if check_urls else []
    return {
        "domain": domain,
        "file": cfg["file"],
        "stale": stale,
        "broken": broken,
    }


def scan_all(
    domain: str | None = None,
    max_age_months: int = DEFAULT_MAX_AGE_MONTHS,
    check_urls: bool = True,
) -> list[dict]:
    """Scan all (or one) domain(s) for freshness issues."""
    results = []
    configs = {}
    if domain:
        if domain in CSV_CONFIG:
            configs[domain] = CSV_CONFIG[domain]
        elif domain in STACK_CONFIG:
            configs[domain] = STACK_CONFIG[domain]
        else:
            return []
    else:
        configs.update(CSV_CONFIG)
        for stack, cfg in STACK_CONFIG.items():
            configs[f"stack:{stack}"] = cfg

    for dom, cfg in configs.items():
        result = scan_domain(dom, cfg, max_age_months, check_urls)
        if result["stale"] or result["broken"]:
            results.append(result)
    return results


# ============ ISSUE FORMATTING ============
def format_issue_body(result: dict) -> str:
    """Format a freshness scan result as a GitHub issue body."""
    lines = [f"## Freshness Report: `{result['domain']}`\n"]
    lines.append(f"**File:** `{result['file']}`\n")

    if result["stale"]:
        lines.append(f"### ⏰ Stale Rows ({len(result['stale'])})\n")
        lines.append("| Line | Name | Last Updated | Age (months) |")
        lines.append("| --- | --- | --- | --- |")
        for row in result["stale"]:
            lines.append(f"| L{row['line']} | {row['name']} | {row['last_updated']} | {row['age_months']} |")
        lines.append("")

    if result["broken"]:
        lines.append(f"### 🔗 Broken URLs ({len(result['broken'])})\n")
        lines.append("| Line | Name | URL | Status | Error |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in result["broken"]:
            lines.append(f"| L{row['line']} | {row['name']} | {row['url']} | {row['status']} | {row.get('error', '')} |")
        lines.append("")

    return "\n".join(lines)


def issue_title(result: dict) -> str:
    """Generate a GitHub issue title for a freshness finding."""
    n_stale = len(result["stale"])
    n_broken = len(result["broken"])
    return f"[Freshness] {result['domain']}: {n_stale} stale, {n_broken} broken URLs"


def check_existing_issue(domain: str) -> bool:
    """Check if an open freshness issue already exists for this domain."""
    prefix = f"[Freshness] {domain}:"
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--search", prefix, "--json", "title"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0 and prefix.lower() in out.stdout.lower():
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def open_issue(title: str, body: str) -> bool:
    """Open a GitHub issue. Returns True on success."""
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body, "--label", "freshness"],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ============ CLI ============
def main() -> int:
    parser = argparse.ArgumentParser(description="Backend Pro Max Freshness Scanner")
    parser.add_argument("--dry-run", action="store_true", help="Preview findings without opening issues")
    parser.add_argument("--open-issues", action="store_true", help="Open GitHub issues for findings")
    parser.add_argument("--domain", type=str, default=None, help="Limit scan to a specific domain")
    parser.add_argument("--max-age-months", type=int, default=DEFAULT_MAX_AGE_MONTHS)
    parser.add_argument("--no-url-check", action="store_true", help="Skip URL checking")
    args = parser.parse_args()

    results = scan_all(
        domain=args.domain,
        max_age_months=args.max_age_months,
        check_urls=not args.no_url_check,
    )

    if not results:
        print("✅ No freshness issues found.")
        return 0

    for result in results:
        title = issue_title(result)
        body = format_issue_body(result)

        if args.dry_run:
            print(f"\n{'=' * 60}")
            print(f"TITLE: {title}")
            print(body)
        elif args.open_issues:
            if check_existing_issue(result["domain"]):
                print(f"⏭  Skipping {result['domain']} — open issue already exists")
                continue
            if open_issue(title, body):
                print(f"✅ Opened issue: {title}")
            else:
                print(f"❌ Failed to open issue: {title}", file=sys.stderr)
        else:
            print(f"{title}")

    total_stale = sum(len(r["stale"]) for r in results)
    total_broken = sum(len(r["broken"]) for r in results)
    print(f"\nSummary: {total_stale} stale rows, {total_broken} broken URLs across {len(results)} domain(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
