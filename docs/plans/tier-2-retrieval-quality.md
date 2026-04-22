# Tier 2 — Retrieval Quality

> BM25 alone won't scale to 1000s of rows. Upgrade the retrieval pipeline
> with intent classification, optional semantic search, and anti-pattern coverage.

**Status:** ✅ Complete
**Branch:** `feat/tier-2-retrieval-quality`
**Depends on:** Tier 1 (constraint columns provide structured metadata that re-ranking can exploit)

---

## Overview

Four features that take retrieval from "keyword match" to "understands what you're asking":

| # | Feature | CLI / API surface | Complexity | Stdlib-safe? |
|---|---------|-------------------|------------|-------------|
| 2.1 | Query intent classifier | Internal — routes to output templates | Medium | ✅ Yes |
| 2.2 | Hybrid retrieval: BM25 + embeddings | `pip install backendpro[semantic]` | High | ✅ Core stays stdlib; embeddings behind optional extra |
| 2.3 | Re-ranking with cross-encoder | `pip install backendpro[rerank]` | Medium | ✅ Optional extra |
| 2.4 | Anti-patterns CSV | `backendpro "distributed monolith" --domain antipattern` | Low–Medium | ✅ Yes |

**Key constraint:** The default install (`pip install backendpro`) stays **zero-dependency**.
Semantic features live behind optional extras and feature flags.

---

## Architecture Decisions

1. **Intent classifier lives in `core.py`** — it's a lightweight regex/keyword
   classifier (no ML), invoked before every search to pick an output template.
   New function: `classify_intent(query) → Intent`.
2. **Embedding index is a new module: `scripts/semantic.py`** — imports
   `sentence_transformers` only when present. Falls back to BM25 gracefully.
   The public API (`search()`, `search_all()`) gains an `engine="bm25"|"hybrid"|"semantic"`
   kwarg; default stays `"bm25"`.
3. **Re-ranker is a thin wrapper in `scripts/rerank.py`** — takes BM25 top-K,
   re-scores with a cross-encoder. Only imported when the extra is installed.
4. **Anti-patterns is a standard domain CSV** — registered in `CSV_CONFIG` like
   every other domain. No new machinery needed beyond the CSV + keyword bag.
5. **Output templates** — new module `scripts/templates.py` with per-intent
   formatters (definition, comparison, troubleshoot, design, migration, incident).
   `search.py` formatters delegate to the appropriate template based on intent.

---

## Task 2.1 — Query Intent Classifier

### Description

Classify every incoming query into one of these intents so the output is
structured for the user's actual need, not a generic row dump:

| Intent | Example queries | Output shape |
|--------|----------------|-------------|
| `definition` | "what is a saga", "explain CQRS" | Name → Definition → When to Use → When NOT → Related |
| `comparison` | "kafka vs rabbitmq", "redis or memcached" | (Already handled by `compare`, but auto-detected now) |
| `troubleshoot` | "kafka consumer lag", "connection pool exhausted" | Symptom → Root Cause → Fix → Verify |
| `design` | "design a URL shortener" | (Routed to Tier 1 `design` command) |
| `migration` | "migrate from monolith", "move from MySQL to Postgres" | From → To → Strategy → Risks → Rollback |
| `incident` | "database failover", "broker outage" | Symptom → Impact → Mitigation → Postmortem checklist |
| `general` | everything else | Current default output |

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 2.1.1 | Define `Intent` enum + `classify_intent()` — keyword/regex classifier | `scripts/core.py` | 2h |
| 2.1.2 | Intent-specific output templates — one formatter per intent | `scripts/templates.py` (new) | 3h |
| 2.1.3 | Wire `format_output()` to delegate to intent-based template | `scripts/search.py` | 1h |
| 2.1.4 | Add `--intent` CLI flag to force a specific intent (override auto) | `scripts/search.py` | 0.5h |
| 2.1.5 | Surface detected intent in JSON output (`"intent": "troubleshoot"`) | `scripts/search.py` | 0.5h |
| 2.1.6 | REPL shows detected intent: `bpm> kafka lag` → `[troubleshoot] ...` | `scripts/search.py` | 0.5h |
| 2.1.7 | Tests — intent classification accuracy + template output correctness | `tests/test_intent.py` (new) | 2h |

### Acceptance Criteria

- [ ] `classify_intent("what is a saga")` → `Intent.DEFINITION`
- [ ] `classify_intent("kafka consumer lag fix")` → `Intent.TROUBLESHOOT`
- [ ] `classify_intent("migrate from mysql to postgres")` → `Intent.MIGRATION`
- [ ] `classify_intent("kafka vs rabbitmq")` → `Intent.COMPARISON`
- [ ] Output for troubleshoot queries shows Symptom → Root Cause → Fix → Verify structure
- [ ] `--intent troubleshoot` overrides auto-detection
- [ ] JSON output includes `"intent"` field
- [ ] Existing tests unbroken (general intent = backward-compatible output)
- [ ] `pytest tests/test_intent.py` passes with ≥20 classification assertions

### Verification

```bash
backendpro "what is a saga" --domain pattern
backendpro "kafka consumer lag" --domain messaging
backendpro "migrate from mysql to postgres" --domain database
backendpro "circuit breaker" --intent definition --domain pattern
backendpro "kafka lag" --json | python3 -c "import sys,json; print(json.load(sys.stdin)['intent'])"
pytest tests/test_intent.py -v
pytest tests/ -v  # regression
```

---

## Task 2.2 — Hybrid Retrieval (BM25 + Embeddings)

### Description

Add an **optional** semantic search path using sentence-transformers
(`all-MiniLM-L6-v2`, ~80 MB model). When installed, queries like
*"how do I avoid losing messages on broker failover?"* find rows even
when no exact keywords match. Uses **reciprocal rank fusion (RRF)** to
merge BM25 and embedding rankings.

**Install:** `pip install backendpro[semantic]` (adds `sentence-transformers` + `numpy`).
**Default:** `pip install backendpro` stays zero-dep; `engine="bm25"` is always the fallback.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 2.2.1 | `scripts/semantic.py` — lazy model loader, embed function, cosine similarity | `scripts/semantic.py` (new) | 2h |
| 2.2.2 | Embedding index builder — embed all search-column texts, cache to `.backendpro_cache/` | `scripts/semantic.py` | 2h |
| 2.2.3 | Reciprocal rank fusion — merge BM25 + embedding rankings | `scripts/semantic.py` | 1.5h |
| 2.2.4 | Wire into `_search_csv()` — `engine` kwarg: `bm25` (default) / `hybrid` / `semantic` | `scripts/core.py` | 2h |
| 2.2.5 | CLI flag `--engine hybrid\|semantic` + env var `BACKENDPRO_ENGINE` | `scripts/search.py` | 1h |
| 2.2.6 | Graceful fallback — if `sentence_transformers` not installed, warn + fall back to BM25 | `scripts/semantic.py` | 0.5h |
| 2.2.7 | `pyproject.toml` — add `[semantic]` optional extra | `pyproject.toml` | 0.5h |
| 2.2.8 | Embedding cache invalidation — mtime-based like BM25 cache | `scripts/semantic.py` | 1h |
| 2.2.9 | Tests — hybrid vs BM25 quality on 10 conceptual queries | `tests/test_semantic.py` (new) | 2h |

### Acceptance Criteria

- [ ] `pip install backendpro` still has zero dependencies
- [ ] `pip install backendpro[semantic]` installs `sentence-transformers`
- [ ] `backendpro "how to avoid losing messages on failover" --engine hybrid` returns relevant messaging rows
- [ ] BM25-only still works identically when `sentence-transformers` is not installed
- [ ] `--engine semantic` with missing package prints warning and falls back to BM25
- [ ] Embedding cache stored in `.backendpro_cache/` (gitignored), invalidated on CSV mtime change
- [ ] First query builds index (~5s), subsequent queries are sub-100ms
- [ ] `pytest tests/test_semantic.py` passes (skips if `sentence-transformers` not installed)
- [ ] Existing 37+ tests unbroken

### Verification

```bash
# Without semantic extra — should work, warn, fallback
backendpro "avoid message loss on failover" --engine hybrid

# With semantic extra
pip install -e ".[semantic]"
backendpro "avoid message loss on failover" --engine hybrid
backendpro "avoid message loss on failover" --engine semantic
backendpro "avoid message loss on failover"  # still BM25 by default

pytest tests/test_semantic.py -v
pytest tests/ -v  # regression
```

---

## Task 2.3 — Re-ranking with Cross-Encoder (Optional)

### Description

For ambiguous queries, BM25 top-20 can be noisy. A tiny cross-encoder
(`cross-encoder/ms-marco-MiniLM-L-6-v2`, ~80 MB) re-scores pairs
(query, row_text) and dramatically improves precision for the top 5.

**Install:** `pip install backendpro[rerank]` (adds `sentence-transformers`).
Can be combined: `pip install backendpro[semantic,rerank]`.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 2.3.1 | `scripts/rerank.py` — lazy cross-encoder loader, `rerank(query, rows, top_k)` | `scripts/rerank.py` (new) | 1.5h |
| 2.3.2 | Wire into `_search_csv()` — when reranker available, BM25 top-20 → rerank → top-N | `scripts/core.py` | 1.5h |
| 2.3.3 | CLI flag `--rerank` (boolean, only effective when extra is installed) | `scripts/search.py` | 0.5h |
| 2.3.4 | `pyproject.toml` — add `[rerank]` optional extra | `pyproject.toml` | 0.5h |
| 2.3.5 | Graceful fallback — warn + skip reranking if not installed | `scripts/rerank.py` | 0.5h |
| 2.3.6 | Tests — verify reranking improves a known ambiguous query | `tests/test_rerank.py` (new) | 1.5h |

### Acceptance Criteria

- [ ] `pip install backendpro[rerank]` installs cross-encoder deps
- [ ] `backendpro "partial failure handling" --rerank` re-orders BM25 top-20
- [ ] Without `[rerank]` installed, `--rerank` prints info message and returns BM25 results
- [ ] Reranker adds `_rerank_score` to each result in JSON mode
- [ ] Latency: reranking top-20 completes in <500ms on CPU
- [ ] `pytest tests/test_rerank.py` passes (skips if deps not installed)

### Verification

```bash
pip install -e ".[rerank]"
backendpro "partial failure handling" --domain pattern --rerank
backendpro "partial failure handling" --domain pattern --rerank --json | python3 -c "import sys,json; [print(r.get('_rerank_score')) for r in json.load(sys.stdin)['results']]"
pytest tests/test_rerank.py -v
```

---

## Task 2.4 — Anti-Patterns CSV

### Description

A dedicated `anti-patterns.csv` domain for the things staff engineers spend
half their day saying "don't do that" about. This is a standard domain CSV —
no new engine code needed, just data + registration.

**Column shape:**

```
Name,Category,Symptom,Root Cause,Why It's Tempting,Fix,Related Patterns,Severity,Keywords,Last Updated
```

**Initial rows (minimum 15):**

| Name | Category |
|------|----------|
| Distributed Monolith | Architecture |
| Shared Database Integration | Integration |
| God Service | Architecture |
| Sync-over-Async | Performance |
| Dual Writes | Consistency |
| Chatty Microservices | Performance |
| Unbounded Retry | Reliability |
| Missing Idempotency Key | Reliability |
| Premature Microservices | Architecture |
| Log-and-Throw | Observability |
| Generic Error Swallowing | Reliability |
| N+1 Query | Performance |
| Secrets in Environment Variables | Security |
| Time-Based Cache Invalidation Only | Cache |
| Polling Instead of Events | Messaging |

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 2.4.1 | Create `data/anti-patterns.csv` with ≥15 rows | `data/anti-patterns.csv` (new) | 3h |
| 2.4.2 | Register in `CSV_CONFIG` + `_DOMAIN_KEYWORDS` | `scripts/core.py` | 0.5h |
| 2.4.3 | Validator schema support | `scripts/validate.py` | 0.5h |
| 2.4.4 | Smoke test + golden query assertions | `tests/test_antipatterns.py` (new) | 1h |

### Acceptance Criteria

- [ ] `backendpro --list` shows `antipattern` domain
- [ ] `backendpro "distributed monolith"` auto-detects `antipattern` domain (or at least returns relevant rows)
- [ ] `backendpro "dual writes" --domain antipattern` returns the row with Symptom/Root Cause/Fix
- [ ] `backendpro-validate` passes with the new CSV
- [ ] Each row has: Name, Category, Symptom, Root Cause, Fix, Severity, Last Updated
- [ ] ≥15 rows in initial CSV
- [ ] `pytest tests/test_antipatterns.py` passes

### Verification

```bash
backendpro --list | grep antipattern
backendpro "distributed monolith"
backendpro "dual writes" --domain antipattern
backendpro "unbounded retry" --domain antipattern
backendpro-validate
pytest tests/test_antipatterns.py -v
pytest tests/ -v  # regression
```

---

## Dependency Graph

```
┌──────────────────┐
│ 2.4 Anti-patterns│  ← Independent, can start immediately
│ (data only)      │
└──────────────────┘

┌──────────────────┐
│ 2.1 Intent       │  ← Independent, can start immediately
│ classifier       │
└────────┬─────────┘
         │ (output templates consume intent)
         ▼
┌──────────────────┐       ┌──────────────────┐
│ 2.2 Hybrid       │──────►│ 2.3 Re-ranking   │
│ retrieval        │       │ (optional layer   │
│ (BM25 + embed)   │       │  on top of 2.2)  │
└──────────────────┘       └──────────────────┘
```

- **2.4** and **2.1** are fully independent — start both in parallel.
- **2.2** can start in parallel with 2.1 but is higher effort.
- **2.3** depends on 2.2 (re-ranking operates on the retrieval pipeline).

### Recommended implementation order

1. **Phase A** (parallel): 2.4 (anti-patterns CSV) + 2.1 (intent classifier)
2. **Phase B**: 2.2 (hybrid retrieval)
3. **Phase C**: 2.3 (re-ranking on top of 2.2)

---

## Checkpoint Criteria

### After Phase A

- [ ] `antipattern` domain queryable, ≥15 rows, validator passes
- [ ] Intent classifier auto-routes queries to correct output template
- [ ] JSON output includes `"intent"` field
- [ ] All existing tests pass + ≥25 new test cases across `test_intent.py` and `test_antipatterns.py`

### After Phase B

- [ ] `pip install backendpro[semantic]` enables hybrid search
- [ ] Default install unchanged (zero-dep BM25)
- [ ] Conceptual queries ("how to avoid message loss") find relevant rows via embeddings
- [ ] Embedding cache works (sub-100ms repeat queries)
- [ ] ≥10 new test cases in `test_semantic.py`

### After Phase C (Tier 2 complete)

- [ ] `--rerank` available for precision boost
- [ ] Full pipeline: intent → hybrid retrieval → rerank → intent-formatted output
- [ ] ≥40 new test cases total for Tier 2
- [ ] `ruff check src tests` clean
- [ ] `backendpro-validate` passes
- [ ] README updated with retrieval quality features
- [ ] CHANGELOG entry

---

## Files to Create / Modify

| Action | File |
|--------|------|
| **Create** | `src/backend-pro-max/data/anti-patterns.csv` |
| **Create** | `src/backend-pro-max/scripts/templates.py` |
| **Create** | `src/backend-pro-max/scripts/semantic.py` |
| **Create** | `src/backend-pro-max/scripts/rerank.py` |
| **Create** | `tests/test_intent.py` |
| **Create** | `tests/test_antipatterns.py` |
| **Create** | `tests/test_semantic.py` |
| **Create** | `tests/test_rerank.py` |
| **Create** | `.backendpro_cache/` (gitignored, runtime) |
| **Modify** | `src/backend-pro-max/scripts/core.py` (Intent enum, classify_intent, engine kwarg, antipattern registration) |
| **Modify** | `src/backend-pro-max/scripts/search.py` (--engine, --rerank, --intent flags, template delegation) |
| **Modify** | `src/backend-pro-max/scripts/validate.py` (antipattern schema) |
| **Modify** | `pyproject.toml` ([semantic], [rerank] extras) |
| **Modify** | `.gitignore` (.backendpro_cache/) |
| **Modify** | `README.md`, `CHANGELOG.md` |

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Intent classifier misroutes queries → wrong output template | Default to `general` intent on low confidence. `--intent` flag lets user override. Classification is conservative (high-precision keywords). |
| `sentence-transformers` adds 500MB+ of transitive deps | Document clearly: this is opt-in. Core stays stdlib. CI tests both with and without the extra. |
| Embedding index build time (~5s) annoys interactive users | Cache to disk (`.backendpro_cache/`), invalidate on mtime. First-run message: "Building semantic index…" |
| Cross-encoder adds latency (~200-500ms) | Only re-rank top-20, not full corpus. `--rerank` is explicit opt-in, never default. |
| Anti-patterns CSV rows are subjective | Each row cites a source (blog, postmortem, official docs). Severity is `critical\|warning\|info`. PR review required for new anti-pattern rows. |
| Model download requires internet on first use | Document in README. Provide `backendpro index --build` command to pre-build cache. CI seeds the cache in test fixtures. |
| Feature flag complexity (3 engines × rerank × intent) | Engine selection is a single `engine` kwarg that flows through one code path. Rerank is a post-processing step. Intent is orthogonal (formatting only). No combinatorial explosion. |
