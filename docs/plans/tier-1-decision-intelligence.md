# Tier 1 — Decision Intelligence

> The staff-engineer differentiator: don't just find — decide and justify.

**Status:** 🔲 Not started
**Branch:** `feat/tier-1-decision-intelligence` (to be created from `main`)
**Depends on:** Current `main` (v0.2.x baseline)

---

## Overview

Four new capabilities that transform Backend Pro Max from a search engine into a decision engine:

| # | Feature | CLI | Complexity |
|---|---------|-----|------------|
| 1.1 | `decide` command | `backendpro decide "<requirement>"` | High |
| 1.2 | `adr` generator | `backendpro adr "<title>" --context <domains>` | Medium |
| 1.3 | `design` command | `backendpro design "<system>" ` | High |
| 1.4 | Constraint-aware filtering | `--constraints "cloud=gcp,latency<10ms"` | Medium |

All features must remain **pure stdlib** (no new runtime dependencies).

---

## Architecture Decisions

1. **New module: `src/backend-pro-max/scripts/decide.py`** — keeps `core.py` focused on retrieval. The `decide` module orchestrates multi-domain searches and formats opinionated output.
2. **ADR template: `src/backend-pro-max/templates/base/adr.md`** — Nygard-format Jinja-free template (string `.format()` / f-string based).
3. **Constraint columns** are added to existing CSVs incrementally (new columns are optional / nullable). `CSV_CONFIG` output_cols updated; validator made tolerant of missing optional cols.
4. **CLI wiring** — new subcommands added to `search.py:_build_parser()` and `main()`, plus REPL shortcuts `/decide`, `/adr`, `/design`.

---

## Task 1.1 — `decide` command

### Description
Multi-domain orchestrated recommendation. Given a natural-language requirement string, the engine:
1. Extracts constraint facets (throughput, latency, cloud, consistency, cost) via regex/keyword extraction.
2. Searches across relevant domains (auto-detected from the query, typically 3–5 domains).
3. Scores candidates against extracted constraints.
4. Returns a ranked recommendation with trade-off table and ADR-ready markdown.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 1.1.1 | Constraint extractor — parse NL requirement into structured facets | `scripts/decide.py` | 2h |
| 1.1.2 | Multi-domain orchestrator — fan out `search()` across detected domains, merge results | `scripts/decide.py` | 2h |
| 1.1.3 | Scoring engine — rank candidates against constraints (satisfied/violated/unknown) | `scripts/decide.py` | 3h |
| 1.1.4 | Markdown formatter — ranked table + trade-offs + constraints matrix | `scripts/decide.py` | 1h |
| 1.1.5 | CLI integration — `backendpro decide "<req>"` + `--json` + REPL `/decide` | `scripts/search.py` | 1h |
| 1.1.6 | Tests — unit tests for extractor, orchestrator, scorer, end-to-end CLI | `tests/test_decide.py` | 2h |

### Acceptance Criteria
- [ ] `backendpro decide "event bus for 50k events/sec, ordered per-tenant, GCP-native"` returns ≥2 ranked candidates with trade-off table
- [ ] Output includes constraints satisfied/violated per candidate
- [ ] `--json` flag produces machine-readable output
- [ ] `/decide` works in REPL
- [ ] `pytest tests/test_decide.py` passes

### Verification
```bash
backendpro decide "event bus for 50k events/sec, ordered per-tenant, GCP-native"
backendpro decide "database for time-series IoT data, 1M inserts/sec, AWS" --json
pytest tests/test_decide.py -v
```

---

## Task 1.2 — `adr` generator

### Description
Generate a Michael Nygard-format Architecture Decision Record pre-filled with cited KB rows.

**Output format:**
```
# ADR-NNNN: <Title>
## Status: Proposed
## Context: (from --context domains, cited rows)
## Decision: (top recommendation from relevant search)
## Alternatives Considered: (other candidates with Strengths/Weaknesses)
## Consequences: (Weaknesses + Pitfalls from chosen option)
## References: (docs URLs from rows)
```

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 1.2.1 | ADR template file | `templates/base/adr.md` | 0.5h |
| 1.2.2 | ADR generator function — search context domains, fill template | `scripts/decide.py` | 2h |
| 1.2.3 | CLI integration — `backendpro adr "<title>" --context <d1,d2> [--out path]` | `scripts/search.py` | 1h |
| 1.2.4 | REPL shortcut `/adr` | `scripts/search.py` | 0.5h |
| 1.2.5 | Tests | `tests/test_decide.py` | 1h |

### Acceptance Criteria
- [ ] `backendpro adr "Adopt outbox pattern" --context messaging,reliability,consistency` produces valid Nygard-format markdown
- [ ] `--out docs/adr/0042.md` writes to file (creates directory if needed)
- [ ] Each section cites specific KB rows (Name + domain)
- [ ] Consequences section pulls from Weaknesses/Pitfalls/Trade-offs columns
- [ ] References section lists Docs URLs / Reference fields from cited rows
- [ ] `pytest tests/test_decide.py::test_adr*` passes

### Verification
```bash
backendpro adr "Adopt outbox pattern" --context messaging,reliability,consistency
backendpro adr "Use Redis for session cache" --context cache,security --out /tmp/test-adr.md
cat /tmp/test-adr.md
pytest tests/test_decide.py -v -k adr
```

---

## Task 1.3 — `design` command

### Description
System-design scaffolding from a one-liner. Given a system description + scale numbers, produce a candidate architecture with cited choices.

**Output sections:** API style, datastore + sharding plan, cache strategy, messaging / async, ID generation, capacity math, failure modes, observability.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 1.3.1 | Requirement parser — extract scale numbers (reads/writes per day, latency target) | `scripts/decide.py` | 1.5h |
| 1.3.2 | Architecture planner — map requirement facets to domain queries | `scripts/decide.py` | 3h |
| 1.3.3 | Capacity math helpers — QPS from daily numbers, storage estimates | `scripts/decide.py` | 1.5h |
| 1.3.4 | Design formatter — structured markdown with sections + citations | `scripts/decide.py` | 1.5h |
| 1.3.5 | CLI + REPL integration | `scripts/search.py` | 1h |
| 1.3.6 | Tests | `tests/test_decide.py` | 2h |

### Acceptance Criteria
- [ ] `backendpro design "url shortener, 100M reads/day, 1M writes/day, <50ms p99"` produces multi-section architecture scaffold
- [ ] Each technology choice cites a KB row
- [ ] Capacity math section shows QPS derivation, storage estimates
- [ ] Failure modes section lists relevant patterns (circuit breaker, retry, etc.)
- [ ] `--json` produces structured output
- [ ] `pytest tests/test_decide.py::test_design*` passes

### Verification
```bash
backendpro design "url shortener, 100M reads/day, 1M writes/day, <50ms p99"
backendpro design "chat system, 10M DAU, <200ms message delivery" --json
pytest tests/test_decide.py -v -k design
```

---

## Task 1.4 — Constraint-aware filtering

### Description
Add structured constraint columns to CSVs and a `--constraints` flag for filtering.

**New optional columns** (added to relevant CSVs, not all):
- `Throughput Tier` — `low | medium | high | very-high`
- `Latency Tier` — `sub-ms | low-ms | tens-ms | hundreds-ms | seconds`
- `Consistency` — `strong | eventual | tunable | none`
- `Cost Tier` — `free | low | medium | high | very-high`
- `Cloud Native` — `aws | gcp | azure | multi | none` (comma-separated)

**CLI:** `backendpro "event store" --constraints "cloud=gcp,latency=low-ms,consistency=strong"`

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 1.4.1 | Define constraint schema + tier enums | `scripts/core.py` (or `scripts/decide.py`) | 1h |
| 1.4.2 | Add constraint columns to `databases.csv` (pilot CSV) | `data/databases.csv` | 1.5h |
| 1.4.3 | Add constraint columns to `messaging.csv`, `cache.csv` | `data/messaging.csv`, `data/cache.csv` | 1.5h |
| 1.4.4 | Constraint parser — parse `--constraints` string into filter dict | `scripts/core.py` | 1h |
| 1.4.5 | Post-BM25 constraint filter — apply after search, annotate satisfied/violated | `scripts/core.py` | 1.5h |
| 1.4.6 | Update `CSV_CONFIG` output_cols + validator tolerance for optional cols | `scripts/core.py`, `scripts/validate.py` | 1h |
| 1.4.7 | CLI flag `--constraints` + formatter update | `scripts/search.py` | 1h |
| 1.4.8 | Tests | `tests/test_constraints.py` | 2h |

### Acceptance Criteria
- [ ] `backendpro "database" --domain database --constraints "cloud=gcp,consistency=strong"` filters results
- [ ] Results annotated with ✅ / ❌ per constraint
- [ ] Missing constraint columns treated as "unknown" (not filtered out)
- [ ] `backendpro-validate` still passes (optional cols tolerated)
- [ ] Existing tests unbroken
- [ ] `pytest tests/test_constraints.py` passes

### Verification
```bash
backendpro "database" --domain database --constraints "cloud=gcp,consistency=strong"
backendpro "message queue" --domain messaging --constraints "latency=low-ms" --json
backendpro-validate
pytest tests/ -v
```

---

## Dependency Graph

```
                    ┌──────────┐
                    │ 1.4      │  Constraint-aware filtering
                    │ (can be  │
                    │ parallel)│
                    └────┬─────┘
                         │ (enriches)
┌──────────┐       ┌─────▼─────┐       ┌──────────┐
│ 1.2 ADR  │◄──────│ 1.1 decide│──────►│ 1.3 design│
│          │       │           │       │           │
└──────────┘       └───────────┘       └───────────┘
```

- **1.4** (constraints) and **1.1** (decide) can start in parallel — constraints enrich decide but decide works without them initially.
- **1.2** (ADR) depends on 1.1's multi-domain search orchestrator.
- **1.3** (design) depends on 1.1's orchestrator + 1.4's capacity reasoning.

### Recommended implementation order
1. **Phase A** (parallel): 1.4 constraint columns + 1.1 subtasks 1.1.1–1.1.4
2. **Phase B**: 1.1.5–1.1.6 (CLI + tests for decide), then 1.2 (ADR, reuses orchestrator)
3. **Phase C**: 1.3 (design, reuses orchestrator + constraints + capacity math)

---

## Checkpoint Criteria

### After Phase A
- [ ] `databases.csv`, `messaging.csv`, `cache.csv` have constraint columns
- [ ] `backendpro-validate` passes
- [ ] `decide()` function returns ranked results (no CLI yet)
- [ ] Existing 37+ tests still pass

### After Phase B
- [ ] `backendpro decide` and `backendpro adr` work end-to-end
- [ ] JSON output works for both
- [ ] REPL shortcuts `/decide` and `/adr` work
- [ ] ≥15 new test cases

### After Phase C (Tier 1 complete)
- [ ] `backendpro design` works end-to-end
- [ ] All 4 new commands work in CLI, REPL, JSON mode
- [ ] ≥25 new test cases for Tier 1
- [ ] `ruff check src tests` clean
- [ ] README updated with Tier 1 features
- [ ] CHANGELOG entry

---

## Files to Create / Modify

| Action | File |
|--------|------|
| **Create** | `src/backend-pro-max/scripts/decide.py` |
| **Create** | `src/backend-pro-max/templates/base/adr.md` |
| **Create** | `tests/test_decide.py` |
| **Create** | `tests/test_constraints.py` |
| **Modify** | `src/backend-pro-max/scripts/search.py` (CLI + REPL) |
| **Modify** | `src/backend-pro-max/scripts/core.py` (constraint filter, export) |
| **Modify** | `src/backend-pro-max/scripts/validate.py` (optional col tolerance) |
| **Modify** | `src/backend-pro-max/data/databases.csv` (constraint cols) |
| **Modify** | `src/backend-pro-max/data/messaging.csv` (constraint cols) |
| **Modify** | `src/backend-pro-max/data/cache.csv` (constraint cols) |
| **Modify** | `src/backend-pro-max/scripts/__init__.py` (export decide) |
| **Modify** | `pyproject.toml` (new entry points if needed) |
| **Modify** | `README.md`, `CHANGELOG.md` |

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| `decide` output quality depends on KB depth (only ~30-60 rows/domain) | Acknowledge limitations in output: "Based on N rows in {domain}. Consider expanding KB." |
| Constraint columns are labor-intensive to backfill | Start with 3 CSVs (databases, messaging, cache) — highest value. Others in later tiers. |
| `design` command scope creep — tempting to build a full system design tool | Keep it as a scaffold/starting-point generator, not a complete design tool. Cap output sections. |
| NL constraint extraction is fragile without NLP | Use explicit regex patterns for common forms (`<50ms`, `100k/sec`, cloud names). Fall back to keyword matching. Accept imperfection — the `--constraints` flag is the precise path. |
| Pure stdlib constraint means no fancy NLP | This is intentional. Decision logic is rule-based over structured CSV columns, not ML. |
