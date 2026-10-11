#!/usr/bin/env python3
"""Backend Pro Max — MCP Server.

Exposes the Backend Pro Max knowledge base as Model Context Protocol tools.
Uses stdio transport (universal for local MCP tools).

Requires the ``mcp`` optional extra:
    pip install backendpro[mcp]

Run:
    backendpro-mcp          # via entry point
    python -m backendpro.scripts.mcp_server   # direct
"""
from __future__ import annotations

import json
import sys
from functools import wraps


def _check_mcp():
    """Fail fast with a helpful message if the mcp SDK is not installed."""
    try:
        import mcp  # noqa: F401
    except ImportError:
        print(
            "Error: The 'mcp' package is not installed.\n"
            "Install it with:  pip install backendpro[mcp]\n",
            file=sys.stderr,
        )
        sys.exit(1)


_check_mcp()

from jsonschema import ValidationError, validate  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp.server.fastmcp.exceptions import ToolError  # noqa: E402
from mcp.types import TextContent  # noqa: E402

# Import core functions — works both as package and standalone.
try:
    from .core import compare, find_stale, search, search_all, search_stack
    from .decide import adr, decide, design
    from .gen_tools_schema import TOOLS
    from .templates import compact_json, format_search_response
except ImportError:
    from core import compare, find_stale, search, search_all, search_stack  # type: ignore[no-redef]
    from decide import adr, decide, design  # type: ignore[no-redef]
    from gen_tools_schema import TOOLS  # type: ignore[no-redef]
    from templates import compact_json, format_search_response  # type: ignore[no-redef]

CONTRACTS = {tool["name"]: tool for tool in TOOLS}


class CanonicalFastMCP(FastMCP):
    async def list_tools(self):
        tools = await super().list_tools()
        for tool in tools:
            contract = CONTRACTS[tool.name]
            tool.inputSchema = contract["parameters"]
            tool.description = contract["description"]
        return tools

    async def call_tool(self, name, arguments):
        if name not in CONTRACTS:
            raise ToolError(f"Unknown tool: {name}")
        try:
            validate(arguments, CONTRACTS[name]["parameters"])
        except ValidationError as error:
            raise ToolError(f"Invalid arguments for {name}: {error.message}") from error
        result = await super().call_tool(name, arguments)
        if arguments.get("response_format") == "compact":
            # FastMCP returns either content or (content, structured output).
            content = result[0] if isinstance(result, tuple) else result
            if not isinstance(content, (list, tuple)):
                raise ToolError("Unsupported MCP compact serialization")
            for block in content:
                if isinstance(block, TextContent):
                    block.text = compact_json(json.loads(block.text))
        return result

# ── Server setup ──────────────────────────────────────────────────
mcp_server = CanonicalFastMCP(
    "Backend Pro Max",
)

def expose(function):
    """Keep direct dict responses compatible; mark failures at the MCP boundary."""
    @wraps(function)
    def transport(**kwargs):
        result = function(**kwargs)
        if "error" in result:
            raise ToolError(str(result["error"]))
        return result

    mcp_server.add_tool(transport, description=CONTRACTS[function.__name__]["description"])
    return function


# ── Tool definitions ─────────────────────────────────────────────

@expose
def backendpro_search(
    query: str,
    domain: str | None = None,
    max_results: int = 5,
    min_score: float = 0.0,
    response_format: str = "raw",
) -> dict:
    """BM25 search in a backend-engineering knowledge domain.

    Returns ranked results with citations. Domain is auto-detected if omitted.
    """
    return format_search_response(
        search(query, domain=domain, max_results=max_results, min_score=min_score), response_format,
    )


@expose
def backendpro_search_all(
    query: str,
    max_results: int = 2,
    response_format: str = "raw",
) -> dict:
    """Cross-domain search across every backend-engineering knowledge base.

    Returns top hits per domain with citations.
    """
    return format_search_response(search_all(query, max_results=max_results), response_format)


@expose
def backendpro_search_stack(
    query: str,
    stack: str,
    max_results: int = 5,
    response_format: str = "raw",
) -> dict:
    """Search stack-specific guidelines for a language / framework.

    Available stacks: go, java-spring, python-fastapi, nodejs-express,
    rust-axum, csharp-aspnet, kotlin-spring, scala-akka, elixir-phoenix,
    ruby-rails, php-laravel, cpp.
    """
    return format_search_response(search_stack(query, stack, max_results=max_results), response_format)


@expose
def backendpro_compare(
    names: list[str],
    domain: str | None = None,
) -> dict:
    """Side-by-side comparison of two or more technologies or patterns.

    Returns a structured table with citations.
    """
    return compare(names, domain=domain)


@expose
def backendpro_decide(
    requirement: str,
) -> dict:
    """Opinionated, constraint-scored recommendation for a backend requirement.

    Searches across relevant domains and ranks candidates by constraint fit.
    """
    return decide(requirement)


@expose
def backendpro_adr(
    title: str,
    context_domains: list[str],
) -> dict:
    """Generate a Michael Nygard-format Architecture Decision Record.

    Searches the specified domains for context and produces a structured ADR.
    """
    return adr(title, context_domains)


@expose
def backendpro_design(
    description: str,
) -> dict:
    """Generate a system-design scaffold from a one-liner requirement.

    Extracts scale numbers, searches relevant domains, and produces a
    candidate architecture with capacity math.
    """
    return design(description)


@expose
def backendpro_find_stale(
    domain: str,
    months: int,
) -> dict:
    """Find knowledge-base entries older than a given threshold.

    Useful for freshness audits of the KB data.
    """
    return find_stale(domain, months)


# ── Entry point ───────────────────────────────────────────────────
def main():
    """Run the MCP server on stdio transport."""
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
