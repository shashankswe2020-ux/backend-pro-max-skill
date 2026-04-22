# Contributing to Backend Pro Max

Thanks for helping make this skill smarter. The bar for contributions is:

> **Would a staff engineer be glad this row exists when an AI assistant
> surfaces it during an architecture review?**

## TL;DR

```bash
python -m pip install -e ".[dev]"
pytest                                 # 37+ tests must pass
python -m backendpro.scripts.validate  # every CSV must validate cleanly
ruff check src tests                   # lint
```

Open a PR on a branch (never push to `main`).

## Repository layout

```
src/backend-pro-max/
├── data/                # Domain CSVs (the knowledge base)
│   └── stacks/          # Per-language stack CSVs
└── scripts/
    ├── core.py          # BM25 engine, caching, synonyms, compare, stale
    ├── search.py        # CLI (search / compare / interactive / stale)
    └── validate.py      # CSV schema validator (used by CI)
tests/                   # pytest suite
.github/workflows/ci.yml # lint + validate + test + smoke test
```

## Adding a new row

1. Pick the right CSV in `src/backend-pro-max/data/`.
2. Match the existing column order **exactly**. If a value contains a
   comma or a newline, **wrap the field in double quotes** (escape inner
   quotes with `""`, never `\"`). The validator will reject misaligned
   rows.
3. Set `Last Updated` (where the column exists) to today's date in
   `YYYY-MM-DD` format. This powers the `--max-age-months` and
   `--stale` flags.
4. Run the validator locally: `python -m backendpro.scripts.validate`.
5. Run the tests: `pytest`.

### Severity / quality guidance

When a CSV has a `Severity` column, use one of: `Low`, `Medium`, `High`,
`Critical`. Reserve `Critical` for things that cause data loss, security
incidents, or outages.

### Keywords column

The `Keywords` column is the single biggest lever for search quality.
Include:

- The canonical name and common aliases (`postgres`, `postgresql`, `pg`).
- The acronym and the expansion (`cdc`, `change data capture`).
- Common misspellings if widely used (`kuberentes`).
- Adjacent jargon a staff engineer might query with.

## Adding a new domain

1. Create `src/backend-pro-max/data/<domain>.csv`.
2. Register it in `CSV_CONFIG` in `core.py` (declare `search_cols` and
   `output_cols`).
3. Add a keyword bag in `_DOMAIN_KEYWORDS` (used by auto-detection).
4. Add at least one row, then run `pytest`.
5. Update `README.md` and `CLAUDE.md`.

## Adding a new stack

1. Create `src/backend-pro-max/data/stacks/<stack>.csv` with the canonical
   columns: `Category, Guideline, Description, Do, Don't, Code Good,
   Code Bad, Severity, Docs URL`.
2. Register it in `STACK_CONFIG`.
3. Update docs.

## Search-quality tests

If you add a domain or noticeably change ranking behavior, please add a
ranking-quality test in `tests/test_search.py`. The contract is:
"this canonical query must rank this canonical row at #1." Example:

```python
def test_search_saga_finds_saga_in_patterns():
    res = core.search("saga", domain="pattern")
    assert any("saga" in str(v).lower() for v in res["results"][0].values())
```

## Synonyms

If a class of queries consistently misses the right row (e.g.,
"partial failure" not finding "Saga"), add a synonym in `_SYNONYMS` in
`core.py`. Keep it conservative — over-expansion hurts precision.

## Releasing

This repo uses GitHub Actions CI. A PR is mergeable when:

- All tests pass on Python 3.9, 3.11, and 3.12.
- `ruff check src tests` passes.
- `python -m backendpro.scripts.validate` returns 0.
- The CLI smoke tests in `ci.yml` succeed.

## Code style

- Pure standard library only for runtime code (no new deps).
- Python 3.8+ compatible (no walrus-only syntax in core, etc.).
- Public functions in `core.py` must keep their existing signatures
  backwards-compatible — add new behavior behind keyword-only args.
