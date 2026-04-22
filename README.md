# backend-pro-max-skill

> A single repo for backend & distributed-systems engineering intelligence —
> usable as an AI skill in Claude Code, Cursor, Windsurf, GitHub Copilot,
> Gemini, Continue, and any other AI coding assistant.

[![20 Domains](https://img.shields.io/badge/domains-20-blue?style=for-the-badge)](#domains)
[![12 Stacks](https://img.shields.io/badge/stacks-12-purple?style=for-the-badge)](#stacks)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-yellow?style=for-the-badge&logo=python&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)

Backend Pro Max gives an AI assistant a **structured, BM25-searchable**
knowledge base for **everything a senior backend / distributed-systems
engineer needs**, modelled after the
[`ui-ux-pro-max-skill`](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
repository structure.

---

## Why?

LLMs know surface-level facts about backend tech, but they:

- Recommend the *trendy* pattern instead of the *right* one for the team / scale.
- Forget timeouts, retries, idempotency, backpressure, and shutdown handling.
- Don't know your stack's idioms (Spring lazy-init pitfalls, FastAPI sync-in-async,
  Express vs Fastify, sqlx compile-time queries, etc.).
- Mix up consistency models, replication modes, and partition strategies.

This skill grounds the model in **curated, opinionated, source-citable**
guidance — and makes the model search it before answering.

---

## Quick start

```bash
# Pure stdlib — no install required
python3 src/backend-pro-max/scripts/search.py --list

# Auto-detect domain
python3 src/backend-pro-max/scripts/search.py "kafka exactly once delivery"

# Explicit domain
python3 src/backend-pro-max/scripts/search.py "circuit breaker" --domain pattern

# Stack-specific guidelines
python3 src/backend-pro-max/scripts/search.py "virtual threads" --stack java-spring

# Cross-domain
python3 src/backend-pro-max/scripts/search.py "idempotency" --all

# JSON output (for tooling / integration)
python3 src/backend-pro-max/scripts/search.py "redis cluster" --json
```

---

## Domains

| Domain          | What's in it                                                      |
|-----------------|-------------------------------------------------------------------|
| `language`      | Go, Java, Kotlin, Python, Rust, Node.js/TS, C#, Scala, Elixir, Ruby, PHP, C++ |
| `pattern`       | Saga, CQRS, Event Sourcing, Outbox, CDC, Circuit Breaker, Bulkhead, Retry, Idempotency, Leader Election, Sidecar, Strangler Fig, ACL, BFF, API Gateway, Rate Limiting, Sharding, Read Replica, Materialized View, Process Manager, Outbox+Inbox, Fan-out / Scatter-Gather |
| `database`      | Postgres, MySQL/Vitess, CockroachDB, Spanner/TiDB, MongoDB, Cassandra/Scylla, DynamoDB, Redis, Memcached, Elastic/OpenSearch, ClickHouse, DuckDB, Snowflake/BigQuery/Redshift, Neo4j/Memgraph, Influx/Timescale/VictoriaMetrics, vector DBs, S3/GCS/Blob, etcd/ZK/Consul, SQLite |
| `messaging`     | Kafka, Redpanda, Pulsar, RabbitMQ, NATS/JetStream, MQTT, SQS, SNS/EventBridge, Kinesis, Pub/Sub, Service Bus / Event Grid / Event Hubs, ZeroMQ |
| `cache`         | In-process LRU, Redis (single + cluster), Memcached, CDN, HTTP cache, read/write/write-back, materialized views, negative caching, Bloom filters, L1+L2 hybrid |
| `cloud`         | AWS / GCP / Azure / Cloudflare service mapping & equivalents      |
| `iac`           | Terraform/OpenTofu, Pulumi, AWS CDK, CloudFormation, Bicep, Ansible, Crossplane, Helm, Kustomize, Packer |
| `container`     | Docker/OCI, Podman, containerd, Kubernetes, EKS/GKE/AKS, Helm, Kustomize, ArgoCD/Flux, Istio/Linkerd/Cilium, Envoy, Karpenter, Nomad, Compose, Testcontainers |
| `observability` | Prometheus, Mimir/Cortex/Thanos/VM, Grafana, Loki, ELK/OpenSearch, Tempo/Jaeger/Zipkin, OpenTelemetry, Pyroscope/Parca, Datadog, New Relic / Honeycomb / Dynatrace, Sentry, Fluent Bit / Vector, PagerDuty / Opsgenie, SLO frameworks |
| `api`           | REST, GraphQL, gRPC, gRPC-Web/Connect, WebSocket, SSE, HTTP/2, HTTP/3, Webhooks, WebSub/ActivityPub, JSON-RPC, SOAP |
| `auth`          | OAuth 2.0 + PKCE, OIDC, JWT, SAML, mTLS, API keys, HMAC signing, sessions, passkeys/WebAuthn, magic links, RBAC/ABAC/ReBAC, SCIM, workload identity (IRSA / WIF) |
| `security`      | OWASP Top 10, CSRF, XSS, SSRF, deserialisation, secrets, supply chain (SLSA, Sigstore), zero-trust, TLS hardening, PII/logging, rate limiting, CORS, SBOM, SAST, DAST/fuzz |
| `cicd`          | GitHub Actions, GitLab CI, Jenkins, CircleCI, Buildkite, Drone, Tekton, Argo Workflows, ArgoCD, Flux, Spinnaker, Argo Rollouts, Renovate/Dependabot, SonarQube, GHAS |
| `testing`       | Unit, component/slice, integration (Testcontainers), contract (Pact), E2E, property-based, fuzz, snapshot, mutation, load, stress/soak, chaos, smoke / synthetic monitoring |
| `architecture`  | Monolith, modular monolith, microservices, serverless/FaaS, event-driven, hexagonal/ports-and-adapters, clean/onion, DDD, CQRS+ES, service mesh, BFF, lambda/kappa, actor model, cell-based |
| `scaling`       | Vertical, horizontal, autoscaling (HPA/KEDA/Karpenter), sharding, read replicas, multi-tier caching, connection pooling, backpressure, bulkhead, hedged requests, load balancing, CDN, geo-distribution, async/queue load levelling, indexing, materialized views, partitioning |
| `consistency`   | Linearizability, sequential, causal, read-your-writes, eventual, SEC/CRDTs, CAP, PACELC, Raft, Paxos, 2PC, snapshot isolation/SSI, quorum, Lamport/vector/HLC clocks |
| `performance`   | N+1, missing indexes, plan regressions, pool exhaustion, GC pauses, hot keys, tail latency, thundering herd, async-blocking, cold starts, leaks, hot-path allocations, JSON serialisation, chatty interfaces, TLS overhead |
| `reliability`   | SLO/SLI/error budget, timeouts, retries+backoff, circuit breaker, bulkhead, idempotency, graceful shutdown, liveness/readiness, capacity & headroom, RPO/RTO, multi-AZ/region, backups + PITR, chaos engineering, runbooks, blue/green & canary, feature flags, per-tenant quotas, postmortems |
| `data`          | Spark, Flink, Kafka Streams/ksqlDB, Airbyte/Fivetran/Stitch/Meltano, dbt, Airflow, Dagster, Prefect, Iceberg/Delta/Hudi, ClickHouse/Druid/Pinot, Spark Streaming + Delta, Debezium, Kafka Connect, LakeFS/Nessie, vector DBs, feature stores |

## Stacks

Each stack file contains tight, opinionated, "what would a staff engineer
say in code review" guidelines — categorised by *Concurrency, HTTP, Errors,
Persistence, Tooling, Observability, Performance, Testing, Build, …* — with
**Do / Don't** and **good vs bad code** examples.

| Stack             | Highlights                                                       |
|-------------------|------------------------------------------------------------------|
| `go`              | `context.Context`, `errgroup`, http.Client reuse, pgx/sqlc, table-driven tests |
| `java-spring`     | Virtual threads (Loom), constructor DI, OSIV off, Flyway, Testcontainers, native image |
| `python-fastapi`  | async-all-the-way, Pydantic v2, httpx, uv, ruff/mypy, structlog, Testcontainers |
| `nodejs-express`  | Fastify > Express, zod at boundaries, Undici pool, pino, OTel, Vitest |
| `rust-axum`       | Tokio + Axum + Tower, sqlx compile-time queries, thiserror/anyhow, tracing, tokio-console |
| `csharp-aspnet`   | Minimal APIs, async-all-the-way, HttpClientFactory, Polly v8, EF Core AsNoTracking, Native AOT |
| `kotlin-spring`   | Coroutines + structured concurrency, Spring Boot Kotlin DSL, Exposed/jOOQ, kotest |
| `scala-akka`      | Pekko (Akka fork), Typed actors, Pekko Streams, Cats Effect / ZIO |
| `elixir-phoenix`  | OTP supervision, GenServer, Task.async_stream, Phoenix LiveView, Broadway, libcluster |
| `ruby-rails`      | Modular Rails (Packwerk), Sidekiq, Puma tuning, Bullet, Rails 7+ defaults, Solid Queue/Cache |
| `php-laravel`     | Octane (Swoole/RoadRunner/FrankenPHP), OPcache+JIT, Horizon, eager loading, PHPStan |
| `cpp`             | C++20+, RAII, jthread/stop_token, coroutines, sanitizers, CMake presets, Conan/vcpkg, GoogleTest, clang-tidy |

---

## Repository structure

See [`CLAUDE.md`](CLAUDE.md) for the full layout. TL;DR:

```
src/backend-pro-max/
├── data/                       # 20 domain CSVs + stacks/ (12 stack CSVs)
├── scripts/                    # core.py (BM25) + search.py (CLI)
└── templates/base/             # skill-content.md & quick-reference.md
.claude/skills/backend-pro-max/ # SKILL.md for Claude Code
.claude-plugin/plugin.json      # Claude marketplace manifest
docs/                           # architecture & usage docs
```

---

## Installation as an AI skill

### Claude Code

Symlink (or copy) the `src/backend-pro-max` directory into your repo at
`.claude/skills/backend-pro-max/` — the `SKILL.md` already lives there. The
agent will discover it automatically.

### Cursor / Windsurf / Continue / Copilot

Copy `src/backend-pro-max/templates/base/skill-content.md` into your editor's
rules file (`.cursor/rules/backend.mdc`, `.windsurfrules`, `AGENTS.md`,
`.github/copilot-instructions.md`, etc.). Make sure the assistant can run
`python3 src/backend-pro-max/scripts/search.py …` in your repo.

### Anywhere else

The CLI is pure Python 3 standard library — clone this repo and run
`python3 src/backend-pro-max/scripts/search.py --list`.

---

## Extending

Adding a new row, a new domain, or a new stack takes ~2 minutes. See
[`CLAUDE.md`](CLAUDE.md) ("Adding new content") and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

PRs welcome — especially for additional stacks (Swift on the server, Erlang
proper, Zig, Crystal, Gleam, …) and new domains (FinOps, ML platform,
edge / WASM, blockchain infra, …).

---

## License

[MIT](LICENSE) © 2025 contributors
