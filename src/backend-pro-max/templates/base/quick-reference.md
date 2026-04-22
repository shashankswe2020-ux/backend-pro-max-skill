# Backend Pro Max — Quick Reference

## Search

```bash
# Auto-detect the domain
python3 src/backend-pro-max/scripts/search.py "kafka exactly once delivery"

# Explicit domain
python3 src/backend-pro-max/scripts/search.py "circuit breaker" --domain pattern

# Language-specific stack guidelines
python3 src/backend-pro-max/scripts/search.py "virtual threads" --stack java-spring

# Cross-domain
python3 src/backend-pro-max/scripts/search.py "idempotency" --all

# JSON output (for tooling)
python3 src/backend-pro-max/scripts/search.py "redis cluster" --json

# List everything
python3 src/backend-pro-max/scripts/search.py --list
```

## Common queries by topic

| Topic                       | Suggested query                                              |
|----------------------------|---------------------------------------------------------------|
| Pick a database             | `--domain database "high write throughput multi-region"`     |
| Pick a message broker       | `--domain messaging "ordered exactly-once high throughput"`  |
| Caching strategy            | `--domain cache "thundering herd"`                            |
| API style (REST/gRPC/etc)   | `--domain api "internal microservices"`                      |
| Auth flow                   | `--domain auth "service-to-service mtls"`                    |
| Resilience pattern          | `--domain pattern "downstream is flaky"`                     |
| Architecture style          | `--domain architecture "small team, fast iteration"`         |
| Scaling technique           | `--domain scaling "read-heavy postgres"`                     |
| Consistency model           | `--domain consistency "collaborative editing offline"`       |
| Performance bug             | `--domain performance "tail latency p99"`                    |
| Reliability practice        | `--domain reliability "graceful shutdown kubernetes"`        |
| Cloud service mapping       | `--domain cloud "managed kafka aws"`                         |
| IaC tool                    | `--domain iac "policy as code"`                              |
| Container / orchestration   | `--domain container "service mesh ebpf"`                     |
| CI/CD                       | `--domain cicd "gitops k8s"`                                 |
| Observability               | `--domain observability "open source apm"`                   |
| Security                    | `--domain security "ssrf"`                                   |
| Testing                     | `--domain testing "contract test microservices"`             |
| Data engineering            | `--domain data "streaming lakehouse"`                        |
| Pick a language             | `--domain language "low-latency cpu-bound network proxy"`    |

## Stack guidelines (per language)

```bash
python3 src/backend-pro-max/scripts/search.py "<query>" --stack <stack>
```

Available stacks: `go`, `java-spring`, `python-fastapi`, `nodejs-express`,
`rust-axum`, `csharp-aspnet`, `kotlin-spring`, `scala-akka`,
`elixir-phoenix`, `ruby-rails`, `php-laravel`, `cpp`.
