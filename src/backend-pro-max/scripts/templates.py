"""
Intent-specific output templates for Backend Pro Max.

Each intent gets a formatter that reshapes raw search results into a
structure optimised for that query type (e.g. troubleshoot → Symptom →
Root Cause → Fix → Verify).

The legacy Markdown formatters accept:
    format_<intent>(result: dict, show_scores: bool) -> str

The ``result`` dict is the standard search result from ``core.search()``.
Opt-in compact formatting also supports stack/cross-domain results and returns
a dictionary serialized with ``compact_json``.
"""
from __future__ import annotations

import json

try:
    from .core import classify_intent
except ImportError:
    from core import classify_intent


COMPACT_MAX_CHARS = 6000
_COMPACT_FIELDS = {
    "guidance": ("Solution", "Description", "Do", "Fix", "Mitigation", "Strengths", "Rule of Thumb"),
    "applicability": ("When to Use", "Use Case", "Workload", "From", "To"),
    "constraints": (
        "When NOT to Use", "Trade-offs", "Consistency", "Consistency Model", "Delivery", "Ordering",
        "Guarantees", "Isolation Level", "Throughput Tier", "Latency Tier", "Consistency Tier",
        "Cost Tier", "Cloud Native", "Engineering Requirement",
    ),
    "failure_modes": (
        "Problem", "Symptom", "Root Cause", "Failure Mode", "Don't", "Weaknesses", "Pitfalls",
        "Common Pitfalls", "Common Mistakes", "Gotcha", "Risk", "Threat", "Rollback Plan",
    ),
    "verification": ("Verification Method", "Evaluation Criteria", "Key Signals", "Postmortem Checklist"),
    "notes": ("Notes", "Severity", "Code Good", "Code Bad"),
}

def compact_json(value: dict) -> str:
    """Canonical compact JSON text; the limit excludes transport envelopes."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def format_compact(result: dict, max_chars: int = COMPACT_MAX_CHARS) -> dict:
    """Bound JSON by dropping whole trailing evidence units, never slicing facts."""
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars <= 0:
        raise ValueError("Compact response limit must be a positive integer")
    if "error" in result:
        raise ValueError(str(result["error"]))
    raw = result.get("results")
    if isinstance(raw, dict):
        rows = [(domain, row) for domain, group in raw.items() for row in group]
    elif isinstance(raw, list):
        rows = [(result.get("stack") or result.get("domain"), row) for row in raw]
    else:
        raise ValueError("Compact formatting requires search results")
    units = []
    for domain, row in rows:
        title_fields = ("Name", "Guideline", "Service", "Topic", "Pattern", "Style", "Operation", "Tool", "Technique")
        title_key = next((key for key in title_fields if row.get(key)), None)
        groups = {
            group: {key: row[key] for key in keys if row.get(key) not in (None, "")}
            for group, keys in _COMPACT_FIELDS.items()
        }
        facts = {key: value for key, value in groups.items() if value}
        sources = {key: row[key] for key in ("Source URL", "Docs URL") if row.get(key)}
        used = {key for group in facts.values() for key in group} | set(sources)
        used.update(("_citation", "_score", "Last Updated", title_key))
        missing = [key for key in _COMPACT_FIELDS if not groups[key]]
        if not sources:
            missing.append("sources")
        if not row.get("_citation"):
            missing.append("citation")
        if not row.get("Last Updated"):
            missing.append("last_updated")
        units.append({
            "domain": domain, "title": row[title_key] if title_key else None,
            "citation": row.get("_citation") or None,
            "sources": sources, "last_updated": row.get("Last Updated") or None,
            "facts": {key: value for group in facts.values() for key, value in group.items()},
            "missing": missing,
            "omitted_fields": [key for key in row if key not in used and row[key] not in (None, "")],
        })
    output = {
        "format": "compact-v1",
        "query": result.get("query", ""),
        "intent": result.get("intent") or classify_intent(result.get("query", "")).value,
        "matched_count": len(units), "count": len(units), "omitted_count": 0, "truncated": False,
        "status": "results" if units else "no_matches",
        "evidence_note": "Quoted KB fields, not verified advice. Missing fields are not inferred. Ranking is not confidence.",
        "results": units,
    }
    if "retrieval" in result:
        output["retrieval"] = result["retrieval"]
    while len(compact_json(output)) > max_chars:
        if not units:
            raise ValueError("Compact response metadata exceeds the character limit; shorten the query")
        units.pop()
        output.update(
            count=len(units), omitted_count=output["matched_count"] - len(units), truncated=True,
            status="results" if units else "budget_exhausted",
        )
    return output


def format_search_response(result: dict, response_format: str = "raw") -> dict:
    if response_format == "raw":
        return result
    if response_format == "compact":
        return format_compact(result)
    raise ValueError("response_format must be 'raw' or 'compact'")


def _head(row: dict) -> str:
    """Return the first non-score value as a heading identifier."""
    for k, v in row.items():
        if k == "_score":
            continue
        val = str(v).strip()
        if val:
            return val
    return "?"


def _score_tag(row: dict, show_scores: bool) -> str:
    score = row.get("_score")
    if show_scores and score is not None:
        return f"  _(rank score: {score:.2f})_"
    return ""


# ────────────────────────────────────────────────────────────────
# DEFINITION intent
# ────────────────────────────────────────────────────────────────
_DEFINITION_FIELDS = [
    ("Name", None),
    ("Category", None),
    ("Problem", "What problem it solves"),
    ("Solution", None),
    ("Description", None),
    ("Use Case", "When to use"),
    ("When to Use", None),
    ("When NOT to Use", None),
    ("Strengths", None),
    ("Weaknesses", None),
    ("Trade-offs", None),
    ("Related Patterns", "Related"),
    ("Alternatives", None),
    ("Notes", None),
]


def format_definition(result: dict, show_scores: bool = True) -> str:
    lines = ["## Backend Pro Max — Definition",
             f"**Domain:** {result.get('domain', '?')} | **Query:** {result.get('query', '?')}",
             f"**Found:** {result.get('count', 0)} result(s)\n"]
    if not result.get("results"):
        lines.append("_No matches._")
        return "\n".join(lines)
    for i, row in enumerate(result["results"], 1):
        lines.append(f"### {i}. {_head(row)}{_score_tag(row, show_scores)}")
        for col, label in _DEFINITION_FIELDS:
            val = str(row.get(col, "")).strip()
            if val:
                display = label or col
                lines.append(f"- **{display}:** {val}")
        lines.append("")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────
# TROUBLESHOOT intent
# ────────────────────────────────────────────────────────────────
_TROUBLESHOOT_FIELDS = [
    ("Symptom", None),
    ("Root Cause", None),
    ("Fix", None),
    ("Mitigation", None),
    ("Do", "✅ Do"),
    ("Don't", "❌ Don't"),
    ("Tooling", "Diagnostic tooling"),
    ("Severity", None),
    ("Notes", "Verify / Notes"),
]


def format_troubleshoot(result: dict, show_scores: bool = True) -> str:
    lines = ["## Backend Pro Max — Troubleshooting",
             f"**Domain:** {result.get('domain', '?')} | **Query:** {result.get('query', '?')}",
             f"**Found:** {result.get('count', 0)} result(s)\n"]
    if not result.get("results"):
        lines.append("_No matches._")
        return "\n".join(lines)
    for i, row in enumerate(result["results"], 1):
        lines.append(f"### {i}. {_head(row)}{_score_tag(row, show_scores)}")
        for col, label in _TROUBLESHOOT_FIELDS:
            val = str(row.get(col, "")).strip()
            if val:
                display = label or col
                lines.append(f"- **{display}:** {val}")
        lines.append("")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────
# MIGRATION intent
# ────────────────────────────────────────────────────────────────
_MIGRATION_FIELDS = [
    ("Name", "Technology / Pattern"),
    ("Category", None),
    ("Use Case", None),
    ("Strengths", "Strengths (target)"),
    ("Weaknesses", "Risks / Weaknesses"),
    ("When to Use", "When to migrate"),
    ("When NOT to Use", "When NOT to migrate"),
    ("Alternatives", None),
    ("Notes", "Migration notes"),
]


def format_migration(result: dict, show_scores: bool = True) -> str:
    lines = ["## Backend Pro Max — Migration Guide",
             f"**Domain:** {result.get('domain', '?')} | **Query:** {result.get('query', '?')}",
             f"**Found:** {result.get('count', 0)} result(s)\n"]
    if not result.get("results"):
        lines.append("_No matches._")
        return "\n".join(lines)
    for i, row in enumerate(result["results"], 1):
        lines.append(f"### {i}. {_head(row)}{_score_tag(row, show_scores)}")
        for col, label in _MIGRATION_FIELDS:
            val = str(row.get(col, "")).strip()
            if val:
                display = label or col
                lines.append(f"- **{display}:** {val}")
        lines.append("")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────
# INCIDENT intent
# ────────────────────────────────────────────────────────────────
_INCIDENT_FIELDS = [
    ("Name", "Component / Topic"),
    ("Symptom", "Symptom / Failure Mode"),
    ("Failure Mode", None),
    ("Root Cause", None),
    ("Mitigation", None),
    ("Fix", "Remediation"),
    ("Do", "✅ Do"),
    ("Don't", "❌ Don't"),
    ("Metric", "Key metric"),
    ("Severity", None),
    ("Notes", "Postmortem notes"),
]


def format_incident(result: dict, show_scores: bool = True) -> str:
    lines = ["## Backend Pro Max — Incident Response",
             f"**Domain:** {result.get('domain', '?')} | **Query:** {result.get('query', '?')}",
             f"**Found:** {result.get('count', 0)} result(s)\n"]
    if not result.get("results"):
        lines.append("_No matches._")
        return "\n".join(lines)
    for i, row in enumerate(result["results"], 1):
        lines.append(f"### {i}. {_head(row)}{_score_tag(row, show_scores)}")
        for col, label in _INCIDENT_FIELDS:
            val = str(row.get(col, "")).strip()
            if val:
                display = label or col
                lines.append(f"- **{display}:** {val}")
        lines.append("")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────
# Dispatch map
# ────────────────────────────────────────────────────────────────
# Note: COMPARISON and DESIGN intents are already handled by dedicated
# code paths in search.py (format_compare / format_design). They are
# included here so callers can dispatch all intents through one dict.
INTENT_FORMATTERS = {
    "definition": format_definition,
    "troubleshoot": format_troubleshoot,
    "migration": format_migration,
    "incident": format_incident,
    # "comparison" and "design" are handled elsewhere; "general" uses the
    # existing format_output in search.py.
}


def format_by_intent(intent_value: str, result: dict, show_scores: bool = True) -> str | None:
    """Dispatch to the intent-specific formatter.

    Returns the formatted string, or None if no special formatter exists
    for the intent (caller should fall back to the default formatter).
    """
    formatter = INTENT_FORMATTERS.get(intent_value)
    if formatter is None:
        return None
    return formatter(result, show_scores=show_scores)
