"""Regress scoped coverage gaps found in the M2 local retrieval run.

These are author-written regression queries, not independently held-out tasks.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from backendpro.scripts import core
from backendpro.scripts.templates import compact_json, format_compact
from backendpro.scripts.validate import _validate_file

CASES = [
    {
        "query": "graceful shutdown", "domain": "container", "stack": None,
        "column": "Name", "name": "Kubernetes Pod termination",
        "source": "https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination-flow",
        "terms": ["preStop", "terminationGracePeriodSeconds", "SIGTERM", "SIGKILL", "concurrently"],
        "variants": ["pod termination preStop", "SIGTERM grace period"],
    },
    {
        "query": "transaction", "domain": None, "stack": "java-spring",
        "column": "Guideline", "name": "Define transaction boundaries through the Spring proxy",
        "source": "https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html",
        "terms": ["proxy mode", "self-invocation", "checked exceptions", "rollbackFor"],
        "variants": ["self-invocation @Transactional", "checked exceptions rollback"],
    },
    {
        "query": "proxy", "domain": None, "stack": "nodejs-express",
        "column": "Guideline", "name": "Match trust proxy to the reverse-proxy topology",
        "source": "https://expressjs.com/en/guide/behind-proxies/",
        "terms": ["X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "hop count", "overwrite"],
        "variants": ["X-Forwarded-For client IP", "trust proxy hop count"],
    },
]


def retrieve(case, query=None, expand=True):
    query = case["query"] if query is None else query
    if case["stack"]:
        return core.search_stack(query, case["stack"], max_results=3, expand=expand)
    return core.search(query, domain=case["domain"], max_results=3, expand=expand)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["stack"] or case["domain"])
def test_diagnosed_gap_returns_relevant_top_result(case):
    core.clear_cache()
    result = retrieve(case)
    assert result["count"] > 0
    row = result["results"][0]
    assert row[case["column"]] == case["name"]
    assert row["Source URL"] == case["source"]
    assert row["_citation"].startswith("[BPM:")
    assert core._parse_date(row["Last Updated"]) is not None
    text = json.dumps(row)
    assert all(term in text for term in case["terms"])


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["stack"] or case["domain"])
def test_paraphrases_and_literal_search_do_not_need_synonym_hacks(case):
    for query in [case["query"], *case["variants"]]:
        result = retrieve(case, query, expand=False)
        assert any(row[case["column"]] == case["name"] for row in result["results"])


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["stack"] or case["domain"])
def test_compact_keeps_the_source_constraints(case):
    raw = retrieve(case)
    compact = format_compact(raw)
    assert compact["count"] > 0
    row = next(row for row in raw["results"] if row[case["column"]] == case["name"])
    unit = next(unit for unit in compact["results"] if unit["title"] == case["name"])
    assert unit["citation"] == row["_citation"]
    assert unit["sources"]["Source URL"] == case["source"]
    assert all(term in json.dumps(unit["facts"]) for term in case["terms"])
    assert len(compact_json(compact)) <= 6000


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["stack"] or case["domain"])
def test_scoped_no_match_remains_empty(case):
    result = retrieve(case, "zz_m4_absent_token_zz", expand=False)
    assert result["results"] == []
    assert result["count"] == 0
    if case["stack"]:
        assert result["stack"] == case["stack"]
    else:
        assert result["domain"] == case["domain"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["stack"] or case["domain"])
def test_affected_csv_schema_is_strictly_valid(case):
    config = core.STACK_CONFIG[case["stack"]] if case["stack"] else core.CSV_CONFIG[case["domain"]]
    columns = core._STACK_COLS if case["stack"] else config
    errors, warnings = _validate_file(
        case["stack"] or case["domain"], core.DATA_DIR / config["file"],
        columns["search_cols"], columns["output_cols"], strict=True,
    )
    assert errors == []
    assert warnings == []


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["stack"] or case["domain"])
def test_cli_returns_the_scoped_guidance(case):
    script = Path(__file__).resolve().parents[1] / "src/backend-pro-max/scripts/search.py"
    scope = ["--stack", case["stack"]] if case["stack"] else ["--domain", case["domain"]]
    completed = subprocess.run(
        [sys.executable, str(script), case["query"], *scope, "--compact"],
        capture_output=True, text=True, check=True,
    )
    value = json.loads(completed.stdout)
    assert value["results"][0]["title"] == case["name"]
    assert len(completed.stdout.rstrip("\n")) <= 6000


def test_existing_application_shutdown_guidance_remains_available():
    result = core.search("graceful shutdown", domain="reliability", max_results=3)
    assert result["count"] > 0
    assert any("Drain LB" in json.dumps(row) for row in result["results"])


def test_mcp_returns_all_three_source_linked_results():
    pytest.importorskip("mcp")
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def exercise():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "backendpro.scripts.mcp_server"],
        )
        with anyio.fail_after(30):
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    for case in CASES:
                        name = "backendpro_search_stack" if case["stack"] else "backendpro_search"
                        arguments = {"query": case["query"], "response_format": "compact"}
                        arguments["stack" if case["stack"] else "domain"] = case["stack"] or case["domain"]
                        result = await session.call_tool(name, arguments)
                        assert not result.isError
                        value = json.loads(result.content[0].text)
                        assert value["results"][0]["title"] == case["name"]
                        assert value["results"][0]["sources"]["Source URL"] == case["source"]

    anyio.run(exercise)
