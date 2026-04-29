# Tier 7 — Quality Engineering on the KB Itself

> Guard retrieval quality as the knowledge base grows. Prevent regressions,
> detect duplicates, and illuminate coverage gaps — all in CI.

**Status:** ✅ Complete
**Branch:** `feat/tier-6-dx-distribution`
**Depends on:** Tier 3 (citation tokens for stable row IDs in golden queries), Tier 4 (expanded KB makes dedup + coverage meaningful), Tier 5 (Source URLs for coverage quality)

---

## Overview

| # | Feature | Surface | Complexity |
|---|---------|---------|------------|
| 7.1 | Golden query test suite | YAML file + pytest fixture | Medium |
| 7.2 | Semantic deduplication | `backendpro dedup [--domain]` + CI check | Medium |
| 7.3 | Coverage report | `backendpro coverage [--domain]` | Low–Medium |

All three are pure stdlib (dedup uses BM25 similarity, not embeddings, for
the default path; optional `[semantic]` extra for embedding-based dedup).

---

## Architecture Decisions

1. **Golden queries live in `tests/golden-queries.yml`** — a flat YAML list of
   `{query, domain, expected_top_ids[], min_score?, notes?}`. pytest loads the
   file and runs each as a parametrized test case.
2. **Dedup uses pairwise BM25 self-similarity.** For each domain, score every
   row against every other row. Pairs above a threshold (default 0.85
   normalised) are flagged. Optional `[semantic]` path uses cosine similarity
   on embeddings for higher accuracy.
3. **Coverage report is a static analysis** of the CSV — counts rows per
   subdomain/category, identifies categories with <3 rows, and compares
   against a target manifest (`coverage-targets.yml`).

---

## Task 7.1 — Golden Query Test Suite

### Description

A YAML file of `(query, expected_top_row)` pairs that run on every PR.
Guards retrieval quality as rows are added, synonyms are changed, or BM25
parameters are tuned. Expand from the current 37 tests to 200+ ranking
assertions.

**Format:**
```yaml
# tests/golden-queries.yml
- query: "circuit breaker"
  domain: pattern
  expected_top:
    - "Circuit Breaker"          # Name column of expected #1 row
  min_score: 2.0
  notes: "Core resilience pattern — must always be #1"

- query: "kafka exactly once"
  domain: messaging
  expected_top:
    - "Apache Kafka"
  min_score: 3.0

- query: "partial failure handling"
  domain: pattern
  expected_top:
    - "Saga"
    - "Circuit Breaker"          # Either in top-2 is acceptable
```

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 7.1.1 | Define YAML schema for golden queries | `tests/golden-queries.yml` (new) | 0.5h |
| 7.1.2 | Write golden queries for all 20 existing domains (≥5 per domain = 100+) | `tests/golden-queries.yml` | 4h |
| 7.1.3 | Write golden queries for stack searches (≥2 per stack = 24+) | `tests/golden-queries.yml` | 1.5h |
| 7.1.4 | Write golden queries for cross-domain (`--all`) searches (≥10) | `tests/golden-queries.yml` | 1h |
| 7.1.5 | Write golden queries for compare mode (≥10) | `tests/golden-queries.yml` | 1h |
| 7.1.6 | Write edge-case queries: typos, multi-word, product names without spaces (≥20) | `tests/golden-queries.yml` | 1h |
| 7.1.7 | pytest fixture — load YAML, parametrize, assert top-N contains expected | `tests/test_golden_queries.py` (new) | 2h |
| 7.1.8 | CI integration — golden query failures block PR merge | `.github/workflows/ci.yml` | 0.5h |
| 7.1.9 | Reporting — on failure, print actual top-5 vs expected for easy debugging | `tests/test_golden_queries.py` | 0.5h |

### Acceptance Criteria

- [ ] `tests/golden-queries.yml` contains ≥150 query assertions
- [ ] Every domain has ≥5 golden queries
- [ ] Every stack has ≥2 golden queries
- [ ] `pytest tests/test_golden_queries.py` passes on current KB
- [ ] On failure, output shows: query, expected, actual top-5 with scores
- [ ] CI runs golden queries on every PR
- [ ] Adding a new row that displaces an existing golden-query top-1 is caught

### Verification

```bash
pytest tests/test_golden_queries.py -v
pytest tests/test_golden_queries.py -v -k "circuit_breaker"  # single query
pytest tests/test_golden_queries.py -v --tb=long  # verbose failure output

# Count assertions
python3 -c "import yaml; d=yaml.safe_load(open('tests/golden-queries.yml')); print(len(d), 'golden queries')"
```

---

## Task 7.2 — Semantic Deduplication

### Description

As the KB grows past 500+ rows, near-duplicates will sneak in (e.g. "Circuit
Breaker" in `patterns.csv` and a "Circuit Breaker Pattern" in
`reliability.csv`). Detect and flag them.

**Approach:** For each domain, compute pairwise similarity between all rows
using the search-column text. Flag pairs above a normalised similarity
threshold.

**Two modes:**
- **BM25 self-similarity (default, stdlib):** Score each row's search text
  against every other row in the same domain. Normalise by max possible score.
- **Embedding cosine similarity (optional, `[semantic]`):** Use Tier 2
  embeddings for cross-domain dedup.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 7.2.1 | `scripts/dedup.py` — pairwise BM25 self-similarity within a domain | `scripts/dedup.py` (new) | 2.5h |
| 7.2.2 | Cross-domain dedup — compare rows across all domains | `scripts/dedup.py` | 1.5h |
| 7.2.3 | Similarity threshold tuning — default 0.85, configurable via `--threshold` | `scripts/dedup.py` | 0.5h |
| 7.2.4 | Output formatter — table of duplicate pairs with similarity score | `scripts/dedup.py` | 1h |
| 7.2.5 | CLI — `backendpro dedup [--domain D] [--threshold 0.85] [--cross-domain]` | `scripts/search.py` | 1h |
| 7.2.6 | Optional embedding-based dedup (uses Tier 2 `semantic.py` if available) | `scripts/dedup.py` | 1h |
| 7.2.7 | CI integration — run on PRs that touch CSVs, warn (not fail) on new duplicates | `.github/workflows/ci.yml` | 0.5h |
| 7.2.8 | Allowlist — `dedup-allowlist.yml` for intentional overlaps (e.g. Redis appears in both cache and database) | `dedup-allowlist.yml` (new) | 0.5h |
| 7.2.9 | Tests — known duplicates detected, allowlisted pairs skipped, threshold works | `tests/test_dedup.py` (new) | 2h |

### Acceptance Criteria

- [ ] `backendpro dedup` scans all domains, reports pairs above 0.85 similarity
- [ ] `backendpro dedup --domain database` scans only that domain
- [ ] `backendpro dedup --cross-domain` finds cross-domain near-duplicates
- [ ] `--threshold 0.7` lowers the bar (more pairs flagged)
- [ ] `dedup-allowlist.yml` suppresses known intentional overlaps
- [ ] `--json` output for CI consumption
- [ ] CI warns on new duplicates in PR diff
- [ ] `pytest tests/test_dedup.py` passes

### Verification

```bash
backendpro dedup
backendpro dedup --domain pattern
backendpro dedup --cross-domain --threshold 0.7
backendpro dedup --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['duplicates']), 'potential duplicates')"
pytest tests/test_dedup.py -v
```

---

## Task 7.3 — Coverage Report

### Description

`backendpro coverage` shows which subdomains are thin and which are well-covered.
Drives contribution by making gaps visible.

**Output:**
```
## Coverage Report

### messaging (12 rows)
  ✅ Distributed log: 3 rows (Kafka, Redpanda, Pulsar)
  ✅ Queue: 3 rows (RabbitMQ, SQS, ActiveMQ)
  ⚠️  Schema registry: 0 rows — consider adding
  ⚠️  Dead-letter queue: 0 rows — consider adding
  ⚠️  Event sourcing integration: 0 rows — consider adding

### database (19 rows)
  ✅ RDBMS: 4 rows
  ✅ Document: 2 rows
  ⚠️  Vector DB: 1 row — consider expanding
  ...
```

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 7.3.1 | Coverage targets manifest — `coverage-targets.yml` listing expected categories per domain | `coverage-targets.yml` (new) | 2h |
| 7.3.2 | `scripts/coverage.py` — scan CSVs, count rows per Category, compare against targets | `scripts/coverage.py` (new) | 2h |
| 7.3.3 | Gap detection — categories in targets with 0 rows | `scripts/coverage.py` | 0.5h |
| 7.3.4 | Thin detection — categories with <3 rows | `scripts/coverage.py` | 0.5h |
| 7.3.5 | Summary stats — total rows, rows per domain, fill rate, % with Source URL | `scripts/coverage.py` | 1h |
| 7.3.6 | CLI — `backendpro coverage [--domain D] [--json]` | `scripts/search.py` | 1h |
| 7.3.7 | Markdown badge generation — `backendpro coverage --badge` outputs shields.io URL | `scripts/coverage.py` | 0.5h |
| 7.3.8 | Tests — coverage report shape, gap detection, thin detection | `tests/test_coverage.py` (new) | 1.5h |

### Acceptance Criteria

- [ ] `backendpro coverage` prints a per-domain coverage report
- [ ] `backendpro coverage --domain messaging` shows only messaging
- [ ] Categories with 0 rows flagged as gaps (⚠️)
- [ ] Categories with <3 rows flagged as thin
- [ ] Summary includes: total rows, domains, avg rows/domain, % with Source URL
- [ ] `--json` produces structured output for dashboards
- [ ] `--badge` generates a shields.io badge URL
- [ ] `coverage-targets.yml` defines expected categories for ≥10 domains
- [ ] `pytest tests/test_coverage.py` passes

### Verification

```bash
backendpro coverage
backendpro coverage --domain messaging
backendpro coverage --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary'])"
backendpro coverage --badge
pytest tests/test_coverage.py -v
```

---

## Dependency Graph

```
┌──────────────────────┐
│ 7.1 Golden queries   │ ← Start first (guards everything else)
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    ▼              ▼
┌──────────┐  ┌──────────┐
│ 7.2 Dedup│  │ 7.3 Cover│ ← Both independent, can be parallel
│          │  │ age      │
└──────────┘  └──────────┘
```

- **7.1** should land first — it guards retrieval quality for everything
  that follows (including Tier 4 KB expansion).
- **7.2** and **7.3** are independent of each other.

### Recommended implementation order

1. **Phase A**: 7.1 (golden queries) — the quality guardrail
2. **Phase B** (parallel): 7.2 (dedup) + 7.3 (coverage)

---

## Checkpoint Criteria

### After Phase A

- [ ] ≥150 golden query assertions in `tests/golden-queries.yml`
- [ ] `pytest tests/test_golden_queries.py` passes
- [ ] CI blocks PRs that break golden queries
- [ ] Failure output is actionable (shows expected vs actual)

### After Phase B (Tier 7 complete)

- [ ] `backendpro dedup` detects near-duplicates with configurable threshold
- [ ] `backendpro coverage` reports gaps and thin categories
- [ ] `coverage-targets.yml` defines expected categories for ≥10 domains
- [ ] `dedup-allowlist.yml` suppresses known intentional overlaps
- [ ] ≥25 new test cases total for Tier 7
- [ ] `ruff check src tests` clean
- [ ] `backendpro-validate` passes
- [ ] README updated with quality engineering section
- [ ] CHANGELOG entry

---

## Files to Create / Modify

| Action | File |
|--------|------|
| **Create** | `tests/golden-queries.yml` |
| **Create** | `tests/test_golden_queries.py` |
| **Create** | `src/backend-pro-max/scripts/dedup.py` |
| **Create** | `src/backend-pro-max/scripts/coverage.py` |
| **Create** | `dedup-allowlist.yml` |
| **Create** | `coverage-targets.yml` |
| **Create** | `tests/test_dedup.py` |
| **Create** | `tests/test_coverage.py` |
| **Modify** | `src/backend-pro-max/scripts/search.py` (`dedup`, `coverage` subcommands) |
| **Modify** | `.github/workflows/ci.yml` (golden queries + dedup warning) |
| **Modify** | `pyproject.toml` (package-data for YAML files if bundled) |
| **Modify** | `README.md`, `CHANGELOG.md` |

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Golden queries are brittle — any row change breaks them | Use `expected_top` as a set (any of these in top-N), not exact rank. Allow `min_score` as a softer check. Mark fragile queries with `notes` for context. |
| 200+ golden queries slow down CI | BM25 with mtime cache is sub-ms per query. 200 queries < 1 second total. Not a concern. |
| BM25 self-similarity for dedup has low recall on conceptual duplicates | It catches keyword-level duplicates (the most common kind). Embedding-based dedup behind `[semantic]` extra catches conceptual duplicates. Default is conservative — better to miss a duplicate than false-positive. |
| Pairwise comparison is O(n²) per domain | With ~60 rows/domain max (Tier 4), that's 3600 comparisons — trivial. Cross-domain is larger but still manageable (<500k pairs for 700 rows). Cache results. |
| Coverage targets become stale as KB evolves | `coverage-targets.yml` is a living document. PRs that add new categories should update it. CI warns (not fails) on missing targets. |
| YAML parsing requires `pyyaml` — not stdlib | Use `json` format instead, or detect `pyyaml` presence with stdlib fallback to a simple line-based parser. Alternatively, add `pyyaml` to `[dev]` extra (already used by pytest ecosystem). Golden queries only run in dev/CI where `[dev]` is installed. |
| Golden queries for Tier 1 commands (decide, design) are hard to write | Scope golden queries to search/compare only (deterministic). Decision commands are tested via their own unit tests (Tier 1 test plan). |
