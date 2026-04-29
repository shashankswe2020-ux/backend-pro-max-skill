"""Golden query test suite — guards BM25 retrieval quality.

Loads ``tests/golden-queries.yml`` and parametrises one test per entry,
asserting that the expected rows appear in the top-N search results.

Requires PyYAML (part of the ``[dev]`` extra).
"""
from __future__ import annotations

import json
from pathlib import Path

import core
import pytest

# ---------------------------------------------------------------------------
# Load golden queries (YAML with stdlib JSON fallback)
# ---------------------------------------------------------------------------
_GOLDEN_FILE = Path(__file__).parent / "golden-queries.yml"


def _load_golden_queries():
    """Load golden queries from YAML (preferred) or JSON."""
    path = _GOLDEN_FILE
    if not path.exists():
        # Try .json fallback
        path = path.with_suffix(".json")
    if not path.exists():
        pytest.skip("golden-queries file not found")

    text = path.read_text(encoding="utf-8")

    if path.suffix in (".yml", ".yaml"):
        try:
            import yaml
        except ImportError:
            # Minimal YAML subset parser — handles our simple list-of-dicts format
            return _parse_simple_yaml(text)
        return yaml.safe_load(text)
    else:
        return json.loads(text)


def _parse_simple_yaml(text: str) -> list[dict]:
    """Minimal parser for the subset of YAML used by golden-queries.yml.

    Handles a flat list of mappings with string/number/list values.
    This avoids requiring PyYAML at runtime.
    """
    import re

    entries: list[dict] = []
    current: dict | None = None

    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue

        # New list item: "- key: value"
        m = re.match(r'^- (\w[\w-]*):\s*(.*)', stripped)
        if m:
            current = {}
            entries.append(current)
            key, val = m.group(1), m.group(2).strip()
            current[key] = _yaml_val(val)
            continue

        # Continuation key: "  key: value"
        m = re.match(r'^(\w[\w-]*):\s*(.*)', stripped)
        if m and current is not None:
            key, val = m.group(1), m.group(2).strip()
            current[key] = _yaml_val(val)
            continue

        # List continuation: "    - value"
        m = re.match(r'^-\s+(.*)', stripped)
        if m and current is not None:
            # Find the last key that has a list value
            for k in reversed(list(current.keys())):
                if isinstance(current[k], list):
                    current[k].append(_yaml_scalar(m.group(1).strip()))
                    break

    return entries


def _yaml_val(val: str):
    """Parse a simple YAML value — string, number, or inline list."""
    if not val:
        return ""
    # Inline list: ["a", "b"]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1]
        return [_yaml_scalar(s.strip().strip('"').strip("'")) for s in inner.split(",") if s.strip()]
    return _yaml_scalar(val)


def _yaml_scalar(val: str):
    """Parse a scalar — number, bool, or string."""
    val = val.strip('"').strip("'")
    if val.replace(".", "", 1).isdigit():
        return float(val) if "." in val else int(val)
    return val


# ---------------------------------------------------------------------------
# Parametrised tests
# ---------------------------------------------------------------------------
_golden = _load_golden_queries()


def _make_id(entry: dict) -> str:
    """Generate a human-readable test ID."""
    target = entry.get("domain") or entry.get("stack") or entry.get("mode", "?")
    q = entry.get("query", "?")[:40]
    return f"{target}:{q}"


def _name_col_value(row: dict) -> str:
    """Extract the 'name' column from a result row (first non-score column)."""
    for k, v in row.items():
        if k.startswith("_"):
            continue
        return str(v)
    return ""


def _matches_any(actual_name: str, expected_list: list[str]) -> bool:
    """Check if actual_name (case-insensitive) contains any expected substring."""
    lower = actual_name.lower()
    return any(exp.lower() in lower for exp in expected_list)


@pytest.mark.parametrize(
    "entry",
    _golden,
    ids=[_make_id(e) for e in _golden],
)
def test_golden_query(entry):
    """Assert that expected rows appear in top-N results."""
    core.clear_cache()

    query = entry["query"]
    expected = entry["expected_top"]
    top_n = entry.get("top_n", 5)
    min_score = entry.get("min_score")
    mode = entry.get("mode")

    # --- Execute search based on mode ---
    if mode == "compare":
        compare_args = entry.get("compare_args", [])
        domain = entry.get("domain")
        result = core.compare(compare_args, domain=domain)
        # compare returns {"entries": {name: row_dict}}
        rows = [v for v in result.get("entries", {}).values() if v]
    elif mode == "all":
        result = core.search_all(query, max_results=top_n)
        # search_all returns {"results": {domain: [rows]}}
        rows = []
        results_dict = result.get("results", {})
        if isinstance(results_dict, dict):
            for d_rows in results_dict.values():
                if isinstance(d_rows, list):
                    rows.extend(d_rows)
    elif "stack" in entry:
        result = core.search_stack(query, entry["stack"], max_results=top_n)
        rows = result.get("results", [])
    else:
        domain = entry.get("domain")
        result = core.search(query, domain=domain, max_results=top_n)
        rows = result.get("results", [])

    # --- Build actual names for assertion ---
    actual_names = [_name_col_value(r) for r in rows[:top_n]]

    # --- Assert at least one expected value appears ---
    found = any(
        _matches_any(name, expected)
        for name in actual_names
    )

    if not found:
        # Build actionable failure message
        actual_display = []
        for i, row in enumerate(rows[:top_n]):
            name = _name_col_value(row)
            score = row.get("_score", "?")
            actual_display.append(f"  #{i + 1}: {name} (score={score})")
        actual_str = "\n".join(actual_display) if actual_display else "  (no results)"
        msg = (
            f"\n{'=' * 60}\n"
            f"GOLDEN QUERY FAILURE\n"
            f"  Query:    {query!r}\n"
            f"  Target:   {entry.get('domain') or entry.get('stack') or mode}\n"
            f"  Expected: any of {expected} in top-{top_n}\n"
            f"  Actual top-{top_n}:\n{actual_str}\n"
            f"{'=' * 60}"
        )
        pytest.fail(msg)

    # --- Optional: check min_score ---
    if min_score is not None and rows:
        top_score = rows[0].get("_score", 0)
        if isinstance(top_score, (int, float)) and top_score < min_score:
            pytest.fail(
                f"Top hit score {top_score:.2f} < min_score {min_score} "
                f"for query {query!r}"
            )
