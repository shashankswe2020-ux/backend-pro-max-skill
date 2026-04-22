# Changelog

All notable changes to **backendpro** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-04-22

### Added
- **Decision Intelligence** — three new commands: `decide`, `adr`, `design` that turn BM25 search into a constraint-aware decision advisor.
  - `backendpro decide "Kafka vs Pulsar"` — ranked recommendation with constraint scoring.
  - `backendpro adr "Redis vs Memcached"` — auto-generated Architecture Decision Record (Markdown).
  - `backendpro design "Postgres for 50M DAU"` — capacity-aware design document with QPS/storage estimates.
- **Constraint extraction** — queries are parsed for facets (`throughput:high`, `latency:low-ms`, `cloud:aws`, `consistency:strong`) and candidates are scored against constraint columns in CSVs.
- **`--constraints` flag** — explicit constraint overrides: `--constraints throughput=high,cloud=aws`.
- **`--out` flag** — write ADR output directly to a file: `backendpro adr "..." --out decision.md`.
- **Constraint columns** on `databases.csv`, `messaging.csv`, `cache.csv` — Throughput Tier, Latency Tier, Consistency Tier, Cost Tier, Cloud Native.
- **43 new tests** (80 total, up from 37) covering `decide`, `adr`, `design`, constraint extraction, constraint application, formatters, capacity math, and edge cases.
- **`_get_name()` helper** — safe row-name extraction replacing fragile `next(iter())` calls.
- **Named constants** — `_PEAK_FACTOR`, `_DEFAULT_ROW_BYTES`, `_DEFAULT_REPLICATION`, `_DAU_TO_REQUESTS`, `_MAX_FIELD_DISPLAY` replace magic numbers.

### Fixed
- **Path traversal** in `--out` flag — rejects `..` segments and absolute paths.
- **ADR TypeError** — removed invalid `query=` kwarg in `adr()` call.
- **Dead `--constraints`** flag — now wired into search path via `parse_constraints()` + `apply_constraints()`.
- **Dedup keeps best score** — when multiple domains return the same candidate, the highest-scored row wins.
- **REPL crash protection** — all REPL handlers wrapped in try/except.
- **Brace escaping** — curly braces in ADR template strings no longer raise `KeyError`.
- **Adjective constraint extraction** — "high throughput" → `throughput:high`, "low latency" → `latency:low-ms`.
- **Help text** for `--constraints` corrected.
- Removed dead `TEMPLATES_DIR` constant.
- Unified truncation with `_MAX_FIELD_DISPLAY`.

### Changed
- Bumped version to **0.3.0**.
- Landing page (`index.html`) updated with Decision Intelligence cards, terminal demo, and 80-test stats.
- README updated with Decision Intelligence section, 5 hard demos, and updated badges/smoke tests.

## [0.2.0] — 2026-04-22

### Added
- **Compare mode** — `backendpro compare "<A>" "<B>" [...] [--domain <d>]` outputs a side-by-side markdown table for tradeoff decisions / ADRs. Programmatic API: `core.compare()`.
- **Interactive REPL** — `backendpro --interactive` (`-i`) with slash commands: `/d`, `/s`, `/all`, `/cmp`, `/stale`, `/list`, `/help`, `/quit`.
- **Synonym / hybrid search** — query expansion bridges keyword gaps (e.g. `"partial failure"` → `compensation, saga, fault`). Disable with `--no-expand`.
- **Confidence scores** — every result now carries a `_score` field (BM25). Markdown output adds a `(score: 7.69, confidence: high)` label per result. Hide with `--no-scores`.
- **Freshness tracking** — optional `Last Updated` column convention (`YYYY-MM-DD`). New flags: `--max-age-months N` (filter), `--stale --domain <d> --max-age-months N` (audit). New API: `core.find_stale()`.
- **In-memory index cache** — lazy, mtime-invalidated. No more BM25 recompute per query. New API: `core.clear_cache()`.
- **CSV validator** — `backendpro-validate` console script (also wired into CI). Validates every CSV against its declared schema (columns, ragged rows, date formats).
- **Test suite** — 37 pytest cases covering BM25 ranking quality, edge cases (empty CSV, missing columns), domain detection, cache behavior, compare, stale filtering, and CSV validation.
- **GitHub Actions CI** — `.github/workflows/ci.yml` runs ruff lint + CSV validator + pytest + CLI smoke tests on Python 3.9 / 3.11 / 3.12.
- **`CONTRIBUTING.md`** — content & schema rules, severity definitions, ranking-quality test contract, synonym guidance.
- **Landing page** (`index.html`) with new "Power Tools" section, refreshed terminal demo, and CI/test stats.
- **`[project.optional-dependencies] dev`** — `pytest`, `pytest-cov`, `ruff`. Plus `[tool.pytest.ini_options]` and `[tool.ruff]` config in `pyproject.toml`.

### Changed
- `core.search()`, `core.search_stack()`, `core.search_all()` accept new keyword-only args (`min_score`, `max_age_months`, `expand`). Existing positional signatures are unchanged → fully backwards compatible.
- Pattern domain rows now include a `Last Updated` column (set to `2026-01-15` for the initial 22 rows).

### Fixed
- **9 pre-existing CSV data-corruption bugs** (caught by the new validator): unquoted commas mis-aligned fields in `api.csv`, `architecture.csv`, `cache.csv`, `iac.csv`, `messaging.csv` (×3), `observability.csv`, plus `csharp-aspnet`, `elixir-phoenix`, `nodejs-express`, `php-laravel`, `rust-axum` stack files. Search was silently degraded for these rows.
- `architecture` domain's `search_cols` referenced a non-existent `Use Case` column → corrected to `When to Use`.
- Replaced deprecated `datetime.utcnow()` with `datetime.now()` (Python 3.13+ deprecation).

## [0.1.0] — Initial release

- 20 backend / distributed-systems knowledge domains (CSV-backed).
- 12 language stack guideline CSVs.
- Pure-stdlib BM25 search engine.
- Keyword-bag domain auto-detection.
- CLI: `backendpro "<query>" [--domain] [--stack] [--all] [--list] [--json]`.
- `pip install -e .` via `setuptools` with hyphenated source layout mapped to the importable `backendpro` package.
