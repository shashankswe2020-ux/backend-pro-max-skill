"""Describe retrieval payloads without confusing ranking or calls with relevance."""
from __future__ import annotations

import hashlib
import json

_EVIDENCE_FORMATS = {"compact-v1", "evidence-v1", "repository-context-v1", "verified-memory-v1", "memory-sequence-context-v1"}

def describe_payload(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Retrieval payload must be a JSON object")
    status = "unclassified"
    rows = None
    if "error" in value:
        status = "error"
    else:
        for key in ("results", "snippets", "documents"):
            if isinstance(value.get(key), list):
                rows = value[key]
                break
        if rows is None:
            for key in ("content", "documentation"):
                if isinstance(value.get(key), str):
                    rows = [value[key]] if value[key].strip() else []
                    break
        if rows is not None:
            status = "returned" if rows else "empty"
            if not rows and value.get("format") in _EVIDENCE_FORMATS and value.get("status") == "budget_exhausted":
                status = "budget_exhausted"
    identifiers = []
    citations = []
    for row in rows or []:
        identifier = row.get("id") if isinstance(row, dict) and value.get("format") in _EVIDENCE_FORMATS else None
        identifiers.append(identifier if isinstance(identifier, str) else hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest())
        if isinstance(row, dict):
            for key in ("_citation", "url", "source_url"):
                if isinstance(row.get(key), str) and row[key]:
                    citations.append(row[key])
            if value.get("format") in _EVIDENCE_FORMATS:
                if isinstance(row.get("citation"), str) and row["citation"]:
                    citations.append(row["citation"])
                for source in row.get("sources", {}).values():
                    if isinstance(source, str) and source:
                        citations.append(source)
                if row.get("kind") in ("local", "verified_memory") and isinstance(row.get("id"), str):
                    citations.append(row["id"])
    return {
        "status": status, "result_count": len(rows) if rows is not None else None,
        "evidence_ids": identifiers, "citations": sorted(set(citations)),
    }


def contains_evidence(value: dict, term: str) -> bool:
    """Inspect returned content, never an echoed query or response metadata."""
    for key in ("results", "snippets", "documents", "content", "documentation"):
        content = value.get(key)
        if isinstance(content, (list, str)) and term.casefold() in json.dumps(content).casefold():
            return True
    return False
