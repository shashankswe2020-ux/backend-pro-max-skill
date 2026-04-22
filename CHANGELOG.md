# Changelog

All notable changes to **backendpro** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] — Unreleased

### Added
- **Smarter `compare`** — when a queried term has zero hits in the chosen domain, the result no longer silently fills the column with `—`. Instead the entry is blanked, the name is added to a new `missing` list, and `suggestions` point at other domains where the term actually lives (e.g. `compare cosmosdb dynamodb` now hints `try --domain cloud → Cosmos DB`). Markdown output renders a `> ⚠️` warning block above the table.
- **Product-name synonyms** — query expansion now bridges no-space variants (`cosmosdb` ↔ `cosmos db`, `dynamodb` ↔ `dynamo db`, `mongodb`, `clickhouse`, `bigquery`, `elasticsearch`, `rabbitmq`, `kubernetes`/`k8s`, `postgres`/`postgresql`, etc.).

### Fixed
- `compare` no longer surfaces a tangentially related row (e.g. MongoDB for `cosmosdb`) just because BM25 scored it highest — matches now require the identifier column to actually contain the queried name (space-insensitive).

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
