---
name: backend-pro-max
description: |
  Backend & distributed-systems engineering intelligence — search 34 domain
  knowledge bases (languages, patterns, databases, messaging, cache, cloud,
  IaC, containers, observability, API design, auth, security, CI/CD, testing,
  architecture, scaling, consistency, performance, reliability, data) and
  12 language-specific stack guidelines.
---

# Backend Pro Max

Use this skill whenever the user asks about backend, cloud, or
distributed-systems engineering — choosing a language / database / broker,
designing an API, sizing a cache, planning multi-region, debugging tail
latency, hardening security, defining SLOs, etc. Apply the retrieval decision below, not a blanket
requirement to retrieve for every backend edit.

## Retrieval decision

- Inspect the request and relevant repository code first. Retrieve when decisions
  depend on transaction boundaries, retries, idempotency, migrations, concurrency,
  consistency, framework behavior, or operational failure handling.
- Skip retrieval for typos, link fixes, renames, formatting, or self-contained
  local edits whose requirements and behavior are already clear. A backend file
  or a framework name alone is not a reason to call a tool.
- When retrieval is warranted and a supported stack is known, search that stack
  first, then the relevant domain. Never guess a stack or query every domain.
- Use existing compare, decide, ADR, or design tools only when the requested
  deliverable needs them. Query intent classification happens after invocation;
  it is not evidence that an agent selected a tool appropriately.
- Check applicability and version constraints before applying evidence. Use
  pinned official framework documentation for version-sensitive APIs. Cite only
  returned sources; acknowledge missing guidance instead of inventing it.
- `--compact` (MCP: `response_format="compact"`) is optional bounded search JSON.
  It preserves whole evidence units, reports omissions and missing metadata,
  and does not convert BM25 ranking into confidence. Use raw output when more
  context is needed.
- BM25 stays the offline default. Optional `--engine hybrid`, `--rerank`, and
  `--candidate-pool N` also exist on MCP as `engine`, `rerank`, and `candidate_pool`.
  Check `retrieval` metadata for effective execution and fallbacks. Use
  `--diagnostics` (MCP: `diagnostics=true`) for auto-scope hints; explicit
  domains/stacks are never widened. Rank scores are not correctness probabilities.
- For version-sensitive guidance, opt in to `--evidence` (MCP:
  `response_format="evidence"`). Supply explicit `library_versions` or a local
  `project_path` only when manifest inspection is authorized. Unknown/conflicting
  versions are not compatibility claims; check platform and API namespace too.
  Whole units preserve warnings within `max_chars` (default 6000); omissions are
  counted. Expand returned IDs with `evidence_detail` rather than guessing facts.

## Search

```bash
python3 src/backend-pro-max/scripts/search.py "<query>" [--domain <domain>] [--stack <stack>] [-n N]
python3 src/backend-pro-max/scripts/search.py "<query>" --all
python3 src/backend-pro-max/scripts/search.py --list
```

## Working principles

1. **Run a `--stack <stack>` query first** when retrieval is warranted and a
   relevant supported language / framework is known. The stack CSV contains guidelines for that
   ecosystem (concurrency, errors, build, testing, …) — follow them.
2. **Then run a `--domain <domain>` query** to pull the right architectural
   pattern, infra component, or operational practice.
3. **Be explicit about consistency, idempotency, retries, timeouts, and
   failure handling** in any code or design you produce.
4. **Default to managed services** unless there is a concrete reason to
   self-host.
5. **Wire observability and security from the start** — never bolt on later.

See `src/backend-pro-max/templates/base/quick-reference.md` for the full
domain/stack catalogue and example queries.
