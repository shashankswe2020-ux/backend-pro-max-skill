# MCP Inspector Report — Backend Pro Max

**Date:** 2026-04-22
**Inspector version:** `npx @modelcontextprotocol/inspector`
**Server:** `backendpro-mcp` (stdio transport)
**Tester:** manual via Inspector UI

**Naming update (#38):** the tables below use the current unprefixed tool names.
The original 2026-04-22 manual run used `backendpro_`-prefixed names; this is not
a claim that Inspector was rerun. Automated stdio tests now verify discovery
and successful calls for all eight short names, plus rejection of obsolete
prefixed names. Current MCP validation failures use `isError=true`; the error
objects below describe the historical run.

---

## Connection

| Check | Result |
|-------|--------|
| Inspector connects to `backendpro-mcp` via stdio | ✅ Pass |
| Server responds to `initialize` handshake | ✅ Pass |

## Tools List

`tools/list` returned **8 tools** with valid input schemas:

| # | Tool | Schema Valid |
|---|------|-------------|
| 1 | `search` | ✅ |
| 2 | `search_all` | ✅ |
| 3 | `search_stack` | ✅ |
| 4 | `compare` | ✅ |
| 5 | `decide` | ✅ |
| 6 | `adr` | ✅ |
| 7 | `design` | ✅ |
| 8 | `find_stale` | ✅ |

## Tool Invocations

| Tool | Input | Result | Latency | Citations |
|------|-------|--------|---------|-----------|
| `search` | `{"query": "kafka", "domain": "messaging"}` | ✅ Structured JSON, results returned | < 1s | ✅ `_citation` present |
| `search_all` | `{"query": "circuit breaker"}` | ✅ Cross-domain results | < 1s | ✅ |
| `search_stack` | `{"query": "error handling", "stack": "go"}` | ✅ Stack guidelines returned | < 1s | ✅ |
| `compare` | `{"names": ["Kafka", "RabbitMQ"], "domain": "messaging"}` | ✅ Compare table | < 1s | ✅ |
| `decide` | `{"requirement": "message broker for 100k msg/s on AWS"}` | ✅ Ranked candidates | < 1s | ✅ |
| `adr` | `{"title": "Adopt circuit breaker", "context_domains": ["pattern"]}` | ✅ ADR text generated | < 1s | ✅ |
| `design` | `{"description": "URL shortener serving 10M reads/day"}` | ✅ Design scaffold | < 1s | ✅ |
| `find_stale` | `{"domain": "pattern", "months": 12}` | ✅ Stale entries listed | < 1s | ✅ |

## Error Handling

| Input | Expected | Result |
|-------|----------|--------|
| `search` with `domain: "nonexistent"` | Error response (not crash) | ✅ `{"error": "Unknown domain: nonexistent..."}` |
| `compare` with single name | Error response | ✅ `{"error": "compare needs at least two names."}` |
| `adr` with empty domains | Error response | ✅ `{"error": "adr requires at least one context domain"}` |

## Summary

- **8/8 tools** connected, listed, and invoked successfully
- **All responses** returned structured JSON with `_citation` fields
- **All error cases** returned graceful error objects (no stack traces)
- **All latencies** < 1s (BM25 engine is sub-millisecond)
- **Verdict: PASS** — ready for shipping
