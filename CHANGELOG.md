# Changelog

All notable changes to **backendpro** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] — 2026-04-28

### Added
- **Tier 6 — DX & Distribution** — five new developer-facing features that turn the knowledge base into an active tool, meeting engineers in IDE, browser, CI, learning, and knowledge export workflows.
- **`backendpro lint`** — regex-based linter scans source files for 18 backend anti-patterns (blocking sleep, missing timeouts, sync-in-async, secrets in .env, SQL injection, eval, unbounded queries, etc.). Outputs human-readable, JSON, and SARIF (GitHub Code Scanning) formats. Each finding includes BPM citation, severity, and fix suggestion. `lint-rules.yml` for extensibility.
- **`.pre-commit-hooks.yaml`** — pre-commit framework integration for `backendpro lint`.
- **`.github/actions/lint/action.yml`** — composite GitHub Action that runs `backendpro lint --format sarif` and uploads to Code Scanning.
- **`backendpro export`** — export the entire KB to Obsidian (one `.md` per row with YAML frontmatter + wikilinks + `_Index.md` MOC), Notion (CSV per domain), or Org-mode (`.org` per domain with headlines + properties). Filter by `--domain`.
- **`backendpro learn`** — spaced-repetition flashcards using SM-2 algorithm. State persists in `~/.backendpro/learn.json`. Supports `--domain` filter, `--daily N`, `--stats`, `--reset`. Atomic file writes for state safety.
- **VS Code extension** (`extensions/vscode/`) — "Backend Pro Max: Search" command, right-click "Explain Selection", CodeLens provider showing stack guidelines for Go/Python/Java/TS/Rust/etc., MCP client mode (stdio JSON-RPC to `backendpro-mcp`), configurable via 6 settings. Compiles with TypeScript, tests with `@vscode/test-electron`.
- **JetBrains plugin stub** (`extensions/jetbrains/`) — Tools menu actions (Search + Explain Selection) shelling out to `backendpro --json`. `plugin.xml` for IntelliJ/GoLand/PyCharm/WebStorm.
- **Web playground** live at [backendpro.cc](https://backendpro.cc) — search-as-you-type, domain filter, shareable permalinks, compare view. Static SPA, zero backend.
- **3 new CLI entry points**: `backendpro-lint`, `backendpro-learn`, `backendpro-export`.
- **3 new subcommands** in `backendpro`: `lint`, `learn`, `export` (dispatched before argparse).
- **58 new tests** (390 total) covering lint rules (29 tests — per-language fixtures, formatters, SARIF), export (12 tests — all 3 formats, frontmatter, wikilinks, domain filtering), and learn (17 tests — SM-2 math, state persistence, due-card selection, stats).
- **Test fixtures**: `tests/fixtures/lint/` with sample Go, Python, TypeScript, Java, and .env files.

### Changed
- `pyproject.toml` version bumped to 0.6.0, 3 new entry points added.
- `search.py` — `lint`, `learn`, `export` subcommands dispatched before argparse.

## [0.5.0] — 2026-04-28

### Added
- **Tier 5 — Trust, Verifiability & Freshness** — every claim in the knowledge base is now sourced, auditable, and freshness-tracked.
- **Source citations on all CSVs** — `Source URL`, `Source Type`, `Last Updated` columns on all 34 domain CSVs and 12 stack CSVs. 100% fill rate (685/685 rows). Source types: `official-docs`, `paper`, `postmortem`, `engineering-blog`, `book`, `benchmark`, `rfc`.
- **Source Type enum validation** — `backendpro-validate` rejects invalid Source Type values. Enforced in CI.
- **Strict validation mode** — `backendpro-validate --strict` fails on rows missing Source URL or Last Updated. Soft mode (default) warns but passes.
- **Auto-freshness CI job** — `.github/workflows/freshness.yml` runs weekly (Monday 09:00 UTC). Flags rows older than 18 months, checks Source URLs for HTTP 200, opens GitHub issues per domain. Deduplication prevents issue spam.
- **`backendpro-validate --check-urls`** — local URL checking for Source URLs (HEAD request, 5s timeout, 3 retries).
- **Provenance auto-populator** — `scripts/provenance.py` uses git blame to populate `Added By` and `Version` columns. `--show-provenance` flag in search output (hidden by default).
- **Conflict/tension detector** — `backendpro conflicts [--domain] [--json]` scans 12 curated architectural tension rules (retry vs latency, cache vs consistency, outbox vs CDC, sharding vs joins, etc.) and surfaces trade-offs with citation tokens.
- **13 new Tier 4 domains** — cost, migration, incident, capacity, compliance, multi-tenant, release, ml-platform, edge, mobile-backend, api-contract, interview, latency-numbers. **34 domains total** (up from 21).
- **51 new Tier 5 tests** (332 total) covering validation (Source Type enum, soft/strict modes, trust column presence), freshness (stale detection, URL checking, issue formatting), provenance (git blame, version validation), and conflicts (rule structure, domain filtering, tension detection).

### Changed
- `patterns.csv` column `Reference` renamed to `Source URL` for consistency across all CSVs.
- `security.csv` column `Reference` renamed to `Source URL`.
- `CSV_CONFIG` in `core.py` — all domain output_cols now include `Source URL`, `Source Type`, `Last Updated`.
- `_STACK_COLS` — stack output_cols now include `Source URL`, `Last Updated`.
- `validate.py` rewritten — returns `(errors, warnings)` tuple, supports `--strict`, `--check-urls`, `--domain` flags, Source Type enum checking.
- README updated: 34 domains, 332 tests, Trust & Verifiability section.
- `index.html` updated: 34 domains, 332 tests, Tier 5 feature cards.
- `pyproject.toml` version bumped to 0.5.0.

## [0.4.0] — 2026-04-22

### Added
- **MCP Server** — `backendpro-mcp` entry point exposes 8 tools via stdio transport (Model Context Protocol). Compatible with Claude Desktop, Cline, Cursor, Zed, and any MCP-aware client. Install with `pip install backendpro[mcp]`. Core remains zero-dependency.
- **Citation Tokens** — every search result carries a stable `[BPM:domain.slug]` citation key. Greppable in PRs (`grep -r '\[BPM:' .`) for provenance verification.
- **JSONL Streaming** — `--jsonl` flag outputs one JSON object per line for agent loops. Works with single-domain, cross-domain, and compare modes.
- **Function-Calling Manifest** — `tools.json` at repo root with dual-format schemas (OpenAI `functions` + Anthropic `tool_use`). Auto-generated by `gen_tools_schema.py` with CI freshness check.
- **MCP Inspector Report** — `docs/mcp-inspector-report.md` documents passing validation of all 8 tools.
- **53 new tests** (196 total) covering citations, JSONL output, tool schemas, and MCP server.

### Changed
- SKILL.md updated with citation instruction: "Always emit `[BPM:…]` citation tokens when referencing results."
- README updated with MCP / Agent Integration section, updated badges (196 tests), updated FAQ.
- Markdown formatters now display citation tokens inline in result headers.

## [0.3.1] — 2026-04-22

### Added
- **Intent Classifier** — auto-detects query intent (`comparison`, `troubleshoot`, `migration`, `incident`, `definition`, `best-practice`, `checklist`) with weighted regex patterns. Structured per-intent templates format output. Override with `--intent <type>`.
- **Hybrid Retrieval** — optional embedding-based search via `sentence-transformers` + Reciprocal Rank Fusion with BM25. Install with `pip install backendpro[semantic]`. Use `--engine hybrid` or `--engine semantic`. Graceful BM25 fallback.
- **Cross-Encoder Re-ranking** — optional cross-encoder re-ranking for precision-critical queries. Install with `pip install backendpro[rerank]`. Use `--rerank`. Graceful fallback.
- **Anti-patterns Domain** — 15 distributed-systems anti-patterns (Distributed Monolith, God Service, Dual Writes, Sync-over-Async, …) with symptoms, root causes, fixes, and severity ratings. 21 domains total.
- **`templates.py`** — per-intent output formatters with structured field extraction.
- **`semantic.py`** — embedding index with safe disk cache (numpy + JSON), mtime-based invalidation.
- **`rerank.py`** — cross-encoder re-ranking with lazy model loading and graceful fallback.
- **68 new tests** (148 total) covering intent classification, anti-patterns, semantic search, re-ranking, and template formatting.

### Fixed
- **Pickle deserialization risk** — replaced `pickle.load()` in semantic cache with `numpy.load(allow_pickle=False)` + `json.load()` (CWE-502, #22).
- **Cache directory permissions** — `.backendpro_cache/` now created with `mode=0o700` (CWE-732, #24).
- **Semantic fallback warning flood** — warning now prints once per process instead of on every call (#23).

### Changed
- Documentation updated: README (21 domains, 148 tests, Tier 2 features), `index.html`, `USAGE.md` (`--intent`, `--engine`, `--rerank` flags), `CHANGELOG`.

## [0.3.0] — 2026-04-22

### Added
- **Decision Intelligence** — three new commands: `decide`, `adr`, `design` that turn BM25 search into a constraint-aware decision advisor.
  - `backendpro decide "Kafka vs Pulsar"` — ranked recommendation with constraint scoring.
  - `backendpro adr "Redis vs Memcached"` — auto-generated Architecture Decision Record (Markdown).
  - `backendpro design "Postgres for 50M DAU"` — capacity-aware design document with QPS/storage estimates.
- **Intent Classifier (Tier 2)** — auto-detects query intent (`comparison`, `troubleshoot`, `migration`, `incident`, `definition`, `best-practice`, `checklist`) using weighted regex patterns. Structured templates format output by intent. Override with `--intent <type>`.
- **Hybrid Retrieval (Tier 2)** — optional embedding-based search via `sentence-transformers` + Reciprocal Rank Fusion with BM25. Install with `pip install backendpro[semantic]`. Use `--engine hybrid` or `--engine semantic`. Graceful fallback to BM25 when not installed.
- **Cross-Encoder Re-ranking (Tier 2)** — optional cross-encoder re-ranking for precision-critical queries. Install with `pip install backendpro[rerank]`. Use `--rerank`. Graceful fallback when not installed.
- **Anti-patterns Domain (Tier 2)** — 15 common distributed-systems anti-patterns (Distributed Monolith, God Service, Dual Writes, Sync-over-Async, Chatty Microservices, …) with symptoms, root causes, fixes, and severity ratings.
- **`templates.py`** — per-intent output formatters with structured field extraction.
- **`semantic.py`** — embedding index with disk cache (numpy + JSON, no pickle), mtime-based invalidation.
- **`rerank.py`** — cross-encoder re-ranking with lazy model loading and graceful fallback.
- **Constraint extraction** — queries are parsed for facets (`throughput:high`, `latency:low-ms`, `cloud:aws`, `consistency:strong`) and candidates are scored against constraint columns in CSVs.
- **`--constraints` flag** — explicit constraint overrides: `--constraints throughput=high,cloud=aws`.
- **`--out` flag** — write ADR output directly to a file: `backendpro adr "..." --out decision.md`.
- **Constraint columns** on `databases.csv`, `messaging.csv`, `cache.csv` — Throughput Tier, Latency Tier, Consistency Tier, Cost Tier, Cloud Native.
- **43 new tests** (80 total, up from 37) covering `decide`, `adr`, `design`, constraint extraction, constraint application, formatters, capacity math, and edge cases.
- **68 more tests (148 total)** covering intent classification (35 tests), anti-patterns (16 tests), semantic search (11 tests), re-ranking (5 tests), and template formatting.
- **`_get_name()` helper** — safe row-name extraction replacing fragile `next(iter())` calls.
- **Named constants** — `_PEAK_FACTOR`, `_DEFAULT_ROW_BYTES`, `_DEFAULT_REPLICATION`, `_DAU_TO_REQUESTS`, `_MAX_FIELD_DISPLAY` replace magic numbers.
- **Smarter `compare`** — when a queried term has zero hits in the chosen domain, the result no longer silently fills the column with `—`. Instead the entry is blanked, the name is added to a new `missing` list, and `suggestions` point at other domains where the term actually lives (e.g. `compare cosmosdb dynamodb` now hints `try --domain cloud → Cosmos DB`). Markdown output renders a `> ⚠️` warning block above the table.
- **Product-name synonyms** — query expansion now bridges no-space variants (`cosmosdb` ↔ `cosmos db`, `dynamodb` ↔ `dynamo db`, `mongodb`, `clickhouse`, `bigquery`, `elasticsearch`, `rabbitmq`, `kubernetes`/`k8s`, `postgres`/`postgresql`, etc.).

### Fixed
- **Pickle deserialization risk** — replaced `pickle.load()` in semantic cache with `numpy.load(allow_pickle=False)` + `json.load()` (CWE-502, #22).
- **Cache directory permissions** — `.backendpro_cache/` now created with `mode=0o700` (CWE-732, #24).
- **Semantic fallback warning flood** — warning now prints once per process instead of on every call (#23).
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
- `compare` no longer surfaces a tangentially related row (e.g. MongoDB for `cosmosdb`) just because BM25 scored it highest — matches now require the identifier column to actually contain the queried name (space-insensitive).

### Changed
- Bumped version to **0.3.0**.
- Landing page (`index.html`) updated with 21 domains, 148 tests, Tier 2 feature cards (intent, hybrid, rerank, anti-patterns).
- README updated with Decision Intelligence section, Tier 2 features, 21 domains, 148 tests, anti-patterns domain, and updated badges.
- USAGE.md updated with `--intent`, `--engine`, `--rerank` flags, anti-patterns examples, and hybrid/rerank sections.

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
