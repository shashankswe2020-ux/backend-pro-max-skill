# MCP Inspector Report — Backend Pro Max

**Date:** 2026-04-22
**Inspector version:** `npx @modelcontextprotocol/inspector`
**Server:** `backendpro-mcp` (stdio transport)
**Tester:** manual via Inspector UI

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
| 1 | `backendpro_search` | ✅ |
| 2 | `backendpro_search_all` | ✅ |
| 3 | `backendpro_search_stack` | ✅ |
| 4 | `backendpro_compare` | ✅ |
| 5 | `backendpro_decide` | ✅ |
| 6 | `backendpro_adr` | ✅ |
| 7 | `backendpro_design` | ✅ |
| 8 | `backendpro_find_stale` | ✅ |

## Tool Invocations

| Tool | Input | Result | Latency | Citations |
|------|-------|--------|---------|-----------|
| `backendpro_search` | `{"query": "kafka", "domain": "messaging"}` | ✅ Structured JSON, results returned | < 1s | ✅ `_citation` present |
| `backendpro_search_all` | `{"query": "circuit breaker"}` | ✅ Cross-domain results | < 1s | ✅ |
| `backendpro_search_stack` | `{"query": "error handling", "stack": "go"}` | ✅ Stack guidelines returned | < 1s | ✅ |
| `backendpro_compare` | `{"names": ["Kafka", "RabbitMQ"], "domain": "messaging"}` | ✅ Compare table | < 1s | ✅ |
| `backendpro_decide` | `{"requirement": "message broker for 100k msg/s on AWS"}` | ✅ Ranked candidates | < 1s | ✅ |
| `backendpro_adr` | `{"title": "Adopt circuit breaker", "context_domains": ["pattern"]}` | ✅ ADR text generated | < 1s | ✅ |
| `backendpro_design` | `{"description": "URL shortener serving 10M reads/day"}` | ✅ Design scaffold | < 1s | ✅ |
| `backendpro_find_stale` | `{"domain": "pattern", "months": 12}` | ✅ Stale entries listed | < 1s | ✅ |

## Error Handling

| Input | Expected | Result |
|-------|----------|--------|
| `backendpro_search` with `domain: "nonexistent"` | Error response (not crash) | ✅ `{"error": "Unknown domain: nonexistent..."}` |
| `backendpro_compare` with single name | Error response | ✅ `{"error": "compare needs at least two names."}` |
| `backendpro_adr` with empty domains | Error response | ✅ `{"error": "adr requires at least one context domain"}` |

## Summary

- **8/8 tools** connected, listed, and invoked successfully
- **All responses** returned structured JSON with `_citation` fields
- **All error cases** returned graceful error objects (no stack traces)
- **All latencies** < 1s (BM25 engine is sub-millisecond)
- **Verdict: PASS** — ready for shipping
