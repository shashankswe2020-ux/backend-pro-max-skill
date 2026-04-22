<div align="center">

# 🚀 Backend Pro Max

### *A staff-engineer-in-a-box for your AI coding assistant*

**Curated, BM25-searchable backend & distributed-systems intelligence**
across **20 domains** and **12 language stacks** — drop it into Claude Code,
Cursor, Windsurf, GitHub Copilot, Gemini, Continue, or any AI assistant.

<br />

[![20 Domains](https://img.shields.io/badge/domains-20-blue?style=for-the-badge)](#-domains)
[![12 Stacks](https://img.shields.io/badge/stacks-12-purple?style=for-the-badge)](#-stacks)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-yellow?style=for-the-badge&logo=python&logoColor=white)](#-prerequisites)
[![Zero Dependencies](https://img.shields.io/badge/deps-stdlib_only-orange?style=for-the-badge)](#-prerequisites)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=for-the-badge)](#-contributing)

<br />

[**Quick Start**](#-quick-start) ·
[**Domains**](#-domains) ·
[**Stacks**](#-stacks) ·
[**Install as a Skill**](#-installation-as-an-ai-skill) ·
[**Examples**](#-example-queries) ·
[**Contributing**](#-contributing)

</div>

---

## ✨ What is this?

> **Backend Pro Max** grounds your AI coding assistant in **opinionated,
> source-citable, senior-engineer-grade** knowledge for backend &
> distributed-systems work — and forces it to *search before answering.*

LLMs know surface-level facts about backend tech, but they:

- 🎯 Recommend the *trendy* pattern instead of the *right* one for your team / scale.
- ⏱️ Forget timeouts, retries, idempotency, backpressure, and graceful shutdown.
- 🧩 Don't know your stack's idioms — Spring lazy-init pitfalls, FastAPI sync-in-async,
  Express vs Fastify, sqlx compile-time queries, EF Core change tracking, …
- 🔀 Mix up consistency models, replication modes, and partition strategies.
- 🛡️ Skip the boring-but-critical stuff: SLOs, error budgets, runbooks, PII in logs.

This skill fixes that with a **structured, searchable** knowledge base that the
model is *instructed* to consult — so its advice cites a row, not a vibe.

---

## 🎁 What you get

| | |
|---|---|
| 📚 **20 domain knowledge bases** | Languages · Patterns · Databases · Messaging · Cache · Cloud · IaC · Containers · Observability · API · Auth · Security · CI/CD · Testing · Architecture · Scaling · Consistency · Performance · Reliability · Data |
| 🛠️ **12 stack guidelines** | Go · Java/Spring · Python/FastAPI · Node/Express · Rust/Axum · C#/ASP.NET · Kotlin/Spring · Scala/Akka · Elixir/Phoenix · Ruby/Rails · PHP/Laravel · C++ |
| 🔎 **Pure-Python BM25 search** | No installs, no models, no network — just `python3`. |
| 🤖 **Drop-in skill files** | `SKILL.md` for Claude Code · `skill-content.md` for Cursor / Windsurf / Copilot / Gemini / Continue |
| 📐 **Do / Don't + Code examples** | Each row contains good vs bad code, severity, and a docs URL |
| 🧠 **Auto domain detection** | Skip `--domain` and the engine picks the right CSV from your query |
| ⚙️ **JSON output mode** | First-class integration with tool-calling agents and MCP servers |

---

## ⚡ Quick start

```bash
# 0. No install needed — pure Python 3.8+ stdlib
python3 src/backend-pro-max/scripts/search.py --list

# 1. Auto-detect the domain from the query
python3 src/backend-pro-max/scripts/search.py "kafka exactly once delivery"

# 2. Constrain to a specific domain
python3 src/backend-pro-max/scripts/search.py "circuit breaker" --domain pattern

# 3. Stack-specific guidance
python3 src/backend-pro-max/scripts/search.py "virtual threads" --stack java-spring

# 4. Cross-domain search
python3 src/backend-pro-max/scripts/search.py "idempotency" --all

# 5. JSON output (great for agents / MCP)
python3 src/backend-pro-max/scripts/search.py "redis cluster" --json
```

> 💡 **Tip:** the search engine ranks results with **BM25** over the search columns
> of each CSV, with light keyword-based domain auto-detection when `--domain`
> is omitted.

---

## 🧭 Example queries

A taste of what to ask — these all return ranked, citable rows:

| Domain          | Try this                                                                 |
|-----------------|--------------------------------------------------------------------------|
| 🧬 `pattern`     | `"saga vs 2pc for distributed transactions"`                             |
| 🗄️ `database`    | `"postgres index on jsonb"` · `"dynamodb single table design"`           |
| 📨 `messaging`   | `"kafka exactly once"` · `"sqs vs sns vs eventbridge"`                   |
| ⚡ `cache`       | `"thundering herd"` · `"negative caching with redis"`                    |
| ☁️ `cloud`       | `"aws gcp azure equivalent of pubsub"`                                   |
| 🛰️ `observability` | `"slo error budget alerting"` · `"otel trace context propagation"`     |
| 🔐 `security`    | `"ssrf prevention"` · `"sigstore supply chain"`                          |
| 🧪 `testing`     | `"contract testing pact"` · `"testcontainers postgres"`                  |
| 🏗️ `architecture` | `"modular monolith vs microservices"`                                   |
| 📈 `scaling`     | `"hedged requests"` · `"backpressure"`                                   |
| ⚖️ `consistency` | `"linearizability vs sequential"` · `"PACELC"`                           |
| 🛡️ `reliability` | `"graceful shutdown"` · `"circuit breaker timeouts"`                     |

---

## 📚 Domains

| Domain          | What's in it                                                      |
|-----------------|-------------------------------------------------------------------|
| 🧠 `language`      | Go, Java, Kotlin, Python, Rust, Node.js/TS, C#, Scala, Elixir, Ruby, PHP, C++ |
| 🧩 `pattern`       | Saga, CQRS, Event Sourcing, Outbox, CDC, Circuit Breaker, Bulkhead, Retry, Idempotency, Leader Election, Sidecar, Strangler Fig, ACL, BFF, API Gateway, Rate Limiting, Sharding, Read Replica, Materialized View, Process Manager, Outbox+Inbox, Fan-out / Scatter-Gather |
| 🗄️ `database`      | Postgres, MySQL/Vitess, CockroachDB, Spanner/TiDB, MongoDB, Cassandra/Scylla, DynamoDB, Redis, Memcached, Elastic/OpenSearch, ClickHouse, DuckDB, Snowflake/BigQuery/Redshift, Neo4j/Memgraph, Influx/Timescale/VictoriaMetrics, vector DBs, S3/GCS/Blob, etcd/ZK/Consul, SQLite |
| 📨 `messaging`     | Kafka, Redpanda, Pulsar, RabbitMQ, NATS/JetStream, MQTT, SQS, SNS/EventBridge, Kinesis, Pub/Sub, Service Bus / Event Grid / Event Hubs, ZeroMQ |
| ⚡ `cache`         | In-process LRU, Redis (single + cluster), Memcached, CDN, HTTP cache, read/write/write-back, materialized views, negative caching, Bloom filters, L1+L2 hybrid |
| ☁️ `cloud`         | AWS / GCP / Azure / Cloudflare service mapping & equivalents      |
| 🏗️ `iac`           | Terraform/OpenTofu, Pulumi, AWS CDK, CloudFormation, Bicep, Ansible, Crossplane, Helm, Kustomize, Packer |
| 📦 `container`     | Docker/OCI, Podman, containerd, Kubernetes, EKS/GKE/AKS, Helm, Kustomize, ArgoCD/Flux, Istio/Linkerd/Cilium, Envoy, Karpenter, Nomad, Compose, Testcontainers |
| 📊 `observability` | Prometheus, Mimir/Cortex/Thanos/VM, Grafana, Loki, ELK/OpenSearch, Tempo/Jaeger/Zipkin, OpenTelemetry, Pyroscope/Parca, Datadog, New Relic / Honeycomb / Dynatrace, Sentry, Fluent Bit / Vector, PagerDuty / Opsgenie, SLO frameworks |
| 🔌 `api`           | REST, GraphQL, gRPC, gRPC-Web/Connect, WebSocket, SSE, HTTP/2, HTTP/3, Webhooks, WebSub/ActivityPub, JSON-RPC, SOAP |
| 🔑 `auth`          | OAuth 2.0 + PKCE, OIDC, JWT, SAML, mTLS, API keys, HMAC signing, sessions, passkeys/WebAuthn, magic links, RBAC/ABAC/ReBAC, SCIM, workload identity (IRSA / WIF) |
| 🛡️ `security`      | OWASP Top 10, CSRF, XSS, SSRF, deserialisation, secrets, supply chain (SLSA, Sigstore), zero-trust, TLS hardening, PII/logging, rate limiting, CORS, SBOM, SAST, DAST/fuzz |
| 🔁 `cicd`          | GitHub Actions, GitLab CI, Jenkins, CircleCI, Buildkite, Drone, Tekton, Argo Workflows, ArgoCD, Flux, Spinnaker, Argo Rollouts, Renovate/Dependabot, SonarQube, GHAS |
| 🧪 `testing`       | Unit, component/slice, integration (Testcontainers), contract (Pact), E2E, property-based, fuzz, snapshot, mutation, load, stress/soak, chaos, smoke / synthetic monitoring |
| 🏛️ `architecture`  | Monolith, modular monolith, microservices, serverless/FaaS, event-driven, hexagonal/ports-and-adapters, clean/onion, DDD, CQRS+ES, service mesh, BFF, lambda/kappa, actor model, cell-based |
| 📈 `scaling`       | Vertical, horizontal, autoscaling (HPA/KEDA/Karpenter), sharding, read replicas, multi-tier caching, connection pooling, backpressure, bulkhead, hedged requests, load balancing, CDN, geo-distribution, async/queue load levelling, indexing, materialized views, partitioning |
| ⚖️ `consistency`   | Linearizability, sequential, causal, read-your-writes, eventual, SEC/CRDTs, CAP, PACELC, Raft, Paxos, 2PC, snapshot isolation/SSI, quorum, Lamport/vector/HLC clocks |
| 🚀 `performance`   | N+1, missing indexes, plan regressions, pool exhaustion, GC pauses, hot keys, tail latency, thundering herd, async-blocking, cold starts, leaks, hot-path allocations, JSON serialisation, chatty interfaces, TLS overhead |
| 🛟 `reliability`   | SLO/SLI/error budget, timeouts, retries+backoff, circuit breaker, bulkhead, idempotency, graceful shutdown, liveness/readiness, capacity & headroom, RPO/RTO, multi-AZ/region, backups + PITR, chaos engineering, runbooks, blue/green & canary, feature flags, per-tenant quotas, postmortems |
| 🧮 `data`          | Spark, Flink, Kafka Streams/ksqlDB, Airbyte/Fivetran/Stitch/Meltano, dbt, Airflow, Dagster, Prefect, Iceberg/Delta/Hudi, ClickHouse/Druid/Pinot, Spark Streaming + Delta, Debezium, Kafka Connect, LakeFS/Nessie, vector DBs, feature stores |

---

## 🛠️ Stacks

Each stack file contains tight, opinionated, *"what would a staff engineer
say in code review"* guidelines — categorised by **Concurrency, HTTP, Errors,
Persistence, Tooling, Observability, Performance, Testing, Build, …** — with
**✅ Do / ❌ Don't** plus **good vs bad code** examples.

| Stack             | Highlights                                                       |
|-------------------|------------------------------------------------------------------|
| 🐹 `go`              | `context.Context`, `errgroup`, `http.Client` reuse, pgx/sqlc, table-driven tests |
| ☕ `java-spring`     | Virtual threads (Loom), constructor DI, OSIV off, Flyway, Testcontainers, native image |
| 🐍 `python-fastapi`  | async-all-the-way, Pydantic v2, httpx, uv, ruff/mypy, structlog, Testcontainers |
| 🟢 `nodejs-express`  | Fastify > Express, zod at boundaries, Undici pool, pino, OTel, Vitest |
| 🦀 `rust-axum`       | Tokio + Axum + Tower, sqlx compile-time queries, thiserror/anyhow, tracing, tokio-console |
| 🟪 `csharp-aspnet`   | Minimal APIs, async-all-the-way, HttpClientFactory, Polly v8, EF Core AsNoTracking, Native AOT |
| 🟧 `kotlin-spring`   | Coroutines + structured concurrency, Spring Boot Kotlin DSL, Exposed/jOOQ, kotest |
| 🔺 `scala-akka`      | Pekko (Akka fork), Typed actors, Pekko Streams, Cats Effect / ZIO |
| 💧 `elixir-phoenix`  | OTP supervision, GenServer, `Task.async_stream`, Phoenix LiveView, Broadway, libcluster |
| 💎 `ruby-rails`      | Modular Rails (Packwerk), Sidekiq, Puma tuning, Bullet, Rails 7+ defaults, Solid Queue/Cache |
| 🐘 `php-laravel`     | Octane (Swoole/RoadRunner/FrankenPHP), OPcache+JIT, Horizon, eager loading, PHPStan |
| ➕ `cpp`             | C++20+, RAII, jthread/stop_token, coroutines, sanitizers, CMake presets, Conan/vcpkg, GoogleTest, clang-tidy |

---

## 🤖 How AI agents use this

A typical interaction inside Claude Code, Cursor, Copilot, etc.:

```
👤  "Add retries to our outbound HTTP client without melting the dependency."

🤖  → search.py "retry backoff jitter circuit breaker" --domain reliability
    → search.py "http client retries" --stack <your stack>
    → answers with: exponential backoff + jitter, max attempts, idempotency
      key requirement, circuit breaker around it, budgeted timeout, plus
      a code snippet using the right library for your stack — and cites
      the row(s) it pulled from.
```

The skill files (`SKILL.md` / `skill-content.md`) instruct the agent to:

1. **Search first** — never guess when a row exists.
2. **Cite the row** (domain + key) so reviewers can verify.
3. **Prefer stack guidelines** for code-shaped answers.
4. **Combine multiple domains** for cross-cutting concerns (e.g. a "saga"
   answer pulls from `pattern` + `messaging` + `consistency` + `reliability`).

---

## 📁 Repository structure

See [`CLAUDE.md`](CLAUDE.md) for the full layout. TL;DR:

```
src/backend-pro-max/
├── data/                       # 20 domain CSVs + stacks/ (12 stack CSVs)
│   ├── languages.csv  patterns.csv  databases.csv  messaging.csv …
│   └── stacks/
│       └── go.csv  java-spring.csv  python-fastapi.csv  …
├── scripts/
│   ├── core.py                 # BM25 engine + domain auto-detection
│   └── search.py               # CLI entry point
└── templates/base/
    ├── skill-content.md        # Drop-in rules for any AI assistant
    └── quick-reference.md      # Cheatsheet

.claude/skills/backend-pro-max/  # Claude Code skill (SKILL.md)
.claude-plugin/plugin.json       # Claude marketplace manifest
docs/                            # ARCHITECTURE.md & USAGE.md
```

---

## 🔌 Installation as an AI skill

<details open>
<summary><strong>🟣 Claude Code</strong></summary>

Symlink (or copy) the `src/backend-pro-max` directory into your repo at
`.claude/skills/backend-pro-max/` — the `SKILL.md` already lives there. The
agent will discover it automatically.

```bash
mkdir -p .claude/skills
ln -s "$(pwd)/src/backend-pro-max" .claude/skills/backend-pro-max
```
</details>

<details>
<summary><strong>🟦 Cursor / Windsurf / Continue / GitHub Copilot / Gemini</strong></summary>

Copy `src/backend-pro-max/templates/base/skill-content.md` into your editor's
rules file:

| Tool             | Rules file                                  |
|------------------|---------------------------------------------|
| Cursor           | `.cursor/rules/backend.mdc`                 |
| Windsurf         | `.windsurfrules`                            |
| Continue         | `AGENTS.md`                                 |
| GitHub Copilot   | `.github/copilot-instructions.md`           |
| Gemini Code Assist | `GEMINI.md`                              |

Make sure the assistant can run `python3 src/backend-pro-max/scripts/search.py …`
in your repo.
</details>

<details>
<summary><strong>⚙️ Anywhere else (CLI / scripts / MCP)</strong></summary>

The CLI is pure Python 3 standard library — clone this repo and run:

```bash
python3 src/backend-pro-max/scripts/search.py --list
python3 src/backend-pro-max/scripts/search.py "redis cluster" --json
```

The `--json` output makes it trivial to wire into an MCP tool, a custom
agent loop, or any CI step.
</details>

---

## ✅ Prerequisites

- **Python 3.8+** — that's it. No `pip install`, no virtualenv, no models.
- Works on Linux, macOS, Windows (WSL/native), and inside containers.

---

## 🧪 Smoke test

```bash
python3 src/backend-pro-max/scripts/search.py --list
python3 src/backend-pro-max/scripts/search.py "circuit breaker"
python3 src/backend-pro-max/scripts/search.py "virtual threads" --stack java-spring
python3 src/backend-pro-max/scripts/search.py "idempotency" --all
```

---

## 🧱 Extending

Adding a new row, a new domain, or a new stack takes ~2 minutes.

| Want to add…       | Steps                                                                 |
|--------------------|-----------------------------------------------------------------------|
| 📝 **A new row**       | Append to the relevant `data/<domain>.csv` (keep column order).       |
| 🆕 **A new domain**    | Add `data/<domain>.csv`, register in `CSV_CONFIG` + `_DOMAIN_KEYWORDS` in `core.py`. |
| 🧱 **A new stack**     | Add `data/stacks/<stack>.csv`, register in `STACK_CONFIG` in `core.py`. |

Full details in [`CLAUDE.md`](CLAUDE.md) (*"Adding new content"*) and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 🤝 Contributing

PRs welcome — especially for:

- 🆕 **New stacks**: Swift on the server, Erlang/OTP, Zig, Crystal, Gleam, Deno, Bun, …
- 🌐 **New domains**: FinOps, ML platform, edge / WASM, blockchain infra, mobile-backend, …
- 🧠 **More rows** in existing CSVs (with `Do`, `Don't`, code, severity, and a docs URL).
- 🐛 **Corrections** — if a recommendation is dated or wrong, open a PR with the source.

Please follow the [Git workflow in `CLAUDE.md`](CLAUDE.md#git-workflow):

1. Branch from `main` (`feat/...` or `fix/...`).
2. Commit with a clear message.
3. Open a PR — never push directly to `main`.

---

## ❓ FAQ

<details>
<summary><strong>Does this need an internet connection?</strong></summary>

No. The CLI is offline-first, pure Python stdlib. The only network calls
are whatever the AI assistant itself makes.
</details>

<details>
<summary><strong>Why CSV instead of YAML / JSON / SQLite?</strong></summary>

CSV diffs cleanly in PRs, opens in any editor / spreadsheet, and is trivial
to parse with stdlib. Search is BM25 over the configured columns.
</details>

<details>
<summary><strong>How is this different from a generic "rules" file?</strong></summary>

A flat rules file forces the model to keep everything in context. This skill
makes the model **search** a structured KB on demand — so it scales to
hundreds of rows across 20+ domains without bloating the prompt.
</details>

<details>
<summary><strong>Can I use it from an MCP server / tool-calling agent?</strong></summary>

Yes — use `--json` and parse the result. Each row includes the citation key,
domain, summary, do/don't, code samples, severity, and docs URL.
</details>

---

## 📜 License

[MIT](LICENSE) © 2025 contributors

<div align="center">

<sub>Built for the engineers who *actually* ship distributed systems.
If this saves you one outage, ⭐ the repo.</sub>

</div>
