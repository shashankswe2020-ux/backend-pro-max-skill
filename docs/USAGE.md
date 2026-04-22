# Usage

## CLI

```bash
python3 src/backend-pro-max/scripts/search.py --help
```

### List domains and stacks

```bash
python3 src/backend-pro-max/scripts/search.py --list
```

### Search a specific domain

```bash
python3 src/backend-pro-max/scripts/search.py "circuit breaker" --domain pattern
python3 src/backend-pro-max/scripts/search.py "wide column multi-region" --domain database
python3 src/backend-pro-max/scripts/search.py "p99 tail latency" --domain performance
```

### Auto-detect the domain

If you omit `--domain`, the tool picks the best one based on keywords:

```bash
python3 src/backend-pro-max/scripts/search.py "kafka exactly once delivery"
# → detected domain: messaging
```

### Stack-specific guidelines

```bash
python3 src/backend-pro-max/scripts/search.py "virtual threads" --stack java-spring
python3 src/backend-pro-max/scripts/search.py "context" --stack go
python3 src/backend-pro-max/scripts/search.py "async" --stack python-fastapi
```

### Cross-domain search

Useful when a concept (idempotency, retries, timeouts) cuts across many
domains:

```bash
python3 src/backend-pro-max/scripts/search.py "idempotency" --all
```

### JSON output

```bash
python3 src/backend-pro-max/scripts/search.py "redis cluster" --json
```

## Recipes

### "I'm starting a new microservice in <X>"

```bash
# 1. Pull the language guidelines
python3 src/backend-pro-max/scripts/search.py "production checklist" --stack <stack>

# 2. Choose an architecture
python3 src/backend-pro-max/scripts/search.py "team size 10 fast iteration" --domain architecture

# 3. Choose a database
python3 src/backend-pro-max/scripts/search.py "OLTP managed multi-region" --domain database

# 4. Choose a broker (if event-driven)
python3 src/backend-pro-max/scripts/search.py "ordered exactly once" --domain messaging

# 5. Wire up observability
python3 src/backend-pro-max/scripts/search.py "open source apm" --domain observability

# 6. Define resilience defaults
python3 src/backend-pro-max/scripts/search.py "retry timeout idempotency" --all
```

### "Production incident — debugging tail latency"

```bash
python3 src/backend-pro-max/scripts/search.py "p99 tail latency" --domain performance
python3 src/backend-pro-max/scripts/search.py "hedged requests" --domain pattern
python3 src/backend-pro-max/scripts/search.py "graceful shutdown kubernetes" --domain reliability
```

### "Migrating monolith to microservices"

```bash
python3 src/backend-pro-max/scripts/search.py "strangler fig" --domain pattern
python3 src/backend-pro-max/scripts/search.py "modular monolith" --domain architecture
python3 src/backend-pro-max/scripts/search.py "anti-corruption layer" --domain pattern
python3 src/backend-pro-max/scripts/search.py "saga outbox" --all
```

### "Multi-region active-active"

```bash
python3 src/backend-pro-max/scripts/search.py "multi region active-active" --domain scaling
python3 src/backend-pro-max/scripts/search.py "consensus raft" --domain consistency
python3 src/backend-pro-max/scripts/search.py "global sql" --domain database
python3 src/backend-pro-max/scripts/search.py "rpo rto disaster recovery" --domain reliability
```

### "Design a URL shortener (TinyURL)"

```bash
# 1. API style (REST + redirect semantics)
python3 src/backend-pro-max/scripts/search.py "API rate limiting REST redirect" --domain api

# 2. Storage — key-value lookup by short code
python3 src/backend-pro-max/scripts/search.py "sharding partitioning key-value NoSQL" --domain database

# 3. Caching — cache-aside with TTL + jitter for hot redirects
python3 src/backend-pro-max/scripts/search.py "cache read-through write-through TTL" --domain cache

# 4. Scaling — stateless horizontal auto-scaling
python3 src/backend-pro-max/scripts/search.py "horizontal scaling stateless" --domain scaling

# 5. Cross-cutting — reliability, patterns, architecture
python3 src/backend-pro-max/scripts/search.py "URL shortener system design" --all
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
`python3 src/backend-pro-max/scripts/search.py …`.

### Programmatic use

```python
from backend_pro_max.scripts.core import search, search_stack, search_all

print(search("circuit breaker", domain="pattern"))
print(search_stack("virtual threads", "java-spring"))
print(search_all("idempotency"))
```

(Treat the package as an importable module if you wire it into a custom
agent.)
