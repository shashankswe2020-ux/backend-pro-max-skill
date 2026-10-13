# Usage

## Install

```bash
pip install -e .                  # runtime CLI only
pip install -e ".[dev]"           # + pytest, ruff for contributors
```

This registers two CLI commands:

| Command              | Purpose                                   |
| -------------------- | ----------------------------------------- |
| `backendpro`         | Search / compare / interactive REPL       |
| `backendpro-validate`| Schema-validate every CSV (used by CI)    |

## CLI

```bash
backendpro --help
```

### List domains and stacks

```bash
backendpro --list
```

### Search a specific domain

```bash
backendpro "circuit breaker" --domain pattern
backendpro "wide column multi-region" --domain database
backendpro "p99 tail latency" --domain performance
```

### Auto-detect the domain

If you omit `--domain`, the tool picks the best one based on keywords:

```bash
backendpro "kafka exactly once delivery"
# → detected domain: messaging
```

### Stack-specific guidelines

```bash
backendpro "virtual threads" --stack java-spring
backendpro "context" --stack go
backendpro "async" --stack python-fastapi
```

### Cross-domain search

Useful when a concept (idempotency, retries, timeouts) cuts across many
domains:

```bash
backendpro "idempotency" --all
```

### Compare two (or more) options side-by-side

The `compare` subcommand renders a markdown table — perfect for ADRs and
tradeoff discussions:

```bash
backendpro compare "Kafka" "RabbitMQ" --domain messaging
backendpro compare "Postgres" "DynamoDB" --domain database
backendpro compare "Saga" "2PC" --domain pattern
```

If `--domain` is omitted, it is auto-detected from the joined names.

### Interactive REPL

For exploratory design sessions:

```bash
backendpro --interactive
```

Inside the REPL:

```
bpm> circuit breaker                 # plain search (auto-detect)
bpm> /d database multi-region        # search a specific domain
bpm> /s go error handling            # stack-specific search
bpm> /all idempotency                # cross-domain
bpm> /cmp Kafka | RabbitMQ | NATS    # compare (pipe-separated)
bpm> /stale pattern 18               # list rows older than 18 months
bpm> /list                           # list domains & stacks
bpm> /help                           # full command list
bpm> /quit                           # exit (or Ctrl-D)
```

### Freshness / staleness

CSVs may carry a `Last Updated` column (`YYYY-MM-DD`). Two flags use it:

```bash
# Filter results to entries updated within the last 18 months
backendpro "service mesh" --domain container --max-age-months 18

# List every stale entry in a domain (audit mode)
backendpro --stale --domain pattern --max-age-months 24
```

Rows without a `Last Updated` value are **never** flagged or filtered —
this avoids false positives while content is being back-filled.

### JSON output

Every command supports `--json` for machine-readable output. JSON results
always include a `_score` field (BM25 score) for downstream re-ranking:

```bash
backendpro "redis cluster" --json
backendpro compare "Kafka" "RabbitMQ" --json
```

### Useful flags (cheat sheet)

| Flag                       | Effect                                                                |
| -------------------------- | --------------------------------------------------------------------- |
| `-n, --max-results N`      | Cap rows per scope (default 5; `--all` defaults to 2 per domain) |
| `--min-score F`            | Drop pre-rerank scores <= F; scale depends on effective engine |
| `--max-age-months N`       | Drop rows whose `Last Updated` is older than N months                 |
| `--no-expand`              | Disable synonym expansion (`partial failure → compensation, saga, …`) |
| `--no-scores`              | Hide rank scores in markdown output |
| `--json`                   | Machine-readable JSON output                                          |
| `--interactive` / `-i`     | Start the REPL                                                        |
| `--stale`                  | Audit mode (with `--domain` and `--max-age-months`)                   |
| `--list`                   | List domains and stacks                                               |
| `--intent <type>`          | Override auto-detected intent (`comparison`, `troubleshoot`, `migration`, `incident`, `definition`, `best-practice`, `checklist`) |
| `--engine <engine>`        | Retrieval engine: `bm25` (default), `hybrid`, or `semantic`. Hybrid/semantic require `pip install backendpro[semantic]` |
| `--rerank`                 | Re-rank candidates before final selection. Requires `pip install backendpro[rerank]` |
| `--candidate-pool N`       | Candidate rows per scope, >= `-n`; default max(20, `-n`) with reranking, otherwise `-n` |
| `--diagnostics`            | Include requested/effective retrieval, fallbacks, counts and scope hints |

### Rank scores

Markdown results show ranking signals, not calibrated confidence:

```
### Result 1  _(rank score: 7.69)_
```

`_score` is BM25, cosine similarity, or reciprocal-rank fusion (RRF), depending
on the effective engine. `_rerank_score` is a cross-encoder ranking signal.
Neither is a correctness probability; independent domain scores are not
globally calibrated. The former high/medium/low confidence labels were removed.
Use `--no-scores` to suppress ranking scores in Markdown.

### Synonym / hybrid search

Common backend aliases are expanded automatically before ranking, so
plain-English queries reach the right rows even when keywords don't
overlap:

```bash
backendpro "how to handle partial failure across services"
# matches "Saga" / "Circuit Breaker" via partial→compensation, failure→fault
```

Pass `--no-expand` to recover pure-keyword behavior.

### Anti-patterns

The `antipattern` domain contains 15 common distributed-systems anti-patterns
with symptoms, root causes, and fixes:

```bash
backendpro "distributed monolith" --domain antipattern
backendpro "dual writes" --domain antipattern
backendpro "god service" --domain antipattern
```

### Intent-aware output

The intent classifier auto-detects query intent and applies structured
templates. You can also override it:

```bash
# Auto-detected as "troubleshoot" → Symptom / Root Cause / Fix template
backendpro "connection pool exhausted"

# Force a specific intent
backendpro "kafka vs rabbitmq" --intent comparison
backendpro "migrate from monolith to microservices" --intent migration
```

### Hybrid retrieval (optional)

For conceptual queries where keyword matching falls short, enable
embedding-based hybrid search:

```bash
pip install backendpro[semantic]

# Hybrid = BM25 + embedding similarity via Reciprocal Rank Fusion
backendpro "how to handle eventual consistency" --engine hybrid

# Pure semantic (embedding only)
backendpro "conceptual distributed systems question" --engine semantic
```

### Cross-encoder re-ranking (optional)

For precision-critical queries, add cross-encoder re-ranking:

```bash
pip install backendpro[rerank]

backendpro "saga pattern" --rerank
```

### Retrieval pipeline and diagnostics

```bash
backendpro "message loss after failover" --domain messaging \
  --engine hybrid --rerank --candidate-pool 50 -n 5 --compact
backendpro "transaction rollback" --stack java-spring \
  --candidate-pool 20 --diagnostics --json
backendpro "idempotency" --all --rerank --candidate-pool 20 -n 5
```

All three search surfaces use the same candidate generation, score/freshness
filtering, optional cross-encoder ranking, constraint preferences and final
top-N selection. Pool size is per domain/stack, not a global evidence budget.
In cross-domain search, reranking happens inside each domain. The opt-in
`evidence` formatter below adds global selection over those returned candidates.

Filters run before candidate truncation. `--constraints` accepts unique
`key=value` preferences using `cloud`, `throughput`, `latency`, `consistency`,
and `cost`. Satisfied preferences sort first, followed by cross-encoder score
if present, otherwise the retrieval score. Unknown metadata is annotated, not
silently excluded. Malformed or unknown constraint keys are errors.

MCP `search`, `search_stack`, and `search_all` expose `engine`, `rerank`,
`candidate_pool`, `diagnostics`, `expand`, `min_score`, `max_age_months`,
`constraints` and `response_format`. Restart clients after updating tool schemas.
`expand=false` corresponds to CLI `--no-expand`.

Default BM25 raw result shapes and result ordering remain unchanged.
Non-default engines, reranking, explicit candidate pools, or `diagnostics=true`
add a `retrieval` object:

- Requested/effective engine and its score kind.
- Whether reranking was requested and actually applied to any candidates.
- Installed dependency capabilities when checked; `not_checked` does not
  mean unavailable. Capability checks do not prove weights can be loaded.
- Pinned model names/revisions, explicit missing-dependency fallbacks, candidate
  and pre-packing returned counts. Cross-domain counts sum all domains.
- Selected scope and up to three keyword-based auto-routing suggestions.
  Suggestions are not retrieval results or confidence estimates.

Compact JSON retains these diagnostics inside its existing 6000-character
bound and continues omitting whole evidence units. A metadata-only response
is explicitly `budget_exhausted`, not useful evidence. JSONL adds a leading
`_type: "retrieval_metadata"` record only when diagnostics exist, including
empty searches. Markdown CLI output prints the same metadata before evidence.

Explicit scopes are never widened. CLI `--domain`, `--stack`, and `--all` are
mutually exclusive. `--all` without `-n` still returns up to two rows per domain;
an explicit `--all -n N` now uses N rather than the old undocumented N/2
conversion, matching the core and MCP APIs.

Optional models keep their existing identities, pinned to immutable revisions:

- `all-MiniLM-L6-v2`: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
- `cross-encoder/ms-marco-MiniLM-L-6-v2`: `233902d25c440f23af6f7d6e94d2946bac0bee0a`

### Version-aware, budget-aware evidence (P2, opt-in)

```bash
backendpro "pydantic dictionary export migration" --stack python-fastapi \
  --evidence --library-version pydantic=2.10.6 --max-chars 6000 -n 20
backendpro "pydantic ORM migration" --stack python-fastapi \
  --evidence --project-path /path/to/project
backendpro "retry timeout" --all --evidence --max-chars 4000
backendpro --evidence-id 'bpme:<64-hex-content-hash>'
```

MCP searches accept `response_format="evidence"`, `max_chars`, `project_path`
and `library_versions` (an object, e.g. `{"pydantic":"2.10.6"}`). The ninth tool,
`evidence_detail(evidence_id)`, expands a returned ID to the full local source
row. Restart clients for the updated schema. Version/budget options on other
formats fail rather than being ignored. Core callers use `evidence=True` and
then `format_search_response(result, "evidence", ...)`.

**Compatibility:** raw search and `compact-v1` remain unchanged. Only the new
format includes the four Pydantic pilot records from `data/evidence.json`.
They are original summaries bound to immutable official documentation URLs,
document SHA256, upstream revision, source license and last-verified date.
No upstream document text is redistributed and no documentation network access
occurs at runtime. Pilot annotations cover **1.10.21 and 2.10.6 only**. Other
versions are not claimed compatible; `pydantic.v1` imports in v2 require separate
inspection. Existing corpus `Version` and `Last Updated` are not library
compatibility or source-verification dates.

**Local version observations:** filesystem inspection is opt-in and reads only
root `requirements.txt`, `pyproject.toml`, `uv.lock`, `poetry.lock`,
`Pipfile.lock` and `.python-version`. It does not run package managers, inspect
code, follow include directives/symlinks or upload content. Python 3.11+ can
inspect TOML with the standard library; older runtimes explicitly report that
limitation. PEP 621 direct dependencies and basic Poetry dependency strings are
supported; optional dependency groups are not inferred as installed. Conditional
Pipfile development entries stay unknown, and partial Python selectors such as
`3.12` are ranges rather than invented `3.12.0` pins. Conditional
markers, prereleases, URLs, dynamic declarations, unsupported constraints and
multiple conflicting lock versions remain unknown/conflicting. Numeric
`==`, `>=`, `>`, `<=`, `<` comma-separated release constraints are supported.
Bare requirements and Poetry `*` are unconstrained numeric release ranges, so
they do not mask a compatible exact lockfile pin.
Explicit versions are additional observations, never silent lockfile overrides.
These are declared constraints, not proof of the running environment.
File-derived observations include the inspected manifest's SHA256, not its
contents or absolute path.

**Selection:** version matches are prioritized, then marginal query-term
coverage, scope diversity and within-scope ordinal rank. Independent BM25
scores are never globally compared. Known version mismatches/conflicts are
omitted; unknown guidance remains explicitly unknown. A match only describes
the declared version range; platform assumptions and API namespaces still need
checking. Stable content IDs change when source fields change; old IDs fail
closed. Duplicate suppression includes all supported facts and applicability
metadata, so different warnings are not merged.

Whole units retain recommendations, preconditions, contraindications,
verification guidance and sources when present; missing fields are explicit.
Oversized units are skipped so a smaller complementary unit may still fit.
`omissions` counts every dropped candidate by budget, duplicate, version
mismatch or version conflict. Counts, rather than an unbounded list of omitted
IDs, keep metadata bounded; source fields not selected into a unit are named
in `omitted_fields` and available through detail expansion. Metadata that
cannot fit causes an explicit error.

The default limit is still **6000 JSON characters**, including metadata but
excluding the CLI newline/MCP envelope; `--max-chars` is an explicit override.
Detail expansion is intentionally full/unpacked. Selection only considers the
rows returned by retrieval: increase `-n`/MCP `max_results` to widen that pool;
`candidate_pool` alone only widens preranking, not delivered rows. `--all`
continues to mean registered domains, not every language stack.

Characters are not token estimates. The benchmark can separately enforce
1k/2k/4k-token budgets using a local hash-pinned target tokenizer; see
[P2 evaluation](../CONTRIBUTING.md#p2-evidence-and-token-budget-evaluation).
No default change or competitive quality claim follows from the small pilot.

Optional embedding/reranker first use may download model data from Hugging Face; queries are evaluated
locally. BM25 never downloads models. Set `HF_HUB_OFFLINE=1` after caching
weights when optional-model execution must also stay offline. Missing optional
packages fall back with a warning and structured metadata; model download,
load or inference errors fail explicitly instead of claiming successful
semantic execution. Benchmarks reject fallback results.

Embedding cache identity includes corpus bytes, searchable columns and pinned
model identity. BM25 checks timestamps and content; copied files with unchanged
timestamps cannot silently retain an old index. Invalid embedding caches are
reported and rebuilt. Existing old cache entries are not reused.

## Recipes

### "I'm starting a new microservice in <X>"

```bash
# 1. Pull the language guidelines
backendpro "production checklist" --stack <stack>

# 2. Choose an architecture
backendpro "team size 10 fast iteration" --domain architecture

# 3. Choose a database
backendpro "OLTP managed multi-region" --domain database

# 4. Choose a broker (if event-driven)
backendpro "ordered exactly once" --domain messaging

# 5. Wire up observability
backendpro "open source apm" --domain observability

# 6. Define resilience defaults
backendpro "retry timeout idempotency" --all
```

### "Production incident — debugging tail latency"

```bash
backendpro "p99 tail latency" --domain performance
backendpro "hedged requests" --domain pattern
backendpro "graceful shutdown kubernetes" --domain reliability
```

### "Migrating monolith to microservices"

```bash
backendpro "strangler fig" --domain pattern
backendpro "modular monolith" --domain architecture
backendpro "anti-corruption layer" --domain pattern
backendpro "saga outbox" --all
```

### "Multi-region active-active"

```bash
backendpro "multi region active-active" --domain scaling
backendpro "consensus raft" --domain consistency
backendpro "global sql" --domain database
backendpro "rpo rto disaster recovery" --domain reliability
```

### "Design a URL shortener (TinyURL)"

```bash
# 1. API style (REST + redirect semantics)
backendpro "API rate limiting REST redirect" --domain api

# 2. Storage — key-value lookup by short code
backendpro "sharding partitioning key-value NoSQL" --domain database

# 3. Caching — cache-aside with TTL + jitter for hot redirects
backendpro "cache read-through write-through TTL" --domain cache

# 4. Scaling — stateless horizontal auto-scaling
backendpro "horizontal scaling stateless" --domain scaling

# 5. Cross-cutting — reliability, patterns, architecture
backendpro "URL shortener system design" --all
```

> Combine the results to produce a full design covering ID generation
> (Snowflake → base62), DynamoDB/Postgres storage, Redis cache-aside with
> jitter, CDN edge caching for 301s, rate limiting, abuse prevention, and
> observability — all wired from day one.

### "Writing an Architecture Decision Record (ADR)"

Use `compare` to generate the tradeoff table directly:

```bash
# Messaging choice
backendpro compare "Kafka" "RabbitMQ" "NATS" --domain messaging

# Database choice
backendpro compare "Postgres" "DynamoDB" "Cassandra" --domain database

# Consistency model
backendpro compare "Linearizable" "Causal Consistency" "Eventual Consistency" --domain consistency
```

Paste the resulting markdown table straight into the ADR's "Options
considered" section.

### "Quarterly knowledge-base audit"

Find and refresh stale entries before they mislead the AI:

```bash
backendpro --stale --domain pattern       --max-age-months 18
backendpro --stale --domain database      --max-age-months 12
backendpro --stale --domain observability --max-age-months 12
```

## Tests, lint, validation (contributors)

```bash
pip install -e ".[dev]"
pytest                          # ranking-quality + unit + edge-case suite
backendpro-validate             # schema-validate every CSV
ruff check src tests            # lint
```

CI runs all three on every PR (Python 3.9 / 3.11 / 3.12).
See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for content & schema rules.

## Integration with AI assistants

### Claude Code

The `.claude/skills/backend-pro-max/SKILL.md` is auto-discovered. The
assistant will run the CLI with the user's question and use the results to
ground its answer.

### Cursor / Windsurf / Copilot / Gemini

Add the contents of `src/backend-pro-max/templates/base/skill-content.md`
(or just a link to the search command) into your editor's rules file:

* Cursor: `.cursor/rules/backend.mdc`
* Windsurf: `.windsurfrules`
* Copilot: `.github/copilot-instructions.md`
* Generic: `AGENTS.md`

Make sure the assistant has shell access in the repo so it can call
`backendpro …`.

### Programmatic use

```python
from backendpro.scripts.core import (
    search, search_stack, search_all, compare, find_stale, clear_cache,
)

# Plain search (auto-detect domain) with synonym expansion + scores
print(search("circuit breaker", domain="pattern"))

# Tighten precision: drop weak hits and stale rows
print(search("service mesh", domain="container",
             min_score=1.5, max_age_months=18))

# Stack-specific guidelines
print(search_stack("virtual threads", "java-spring"))

# Cross-domain
print(search_all("idempotency"))

# Side-by-side comparison (returns a dict ready to render as a table)
print(compare(["Kafka", "RabbitMQ"], domain="messaging"))

# Audit: list rows older than 18 months
print(find_stale("pattern", months=18))

# Long-running process? Indexes invalidate on timestamp or content changes.
# Force a refresh after manual edits:
clear_cache()
```

Every result row carries a `_score` (BM25) field for downstream re-ranking.
