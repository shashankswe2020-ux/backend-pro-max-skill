# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) and other AI
coding assistants when working with this repository.

## Project Overview

**Backend Pro Max** is an AI skill that provides backend / distributed-systems
engineering intelligence: searchable knowledge bases for programming languages,
databases, message brokers, caching, cloud, IaC, containers, observability,
API design, auth, security, CI/CD, testing, architecture, scaling,
consistency, performance, reliability, and data engineering — plus
language-specific stack guidelines.

It is intended to be installed as a skill / rules file in any AI coding
assistant (Claude Code, Cursor, Windsurf, Copilot, Gemini, etc.).

## Search Command

```bash
python3 src/backend-pro-max/scripts/search.py "<query>" --domain <domain> [-n <max_results>]
python3 src/backend-pro-max/scripts/search.py "<query>" --stack <stack>
python3 src/backend-pro-max/scripts/search.py "<query>" --all          # cross-domain
python3 src/backend-pro-max/scripts/search.py --list                   # list domains & stacks
```

### Domains

`language`, `pattern`, `database`, `messaging`, `cache`, `cloud`, `iac`,
`container`, `observability`, `api`, `auth`, `security`, `cicd`, `testing`,
`architecture`, `scaling`, `consistency`, `performance`, `reliability`, `data`

### Stacks

`go`, `java-spring`, `python-fastapi`, `nodejs-express`, `rust-axum`,
`csharp-aspnet`, `kotlin-spring`, `scala-akka`, `elixir-phoenix`, `ruby-rails`,
`php-laravel`, `cpp`

## Architecture

```
src/backend-pro-max/                 # Source of truth
├── data/                            # Canonical CSV knowledge bases
│   ├── languages.csv
│   ├── patterns.csv
│   ├── databases.csv
│   ├── messaging.csv
│   ├── cache.csv
│   ├── cloud.csv
│   ├── iac.csv
│   ├── containers.csv
│   ├── observability.csv
│   ├── api.csv
│   ├── auth.csv
│   ├── security.csv
│   ├── cicd.csv
│   ├── testing.csv
│   ├── architecture.csv
│   ├── scaling.csv
│   ├── consistency.csv
│   ├── performance.csv
│   ├── reliability.csv
│   ├── data-engineering.csv
│   └── stacks/                      # Per-language guidelines
│       ├── go.csv
│       ├── java-spring.csv
│       ├── python-fastapi.csv
│       ├── nodejs-express.csv
│       ├── rust-axum.csv
│       ├── csharp-aspnet.csv
│       ├── kotlin-spring.csv
│       ├── scala-akka.csv
│       ├── elixir-phoenix.csv
│       ├── ruby-rails.csv
│       ├── php-laravel.csv
│       └── cpp.csv
├── scripts/
│   ├── search.py                    # CLI entry point
│   └── core.py                      # BM25 search engine + domain detection
└── templates/
    └── base/
        ├── skill-content.md         # Common SKILL.md content
        └── quick-reference.md       # Quick-reference cheatsheet

.claude/skills/backend-pro-max/      # Claude Code skill (SKILL.md)
.claude-plugin/plugin.json           # Claude Marketplace manifest
docs/                                # Architecture & usage docs
```

The search engine uses BM25 ranking over the search columns of each CSV,
with light keyword-based domain auto-detection when `--domain` is omitted.

## Adding new content

1. **New row** — append to the relevant `data/<domain>.csv`. Keep the column
   order; only add columns if you also update `CSV_CONFIG` in `core.py`.
2. **New domain** — add a CSV under `data/`, register it in `CSV_CONFIG` in
   `core.py`, and add a keyword bag in `_DOMAIN_KEYWORDS`.
3. **New stack** — add `data/stacks/<stack>.csv` (using the stack column
   shape: `Category, Guideline, Description, Do, Don't, Code Good, Code Bad,
   Severity, Docs URL`) and register it in `STACK_CONFIG` in `core.py`.

## Smoke test

```bash
python3 src/backend-pro-max/scripts/search.py --list
python3 src/backend-pro-max/scripts/search.py "circuit breaker"
python3 src/backend-pro-max/scripts/search.py "virtual threads" --stack java-spring
python3 src/backend-pro-max/scripts/search.py "idempotency" --all
```

## Prerequisites

Python 3.8+ (no external dependencies required — pure standard library).

## Git Workflow

Never push directly to `main`. Always:

1. Create a new branch: `git checkout -b feat/...` or `fix/...`
2. Commit changes
3. Push branch: `git push -u origin <branch>`
4. Create PR: `gh pr create`
