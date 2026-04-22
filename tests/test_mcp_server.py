"""Tests for Tier 3.1 — MCP Server.

These tests validate the MCP tool functions directly (without the MCP transport
layer) to ensure each tool returns well-structured responses.

The full MCP protocol integration (stdio handshake, tools/list) is tested via
MCP Inspector as documented in the plan.
"""
from __future__ import annotations

import pytest
import sys

# Skip the entire module if the `mcp` package is not installed.
mcp_available = True
try:
    import mcp  # noqa: F401
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")

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
        backendpro_search,
        backendpro_search_all,
        backendpro_search_stack,
        backendpro_compare,
        backendpro_decide,
        backendpro_adr,
        backendpro_design,
        backendpro_find_stale,
        mcp_server,
    )


# ── Tool-level tests (2 per tool = 16) ───────────────────────────

class TestBackendproSearch:
    def test_valid_query(self):
        result = backendpro_search("kafka", domain="messaging")
        assert "results" in result
        assert result["count"] > 0
        assert all("_citation" in r for r in result["results"])

    def test_unknown_domain_returns_error(self):
        result = backendpro_search("test", domain="nonexistent")
        assert "error" in result


class TestBackendproSearchAll:
    def test_cross_domain(self):
        result = backendpro_search_all("circuit breaker")
        assert "results" in result
        assert "domains" in result

    def test_empty_query(self):
        result = backendpro_search_all("")
        assert isinstance(result, dict)


class TestBackendproSearchStack:
    def test_valid_stack(self):
        result = backendpro_search_stack("error handling", stack="go")
        assert "results" in result
        assert result["count"] > 0

    def test_unknown_stack_returns_error(self):
        result = backendpro_search_stack("test", stack="nonexistent")
        assert "error" in result


class TestBackendproCompare:
    def test_two_names(self):
        result = backendpro_compare(["Kafka", "RabbitMQ"], domain="messaging")
        assert result["mode"] == "compare"
        assert "entries" in result

    def test_single_name_returns_error(self):
        result = backendpro_compare(["Kafka"])
        assert "error" in result


class TestBackendproDecide:
    def test_valid_requirement(self):
        result = backendpro_decide("message broker for 100k msg/s on AWS")
        assert result["mode"] == "decide"
        assert "candidates" in result

    def test_empty_requirement(self):
        result = backendpro_decide("")
        assert isinstance(result, dict)


class TestBackendproAdr:
    def test_valid_adr(self):
        result = backendpro_adr("Adopt circuit breaker", context_domains=["pattern"])
        assert result["mode"] == "adr"
        assert "text" in result

    def test_no_domains_returns_error(self):
        result = backendpro_adr("Test", context_domains=[])
        assert "error" in result


class TestBackendproDesign:
    def test_valid_design(self):
        result = backendpro_design("URL shortener serving 10M reads/day")
        assert result["mode"] == "design"
        assert "sections" in result

    def test_simple_requirement(self):
        result = backendpro_design("chat application")
        assert isinstance(result, dict)
        assert "sections" in result


class TestBackendproFindStale:
    def test_valid_domain(self):
        result = backendpro_find_stale("pattern", months=6)
        assert "results" in result
        assert "count" in result

    def test_unknown_domain_returns_error(self):
        result = backendpro_find_stale("nonexistent", months=6)
        assert "error" in result


# ── Server metadata ───────────────────────────────────────────────

class TestServerMetadata:
    def test_server_name(self):
        assert mcp_server.name == "Backend Pro Max"

    def test_tool_count(self):
        """Server should expose exactly 8 tools."""
        # FastMCP stores tools internally; we verify via our definitions
        tools = mcp_server._tool_manager._tools
        assert len(tools) == 8, f"Expected 8 tools, got {len(tools)}: {list(tools.keys())}"
