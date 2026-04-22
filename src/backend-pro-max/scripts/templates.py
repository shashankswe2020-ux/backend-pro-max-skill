"""
Intent-specific output templates for Backend Pro Max.

Each intent gets a formatter that reshapes raw search results into a
structure optimised for that query type (e.g. troubleshoot → Symptom →
Root Cause → Fix → Verify).

All formatters accept the same signature:
    format_<intent>(result: dict, show_scores: bool) -> str

The ``result`` dict is the standard search result from ``core.search()``.
"""
from __future__ import annotations


def _head(row: dict) -> str:
    """Return the first non-score value as a heading identifier."""
    for k, v in row.items():
        if k == "_score":
            continue
        val = str(v).strip()
        if val:
            return val
    return "?"


def _confidence_label(score: float) -> str:
    if score >= 4.0:
        return "high"
    if score >= 1.5:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def _score_tag(row: dict, show_scores: bool) -> str:
    score = row.get("_score")
    if show_scores and score is not None:
        return f"  _(score: {score:.2f}, confidence: {_confidence_label(score)})_"
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
