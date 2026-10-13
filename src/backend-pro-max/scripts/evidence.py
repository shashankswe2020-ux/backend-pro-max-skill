"""Opt-in, source-bound evidence and whole-unit budget selection. No network access."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

try:
    from .versions import interval, normalize_name, resolve_versions, version_match
except ImportError:
    from versions import interval, normalize_name, resolve_versions, version_match

DATA_DIR = Path(__file__).parent.parent / "data"
METADATA = ("Library", "Applies To", "Platform Assumptions", "Source Revision", "Source SHA256", "Last Verified")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def validate_metadata(row: dict) -> None:
    if not any(row.get(key) for key in METADATA):
        return
    if any(not isinstance(row.get(key), str) or not row[key].strip() for key in METADATA):
        raise ValueError("Versioned evidence requires library, range, platform, revision, source hash and verification date")
    normalize_name(row["Library"])
    bounds = interval(row["Applies To"])
    if bounds[1][0] is not None and (
        bounds[0][0] > bounds[1][0] or (bounds[0][0] == bounds[1][0] and not all((bounds[0][1], bounds[1][1])))
    ):
        raise ValueError("Empty applicability range")
    date.fromisoformat(row["Last Verified"])
    if not re.fullmatch(r"[0-9a-f]{64}", row["Source SHA256"]):
        raise ValueError("Invalid source SHA256")
    revision = row["Source Revision"]
    url = urlsplit(row.get("Source URL", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or url.scheme != "https" or not url.hostname:
        raise ValueError("Versioned evidence requires an HTTPS source and immutable git revision")
    if revision not in url.path.split("/") or url.username or url.password or url.query:
        raise ValueError("Source URL must bind the immutable revision without credentials or query parameters")


def supplemental_rows(scope_file: str) -> list[dict]:
    return [record["fields"] for record in validate_corpus() if record["scope_file"] == scope_file]


def validate_corpus() -> list[dict]:
    try:
        from . import core
    except ImportError:
        import core
    document = json.loads((DATA_DIR / "evidence.json").read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict) or document.get("format") != "source-evidence-v1"
        or not isinstance(document.get("records"), list)
    ):
        raise ValueError("Invalid evidence corpus")
    scopes = {config["file"] for config in (*core.CSV_CONFIG.values(), *core.STACK_CONFIG.values())}
    seen = set()
    for record in document["records"]:
        if (
            not isinstance(record, dict) or not isinstance(record.get("scope_file"), str)
            or record["scope_file"] not in scopes
        ):
            raise ValueError("Evidence record must reference a registered scope")
        fields = record.get("fields")
        if not isinstance(fields, dict) or not fields or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in fields.items()
        ):
            raise ValueError("Evidence fields must be non-empty string mappings")
        validate_metadata(fields)
        if not fields.get("Library") or not (fields.get("Guideline") or fields.get("Name")):
            raise ValueError("Supplemental evidence requires a title and version metadata")
        identity = bind_row(fields, record["scope_file"], supplemental=True)["id"]
        if identity in seen:
            raise ValueError("Duplicate supplemental evidence identity")
        seen.add(identity)
    return document["records"]


def bind_row(row: dict, scope_file: str, *, supplemental: bool = False) -> dict:
    validate_metadata(row)
    fields = {key: value for key, value in row.items() if not key.startswith("_")}
    identity = {"scope_file": scope_file, "fields": fields, "origin": "evidence.json" if supplemental else scope_file}
    return {"id": "bpme:" + _hash(identity), "binding": {
        "file": identity["origin"], "scope_file": scope_file, "row_sha256": _hash(fields),
    }, "fields": fields}


def evidence_detail(evidence_id: str) -> dict:
    """Expand an exact content identity; modified or removed evidence fails closed."""
    if not isinstance(evidence_id, str) or not re.fullmatch(r"bpme:[0-9a-f]{64}", evidence_id):
        raise ValueError("Invalid evidence_id")
    try:
        from . import core
    except ImportError:
        import core
    for config in (*core.CSV_CONFIG.values(), *core.STACK_CONFIG.values()):
        scope_file = config["file"]
        for supplemental, rows in (
            (False, core._load_csv(core.DATA_DIR / scope_file)),
            (True, supplemental_rows(scope_file)),
        ):
            for row in rows:
                bound = bind_row(row, scope_file, supplemental=supplemental)
                if bound["id"] == evidence_id:
                    return bound
    raise ValueError("Evidence not found at this corpus revision; repeat the search")


def _unit(domain, row, context):
    try:
        from .templates import _COMPACT_FIELDS
    except ImportError:
        from templates import _COMPACT_FIELDS
    bound = row.get("_evidence")
    if not bound:
        raise ValueError("Evidence formatting requires core search with evidence=True")
    fields = bound["fields"]
    groups = {group: {key: fields[key] for key in keys if fields.get(key)} for group, keys in _COMPACT_FIELDS.items()}
    library = normalize_name(fields["Library"]) if fields.get("Library") else None
    observed = context["libraries"].get(library, {"status": "unknown", "observations": []})
    status = version_match(fields["Applies To"], observed) if library else "unknown"
    title = next((fields[key] for key in (
        "Name", "Guideline", "Service", "Topic", "Pattern", "Style", "Operation", "Tool", "Technique",
    ) if fields.get(key)), None)
    sources = {key: fields[key] for key in ("Source URL", "Docs URL") if fields.get(key)}
    facts = {key: value for group in groups.values() for key, value in group.items()}
    used = set(facts) | set(sources) | set(METADATA)
    missing = [key for key, group in groups.items() if not group]
    if not sources:
        missing.append("sources")
    missing += [key for key in METADATA if not fields.get(key)]
    return {
        "id": bound["id"], "domain": domain, "title": title, "binding": bound["binding"],
        "citation": row.get("_citation"), "sources": sources,
        "applicability": {key: fields[key] for key in METADATA if fields.get(key)},
        "version_match": status, "platform_check": "not_evaluated",
        "facts": facts, "missing": missing,
        "omitted_fields": [key for key, value in fields.items() if value and key not in used],
    }


def format_evidence(result: dict, max_chars: int = 6000, *, project_path: str | None = None,
                    library_versions: dict | None = None, token_counter=None, max_tokens=None) -> dict:
    """Select complementary units by version, query coverage, scope diversity and ordinal rank."""
    try:
        from .core import classify_intent
    except ImportError:
        from core import classify_intent
    if type(max_chars) is not int or max_chars <= 0:
        raise ValueError("max_chars must be a positive integer")
    if (token_counter is None) != (max_tokens is None) or (
        max_tokens is not None and (type(max_tokens) is not int or max_tokens <= 0)
    ):
        raise ValueError("Token budgets require a pinned tokenizer and positive max_tokens")
    if "error" in result:
        raise ValueError(str(result["error"]))
    context = resolve_versions(project_path, library_versions)
    raw = result.get("results")
    if isinstance(raw, dict):
        rows = [(domain, rank, row) for domain, group in raw.items() for rank, row in enumerate(group)]
    elif isinstance(raw, list):
        rows = [(result.get("stack") or result.get("domain"), rank, row) for rank, row in enumerate(raw)]
    else:
        raise ValueError("Evidence formatting requires search results")
    units = [(rank, _unit(domain, row, context)) for domain, rank, row in rows]
    libraries = {unit["applicability"].get("Library") for _, unit in units} - {None}
    context["libraries"] = {
        normalize_name(name): context["libraries"].get(normalize_name(name), {"status": "unknown", "observations": []})
        for name in sorted(libraries)
    }
    omissions = {"budget": 0, "duplicate": 0, "version_mismatch": 0, "version_conflict": 0}
    output = {
        "format": "evidence-v1", "query": result.get("query", ""), "matched_count": len(units),
        "intent": result.get("intent") or classify_intent(result.get("query", "")).value,
        "count": 0, "omitted_count": len(units), "status": "no_matches",
        "versions": context, "omissions": omissions, "results": [],
        "selection": "version match, marginal query coverage, scope diversity, within-scope rank",
        "evidence_note": "Source-bound KB guidance, not verified advice. Version matches do not verify platform or API namespace. Unknowns require review.",
    }
    if "retrieval" in result:
        output["retrieval"] = result["retrieval"]
    pending = []
    seen = set()
    for rank, unit in units:
        match = unit["version_match"]
        if match in ("mismatch", "conflict"):
            omissions["version_" + match] += 1
            continue
        fingerprint = _hash({"facts": unit["facts"], "applicability": unit["applicability"]})
        # Empty units with distinct titles are not semantic duplicates.
        if not unit["facts"]:
            fingerprint = unit["id"]
        if fingerprint in seen:
            omissions["duplicate"] += 1
            continue
        seen.add(fingerprint)
        pending.append((rank, unit))
    omissions["budget"] = len(pending)
    covered = set()
    scope_counts = Counter()
    terms = set(re.findall(r"\w+", result.get("query", "").lower()))

    def words(unit):
        return set(re.findall(r"\w+", (str(unit["title"]) + " " + _json(unit["facts"])).lower())) & terms

    def update():
        output["count"] = len(output["results"])
        output["omitted_count"] = sum(omissions.values())
        output["status"] = "results" if output["count"] else ("no_eligible_evidence" if units else "no_matches")
        if not output["count"] and omissions["budget"]:
            output["status"] = "budget_exhausted"

    def fits():
        text = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
        return len(text) <= max_chars and (token_counter is None or token_counter(text) <= max_tokens)

    update()
    if not fits():
        raise ValueError("Evidence metadata exceeds the budget; increase the limit or narrow the query/scope")
    while pending:
        pending.sort(key=lambda pair: (
            pair[1]["version_match"] != "match", -len(words(pair[1]) - covered),
            scope_counts[pair[1]["domain"]], pair[0], str(pair[1]["domain"]), pair[1]["id"],
        ))
        _, unit = pending.pop(0)
        output["results"].append(unit)
        omissions["budget"] -= 1
        update()
        if fits():
            covered.update(words(unit))
            scope_counts[unit["domain"]] += 1
        else:
            output["results"].pop()
            omissions["budget"] += 1
            update()
    return output
