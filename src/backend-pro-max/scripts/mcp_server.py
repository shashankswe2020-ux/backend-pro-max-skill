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

import sys


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

from mcp.server.fastmcp import FastMCP  # noqa: E402

# Import core functions — works both as package and standalone.
try:
    from .core import compare, find_stale, search, search_all, search_stack
    from .decide import adr, decide, design
except ImportError:
    from core import compare, find_stale, search, search_all, search_stack  # type: ignore[no-redef]
    from decide import adr, decide, design  # type: ignore[no-redef]

# ── Server setup ──────────────────────────────────────────────────
mcp_server = FastMCP(
    "Backend Pro Max",
)


# ── Tool definitions ─────────────────────────────────────────────

@mcp_server.tool()
def backendpro_search(
    query: str,
    domain: str | None = None,
    max_results: int = 5,
    min_score: float = 0.0,
) -> dict:
    """BM25 search in a backend-engineering knowledge domain.

    Returns ranked results with citations. Domain is auto-detected if omitted.
    """
    try:
        return search(query, domain=domain, max_results=max_results, min_score=min_score)
    except Exception as e:
        return {"error": str(e)}


@mcp_server.tool()
def backendpro_search_all(
    query: str,
    max_results: int = 2,
) -> dict:
    """Cross-domain search across every backend-engineering knowledge base.

    Returns top hits per domain with citations.
    """
    try:
        return search_all(query, max_results=max_results)
    except Exception as e:
        return {"error": str(e)}


@mcp_server.tool()
def backendpro_search_stack(
    query: str,
    stack: str,
    max_results: int = 5,
) -> dict:
    """Search stack-specific guidelines for a language / framework.

    Available stacks: go, java-spring, python-fastapi, nodejs-express,
    rust-axum, csharp-aspnet, kotlin-spring, scala-akka, elixir-phoenix,
    ruby-rails, php-laravel, cpp.
    """
    try:
        return search_stack(query, stack, max_results=max_results)
    except Exception as e:
        return {"error": str(e)}


@mcp_server.tool()
def backendpro_compare(
    names: list[str],
    domain: str | None = None,
) -> dict:
    """Side-by-side comparison of two or more technologies or patterns.

    Returns a structured table with citations.
    """
    try:
        return compare(names, domain=domain)
    except Exception as e:
        return {"error": str(e)}


@mcp_server.tool()
def backendpro_decide(
    requirement: str,
) -> dict:
    """Opinionated, constraint-scored recommendation for a backend requirement.

    Searches across relevant domains and ranks candidates by constraint fit.
    """
    try:
        return decide(requirement)
    except Exception as e:
        return {"error": str(e)}


@mcp_server.tool()
def backendpro_adr(
    title: str,
    context_domains: list[str],
) -> dict:
    """Generate a Michael Nygard-format Architecture Decision Record.

    Searches the specified domains for context and produces a structured ADR.
    """
    try:
        return adr(title, context_domains)
    except Exception as e:
        return {"error": str(e)}


@mcp_server.tool()
def backendpro_design(
    description: str,
) -> dict:
    """Generate a system-design scaffold from a one-liner requirement.

    Extracts scale numbers, searches relevant domains, and produces a
    candidate architecture with capacity math.
    """
    try:
        return design(description)
    except Exception as e:
        return {"error": str(e)}


@mcp_server.tool()
def backendpro_find_stale(
    domain: str,
    months: int,
) -> dict:
    """Find knowledge-base entries older than a given threshold.

    Useful for freshness audits of the KB data.
    """
    try:
        return find_stale(domain, months)
    except Exception as e:
        return {"error": str(e)}


# ── Entry point ───────────────────────────────────────────────────
def main():
    """Run the MCP server on stdio transport."""
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
