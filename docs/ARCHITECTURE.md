# Architecture

## Overview

`backend-pro-max-skill` is a **knowledge skill**, not a runtime: a curated
set of CSV knowledge bases plus a tiny pure-Python BM25 search engine that
an AI assistant calls to ground its backend / distributed-systems answers.

```
              ┌──────────────────────────────────────────────────┐
              │  AI Assistant (Claude Code / Cursor / Copilot…)  │
              └─────────────────┬────────────────────────────────┘
                                │  shell call
                                ▼
                ┌──────────────────────────────┐
                │ python3 search.py "<query>"  │
                │   --domain <d> | --stack <s> │
                └───────────────┬──────────────┘
                                ▼
                ┌──────────────────────────────┐
                │   core.py (BM25 + detect)    │
                └───────────────┬──────────────┘
                                ▼
                ┌──────────────────────────────┐
                │     data/*.csv (20 domains)  │
                │     data/stacks/*.csv (12)   │
                └──────────────────────────────┘
```

## Components

### `scripts/core.py`

* **`CSV_CONFIG`** — registry mapping each `--domain` to its CSV file plus
  the `search_cols` (BM25-indexed) and `output_cols` (rendered to the user).
* **`STACK_CONFIG`** — same pattern for per-language stack CSVs.
* **`BM25`** — pure-stdlib BM25 (k1=1.5, b=0.75) over tokenised search
  columns. No external deps.
* **`detect_domain(query)`** — light keyword-bag classifier that picks the
  best domain when `--domain` is omitted.
* **`search` / `search_stack` / `search_all`** — top-level entry points.

### `scripts/search.py`

Thin CLI wrapper that:

* Forces UTF-8 stdout/stderr (Windows fix for emojis).
* Renders results in a token-economical Markdown shape designed for LLM
  consumption (truncates very long fields).
* Supports `--json` for tooling.

### `data/<domain>.csv`

Each domain CSV is a small, opinionated, hand-curated table. The schema is
domain-specific (declared in `core.py`). The most useful columns
(`search_cols`) are BM25-indexed; the columns rendered back to the user
(`output_cols`) include enough context to be actionable (Do / Don't,
trade-offs, alternatives, references).

### `data/stacks/<stack>.csv`

All stack CSVs share one schema:

| Column         | Purpose                                                        |
|----------------|----------------------------------------------------------------|
| `Category`     | Grouping (Concurrency / HTTP / Errors / Observability / …)     |
| `Guideline`    | Short imperative title of the rule                             |
| `Description`  | One-paragraph rationale                                        |
| `Do`           | Bullet of the recommended approach                             |
| `Don't`        | Bullet of the anti-pattern                                     |
| `Code Good`    | Minimal good-code example                                      |
| `Code Bad`     | Minimal bad-code counter-example                               |
| `Severity`     | `Critical` / `High` / `Medium`                                 |
| `Docs URL`     | Authoritative reference                                        |

This shape is enforced by `_STACK_COLS` in `core.py` and means new stacks
can be added without changing any code.

## Design principles

1. **Pure standard library.** No `requirements.txt`, no install step. Skills
   should be drop-in and zero-friction.
2. **CSV, not JSON.** Diff-friendly, spreadsheet-friendly, easy to extend by
   non-Python contributors.
3. **Curated, not crawled.** Every row is hand-written and reviewed. Quality
   beats quantity for a skill — the model already has the breadth.
4. **Token-economical output.** Rendered results are <300 chars per field
   and include only `output_cols` so we don't blow context budgets.
5. **Stack-first, then domain.** When the user has named a language /
   framework, run `--stack` first so the model anchors to that ecosystem's
   idioms before reaching for generic patterns.

## Adding new content

See [`CLAUDE.md`](../CLAUDE.md) → *Adding new content*.

## Out of scope

* No web service / hosted API. The CLI runs locally in the assistant's
  shell.
* No project-scaffolding generators (this is a *knowledge* skill — pair it
  with `cookiecutter`, `nx`, `dotnet new`, `cargo generate`, etc.).
* No vendor-specific marketing recommendations. CSV rows aim to capture
  trade-offs, not "best of" rankings.
