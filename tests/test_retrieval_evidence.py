"""Payload structure is observable; relevance must never be inferred from scores."""
import pytest
from backendpro.scripts.retrieval_evidence import describe_payload


@pytest.mark.parametrize("value,status,count", [
    ({"results": []}, "empty", 0),
    ({"results": [{"_score": 1000, "_citation": "[BPM:test]"}]}, "returned", 1),
    ({"error": "unavailable"}, "error", None),
    ({"unexpected": "success"}, "unclassified", None),
    ({"documentation": ""}, "empty", 0),
    ({"content": "Django model reference"}, "returned", 1),
])
def test_payload_status(value, status, count):
    result = describe_payload(value)
    assert result["status"] == status
    assert result["result_count"] == count
    assert "relevance" not in result
    assert "application" not in result


def test_evidence_identifiers_and_citations_are_stable():
    first = describe_payload({"results": [{"text": "example", "_citation": "[BPM:test]"}]})
    second = describe_payload({"results": [{"_citation": "[BPM:test]", "text": "example"}]})
    assert first == second
    assert len(first["evidence_ids"][0]) == 64
    assert first["citations"] == ["[BPM:test]"]


@pytest.mark.parametrize("value", [None, [], "not an object"])
def test_invalid_payload_is_explicitly_rejected(value):
    with pytest.raises(ValueError, match="JSON object"):
        describe_payload(value)


def test_compact_citations_and_budget_exhaustion_are_not_lost():
    result = describe_payload({
        "format": "compact-v1", "results": [
            {"citation": "[BPM:test]", "sources": {"Source URL": "https://example.test"}},
        ],
    })
    assert result["citations"] == ["[BPM:test]", "https://example.test"]
    exhausted = describe_payload({"format": "compact-v1", "status": "budget_exhausted", "results": []})
    assert exhausted["status"] == "budget_exhausted"
