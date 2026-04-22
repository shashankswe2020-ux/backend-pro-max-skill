# Tier 5 — Trust, Verifiability, Freshness

> Staff-grade means every claim is sourced, every row is accountable, and
> contradictions are surfaced — not buried. This tier turns Backend Pro Max
> from "useful tribal knowledge" into "auditable engineering reference."

**Status:** 🔲 Not started
**Branch:** `feat/tier-5-trust-verifiability` (to be created from `main`)
**Depends on:** Tier 3 (citation tokens give stable row identifiers), Tier 4 (new CSVs already follow Source URL convention)

---

## Overview

| # | Feature | Surface | Complexity |
|---|---------|---------|------------|
| 5.1 | Source citations per row | `Source URL` + `Source Type` columns on all CSVs | High (backfill volume) |
| 5.2 | Auto-freshness CI job | Weekly GitHub Action → issues for stale/broken rows | Medium |
| 5.3 | Provenance & changelog per row | `Added By`, `Last Reviewed By`, `Version` columns | Medium |
| 5.4 | Conflict detection | `backendpro conflicts [--domain]` | Medium |

---

## Current State

| Column | CSVs that have it | CSVs that lack it |
|--------|-------------------|-------------------|
| `Last Updated` | `patterns.csv` | All other 19 domain CSVs + 12 stacks |
| `Reference` / `Source URL` | `patterns.csv` (as `Reference`) | All other 19 domain CSVs + 12 stacks |
| `Source Type` | None | All |
| `Added By` | None | All |
| `Last Reviewed By` | None | All |

**The gap is significant.** Only `patterns.csv` has dates and sources. The
rest rely on implicit trust — unacceptable at staff-engineer grade.

---

## Architecture Decisions

1. **Standardise on `Source URL`, `Source Type`, `Last Updated` as mandatory
   columns on all domain CSVs.** Stacks CSVs get `Source URL` + `Last Updated`
   (no provenance — they're guidelines, not factual claims).
2. **Validator enforced in tiers:**
   - **Phase 1 (soft):** warn on missing Source URL / Last Updated, don't fail CI.
   - **Phase 2 (hard):** fail CI on new/modified rows without Source URL + Last Updated.
   - This avoids a massive blocking backfill PR.
3. **Provenance columns (`Added By`, `Last Reviewed By`) are optional** — populated
   via a git-blame-based script, not manual entry. `Version` tracks which release
   added/changed the row.
4. **Conflict detection is a static analysis pass** over the full KB — no runtime
   cost. Runs as `backendpro conflicts` CLI command and in CI.
5. **Auto-freshness is a GitHub Action** (`.github/workflows/freshness.yml`) on a
   weekly cron. It opens GitHub issues, not PRs — humans decide what to update.

---

## Task 5.1 — Source Citations Per Row

### Description

Add `Source URL`, `Source Type`, and `Last Updated` to every domain CSV.
`Source Type` is an enum: `official-docs | paper | postmortem | engineering-blog | book | benchmark | rfc`.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 5.1.1 | Add columns to CSV headers for all 20 domain CSVs (empty values for now) | `data/*.csv` | 1h |
| 5.1.2 | Update `CSV_CONFIG` output_cols for all 20 domains | `scripts/core.py` | 1h |
| 5.1.3 | Backfill `databases.csv` — Source URL + Source Type + Last Updated for all ~19 rows | `data/databases.csv` | 3h |
| 5.1.4 | Backfill `messaging.csv` (~12 rows) | `data/messaging.csv` | 2h |
| 5.1.5 | Backfill `cache.csv` (~10 rows) | `data/cache.csv` | 1.5h |
| 5.1.6 | Backfill `reliability.csv` (~18 rows) | `data/reliability.csv` | 2.5h |
| 5.1.7 | Backfill `architecture.csv` (~15 rows) | `data/architecture.csv` | 2h |
| 5.1.8 | Backfill `performance.csv` (~17 rows) | `data/performance.csv` | 2h |
| 5.1.9 | Backfill `cloud.csv` (~11 rows) | `data/cloud.csv` | 2h |
| 5.1.10 | Backfill remaining 12 domain CSVs (api, auth, security, cicd, testing, observability, iac, container, scaling, consistency, languages, data-engineering) | `data/*.csv` | 8h |
| 5.1.11 | Backfill stacks CSVs — Source URL + Last Updated (12 stacks, ~180 rows) | `data/stacks/*.csv` | 6h |
| 5.1.12 | Normalise `patterns.csv` — rename `Reference` → `Source URL`, add `Source Type` | `data/patterns.csv`, `scripts/core.py` | 0.5h |
| 5.1.13 | Validator soft mode — warn (not fail) on missing Source URL / Last Updated | `scripts/validate.py` | 1h |
| 5.1.14 | Validator hard mode — fail CI on rows without Source URL + Last Updated (behind `--strict` flag) | `scripts/validate.py` | 1h |
| 5.1.15 | Tests — validator catches missing sources, Source Type enum check | `tests/test_validation.py` (extend) | 1.5h |

### Acceptance Criteria

- [ ] All 20 domain CSVs + 12 stack CSVs have `Source URL` and `Last Updated` columns
- [ ] All 20 domain CSVs have `Source Type` column
- [ ] ≥90% of rows in high-priority CSVs (databases, messaging, cache, reliability, patterns) have non-empty Source URL
- [ ] `backendpro-validate` passes (soft mode — warns on gaps)
- [ ] `backendpro-validate --strict` fails if any row in modified CSVs lacks Source URL + Last Updated
- [ ] `patterns.csv` `Reference` column renamed to `Source URL` (backward-compatible output key)
- [ ] Source Type values are from the allowed enum
- [ ] `pytest tests/test_validation.py` passes

### Verification

```bash
# Check column presence
head -1 src/backend-pro-max/data/databases.csv | grep -c "Source URL"
head -1 src/backend-pro-max/data/databases.csv | grep -c "Source Type"
head -1 src/backend-pro-max/data/databases.csv | grep -c "Last Updated"

# Soft validation
backendpro-validate

# Strict validation
backendpro-validate --strict

# Search includes source
backendpro "postgres" --domain database --json | python3 -c "import sys,json; r=json.load(sys.stdin)['results'][0]; print(r.get('Source URL','MISSING'), r.get('Source Type','MISSING'))"

pytest tests/test_validation.py -v
```

---

## Task 5.2 — Auto-Freshness CI Job

### Description

A weekly GitHub Action that:
1. Flags rows with `Last Updated` older than 18 months.
2. Checks `Source URL` for HTTP 200 (HEAD request, 5s timeout, 3 retries).
3. Opens a GitHub issue per domain with stale/broken rows listed.

Builds on the existing `--stale` flag and `find_stale()` function.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 5.2.1 | `scripts/freshness.py` — orchestrate stale scan + URL check across all domains | `scripts/freshness.py` (new) | 2h |
| 5.2.2 | URL checker — HEAD request, retries, timeout, report broken/redirect/ok | `scripts/freshness.py` | 1.5h |
| 5.2.3 | GitHub issue formatter — markdown body with stale rows + broken URLs per domain | `scripts/freshness.py` | 1h |
| 5.2.4 | GitHub Action workflow — weekly cron, runs freshness.py, opens issues via `gh` CLI | `.github/workflows/freshness.yml` (new) | 1.5h |
| 5.2.5 | `--check-urls` flag on `backendpro-validate` for local use | `scripts/validate.py` | 1h |
| 5.2.6 | Deduplication — don't open a new issue if one already exists for the same domain | `scripts/freshness.py` | 1h |
| 5.2.7 | Tests — mock URL checks, stale detection, issue body formatting | `tests/test_freshness.py` (new) | 2h |

### Acceptance Criteria

- [ ] `.github/workflows/freshness.yml` runs weekly on cron (`0 9 * * 1`)
- [ ] Scans all domains + stacks for rows older than 18 months
- [ ] Checks all `Source URL` values for HTTP 200 (HEAD, 5s timeout)
- [ ] Opens one GitHub issue per domain with findings (title: `[Freshness] <domain>: N stale, M broken URLs`)
- [ ] Skips domains with no findings (no noise)
- [ ] Doesn't duplicate — checks for existing open issue with same title prefix
- [ ] `backendpro-validate --check-urls` runs URL checks locally
- [ ] `python scripts/freshness.py --dry-run` previews without opening issues
- [ ] `pytest tests/test_freshness.py` passes

### Verification

```bash
# Local dry-run
python3 src/backend-pro-max/scripts/freshness.py --dry-run --domain pattern

# URL check
backendpro-validate --check-urls --domain pattern

# Test
pytest tests/test_freshness.py -v

# Workflow syntax check
gh workflow view freshness 2>/dev/null || echo "Workflow not yet pushed"
```

---

## Task 5.3 — Provenance & Changelog Per Row

### Description

Track who added each row, who last reviewed it, and which version. Rather than
manual entry, this is primarily **automated via git blame** with a helper script.

**New columns** (optional, domain CSVs only):
- `Added By` — git author of the commit that added the row
- `Last Reviewed By` — manually set during review passes
- `Version` — semver tag when the row was added/last modified

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 5.3.1 | `scripts/provenance.py` — git-blame-based script to populate `Added By` and `Version` | `scripts/provenance.py` (new) | 2.5h |
| 5.3.2 | Add `Added By`, `Last Reviewed By`, `Version` columns to all domain CSV headers | `data/*.csv` | 1h |
| 5.3.3 | Run provenance script to backfill `Added By` + `Version` from git history | `data/*.csv` | 1h (automated) |
| 5.3.4 | Update `CSV_CONFIG` — provenance cols in output_cols (optional display) | `scripts/core.py` | 0.5h |
| 5.3.5 | `--show-provenance` flag to include provenance in output (hidden by default) | `scripts/search.py` | 0.5h |
| 5.3.6 | Validator — provenance columns optional, but `Version` must be valid semver if present | `scripts/validate.py` | 0.5h |
| 5.3.7 | CI step — run provenance.py on PRs that touch CSVs, commit auto-populated fields | `.github/workflows/ci.yml` | 1h |
| 5.3.8 | Tests | `tests/test_provenance.py` (new) | 1.5h |

### Acceptance Criteria

- [ ] `Added By`, `Last Reviewed By`, `Version` columns present in all domain CSVs
- [ ] `python scripts/provenance.py` auto-populates `Added By` + `Version` from git blame
- [ ] `backendpro "kafka" --domain messaging --show-provenance` shows provenance fields
- [ ] Provenance columns hidden by default (not in standard output)
- [ ] `backendpro-validate` passes (provenance columns are optional)
- [ ] `Version` values are valid semver (e.g. `0.2.0`) when present
- [ ] `pytest tests/test_provenance.py` passes

### Verification

```bash
python3 src/backend-pro-max/scripts/provenance.py --dry-run
backendpro "kafka" --domain messaging --show-provenance
backendpro "kafka" --domain messaging  # provenance NOT shown by default
backendpro-validate
pytest tests/test_provenance.py -v
```

---

## Task 5.4 — Conflict Detection

### Description

When two rows across different domains (or within the same domain) give
contradicting advice, surface it. Examples:

- `pattern.outbox` says "write to outbox table in same transaction" but
  `data.cdc` says "use CDC from the WAL directly" — these aren't contradictions
  but an uninformed reader might think so. Surface the tension.
- `reliability` says "retry with exponential backoff" but `performance` says
  "retries add p99 latency" — real trade-off to surface.

**Approach:** Define a conflict rule set (pairs of domains/keywords that are
known tension points). Scan the KB and emit warnings.

### Subtasks

| # | Subtask | Files | Est |
|---|---------|-------|-----|
| 5.4.1 | Define conflict rules — YAML/Python dict of known tension pairs | `scripts/conflicts.py` (new) | 2h |
| 5.4.2 | Conflict scanner — for each rule, search both sides, check for contradicting advice in Strengths/Weaknesses/Notes | `scripts/conflicts.py` | 3h |
| 5.4.3 | Conflict formatter — `⚠ Tension: <domain1>.<row> says X, <domain2>.<row> says Y` | `scripts/conflicts.py` | 1h |
| 5.4.4 | CLI command — `backendpro conflicts [--domain D]` | `scripts/search.py` | 1h |
| 5.4.5 | CI integration — run conflict scan on PRs that modify CSVs, warn (not fail) | `.github/workflows/ci.yml` | 0.5h |
| 5.4.6 | Tests — known conflict rules fire, non-conflicts don't false-positive | `tests/test_conflicts.py` (new) | 2h |

### Acceptance Criteria

- [ ] `backendpro conflicts` scans all domains and reports known tensions
- [ ] `backendpro conflicts --domain messaging` scans only messaging + its known tension pairs
- [ ] Output format: `⚠ Tension [BPM:domain1.row] vs [BPM:domain2.row]: <description>`
- [ ] Uses citation tokens (Tier 3) for greppable references
- [ ] ≥10 conflict rules defined (retry/latency, outbox/CDC, consistency/performance, cache/consistency, etc.)
- [ ] `--json` produces structured conflict list
- [ ] CI warns on new conflicts but doesn't block PRs
- [ ] `pytest tests/test_conflicts.py` passes

### Verification

```bash
backendpro conflicts
backendpro conflicts --domain messaging
backendpro conflicts --json | python3 -c "import sys,json; print(len(json.load(sys.stdin)['tensions']), 'tensions found')"
pytest tests/test_conflicts.py -v
```

---

## Dependency Graph

```
┌───────────────────────┐
│ 5.1 Source citations  │ ← Start first (all other tasks need Source URL column)
│ (backfill all CSVs)   │
└───────────┬───────────┘
            │
     ┌──────┴──────┐
     ▼              ▼
┌──────────┐  ┌──────────┐
│ 5.2 Auto │  │ 5.3 Prov │ ← Both depend on 5.1 (need Source URL + Last Updated)
│ freshness│  │ enance   │
└──────────┘  └──────────┘

┌───────────────────────┐
│ 5.4 Conflict detection│ ← Independent of 5.1–5.3 (reads existing content)
│                       │   but benefits from citation tokens (Tier 3)
└───────────────────────┘
```

### Recommended implementation order

1. **Phase A**: 5.1 (source citations backfill) — the foundation everything else needs
2. **Phase B** (parallel): 5.2 (auto-freshness) + 5.3 (provenance) + 5.4 (conflict detection)

Within 5.1, batch the backfill by priority: databases → messaging → cache →
reliability → patterns (normalise) → remaining domains → stacks.

---

## Checkpoint Criteria

### After Phase A

- [ ] All CSVs have `Source URL`, `Source Type`, `Last Updated` columns
- [ ] ≥90% fill rate on top-5 priority CSVs
- [ ] `backendpro-validate` passes (soft mode)
- [ ] `backendpro-validate --strict` passes on fully-backfilled CSVs
- [ ] Existing tests pass

### After Phase B (Tier 5 complete)

- [ ] Weekly freshness Action runs, opens issues for stale/broken rows
- [ ] `backendpro-validate --check-urls` works locally
- [ ] Provenance auto-populated from git blame
- [ ] `backendpro conflicts` reports ≥10 known tensions
- [ ] ≥30 new test cases total for Tier 5
- [ ] `ruff check src tests` clean
- [ ] `backendpro-validate` passes
- [ ] README updated with trust/verifiability features
- [ ] CHANGELOG entry

---

## Files to Create / Modify

| Action | File |
|--------|------|
| **Create** | `src/backend-pro-max/scripts/freshness.py` |
| **Create** | `src/backend-pro-max/scripts/provenance.py` |
| **Create** | `src/backend-pro-max/scripts/conflicts.py` |
| **Create** | `.github/workflows/freshness.yml` |
| **Create** | `tests/test_freshness.py` |
| **Create** | `tests/test_provenance.py` |
| **Create** | `tests/test_conflicts.py` |
| **Modify** | All 20 `src/backend-pro-max/data/*.csv` (add Source URL, Source Type, Last Updated columns + backfill) |
| **Modify** | All 12 `src/backend-pro-max/data/stacks/*.csv` (add Source URL, Last Updated) |
| **Modify** | `src/backend-pro-max/scripts/core.py` (CSV_CONFIG output_cols for new columns) |
| **Modify** | `src/backend-pro-max/scripts/validate.py` (--strict, --check-urls, Source Type enum, provenance validation) |
| **Modify** | `src/backend-pro-max/scripts/search.py` (`conflicts` command, `--show-provenance` flag) |
| **Modify** | `.github/workflows/ci.yml` (provenance auto-populate, conflict scan) |
| **Modify** | `pyproject.toml` (new entry points if needed) |
| **Modify** | `README.md`, `CHANGELOG.md` |

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Backfilling ~470 rows with Source URLs is extremely time-consuming | Phase it: top-5 CSVs first (databases, messaging, cache, reliability, patterns). Use soft validation so CI doesn't block on incomplete backfill. Tier 4 new CSVs already require Source URL from day one. |
| Source URLs break over time (link rot) | Freshness CI job checks weekly. Prefer permanent URLs: official docs > blog posts > tweets. Accept DOIs, RFC numbers, archived links. |
| Git blame provenance is noisy (reformat commits populate Added By incorrectly) | Use `git log --follow --diff-filter=A` to find the commit that truly added the row. Fall back to earliest non-reformat commit. Mark auto-populated provenance with `(auto)` suffix. |
| Conflict detection false positives annoy users | Conflicts are **warnings**, never errors. Start with a curated rule set of known architectural tensions. False positives → remove the rule. Community can contribute rules via PRs. |
| `--strict` mode blocks all CI if any CSV has gaps | `--strict` is opt-in (not default). CI uses soft mode for existing CSVs. `--strict` only applies to rows modified in the PR (via git diff). |
| URL checking hits rate limits or firewalls | HEAD requests only, 5s timeout, max 3 retries with backoff. Parallelism capped at 5 concurrent requests. Cache results in `.backendpro_cache/url-check.json` for 7 days. |
| Adding 3-5 new columns to every CSV is a massive diff | Split into multiple PRs: (1) add empty columns to headers, (2) backfill per-domain. Each PR is reviewable. |
