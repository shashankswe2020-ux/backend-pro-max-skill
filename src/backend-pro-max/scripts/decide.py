#!/usr/bin/env python3
"""
Backend Pro Max — Decision Intelligence module.

Provides opinionated, multi-domain recommendations:
  - decide()  — ranked recommendations with constraint scoring
  - adr()     — Architecture Decision Record generator
  - design()  — system design scaffolding

Pure standard-library implementation (Python 3.8+).
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    from .core import (
        _CONSTRAINT_COL_MAP,
        apply_constraints,
        detect_domain,
        search,
    )
except ImportError:
    from core import (  # type: ignore[no-redef]
        _CONSTRAINT_COL_MAP,
        apply_constraints,
        detect_domain,
        search,
    )

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "base"


def _get_name(row):
    """Extract the display name from a KB row with explicit key lookup + fallback."""
    return (row.get("Name") or row.get("Technology") or row.get("Pattern")
            or str(next(iter(row.values()), ""))).strip()


# ============ CONSTRAINT EXTRACTOR ============
# Regex patterns to extract structured facets from natural-language requirements.

_THROUGHPUT_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*([kmbt])\s*(?:events?|msg|messages?|req|requests?|ops?|writes?|reads?|inserts?|qps|rps|tps)(?:/\s*(?:sec|s|second|min|minute|day|d))?',
    re.IGNORECASE,
)
_LATENCY_RE = re.compile(
    r'[<≤]?\s*(\d+(?:\.\d+)?)\s*(ms|μs|us|s|seconds?|milliseconds?)',
    re.IGNORECASE,
)
_CLOUD_RE = re.compile(
    r'\b(aws|gcp|google\s*cloud|azure|multi[- ]?cloud)\b',
    re.IGNORECASE,
)
_CONSISTENCY_RE = re.compile(
    r'\b(strong(?:ly)?[ -]?consisten\w*|eventual(?:ly)?[ -]?consisten\w*|linearizab\w*|causal|tunable)\b',
    re.IGNORECASE,
)
_ORDERED_RE = re.compile(
    r'\b(ordered|ordering|fifo|in[- ]?order)\b',
    re.IGNORECASE,
)

_MULTIPLIERS = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "t": 1_000_000_000_000}


def extract_constraints(requirement):
    """Parse a natural-language requirement string into structured constraint facets.

    Returns a dict with keys: throughput, latency, cloud, consistency, ordering,
    and the raw values extracted.
    """
    facets = {}

    # Throughput
    m = _THROUGHPUT_RE.search(requirement)
    if m:
        num = float(m.group(1).replace(",", ""))
        mult = _MULTIPLIERS.get(m.group(2).lower(), 1)
        total = num * mult
        if total >= 100_000:
            facets["throughput"] = "very-high"
        elif total >= 10_000:
            facets["throughput"] = "high"
        elif total >= 1_000:
            facets["throughput"] = "medium"
        else:
            facets["throughput"] = "low"
        facets["_throughput_raw"] = int(total)

    # Latency
    m = _LATENCY_RE.search(requirement)
    if m:
        num = float(m.group(1))
        unit = m.group(2).lower()
        if unit in ("μs", "us"):
            ms = num / 1000
        elif unit in ("s", "seconds", "second"):
            ms = num * 1000
        else:
            ms = num
        if ms < 1:
            facets["latency"] = "sub-ms"
        elif ms < 10:
            facets["latency"] = "low-ms"
        elif ms < 100:
            facets["latency"] = "tens-ms"
        elif ms < 1000:
            facets["latency"] = "hundreds-ms"
        else:
            facets["latency"] = "seconds"
        facets["_latency_ms"] = ms

    # Cloud
    m = _CLOUD_RE.search(requirement)
    if m:
        raw = m.group(1).lower().replace(" ", "")
        cloud_map = {"googlecloud": "gcp", "multicloud": "multi"}
        facets["cloud"] = cloud_map.get(raw, raw)

    # Consistency
    m = _CONSISTENCY_RE.search(requirement)
    if m:
        raw = m.group(1).lower()
        if "strong" in raw or "lineariz" in raw:
            facets["consistency"] = "strong"
        elif "eventual" in raw:
            facets["consistency"] = "eventual"
        elif "causal" in raw:
            facets["consistency"] = "tunable"
        elif "tunable" in raw:
            facets["consistency"] = "tunable"

    # Ordering
    if _ORDERED_RE.search(requirement):
        facets["ordering"] = True

    return facets


def _detect_relevant_domains(requirement):
    """Detect which domains are relevant for a multi-domain recommendation."""
    # Use detect_domain for the primary, but also check for secondary domains.
    primary = detect_domain(requirement)
    domains = [primary]

    # Keywords that suggest additional domains to search.
    domain_hints = {
        "cloud": ["cloud"],
        "cache": ["cache", "caching", "redis", "cdn"],
        "messaging": ["event", "queue", "broker", "kafka", "messaging", "stream"],
        "database": ["database", "db", "store", "storage", "postgres", "mysql", "mongo"],
        "pattern": ["pattern", "circuit", "saga", "retry", "outbox"],
        "scaling": ["scale", "scaling", "shard", "partition", "replica"],
        "reliability": ["reliable", "reliability", "failover", "retry", "timeout"],
        "consistency": ["consistent", "consistency", "eventual", "strong"],
        "performance": ["latency", "throughput", "performance", "p99"],
    }

    req_lower = requirement.lower()
    for domain, keywords in domain_hints.items():
        if domain not in domains:
            for kw in keywords:
                if kw in req_lower:
                    domains.append(domain)
                    break

    return domains[:5]  # Cap at 5 domains


# ============ DECIDE ============
def decide(requirement, max_candidates=5):
    """Multi-domain orchestrated recommendation.

    Given a natural-language requirement, extract constraints, search across
    relevant domains, score candidates, and return ranked recommendations.

    Returns a dict with:
      - requirement: the original string
      - facets: extracted constraint facets
      - domains_searched: list of domains queried
      - candidates: ranked list of candidates with constraint annotations
      - recommendation: the top-ranked candidate
    """
    facets = extract_constraints(requirement)
    domains = _detect_relevant_domains(requirement)

    # Collect candidates from all relevant domains.
    all_candidates = []
    domains_searched = []

    for domain in domains:
        result = search(requirement, domain=domain, max_results=max_candidates)
        if "error" in result or result.get("count", 0) == 0:
            continue
        domains_searched.append(domain)
        for row in result["results"]:
            row["_source_domain"] = domain
            all_candidates.append(row)

    # Build constraint dict for apply_constraints (exclude private keys).
    constraint_dict = {k: v for k, v in facets.items() if not k.startswith("_")}
    # Remove non-column constraints (like 'ordering') that don't map to CSV columns.
    column_constraints = {k: v for k, v in constraint_dict.items() if k in _CONSTRAINT_COL_MAP}

    # Apply constraint filtering.
    if column_constraints:
        all_candidates = apply_constraints(all_candidates, column_constraints)

    # Deduplicate by name — keep highest-scored row per name.
    best_by_name = {}
    for c in all_candidates:
        name = _get_name(c).lower()
        score = float(c.get("_score", 0))
        if name not in best_by_name or score > float(best_by_name[name].get("_score", 0)):
            best_by_name[name] = c
    candidates = list(best_by_name.values())[:max_candidates]

    return {
        "mode": "decide",
        "requirement": requirement,
        "facets": facets,
        "domains_searched": domains_searched,
        "candidates_count": len(candidates),
        "candidates": candidates,
        "recommendation": candidates[0] if candidates else None,
    }


# ============ ADR GENERATOR ============
_ADR_TEMPLATE = """\
# ADR: {title}

## Status

Proposed

## Context

{context}

## Decision

{decision}

## Alternatives Considered

{alternatives}

## Consequences

{consequences}

## References

{references}
"""


def adr(title, context_domains, out_path=None):
    """Generate a Michael Nygard-format Architecture Decision Record.

    Args:
        title: ADR title (e.g. "Adopt outbox pattern").
        context_domains: list of domain names to search for context.
        out_path: if set, write the ADR to this file path.

    Returns a dict with the ADR text and structured data.
    """
    if not context_domains:
        return {"error": "adr requires at least one context domain (--context)."}

    # Search each context domain for the title.
    all_rows = []
    context_parts = []
    for domain in context_domains:
        result = search(title, domain=domain, max_results=3)
        if "error" in result or result.get("count", 0) == 0:
            continue
        for row in result["results"]:
            row["_source_domain"] = domain
            all_rows.append(row)
        # Build context paragraph from top result.
        top = result["results"][0]
        name = _get_name(top)
        strengths = top.get("Strengths", top.get("Use Case", ""))
        context_parts.append(
            f"- **{name}** (`{domain}`): {strengths}" if strengths
            else f"- **{name}** (`{domain}`)"
        )

    if not all_rows:
        return {"error": f"No KB rows found for '{title}' in domains: {', '.join(context_domains)}"}

    # Decision: top-ranked row.
    top_row = all_rows[0]
    top_name = _get_name(top_row)
    top_domain = top_row.get("_source_domain", "?")

    # Alternatives: remaining unique rows.
    alt_parts = []
    seen = {top_name.lower()}
    for row in all_rows[1:]:
        name = _get_name(row)
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        strengths = row.get("Strengths", "")
        weaknesses = row.get("Weaknesses", "")
        line = f"- **{name}** (`{row.get('_source_domain', '?')}`)"
        if strengths:
            line += f"\n  - Strengths: {strengths}"
        if weaknesses:
            line += f"\n  - Weaknesses: {weaknesses}"
        alt_parts.append(line)

    # Consequences from chosen option.
    consequence_parts = []
    for key in ("Weaknesses", "Pitfalls", "Trade-offs", "When NOT to Use"):
        val = top_row.get(key, "").strip()
        if val:
            consequence_parts.append(f"- **{key}:** {val}")

    # References.
    ref_parts = []
    ref_seen = set()
    for row in all_rows:
        for key in ("Reference", "Docs URL", "Source URL"):
            val = row.get(key, "").strip()
            if val and val not in ref_seen:
                ref_seen.add(val)
                name = _get_name(row)
                ref_parts.append(f"- [{name}]({val})")

    # Escape braces in user-supplied title to prevent str.format() KeyError.
    safe_title = title.replace("{", "{{").replace("}", "}}")

    adr_text = _ADR_TEMPLATE.format(
        title=safe_title,
        context="\n".join(context_parts) or "_No relevant context found._",
        decision=f"Adopt **{top_name}** (from `{top_domain}` domain).\n\n"
                 + (f"**Strengths:** {top_row.get('Strengths', 'N/A')}" if top_row.get('Strengths') else ""),
        alternatives="\n".join(alt_parts) or "_No alternatives found in the KB._",
        consequences="\n".join(consequence_parts) or "_No specific consequences identified._",
        references="\n".join(ref_parts) or "_No references available._",
    )

    # Write to file if requested.
    if out_path:
        out = Path(out_path).resolve()
        cwd = Path.cwd().resolve()
        if not str(out).startswith(str(cwd) + "/") and out != cwd:
            return {"error": f"--out path must be under current directory ({cwd})"}
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(adr_text, encoding="utf-8")

    return {
        "mode": "adr",
        "title": title,
        "context_domains": context_domains,
        "rows_cited": len(all_rows),
        "decision": top_name,
        "decision_domain": top_domain,
        "out_path": str(out_path) if out_path else None,
        "text": adr_text,
    }


# ============ DESIGN COMMAND ============
_SCALE_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*([kmbt]?)\s*(reads?|writes?|dau|mau|users?|req|requests?|inserts?|qps|rps)(?:/\s*(?:day|d|sec|s|second|min|minute|hour|h))?',
    re.IGNORECASE,
)


def _parse_scale(requirement):
    """Extract scale numbers from a requirement string."""
    scales = {}
    for m in _SCALE_RE.finditer(requirement):
        num = float(m.group(1).replace(",", ""))
        mult = _MULTIPLIERS.get(m.group(2).lower(), 1) if m.group(2) else 1
        total = num * mult
        kind = m.group(3).lower()
        if kind.startswith("read"):
            scales["reads_per_day"] = int(total)
        elif kind.startswith("write") or kind.startswith("insert"):
            scales["writes_per_day"] = int(total)
        elif kind in ("dau", "users", "user"):
            scales["dau"] = int(total)
        elif kind in ("mau",):
            scales["mau"] = int(total)
        elif kind in ("qps", "rps", "req", "requests"):
            scales["qps"] = int(total)
    return scales


def _qps_from_daily(daily, peak_factor=3):
    """Convert daily count to QPS (average and peak)."""
    avg = daily / 86400
    return {"avg": round(avg, 1), "peak": round(avg * peak_factor, 1)}


def _storage_estimate(rows, row_bytes=500, replication=3):
    """Estimate storage needs."""
    raw_gb = (rows * row_bytes) / (1024 ** 3)
    return {
        "raw_gb": round(raw_gb, 1),
        "with_replication_gb": round(raw_gb * replication, 1),
        "assumptions": f"{row_bytes}B/row, {replication}x replication",
    }


def design(requirement, max_per_section=2):
    """System-design scaffolding from a one-liner.

    Given a system description with scale numbers, produce a candidate
    architecture with cited KB choices.

    Returns structured design sections.
    """
    scales = _parse_scale(requirement)
    facets = extract_constraints(requirement)

    # Define design sections → domain queries.
    sections_config = [
        ("API Style", "api", requirement),
        ("Data Store", "database", requirement),
        ("Cache Strategy", "cache", requirement + " cache"),
        ("Messaging / Async", "messaging", requirement + " async event"),
        ("Failure Modes & Resilience", "pattern", "circuit breaker retry timeout fallback"),
        ("Observability", "observability", requirement + " monitoring metrics"),
    ]

    sections = []
    all_cited = []

    for section_name, domain, query in sections_config:
        result = search(query, domain=domain, max_results=max_per_section)
        if "error" in result or result.get("count", 0) == 0:
            sections.append({
                "name": section_name,
                "domain": domain,
                "recommendations": [],
                "notes": "No relevant KB rows found.",
            })
            continue

        recs = []
        for row in result["results"]:
            name = _get_name(row)
            strengths = row.get("Strengths", row.get("Use Case", ""))
            weaknesses = row.get("Weaknesses", "")
            recs.append({
                "name": name,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "domain": domain,
                "score": row.get("_score", 0),
            })
            all_cited.append({"name": name, "domain": domain})

        sections.append({
            "name": section_name,
            "domain": domain,
            "recommendations": recs,
        })

    # Capacity math section.
    capacity = {}
    if scales.get("reads_per_day"):
        capacity["read_qps"] = _qps_from_daily(scales["reads_per_day"])
    if scales.get("writes_per_day"):
        capacity["write_qps"] = _qps_from_daily(scales["writes_per_day"])
    if scales.get("dau"):
        # Estimate: ~10 requests per DAU per day.
        capacity["estimated_qps"] = _qps_from_daily(scales["dau"] * 10)
    if scales.get("writes_per_day"):
        capacity["storage_1yr"] = _storage_estimate(scales["writes_per_day"] * 365)

    return {
        "mode": "design",
        "requirement": requirement,
        "scales": scales,
        "facets": facets,
        "sections": sections,
        "capacity": capacity,
        "cited_count": len(all_cited),
    }


# ============ FORMATTERS ============
def format_decide(result):
    """Format decide output as markdown."""
    if "error" in result:
        return f"Error: {result['error']}"

    out = ["## Backend Pro Max — Decision",
           f"**Requirement:** {result['requirement']}",
           f"**Domains searched:** {', '.join(result['domains_searched'])}",
           f"**Candidates found:** {result['candidates_count']}\n"]

    # Facets.
    if result["facets"]:
        out.append("### Extracted Constraints")
        for k, v in result["facets"].items():
            if not k.startswith("_"):
                out.append(f"- **{k}:** {v}")
        out.append("")

    # Recommendation.
    rec = result.get("recommendation")
    if rec:
        name = _get_name(rec)
        domain = rec.get("_source_domain", "?")
        out.append(f"### 🏆 Recommendation: **{name}** (`{domain}`)")
        # Show constraint matches.
        cm = rec.get("_constraints", {})
        if cm:
            for k, info in cm.items():
                icon = "✅" if info["match"] is True else ("❌" if info["match"] is False else "❓")
                out.append(f"- {icon} **{k}:** wanted `{info['wanted']}`, got `{info['value'] or 'unknown'}`")
        out.append("")

    # Candidates table.
    if result["candidates"]:
        out.append("### Candidates (ranked)")
        out.append("| # | Name | Domain | Score | Constraints |")
        out.append("| --- | --- | --- | --- | --- |")
        for i, c in enumerate(result["candidates"], 1):
            name = _get_name(c)
            domain = c.get("_source_domain", "?")
            score = c.get("_score", 0)
            cm = c.get("_constraints", {})
            satisfied = sum(1 for v in cm.values() if v["match"] is True)
            total = len(cm)
            constraint_str = f"{satisfied}/{total}" if total else "—"
            out.append(f"| {i} | {name} | {domain} | {score:.2f} | {constraint_str} |")
        out.append("")

    # Trade-offs.
    if result["candidates"]:
        out.append("### Trade-offs")
        for c in result["candidates"][:3]:
            name = _get_name(c)
            strengths = c.get("Strengths", "")
            weaknesses = c.get("Weaknesses", "")
            if strengths or weaknesses:
                out.append(f"**{name}:**")
                if strengths:
                    out.append(f"- ✅ {strengths[:300]}")
                if weaknesses:
                    out.append(f"- ⚠️ {weaknesses[:300]}")
                out.append("")

    caveat = f"> _Based on {result['candidates_count']} candidates across {len(result['domains_searched'])} domain(s). Consider expanding the KB for more options._"
    out.append(caveat)

    return "\n".join(out)


def format_adr(result):
    """Format ADR output."""
    if "error" in result:
        return f"Error: {result['error']}"
    return result["text"]


def format_design(result):
    """Format design output as markdown."""
    if "error" in result:
        return f"Error: {result['error']}"

    out = ["## Backend Pro Max — System Design Scaffold",
           f"**Requirement:** {result['requirement']}\n"]

    # Scales.
    if result["scales"]:
        out.append("### Scale Numbers")
        for k, v in result["scales"].items():
            out.append(f"- **{k}:** {v:,}")
        out.append("")

    # Capacity math.
    if result["capacity"]:
        out.append("### Capacity Estimates")
        for k, v in result["capacity"].items():
            if isinstance(v, dict):
                parts = ", ".join(f"{kk}: {vv}" for kk, vv in v.items())
                out.append(f"- **{k}:** {parts}")
            else:
                out.append(f"- **{k}:** {v}")
        out.append("")

    # Architecture sections.
    for section in result["sections"]:
        out.append(f"### {section['name']}")
        recs = section.get("recommendations", [])
        if not recs:
            out.append(f"_{section.get('notes', 'No recommendations.')}_\n")
            continue
        for rec in recs:
            out.append(f"- **{rec['name']}** (`{rec['domain']}`)")
            if rec.get("strengths"):
                s = rec["strengths"]
                if len(s) > 200:
                    s = s[:200] + "…"
                out.append(f"  - Strengths: {s}")
            if rec.get("weaknesses"):
                w = rec["weaknesses"]
                if len(w) > 200:
                    w = w[:200] + "…"
                out.append(f"  - Weaknesses: {w}")
        out.append("")

    out.append(f"> _Cited {result['cited_count']} KB rows. This is a starting scaffold — validate each choice against your specific constraints._")

    return "\n".join(out)
