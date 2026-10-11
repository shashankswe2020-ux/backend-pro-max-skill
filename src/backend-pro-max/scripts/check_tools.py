"""Offline MCP discovery, contract, retrieval, and error-contract smoke checks.

Run with: python -m backendpro.scripts.check_tools
Requires the optional MCP extra. Does not read credentials or call providers.
"""
from __future__ import annotations

import json
import sys

from .core import CSV_CONFIG, STACK_CONFIG
from .gen_tools_schema import TOOLS


async def check_session(session) -> dict:
    initialized = await session.initialize()
    if initialized.serverInfo.name != "Backend Pro Max":
        raise ValueError("Unexpected MCP server identity")
    discovered = (await session.list_tools()).tools
    expected = {tool["name"]: tool for tool in TOOLS}
    if len(discovered) != len(expected) or {tool.name for tool in discovered} != expected.keys():
        raise ValueError("MCP tool discovery does not match the canonical manifest")
    for tool in discovered:
        contract = expected[tool.name]
        if tool.inputSchema != contract["parameters"] or tool.description != contract["description"]:
            raise ValueError(f"MCP contract drift: {tool.name}")
        if tool.outputSchema is not None and tool.outputSchema.get("type") != "object":
            raise ValueError(f"MCP output is no longer a structured dictionary: {tool.name}")

    result = await session.call_tool("search", {"query": "Kafka", "domain": "messaging"})
    if result.isError:
        raise ValueError("Known-answer MCP retrieval failed")
    value = json.loads(result.content[0].text)
    rows = value.get("results", [])
    if not rows or not any("Kafka" in json.dumps(row) for row in rows):
        raise ValueError("Known-answer MCP retrieval did not return Kafka evidence")
    if not all(row.get("_citation") for row in rows):
        raise ValueError("Known-answer MCP retrieval lacks citations")
    empty = await session.call_tool(
        "search", {"query": "Kafka", "domain": "messaging", "min_score": 1e100},
    )
    if empty.isError or json.loads(empty.content[0].text).get("count") != 0:
        raise ValueError("Empty retrieval must remain a successful zero-result response")
    invalid_cases = [
        ("search", {"query": "Kafka", "domain": "nonexistent"}),
        ("search", {"query": "Kafka", "max_results": 0}),
        ("search_stack", {"query": "errors", "stack": "nonexistent"}),
        ("compare", {"names": ["Kafka"]}),
        ("adr", {"title": "Decision", "context_domains": []}),
        ("find_stale", {"domain": "pattern", "months": -1}),
        ("search", {}),
        ("adr", {"title": "zzqxvzzqxv", "context_domains": ["pattern"]}),
        ("nonexistent", {}),
    ]
    for name, arguments in invalid_cases:
        failure = await session.call_tool(name, arguments)
        if not failure.isError:
            raise ValueError(f"MCP invalid input was reported as success: {name}")
    return {
        "status": "passed", "transport": "mcp_stdio", "tools": len(discovered),
        "domains": len(CSV_CONFIG), "stacks": len(STACK_CONFIG),
        "known_answer": "Kafka/messaging with citations", "empty_result_checked": True,
        "invalid_cases_checked": len(invalid_cases),
    }


def check_stdio() -> dict:
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
                    return await check_session(session)

    return anyio.run(exercise)


if __name__ == "__main__":
    print(json.dumps(check_stdio(), indent=2))
