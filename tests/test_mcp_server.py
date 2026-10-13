"""Tests for Tier 3.1 — MCP Server.

Validate direct tool functions and real stdio discovery, calls, and errors.
"""
from __future__ import annotations

import json
import sys

import pytest

# Skip the entire module if the `mcp` package is not installed.
mcp_available = True
try:
    import mcp  # noqa: F401
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")

def test_stdio_transport(tmp_path):
    import anyio
    from backendpro.scripts.check_tools import check_session
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def exercise_server():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(_scripts / "mcp_server.py")],
            cwd=str(tmp_path),
        )
        with anyio.fail_after(30):
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    result = await check_session(session)
                    assert result["status"] == "passed"
                    assert result["tools"] == 11
                    cases = {
                        "search": {"query": "Kafka", "domain": "messaging"},
                        "search_all": {"query": "idempotency"},
                        "search_stack": {"query": "error handling", "stack": "go"},
                        "compare": {"names": ["Kafka", "RabbitMQ"], "domain": "messaging"},
                        "decide": {"requirement": "message broker for 100k msg/s on AWS"},
                        "adr": {"title": "Adopt circuit breaker", "context_domains": ["pattern"]},
                        "design": {"description": "URL shortener serving 10M reads/day"},
                        "find_stale": {"domain": "pattern", "months": 0},
                    }
                    assert {tool.name for tool in (await session.list_tools()).tools} == set(cases) | {"evidence_detail", "repository_context", "memory_context"}
                    versioned = await session.call_tool("search_stack", {
                        "query": "pydantic dictionary", "stack": "python-fastapi",
                        "response_format": "evidence", "library_versions": {"pydantic": "2.10.6"},
                        "max_chars": 5000,
                    })
                    assert not versioned.isError
                    value = json.loads(versioned.content[0].text)
                    assert len(versioned.content[0].text) <= 5000
                    assert value["results"][0]["version_match"] == "match"
                    detail = await session.call_tool("evidence_detail", {"evidence_id": value["results"][0]["id"]})
                    assert not detail.isError
                    assert json.loads(detail.content[0].text)["id"] == value["results"][0]["id"]
                    stale = await session.call_tool("evidence_detail", {"evidence_id": "bpme:" + "0" * 64})
                    assert stale.isError
                    for name, arguments in cases.items():
                        response = await session.call_tool(name, arguments)
                        assert not response.isError, name
                        assert isinstance(json.loads(response.content[0].text), dict)
                        obsolete = await session.call_tool(f"backendpro_{name}", arguments)
                        assert obsolete.isError, name
                    for name, arguments in [
                        ("search", {"query": "Kafka", "domain": "messaging"}),
                        ("search_all", {"query": "idempotency"}),
                        ("search_stack", {"query": "error handling", "stack": "go"}),
                    ]:
                        compact = await session.call_tool(name, {**arguments, "response_format": "compact"})
                        assert not compact.isError
                        assert len(compact.content[0].text) <= 6000
                        value = json.loads(compact.content[0].text)
                        assert value["format"] == "compact-v1"
                        assert value["count"] > 0
                        evidence_response = await session.call_tool(name, {
                            **arguments, "response_format": "evidence", "max_chars": 5000,
                        })
                        assert not evidence_response.isError
                        assert len(evidence_response.content[0].text) <= 5000
                        actual_evidence = json.loads(evidence_response.content[0].text)
                        assert actual_evidence == globals()[name](
                            **arguments, response_format="evidence", max_chars=5000,
                        )
                    invalid = await session.call_tool(
                        "search", {"query": "Kafka", "response_format": "unsupported"},
                    )
                    assert invalid.isError
                    for name, scope in [
                        ("search", {"domain": "pattern"}),
                        ("search_stack", {"stack": "go"}),
                        ("search_all", {}),
                    ]:
                        arguments = {
                            "query": "retry", **scope, "max_results": 2, "candidate_pool": 20,
                            "diagnostics": True, "expand": False, "min_score": 0,
                            "max_age_months": 240, "constraints": "cloud=aws",
                        }
                        response = await session.call_tool(name, arguments)
                        assert not response.isError
                        actual = json.loads(response.content[0].text)
                        import core
                        assert actual == getattr(core, name)(**arguments)
                        compact = await session.call_tool(name, {**arguments, "response_format": "compact"})
                        assert not compact.isError
                        assert len(compact.content[0].text) <= 6000
                        assert json.loads(compact.content[0].text)["retrieval"] == actual["retrieval"]
                    for options in [
                        {"engine": "bogus"}, {"candidate_pool": 1, "max_results": 5},
                        {"max_age_months": -1}, {"rerank": "yes"}, {"constraints": "bogus"},
                        {"response_format": "evidence", "max_chars": 0},
                        {"response_format": "evidence", "library_versions": {"pydantic": "latest"}},
                        {"response_format": "raw", "project_path": str(tmp_path)},
                    ]:
                        response = await session.call_tool("search", {"query": "saga", **options})
                        assert response.isError

    anyio.run(exercise_server)


def test_real_model_pipeline_over_mcp():
    pytest.importorskip("sentence_transformers")
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def exercise():
        parameters = StdioServerParameters(command=sys.executable, args=[str(_scripts / "mcp_server.py")])
        with anyio.fail_after(180):
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    response = await session.call_tool("search", {
                        "query": "saga", "domain": "pattern", "engine": "hybrid",
                        "rerank": True, "candidate_pool": 20, "max_results": 5,
                        "response_format": "compact",
                    })
                    assert not response.isError
                    result = json.loads(response.content[0].text)
                    assert result["retrieval"]["effective_engine"] == "hybrid"
                    assert result["retrieval"]["rerank_applied"]
                    assert not result["retrieval"]["fallbacks"]
                    assert result["retrieval"]["candidate_count"] > 5
                    assert result["count"] > 0
                    assert len(response.content[0].text) <= 6000
                    arguments = {
                        "query": "pydantic dictionary export migration", "stack": "python-fastapi",
                        "engine": "hybrid", "rerank": True, "candidate_pool": 20,
                    }
                    baseline = await session.call_tool("search_stack", arguments)
                    assert not baseline.isError
                    versioned = await session.call_tool("search_stack", {
                        **arguments, "response_format": "evidence",
                        "library_versions": {"pydantic": "2.10.6"},
                    })
                    assert not versioned.isError
                    result = json.loads(versioned.content[0].text)
                    assert result["retrieval"]["effective_engine"] == "hybrid"
                    assert result["retrieval"]["rerank_applied"]
                    assert result["results"][0]["version_match"] == "match"
                    assert len(versioned.content[0].text) <= 6000
    anyio.run(exercise)

# ── We test the underlying tool functions directly ──────────────

# Since mcp_server.py calls _check_mcp() at import time, we need to import
# conditionally to avoid an exit when mcp is not installed.
if mcp_available:
    # Patch sys.path so we can import from the scripts directory
    from pathlib import Path
    _scripts = Path(__file__).resolve().parent.parent / "src" / "backend-pro-max" / "scripts"
    if str(_scripts) not in sys.path:
        sys.path.insert(0, str(_scripts))

    from mcp_server import (
        adr,
        compare,
        decide,
        design,
        evidence_detail,
        find_stale,
        mcp_server,
        memory_context,
        repository_context,
        search,
        search_all,
        search_stack,
    )


# ── Tool-level tests (2 per tool = 16) ───────────────────────────

class TestBackendproSearch:
    def test_valid_query(self):
        result = search("kafka", domain="messaging")
        assert "results" in result
        assert result["count"] > 0
        assert all("_citation" in r for r in result["results"])

    def test_unknown_domain_returns_error(self):
        result = search("test", domain="nonexistent")
        assert "error" in result


class TestBackendproSearchAll:
    def test_cross_domain(self):
        result = search_all("circuit breaker")
        assert "results" in result
        assert "domains" in result

    def test_empty_query(self):
        result = search_all("")
        assert isinstance(result, dict)


class TestBackendproSearchStack:
    def test_valid_stack(self):
        result = search_stack("error handling", stack="go")
        assert "results" in result
        assert result["count"] > 0

    def test_unknown_stack_returns_error(self):
        result = search_stack("test", stack="nonexistent")
        assert "error" in result


class TestBackendproCompare:
    def test_two_names(self):
        result = compare(["Kafka", "RabbitMQ"], domain="messaging")
        assert result["mode"] == "compare"
        assert "entries" in result

    def test_single_name_returns_error(self):
        result = compare(["Kafka"])
        assert "error" in result


class TestBackendproDecide:
    def test_valid_requirement(self):
        result = decide("message broker for 100k msg/s on AWS")
        assert result["mode"] == "decide"
        assert "candidates" in result

    def test_empty_requirement(self):
        result = decide("")
        assert isinstance(result, dict)


class TestBackendproAdr:
    def test_valid_adr(self):
        result = adr("Adopt circuit breaker", context_domains=["pattern"])
        assert result["mode"] == "adr"
        assert "text" in result

    def test_no_domains_returns_error(self):
        result = adr("Test", context_domains=[])
        assert "error" in result


class TestBackendproDesign:
    def test_valid_design(self):
        result = design("URL shortener serving 10M reads/day")
        assert result["mode"] == "design"
        assert "sections" in result

    def test_simple_requirement(self):
        result = design("chat application")
        assert isinstance(result, dict)
        assert "sections" in result


class TestBackendproFindStale:
    def test_valid_domain(self):
        result = find_stale("pattern", months=6)
        assert "results" in result
        assert "count" in result

    def test_unknown_domain_returns_error(self):
        result = find_stale("nonexistent", months=6)
        assert "error" in result


# ── Server metadata ───────────────────────────────────────────────

class TestServerMetadata:
    def test_server_name(self):
        assert mcp_server.name == "Backend Pro Max"

    def test_tool_count(self):
        """Server should expose the eleven canonical tools."""
        # FastMCP stores tools internally; we verify via our definitions
        tools = mcp_server._tool_manager._tools
        assert len(tools) == 11, f"Expected 11 tools, got {len(tools)}: {list(tools.keys())}"


def test_unexpected_failure_is_not_a_success_dictionary(monkeypatch):
    import mcp_server as module

    def fail(*args, **kwargs):
        raise OSError("test storage unavailable")

    monkeypatch.setattr(module.core, "search", fail)
    with pytest.raises(OSError, match="storage unavailable"):
        search("Kafka")


def test_unknown_evidence_id_fails_directly():
    with pytest.raises(ValueError, match="not found"):
        evidence_detail("bpme:" + "0" * 64)


def test_local_context_is_disabled_without_operator_authorization(monkeypatch):
    monkeypatch.delenv("BACKENDPRO_WORKSPACE", raising=False)
    with pytest.raises(ValueError, match="disabled"):
        repository_context("retry", ["ops.py"])


def test_memory_is_disabled_without_operator_authorization(monkeypatch):
    monkeypatch.delenv("BACKENDPRO_MEMORY_STORE", raising=False)
    with pytest.raises(ValueError, match="disabled"):
        memory_context("retry", "pilot", "retry", "second", 1, ["first"], {"python": "3.12.13"})


def test_tool_contracts_match_function_signatures():
    import inspect

    from backendpro.scripts.gen_tools_schema import TOOLS

    for tool in TOOLS:
        signature = inspect.signature(globals()[tool["name"]])
        schema = tool["parameters"]
        assert set(signature.parameters) == set(schema["properties"])
        required = []
        for name, parameter in signature.parameters.items():
            if parameter.default is inspect.Parameter.empty:
                required.append(name)
            else:
                assert schema["properties"][name]["default"] == parameter.default
        assert required == schema["required"]
