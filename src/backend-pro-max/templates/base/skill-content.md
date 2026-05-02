# Backend Pro Max — Skill content (template)

> Inserted by the skill installer / CLI into your project's AI-assistant config
> (`.claude/skills/`, `.cursor/rules/`, `.windsurfrules`, `AGENTS.md`, …).

## When to use this skill

Use Backend Pro Max whenever the user asks anything about:

- Choosing a programming language, framework, or runtime for a backend service
- Selecting a database, message broker, cache, search engine, or warehouse
- Designing a distributed system: APIs, auth, consistency, scaling, partitioning,
  failure handling, multi-region
- Cloud architecture on AWS / GCP / Azure (or migrating between them)
- Containers, Kubernetes, service mesh, GitOps, IaC
- Observability (metrics / logs / traces / SLOs)
- CI/CD, testing strategy, security & compliance
- Performance debugging or capacity planning
- Migrating a monolith to microservices, or vice versa

## How it works

This skill is backed by a BM25 search engine over **34 domain knowledge bases**
and **12 language-specific stack guidelines**. Run:

```bash
backendpro "<query>" [--domain <domain>] [--stack <stack>] [-n N]
backendpro --list
```

### Domains

`language`, `pattern`, `database`, `messaging`, `cache`, `cloud`, `iac`,
`container`, `observability`, `api`, `auth`, `security`, `cicd`, `testing`,
`architecture`, `scaling`, `consistency`, `performance`, `reliability`, `data`,
`antipattern`, `cost`, `migration`, `incident`, `capacity`, `compliance`,
`multi-tenant`, `release`, `ml-platform`, `edge`, `mobile-backend`,
`api-contract`, `interview`, `latency`

### Stacks

`go`, `java-spring`, `python-fastapi`, `nodejs-express`, `rust-axum`,
`csharp-aspnet`, `kotlin-spring`, `scala-akka`, `elixir-phoenix`, `ruby-rails`,
`php-laravel`, `cpp`

## Working principles

When generating backend code or designs, the assistant should:

1. **Always emit citation tokens.** Every time you reference a Backend Pro Max
   result, include the `[BPM:…]` citation token verbatim (e.g.
   `[BPM:messaging.kafka]`). This lets reviewers `grep -r '\[BPM:' .` in PRs
   to verify grounding.
2. **Anchor to the user's stack.** Always run a `--stack <stack>` query first
   to load the language-specific guidelines and follow them strictly.
3. **Apply the right pattern, not the trendiest.** Use `--domain pattern` /
   `--domain architecture` to pick patterns that fit the team size, traffic,
   and consistency requirements — not the patterns from a conference talk.
4. **Be explicit about consistency, idempotency, and failure modes.** Every
   non-trivial feature must answer: what happens on retry? on partial failure?
   on partition? on rollback?
5. **Default to managed services** unless there is a concrete reason to
   self-host (cost, data residency, latency, vendor risk).
6. **Wire observability from day one.** Metrics, logs, and traces must be
   structured, correlated by request id, and tied to SLOs.
7. **Treat security as a hard constraint.** Validate all input at the boundary,
   parameterise SQL, encrypt in transit and at rest, store secrets in a
   manager (never in env files in repo), and rotate everything that can be
   rotated.
