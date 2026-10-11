"""Keep published comparison claims bound to the unmodified run exports."""
from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmarks/m3/results/2026-10-11"


def test_publication_is_bound_to_original_protocol_and_report():
    report_bytes = (RESULTS / "comparison.json").read_bytes()
    report = json.loads(report_bytes)
    diagnostics = json.loads((RESULTS / "retrieval-summary.json").read_bytes())
    assert hashlib.sha256(report_bytes).hexdigest() == diagnostics["source_comparison_sha256"]
    assert hashlib.sha256((RESULTS / "protocol.json").read_bytes()).hexdigest() == report["protocol_sha256"]
    assert report["protocol_sha256"] == diagnostics["protocol_sha256"]
    assert report["observations_sha256"] == diagnostics["source_observations_sha256"]
    assert report["assigned"] == len(report["attempts"]) == 96
    assert report["delivered_retrieval_calls"] == diagnostics["delivered_retrieval_calls"] == 120
    assert sum(row["passed"] for row in report["attempts"]) == 96
    assert not report["superiority_claim_supported"]
    assert not report["retrieval_quality_evaluable"]


def test_provider_totals_match_reported_arm_totals():
    report = json.loads((RESULTS / "comparison.json").read_bytes())
    diagnostics = json.loads((RESULTS / "retrieval-summary.json").read_bytes())
    arms = report["overall"]
    assert sum(row["retrieval_calls"] for row in arms.values()) == sum(
        provider["calls"] for provider in diagnostics["providers"].values()
    )
    assert sum(row["empty_retrievals"] for row in arms.values()) == sum(
        provider["empty"] for provider in diagnostics["providers"].values()
    )
    for provider in diagnostics["providers"].values():
        assert provider["calls"] == provider["nonempty"] + provider["empty"] + provider["errors"]
        assert provider["truncated"] <= provider["calls"]
    assert sum(diagnostics["backendpro_empty_by_track"].values()) == 21
    assert all(row["assigned"] == row["resolved"] == 24 for row in arms.values())
    assert report["spending"]["accounted_upper_bound_micro_usd"] == 2_911_524


def test_graph_has_accessible_labels_equal_bars_and_measured_counts():
    svg = ET.parse(ROOT / "docs/readme/context7-vs-backendpro.svg").getroot()
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert svg.attrib["role"] == "img"
    assert svg.find("s:title", ns).text
    assert "does not establish a winner" in svg.find("s:desc", ns).text
    bars = [node for node in svg.iter("{http://www.w3.org/2000/svg}rect") if node.attrib.get("x") == "245"]
    assert len(bars) == 4
    assert {node.attrib["width"] for node in bars} == {"734"}
    labels = [node.text for node in svg.iter("{http://www.w3.org/2000/svg}text")]
    assert labels.count("24 / 24") == 4
    assert "This run: 48/48 nonempty; 22 truncated*" in labels
    assert "This run: 51/72 nonempty; 21 empty*" in labels
    assert "* Provider totals include the both arm. Nonempty is not relevant. 6000-character delivery bound." in labels
