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
| `-n, --max-results N`      | Cap returned rows (default 5)                                         |
| `--min-score F`            | Drop weak matches (BM25 score ≤ F)                                    |
| `--max-age-months N`       | Drop rows whose `Last Updated` is older than N months                 |
| `--no-expand`              | Disable synonym expansion (`partial failure → compensation, saga, …`) |
| `--no-scores`              | Hide BM25 confidence scores in markdown output                        |
| `--json`                   | Machine-readable JSON output                                          |
| `--interactive` / `-i`     | Start the REPL                                                        |
| `--stale`                  | Audit mode (with `--domain` and `--max-age-months`)                   |
| `--list`                   | List domains and stacks                                               |

### Confidence scores

Markdown results carry a per-result confidence label so an AI agent can
gate its trust:

```
### Result 1  _(score: 7.69, confidence: high)_
```

Buckets: `score ≥ 4.0` = **high**, `≥ 1.5` = **medium**, `> 0` = **low**.
Use `--no-scores` to suppress them in human-only output.

### Synonym / hybrid search

Common backend aliases are expanded automatically before ranking, so
plain-English queries reach the right rows even when keywords don't
overlap:

```bash
backendpro "how to handle partial failure across services"
# matches "Saga" / "Circuit Breaker" via partial→compensation, failure→fault
```

Pass `--no-expand` to recover pure-keyword behavior.

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

# Long-running process? Indexes are mtime-cached automatically.
# Force a refresh after manual edits:
clear_cache()
```

Every result row carries a `_score` (BM25) field for downstream re-ranking.
