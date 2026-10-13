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
import os
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
    from . import core
    from . import decide as decisions
    from .evidence import evidence_detail as expand_evidence
    from .gen_tools_schema import TOOLS
    from .memory import memory_context as recalled_context
    from .repository import repository_context as local_context
    from .templates import compact_json, format_search_response
except ImportError:
    import core  # type: ignore[no-redef]
    import decide as decisions  # type: ignore[no-redef]
    from evidence import evidence_detail as expand_evidence  # type: ignore[no-redef]
    from gen_tools_schema import TOOLS  # type: ignore[no-redef]
    from memory import memory_context as recalled_context  # type: ignore[no-redef]
    from repository import repository_context as local_context  # type: ignore[no-redef]
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
        if arguments.get("response_format") in ("compact", "evidence") or name in ("repository_context", "memory_context"):
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
def memory_context(
    query: str, sequence: str, family: str, task: str, ordinal: int,
    allowed_tasks: list[str], library_versions: dict[str, str], max_chars: int = 6000,
) -> dict:
    """Read approved summaries; only the operator CLI can mutate or approve the store."""
    root, store = os.environ.get("BACKENDPRO_WORKSPACE"), os.environ.get("BACKENDPRO_MEMORY_STORE")
    if not root or not store:
        raise ValueError("Memory is disabled; operator must configure BACKENDPRO_WORKSPACE and BACKENDPRO_MEMORY_STORE")
    return recalled_context(query, sequence, family, task, ordinal, allowed_tasks, library_versions,
                            workspace_root=root, store=store, max_chars=max_chars)


@expose
def search(
    query: str,
    domain: str | None = None,
    max_results: int = 5,
    min_score: float = 0.0,
    response_format: str = "raw",
    engine: str = "bm25",
    rerank: bool = False,
    candidate_pool: int | None = None,
    diagnostics: bool = False,
    expand: bool = True,
    max_age_months: int | None = None,
    constraints: str | None = None,
    max_chars: int = 6000,
    project_path: str | None = None,
    library_versions: dict[str, str] | None = None,
) -> dict:
    """BM25 search in a backend-engineering knowledge domain.

    Returns ranked results with citations. Domain is auto-detected if omitted.
    """
    return format_search_response(
        core.search(
            query, domain=domain, max_results=max_results, min_score=min_score, engine=engine,
            rerank=rerank, candidate_pool=candidate_pool, diagnostics=diagnostics, expand=expand,
            max_age_months=max_age_months, constraints=constraints, evidence=response_format == "evidence",
        ), response_format, max_chars=max_chars, project_path=project_path, library_versions=library_versions,
    )


@expose
def search_all(
    query: str,
    max_results: int = 2,
    response_format: str = "raw",
    engine: str = "bm25",
    rerank: bool = False,
    candidate_pool: int | None = None,
    diagnostics: bool = False,
    expand: bool = True,
    min_score: float = 0.0,
    max_age_months: int | None = None,
    constraints: str | None = None,
    max_chars: int = 6000,
    project_path: str | None = None,
    library_versions: dict[str, str] | None = None,
) -> dict:
    """Cross-domain search across every backend-engineering knowledge base.

    Returns top hits per domain with citations.
    """
    return format_search_response(core.search_all(
        query, max_results=max_results, min_score=min_score, engine=engine, rerank=rerank,
        candidate_pool=candidate_pool, diagnostics=diagnostics, expand=expand,
        max_age_months=max_age_months, constraints=constraints, evidence=response_format == "evidence",
    ), response_format, max_chars=max_chars, project_path=project_path, library_versions=library_versions)


@expose
def search_stack(
    query: str,
    stack: str,
    max_results: int = 5,
    response_format: str = "raw",
    engine: str = "bm25",
    rerank: bool = False,
    candidate_pool: int | None = None,
    diagnostics: bool = False,
    expand: bool = True,
    min_score: float = 0.0,
    max_age_months: int | None = None,
    constraints: str | None = None,
    max_chars: int = 6000,
    project_path: str | None = None,
    library_versions: dict[str, str] | None = None,
) -> dict:
    """Search stack-specific guidelines for a language / framework.

    Available stacks: go, java-spring, python-fastapi, nodejs-express,
    rust-axum, csharp-aspnet, kotlin-spring, scala-akka, elixir-phoenix,
    ruby-rails, php-laravel, cpp.
    """
    return format_search_response(core.search_stack(
        query, stack, max_results=max_results, min_score=min_score, engine=engine, rerank=rerank,
        candidate_pool=candidate_pool, diagnostics=diagnostics, expand=expand,
        max_age_months=max_age_months, constraints=constraints, evidence=response_format == "evidence",
    ), response_format, max_chars=max_chars, project_path=project_path, library_versions=library_versions)


@expose
def repository_context(
    query: str, paths: list[str], max_chars: int = 6000,
    editor: dict | None = None, expected_revision: str | None = None,
    expected_files: dict[str, str] | None = None, domain: str | None = None,
    stack: str | None = None, library_versions: dict[str, str] | None = None,
) -> dict:
    """Read explicit local files only inside the operator-configured workspace."""
    root = os.environ.get("BACKENDPRO_WORKSPACE")
    if not root:
        raise ValueError("Local context is disabled; configure BACKENDPRO_WORKSPACE to authorize a Git root")
    return local_context(
        query, paths, workspace_root=root, max_chars=max_chars, editor=editor,
        expected_revision=expected_revision, expected_files=expected_files,
        domain=domain, stack=stack, library_versions=library_versions,
    )


@expose
def evidence_detail(evidence_id: str) -> dict:
    """Expand an exact local evidence ID without network access; stale IDs fail."""
    return expand_evidence(evidence_id)


@expose
def compare(
    names: list[str],
    domain: str | None = None,
) -> dict:
    """Side-by-side comparison of two or more technologies or patterns.

    Returns a structured table with citations.
    """
    return core.compare(names, domain=domain)


@expose
def decide(
    requirement: str,
) -> dict:
    """Opinionated, constraint-scored recommendation for a backend requirement.

    Searches across relevant domains and ranks candidates by constraint fit.
    """
    return decisions.decide(requirement)


@expose
def adr(
    title: str,
    context_domains: list[str],
) -> dict:
    """Generate a Michael Nygard-format Architecture Decision Record.

    Searches the specified domains for context and produces a structured ADR.
    """
    return decisions.adr(title, context_domains)


@expose
def design(
    description: str,
) -> dict:
    """Generate a system-design scaffold from a one-liner requirement.

    Extracts scale numbers, searches relevant domains, and produces a
    candidate architecture with capacity math.
    """
    return decisions.design(description)


@expose
def find_stale(
    domain: str,
    months: int,
) -> dict:
    """Find knowledge-base entries older than a given threshold.

    Useful for freshness audits of the KB data.
    """
    return core.find_stale(domain, months)


# ── Entry point ───────────────────────────────────────────────────
def main():
    """Run the MCP server on stdio transport."""
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
