# Code Review Checkpoint 1: Tier 1 — Decision Intelligence

> **Reviewer:** Code Reviewer Agent (Staff Engineer)
> **Date:** 2026-04-22
> **Scope:** Tier 1 — `decide`, `adr`, `design` commands + constraint filtering (`d921508`)
> **Test suite:** 50 tests passing (5 files), lint ✅, build ✅, validator ✅

---

## Verdict: ❌ REQUEST CHANGES

**Overview:** Solid first implementation of the decision intelligence tier — the `decide`, `adr`, and `design` commands produce impressive multi-domain output with constraint scoring. However, there is one runtime crash bug (wrong `adr()` call signature), a dead `--constraints` flag, and several important gaps in test coverage and error handling.

---

## Critical Issues

### 1. `adr()` call in CLI will crash with `TypeError`
- **File:** `src/backend-pro-max/scripts/search.py:353`
- **Problem:** `main()` calls `adr(args.adr, domains, query=args.query)`, but `adr()` signature is `adr(title, context_domains, out_path=None)`. There is no `query` keyword parameter. This will raise `TypeError: adr() got an unexpected keyword argument 'query'` at runtime whenever `--adr` is used from the CLI.
- **Fix:** Remove the `query=` kwarg:
  ```python
  result = adr(args.adr, domains)
  ```
  Or, if query should influence the search, add `query=None` to `adr()` signature and use it as a fallback search term.

### 2. `--constraints` flag is parsed but never used
- **File:** `src/backend-pro-max/scripts/search.py:320–321`
- **Problem:** `_build_parser()` defines `--constraints` and the help text documents it, but `main()` never reads `args.constraints`. The flag is completely dead code — users who pass `--constraints "cloud=gcp"` will see no effect.
- **Fix:** Wire `args.constraints` into the search path:
  ```python
  if args.constraints:
      from core import parse_constraints, apply_constraints
      constraints = parse_constraints(args.constraints)
      apply_constraints(result["results"], constraints)
  ```
  Apply this in the standard search path and in `--decide`.

---

## Important Issues

### 3. `--constraints` help text shows wrong syntax
- **File:** `src/backend-pro-max/scripts/search.py:321`
- **Problem:** Help string says `'throughput>=high,latency<=low'` with `>=`/`<=` operators, but `parse_constraints()` only supports `=` (splits on `=`). Users following the documented syntax will get no results.
- **Fix:** Change help to `"Constraint expression, e.g. 'cloud=gcp,latency=low-ms,consistency=strong'"`.

### 4. Deduplication in `decide()` relies on `next(iter(c.values()))` — fragile and dict-order-dependent
- **File:** `src/backend-pro-max/scripts/decide.py:211–215`
- **Problem:** Deduplication and display extract the "name" as the first value of the dict (`next(iter(c.values()))`). This is used in ~8 places across `decide.py`. It works because Python 3.7+ preserves insertion order and the CSVs have `Name` as the first column, but it's fragile — if any CSV reorders columns or if a row comes from a domain where the first column isn't the name (e.g. stacks use `Technology`), this silently breaks.
- **Fix:** Use an explicit key lookup with fallback:
  ```python
  def _get_name(row):
      return (row.get("Name") or row.get("Technology") or 
              str(next(iter(row.values()), ""))).strip()
  ```
  Then use `_get_name(c)` everywhere.

### 5. `_detect_relevant_domains` keyword hints overlap with `detect_domain` causing redundant or misleading results
- **File:** `src/backend-pro-max/scripts/decide.py:142–167`
- **Problem:** The `domain_hints` dict uses very generic keywords like `"store"` for database and `"event"` for messaging. Searching for "event store" triggers both `database` (via "store") and `messaging` (via "event"), and then the same technology might appear in candidates from different domains, scored differently. The deduplication handles this, but the duplicate work is wasteful and the first occurrence wins, which may not be the best-scored one.
- **Fix:** Either deduplicate by picking the highest-scored row per name (not just first-seen), or tighten the keywords.

### 6. No error handling in REPL `/decide`, `/adr`, `/design` commands
- **File:** `src/backend-pro-max/scripts/search.py:258–278`
- **Problem:** The REPL handlers call `decide()`, `adr()`, `design()` with no `try/except`. If any of these raise (e.g., empty input, malformed query), the REPL crashes and exits. The existing `/stale` handler has `try/except`, establishing a convention these new handlers break.
- **Fix:** Wrap each in `try/except Exception as e: print(f"Error: {e}")`.

### 7. Test coverage is shallow — only happy paths tested
- **File:** `tests/test_decide.py`
- **Problem:** 13 tests is a good start, but there are significant gaps:
  - No test for `apply_constraints()` (the core constraint engine)
  - No test for `format_decide()`, `format_adr()`, `format_design()` formatters
  - No test for `_parse_scale()` (capacity math)
  - No edge case tests: empty candidates, all constraints failing, unknown constraint keys
  - No test verifying `decide()` actually uses constraint scoring to reorder results
  - No CLI integration test (`main()` with `--decide`/`--adr`/`--design`)
  - The `adr` test uses `["database"]` which happens to work, but doesn't verify the Nygard format structure
- **Fix:** Add tests for `apply_constraints`, `_parse_scale`, formatters, edge cases, and at least one test verifying constraint-based reordering.

### 8. `adr()` doesn't pass through `--out` from CLI
- **File:** `src/backend-pro-max/scripts/search.py:351–354`
- **Problem:** The plan specifies `--out path` to write ADR to disk, and `adr()` supports `out_path`, but there's no `--out` argument in `_build_parser()` and `main()` never passes `out_path`. The Tier 1 acceptance criteria mentions this.
- **Fix:** Add `parser.add_argument("--out", metavar="PATH", help="Write output to file")` and pass it: `result = adr(args.adr, domains, out_path=args.out)`.

---

## Suggestions

### 9. `TEMPLATES_DIR` defined but never used
- **File:** `src/backend-pro-max/scripts/decide.py:33`
- `TEMPLATES_DIR` points to `templates/base/` but the ADR template is defined inline as `_ADR_TEMPLATE`. The external `adr.md` template file exists but isn't loaded. Either use it or remove the dead reference.

### 10. Magic numbers in capacity math
- **File:** `src/backend-pro-max/scripts/decide.py:393–398`
- `peak_factor=3`, `row_bytes=500`, `replication=3`, DAU-to-requests ratio of `10` are all magic numbers. They're reasonable defaults but should be named constants or documented in the output.

### 11. `format_design` truncates strengths/weaknesses at 200 chars but `format_decide` at 300
- **Files:** `decide.py:567` vs `decide.py:530`
- Inconsistent truncation limits. Pick one and extract a constant.

### 12. Consider making `extract_constraints` handle "high throughput" (adjective form)
- **File:** `src/backend-pro-max/scripts/decide.py:68–130`
- Currently `extract_constraints("I need high throughput")` returns `{}` because the regex requires a number+unit pattern like `50k req/sec`. The keyword form is very common in natural language. A simple keyword fallback (`if "high throughput" in req_lower: facets["throughput"] = "high"`) would improve UX significantly.

---

## What's Done Well

- **Clean separation**: `decide.py` as a distinct module keeps `core.py` focused on retrieval — good architectural boundary.
- **Constraint tier ordering logic** in `apply_constraints()` is elegant — "latency lower is better, throughput higher is better" via index comparison.
- **Rich markdown output**: The `format_decide()` output with constraint matrix, trade-offs table, and recommendation is genuinely useful for architecture decisions.
- **`design()` capacity math**: Deriving QPS from daily numbers with peak factor, plus storage estimates, is a nice system-design interview-style touch.
- **Zero new dependencies**: The entire decision intelligence layer is pure stdlib — impressive for this feature scope.
- **Full constraint column backfill**: All 43 rows across 3 CSVs populated with realistic tier values.

---

## Verification Story

| Check | Status | Notes |
|-------|--------|-------|
| Tests reviewed | ✅ | 50 passing, but coverage gaps (see #7) |
| Lint verified | ✅ | `ruff check src tests` clean |
| Validator verified | ✅ | 20 domains + 12 stacks valid |
| Security checked | ✅ | No user input passed to shell/eval; `out_path` uses `Path` (no injection risk); no secrets |
| Coverage | ⚠️ | ~13 tests for ~600 lines of new code; `apply_constraints`, formatters, CLI untested |

---

## Action Items

| # | Priority | Issue | Target |
|---|----------|-------|--------|
| 1 | Critical | `adr()` call crashes with wrong kwarg `query=` | Hotfix |
| 2 | Critical | `--constraints` flag is dead code — never read from `args` | Hotfix |
| 3 | Important | `--constraints` help text shows wrong `>=`/`<=` syntax | Hotfix |
| 4 | Important | Name extraction via `next(iter())` is fragile | This PR |
| 5 | Important | Redundant domain detection + first-wins dedup may drop best-scored row | This PR |
| 6 | Important | REPL handlers lack error handling (will crash REPL) | This PR |
| 7 | Important | Test coverage shallow — no `apply_constraints`, formatter, edge case, or CLI tests | This PR |
| 8 | Important | `--out` flag missing for ADR file output | This PR |
| 9 | Suggestion | `TEMPLATES_DIR` unused — dead code | Backlog |
| 10 | Suggestion | Magic numbers in capacity math | Backlog |
| 11 | Suggestion | Inconsistent truncation limits (200 vs 300 chars) | Backlog |
| 12 | Suggestion | `extract_constraints` doesn't handle adjective-form constraints | Backlog |
