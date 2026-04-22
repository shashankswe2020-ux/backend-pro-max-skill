# Usage

## Install

```bash
pip install -e .
```

This registers the `backendpro` CLI command.

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

### JSON output

```bash
backendpro "redis cluster" --json
```

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
from backendpro.scripts.core import search, search_stack, search_all

print(search("circuit breaker", domain="pattern"))
print(search_stack("virtual threads", "java-spring"))
print(search_all("idempotency"))
```

(Treat the package as an importable module if you wire it into a custom
agent.)
