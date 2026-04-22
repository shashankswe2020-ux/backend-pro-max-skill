# Tier 4 — Knowledge Depth

> Where staff engineers will find you lacking. Currently ~510 lines across 32 CSVs
> (≈12–22 rows per domain, ≈12–17 rows per stack). Expand strategically — both
> new domains and new columns on existing data.

**Status:** 🔲 Not started
**Branch:** `feat/tier-4-knowledge-depth` (to be created from `main`)
**Depends on:** Tier 1 (constraint columns established), Tier 3 (citation tokens give stable row IDs)

---

## Overview

| # | Feature | Type | Complexity |
|---|---------|------|------------|
| 4.1 | Add high-value domains (12 new CSVs) | New data | High (volume) |
| 4.2 | Numerical baselines column | Column addition to existing CSVs | Medium |
| 4.3 | "Latency numbers every engineer should know" dataset | New queryable CSV | Low |
| 4.4 | Capacity calculators (`backendpro calc`) | New command | Medium |

**Key constraint:** Every new row must have a `Last Updated` date and a
`Source URL` (Tier 5 will enforce this in CI — start the discipline now).

---

## Current State (baseline)

| CSV | Rows (excl. header) | Depth assessment |
|-----|---------------------|------------------|
| architecture.csv | ~15 | Thin — missing event mesh, cell-based, data mesh |
| api.csv | ~10 | Thin — missing versioning strategies, pagination patterns |
| auth.csv | ~12 | OK for breadth, missing device auth, token rotation |
| cache.csv | ~10 | Thin — missing multi-tier, distributed cache patterns |
| cicd.csv | ~14 | OK |
| cloud.csv | ~11 | Thin — missing edge, serverless nuances, multi-cloud |
| consistency.csv | ~12 | Good conceptual coverage |
| containers.csv | ~12 | OK |
| data-engineering.csv | ~16 | OK |
| databases.csv | ~19 | Good |
| iac.csv | ~12 | OK |
| languages.csv | ~12 | OK |
| messaging.csv | ~12 | Thin — missing schema registry, dead-letter patterns |
| observability.csv | ~14 | OK |
| patterns.csv | ~22 | Best-covered domain |
| performance.csv | ~17 | OK |
| reliability.csv | ~18 | Good |
| scaling.csv | ~17 | OK |
| security.csv | ~18 | OK |
| testing.csv | ~13 | Thin — missing contract testing details, chaos eng |

**Total domain rows:** ~290 | **Total stack rows:** ~180 | **Grand total:** ~470

---

## Task 4.1 — Add High-Value Domains

### Description

Add 12 new domain CSVs. Each domain addresses a gap that staff engineers hit
weekly. Prioritised by how often the topic comes up in system design reviews,
ADRs, and incident retros.

### New Domains (priority order)

| # | Domain key | CSV file | Column shape | Min rows | Why staff engineers need it |
|---|-----------|----------|-------------|----------|---------------------------|
| A | `cost` | `cost.csv` | Name, Category, Cloud, Service, Cost Driver, Mitigation, Order of Magnitude, Gotcha, Source URL, Last Updated | 20 | Egress, cross-AZ, NAT, DynamoDB hot partitions, S3 request pricing, GPU economics |
| B | `migration` | `migration.csv` | Name, Category, Strategy, From, To, Risk, Rollback Plan, Duration Estimate, Gotcha, Related Patterns, Source URL, Last Updated | 15 | Strangler fig, dual-write, expand-contract schema, zero-downtime cutover |
| C | `incident` | `incident.csv` | Name, Category, Severity, Symptom, Root Cause, Mitigation, Communication Template, Postmortem Checklist, Source URL, Last Updated | 15 | IMOC roles, comms templates, severity matrices, blameless culture |
| D | `capacity` | `capacity.csv` | Name, Category, Formula, Inputs, Example Calculation, Rule of Thumb, Gotcha, Source URL, Last Updated | 15 | Little's Law, USE/RED/USL, headroom math, queue theory |
| E | `compliance` | `compliance.csv` | Name, Standard, Category, Engineering Requirement, Verification Method, Gotcha, Penalty, Source URL, Last Updated | 15 | SOC2/HIPAA/PCI/GDPR engineering checklists |
| F | `multi-tenant` | `multi-tenant.csv` | Name, Category, Strategy, Isolation Level, Strengths, Weaknesses, When to Use, Gotcha, Source URL, Last Updated | 12 | Pool vs silo, noisy neighbor, per-tenant rate limits |
| G | `release` | `release.csv` | Name, Category, Strategy, Risk, Rollback Time, Blast Radius, Tooling, Gotcha, Source URL, Last Updated | 15 | Feature flags, canary, blue/green, progressive delivery |
| H | `ml-platform` | `ml-platform.csv` | Name, Category, Use Case, Strengths, Weaknesses, Alternatives, Gotcha, Source URL, Last Updated | 12 | Feature stores, model registries, online/offline skew, RAG ops |
| I | `edge` | `edge.csv` | Name, Category, Runtime, Use Case, Strengths, Weaknesses, Consistency Model, Gotcha, Source URL, Last Updated | 10 | Cloudflare Workers, Fastly Compute, WASI, edge KV |
| J | `mobile-backend` | `mobile-backend.csv` | Name, Category, Pattern, Use Case, Strengths, Weaknesses, Gotcha, Source URL, Last Updated | 10 | BFF, offline-first sync, push delivery, CDN for APIs |
| K | `api-contract` | `api-contract.csv` | Name, Category, Strategy, Tooling, Strengths, Weaknesses, When to Use, Gotcha, Source URL, Last Updated | 12 | OpenAPI codegen, GraphQL federation, BFF, schema evolution |
| L | `interview` | `interview.csv` | Name, Category, Level, Key Signals, Common Mistakes, Evaluation Criteria, Source URL, Last Updated | 12 | System design rubrics, staff+ behavioral signals |

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 4.1.1 | Create `cost.csv` (≥20 rows) + register in `CSV_CONFIG` + `_DOMAIN_KEYWORDS` | `data/cost.csv`, `scripts/core.py` | 3h |
| 4.1.2 | Create `migration.csv` (≥15 rows) + register | `data/migration.csv`, `scripts/core.py` | 2.5h |
| 4.1.3 | Create `incident.csv` (≥15 rows) + register | `data/incident.csv`, `scripts/core.py` | 2.5h |
| 4.1.4 | Create `capacity.csv` (≥15 rows) + register | `data/capacity.csv`, `scripts/core.py` | 2.5h |
| 4.1.5 | Create `compliance.csv` (≥15 rows) + register | `data/compliance.csv`, `scripts/core.py` | 2.5h |
| 4.1.6 | Create `multi-tenant.csv` (≥12 rows) + register | `data/multi-tenant.csv`, `scripts/core.py` | 2h |
| 4.1.7 | Create `release.csv` (≥15 rows) + register | `data/release.csv`, `scripts/core.py` | 2h |
| 4.1.8 | Create `ml-platform.csv` (≥12 rows) + register | `data/ml-platform.csv`, `scripts/core.py` | 2h |
| 4.1.9 | Create `edge.csv` (≥10 rows) + register | `data/edge.csv`, `scripts/core.py` | 1.5h |
| 4.1.10 | Create `mobile-backend.csv` (≥10 rows) + register | `data/mobile-backend.csv`, `scripts/core.py` | 1.5h |
| 4.1.11 | Create `api-contract.csv` (≥12 rows) + register | `data/api-contract.csv`, `scripts/core.py` | 2h |
| 4.1.12 | Create `interview.csv` (≥12 rows) + register | `data/interview.csv`, `scripts/core.py` | 2h |
| 4.1.13 | Update validator for all 12 new schemas | `scripts/validate.py` | 1h |
| 4.1.14 | Smoke tests for all 12 new domains | `tests/test_new_domains.py` (new) | 2h |
| 4.1.15 | Update `--list` output, README domain table, SKILL.md | `README.md`, templates | 1h |

### Acceptance Criteria

- [ ] `backendpro --list` shows 32 domains (20 existing + 12 new)
- [ ] Each new domain has ≥ its minimum row count
- [ ] Every new row has `Source URL` and `Last Updated` columns populated
- [ ] `backendpro-validate` passes for all 32 domains
- [ ] Auto-detection works: `backendpro "cross-AZ data transfer cost"` → `cost` domain
- [ ] `backendpro "strangler fig" --domain migration` returns relevant rows
- [ ] `pytest tests/test_new_domains.py` passes (≥24 assertions, 2 per domain)

### Verification

```bash
backendpro --list | wc -l  # should show 32 domains + 12 stacks
backendpro "egress cost AWS" --domain cost
backendpro "strangler fig" --domain migration
backendpro "severity matrix" --domain incident
backendpro "Little's Law" --domain capacity
backendpro "SOC2 logging" --domain compliance
backendpro "noisy neighbor" --domain multi-tenant
backendpro "canary deployment" --domain release
backendpro "feature store" --domain ml-platform
backendpro "cloudflare workers" --domain edge
backendpro "BFF pattern" --domain mobile-backend
backendpro "schema evolution" --domain api-contract
backendpro "system design rubric" --domain interview
backendpro-validate
pytest tests/test_new_domains.py -v
```

---

## Task 4.2 — Numerical Baselines Column

### Description

Add a `Benchmarks` column to existing CSVs with order-of-magnitude numbers.
Staff engineers reason in numbers, not vibes. Examples:

| Domain | Row | Benchmarks value |
|--------|-----|-----------------|
| database | PostgreSQL | `~5k tps/core OLTP; ~1ms LAN read; WAL: ~100MB/min at load` |
| database | Redis | `~100k ops/sec/core; <1ms p99; 1GB ≈ 1M 1KB keys` |
| messaging | Kafka | `~1MB/s/partition; ~2ms p50 produce; 1 broker ≈ 10k partitions safe` |
| cache | Redis (cache) | `~100k ops/sec; 6.4μs avg latency; cluster: 1000 nodes max` |
| scaling | Consistent Hashing | `~O(K/N) keys moved on node add; vnodes: 100-256 per node` |

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 4.2.1 | Add `Benchmarks` column to `databases.csv` (all rows) | `data/databases.csv` | 2h |
| 4.2.2 | Add `Benchmarks` to `messaging.csv` | `data/messaging.csv` | 1h |
| 4.2.3 | Add `Benchmarks` to `cache.csv` | `data/cache.csv` | 1h |
| 4.2.4 | Add `Benchmarks` to `performance.csv` | `data/performance.csv` | 1h |
| 4.2.5 | Add `Benchmarks` to `scaling.csv` | `data/scaling.csv` | 1h |
| 4.2.6 | Add `Benchmarks` to `cloud.csv` (service limits / pricing) | `data/cloud.csv` | 1.5h |
| 4.2.7 | Update `CSV_CONFIG` output_cols for all 6 CSVs | `scripts/core.py` | 0.5h |
| 4.2.8 | Validator tolerance for optional `Benchmarks` column | `scripts/validate.py` | 0.5h |
| 4.2.9 | Tests — verify Benchmarks column present and non-empty on ≥80% of rows | `tests/test_benchmarks.py` (new) | 1h |

### Acceptance Criteria

- [ ] `Benchmarks` column present in databases, messaging, cache, performance, scaling, cloud CSVs
- [ ] ≥80% of rows in those CSVs have a non-empty `Benchmarks` value
- [ ] `backendpro "postgres" --domain database --json` includes `Benchmarks` in output
- [ ] `backendpro-validate` passes
- [ ] Numbers are sourced (each should reference official docs or benchmarks in the row's Source URL)
- [ ] `pytest tests/test_benchmarks.py` passes

### Verification

```bash
backendpro "redis" --domain database --json | python3 -c "import sys,json; print(json.load(sys.stdin)['results'][0].get('Benchmarks','MISSING'))"
backendpro "kafka" --domain messaging
backendpro-validate
pytest tests/test_benchmarks.py -v
```

---

## Task 4.3 — Latency Numbers Dataset

### Description

A dedicated queryable CSV: Jeff Dean's "latency numbers every programmer
should know" — updated for 2025 hardware (NVMe, RDMA, modern NICs,
cross-region, cloud-specific).

**Column shape:**
```
Operation,Category,Latency,Order of Magnitude,Hardware Era,Notes,Source URL,Last Updated
```

**Initial rows (≥25):**

| Operation | Latency |
|-----------|---------|
| L1 cache reference | 1 ns |
| L2 cache reference | 4 ns |
| Branch mispredict | 3 ns |
| Mutex lock/unlock | 17 ns |
| Main memory reference | 100 ns |
| Compress 1KB (Snappy) | 2 μs |
| Send 2KB over 1Gbps NIC | 16 μs |
| NVMe SSD random read | 10 μs |
| NVMe SSD sequential read 1MB | 50 μs |
| RDMA round trip | 2 μs |
| Same-AZ network round trip | 0.5 ms |
| Cross-AZ network round trip | 1 ms |
| SSD random read (SATA) | 100 μs |
| HDD seek | 4 ms |
| Cross-region round trip (US-EU) | 70 ms |
| Cross-region round trip (US-Asia) | 150 ms |
| TLS handshake | 5 ms |
| Redis GET (localhost) | 0.1 ms |
| PostgreSQL simple query | 0.5 ms |
| Kafka produce ack (acks=1) | 2 ms |
| S3 GET (same region) | 10-50 ms |
| DynamoDB GetItem | 5 ms |
| DNS resolution (cold) | 20-120 ms |
| TCP three-way handshake (same AZ) | 0.5 ms |
| Context switch (Linux) | 3-5 μs |

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 4.3.1 | Create `data/latency-numbers.csv` with ≥25 rows | `data/latency-numbers.csv` (new) | 2h |
| 4.3.2 | Register as `latency` domain in `CSV_CONFIG` + keywords | `scripts/core.py` | 0.5h |
| 4.3.3 | Special formatter — sorted by latency magnitude | `scripts/search.py` | 1h |
| 4.3.4 | `backendpro latency` shortcut (no query needed — lists all) | `scripts/search.py` | 0.5h |
| 4.3.5 | Tests | `tests/test_latency_numbers.py` (new) | 1h |

### Acceptance Criteria

- [ ] `backendpro latency` prints all rows sorted by latency magnitude
- [ ] `backendpro "NVMe" --domain latency` finds the NVMe rows
- [ ] `backendpro "cross region" --domain latency` returns relevant rows
- [ ] Each row has `Source URL` and `Last Updated`
- [ ] ≥25 rows covering CPU → memory → disk → network → cloud services
- [ ] `backendpro-validate` passes
- [ ] `pytest tests/test_latency_numbers.py` passes

### Verification

```bash
backendpro latency
backendpro "NVMe" --domain latency
backendpro "cross region" --domain latency
backendpro-validate
pytest tests/test_latency_numbers.py -v
```

---

## Task 4.4 — Capacity Calculators

### Description

`backendpro calc` subcommand for back-of-envelope capacity math. Staff
engineers do this on whiteboards daily — make it instant.

**Calculators:**

| Calculator | Command | Formula |
|-----------|---------|---------|
| QPS from daily | `backendpro calc qps --daily 100M` | daily / 86400, × peak factor |
| Storage | `backendpro calc storage --rows 1B --row-bytes 200` | rows × bytes × replication |
| Bandwidth | `backendpro calc bandwidth --qps 5000 --payload-kb 2` | qps × payload |
| Concurrency (Little's Law) | `backendpro calc concurrency --rps 5000 --latency-ms 50` | L = λ × W |
| Partitions (Kafka) | `backendpro calc partitions --target-throughput-mb 100 --per-partition-mb 1` | ceil(target / per) |
| Cache hit rate | `backendpro calc cache-hit --requests 1M --cache-size 100k --zipf 0.8` | Zipfian estimate |
| Fanout | `backendpro calc fanout --followers 1000 --posts-per-day 10 --fanout-on write` | total writes/day |

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 4.4.1 | `scripts/calc.py` — calculator registry + base helpers | `scripts/calc.py` (new) | 1.5h |
| 4.4.2 | QPS calculator | `scripts/calc.py` | 0.5h |
| 4.4.3 | Storage calculator | `scripts/calc.py` | 0.5h |
| 4.4.4 | Bandwidth calculator | `scripts/calc.py` | 0.5h |
| 4.4.5 | Concurrency (Little's Law) calculator | `scripts/calc.py` | 0.5h |
| 4.4.6 | Partitions calculator | `scripts/calc.py` | 0.5h |
| 4.4.7 | Cache hit rate estimator | `scripts/calc.py` | 1h |
| 4.4.8 | Fanout calculator | `scripts/calc.py` | 0.5h |
| 4.4.9 | Markdown + JSON formatters for calc output | `scripts/calc.py` | 1h |
| 4.4.10 | CLI integration — `backendpro calc <type> [--flags]` + `--json` | `scripts/search.py` | 1h |
| 4.4.11 | REPL shortcut `/calc` | `scripts/search.py` | 0.5h |
| 4.4.12 | Tests — known inputs → expected outputs for all 7 calculators | `tests/test_calc.py` (new) | 2h |

### Acceptance Criteria

- [ ] `backendpro calc qps --daily 100000000` → `~1,157 QPS avg, ~3,472 QPS peak (3x)`
- [ ] `backendpro calc storage --rows 1000000000 --row-bytes 200` → `~200 GB raw, ~600 GB with 3x replication`
- [ ] `backendpro calc concurrency --rps 5000 --latency-ms 50` → `250 concurrent requests (Little's Law: L = 5000 × 0.05)`
- [ ] All calculators support `--json` output
- [ ] `/calc qps --daily 100M` works in REPL
- [ ] `backendpro calc --help` lists all available calculators
- [ ] `pytest tests/test_calc.py` passes (≥14 test cases, 2 per calculator)

### Verification

```bash
backendpro calc qps --daily 100000000
backendpro calc storage --rows 1000000000 --row-bytes 200 --replication 3
backendpro calc concurrency --rps 5000 --latency-ms 50
backendpro calc partitions --target-throughput-mb 100 --per-partition-mb 1
backendpro calc bandwidth --qps 5000 --payload-kb 2
backendpro calc cache-hit --requests 1000000 --cache-size 100000
backendpro calc fanout --followers 1000 --posts-per-day 10
backendpro calc qps --daily 100000000 --json
pytest tests/test_calc.py -v
```

---

## Dependency Graph

```
┌───────────────────────┐
│ 4.3 Latency numbers   │ ← Independent
└───────────────────────┘

┌───────────────────────┐
│ 4.2 Benchmarks column │ ← Independent (enriches existing CSVs)
└───────────────────────┘

┌───────────────────────┐
│ 4.1 New domains       │ ← Independent (12 CSVs, can be parallelized per-CSV)
│  A cost               │
│  B migration          │
│  ...                  │
│  L interview          │
└───────────┬───────────┘
            │ (capacity domain feeds into calc)
            ▼
┌───────────────────────┐
│ 4.4 Capacity calcs    │ ← Benefits from 4.1.D (capacity CSV for formulas)
└───────────────────────┘
```

All four tasks are largely independent. 4.1 subtasks (A–L) are fully
parallelizable — each CSV is a self-contained unit of work.

### Recommended implementation order

1. **Phase A** (parallel): 4.1 A–D (cost, migration, incident, capacity — highest value) + 4.3 (latency numbers)
2. **Phase B** (parallel): 4.1 E–H (compliance, multi-tenant, release, ml-platform) + 4.2 (benchmarks column)
3. **Phase C** (parallel): 4.1 I–L (edge, mobile-backend, api-contract, interview) + 4.4 (capacity calculators)

---

## Checkpoint Criteria

### After Phase A

- [ ] 4 new domains live (cost, migration, incident, capacity)
- [ ] Latency numbers dataset queryable
- [ ] `backendpro --list` shows 25 domains
- [ ] `backendpro-validate` passes
- [ ] ≥65 new rows added to the KB

### After Phase B

- [ ] 8 new domains live
- [ ] Benchmarks column on 6 existing CSVs
- [ ] `backendpro --list` shows 29 domains
- [ ] ≥120 new rows total

### After Phase C (Tier 4 complete)

- [ ] 12 new domains live (32 total)
- [ ] `backendpro calc` works with 7 calculators
- [ ] Latency numbers shortcut works
- [ ] Benchmarks column populated on key CSVs
- [ ] Total KB rows: ~650+ (up from ~470)
- [ ] Every new row has `Source URL` + `Last Updated`
- [ ] ≥50 new test cases for Tier 4
- [ ] `ruff check src tests` clean
- [ ] `backendpro-validate` passes for all 32 domains + 12 stacks
- [ ] README updated with new domains, calc, latency
- [ ] CHANGELOG entry

---

## Files to Create / Modify

| Action | File |
|--------|------|
| **Create** | `src/backend-pro-max/data/cost.csv` |
| **Create** | `src/backend-pro-max/data/migration.csv` |
| **Create** | `src/backend-pro-max/data/incident.csv` |
| **Create** | `src/backend-pro-max/data/capacity.csv` |
| **Create** | `src/backend-pro-max/data/compliance.csv` |
| **Create** | `src/backend-pro-max/data/multi-tenant.csv` |
| **Create** | `src/backend-pro-max/data/release.csv` |
| **Create** | `src/backend-pro-max/data/ml-platform.csv` |
| **Create** | `src/backend-pro-max/data/edge.csv` |
| **Create** | `src/backend-pro-max/data/mobile-backend.csv` |
| **Create** | `src/backend-pro-max/data/api-contract.csv` |
| **Create** | `src/backend-pro-max/data/interview.csv` |
| **Create** | `src/backend-pro-max/data/latency-numbers.csv` |
| **Create** | `src/backend-pro-max/scripts/calc.py` |
| **Create** | `tests/test_new_domains.py` |
| **Create** | `tests/test_benchmarks.py` |
| **Create** | `tests/test_latency_numbers.py` |
| **Create** | `tests/test_calc.py` |
| **Modify** | `src/backend-pro-max/scripts/core.py` (13 new CSV_CONFIG entries + keyword bags + Benchmarks in output_cols) |
| **Modify** | `src/backend-pro-max/scripts/search.py` (`calc` subcommand, `latency` shortcut, REPL `/calc`) |
| **Modify** | `src/backend-pro-max/scripts/validate.py` (13 new schemas) |
| **Modify** | `src/backend-pro-max/data/databases.csv` (Benchmarks column) |
| **Modify** | `src/backend-pro-max/data/messaging.csv` (Benchmarks column) |
| **Modify** | `src/backend-pro-max/data/cache.csv` (Benchmarks column) |
| **Modify** | `src/backend-pro-max/data/performance.csv` (Benchmarks column) |
| **Modify** | `src/backend-pro-max/data/scaling.csv` (Benchmarks column) |
| **Modify** | `src/backend-pro-max/data/cloud.csv` (Benchmarks column) |
| **Modify** | `pyproject.toml` (package-data for new CSVs) |
| **Modify** | `README.md`, `CHANGELOG.md` |

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| 12 new CSVs is a large surface area — quality may vary | Batch in 3 phases. Each phase includes validator pass + smoke tests. Review each CSV in its own PR. |
| Benchmark numbers become stale fast | Every Benchmarks cell includes the hardware era / year. `--stale` flag works on these rows too. Tier 5 auto-freshness CI will catch drift. |
| Latency numbers are famously version-dependent | Include `Hardware Era` column (e.g. "2024 NVMe Gen4", "AWS 2025"). Cite source. Users understand these are order-of-magnitude. |
| Capacity calculators could be endlessly expanded | Cap at 7 calculators for Tier 4. Community can contribute more. Each calculator is a pure function — easy to add without touching the core. |
| New domain keyword bags may conflict with existing domains | Test auto-detection for each new domain. Use specific keywords (e.g. `cost` domain uses "egress", "pricing", "finops" — not generic terms). Add disambiguation tests. |
| `interview` domain may seem off-brand | Frame as "system design evaluation" — staff engineers use this during hiring loops, leveling discussions. Keep it technical, not behavioral. |
| Source URLs may rot | Every new row must have a Source URL. Tier 5 (task 5.2) adds HTTP-200 checking in CI. Start the discipline now even without enforcement. |
