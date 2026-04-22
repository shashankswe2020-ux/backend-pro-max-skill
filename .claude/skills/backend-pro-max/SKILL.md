---
name: backend-pro-max
description: |
  Backend & distributed-systems engineering intelligence — search 20 domain
  knowledge bases (languages, patterns, databases, messaging, cache, cloud,
  IaC, containers, observability, API design, auth, security, CI/CD, testing,
  architecture, scaling, consistency, performance, reliability, data) and
  12 language-specific stack guidelines.
---

# Backend Pro Max

Use this skill whenever the user asks about backend, cloud, or
distributed-systems engineering — choosing a language / database / broker,
designing an API, sizing a cache, planning multi-region, debugging tail
latency, hardening security, defining SLOs, etc.

## Search

```bash
python3 src/backend-pro-max/scripts/search.py "<query>" [--domain <domain>] [--stack <stack>] [-n N]
python3 src/backend-pro-max/scripts/search.py "<query>" --all
python3 src/backend-pro-max/scripts/search.py --list
```

## Working principles

1. **Run a `--stack <stack>` query first** if the user has named a language /
   framework. The stack CSV contains the strict guidelines for that
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
