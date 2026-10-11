"""Describe retrieval payloads without confusing ranking or calls with relevance."""
from __future__ import annotations

import hashlib
import json


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
            if not rows and value.get("format") == "compact-v1" and value.get("status") == "budget_exhausted":
                status = "budget_exhausted"
    identifiers = []
    citations = []
    for row in rows or []:
        identifiers.append(hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest())
        if isinstance(row, dict):
            for key in ("_citation", "url", "source_url"):
                if isinstance(row.get(key), str) and row[key]:
                    citations.append(row[key])
            if value.get("format") == "compact-v1":
                if isinstance(row.get("citation"), str) and row["citation"]:
                    citations.append(row["citation"])
                for source in row.get("sources", {}).values():
                    if isinstance(source, str) and source:
                        citations.append(source)
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
