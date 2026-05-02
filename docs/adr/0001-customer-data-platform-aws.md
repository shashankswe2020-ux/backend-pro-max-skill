# ADR 0001 — Scalable Customer Data Platform on AWS for self-serve analytics

| Field | Value |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-05-02 |
| **Owners** | Platform / Data Engineering |
| **Constraint** | **AWS only** (existing footprint, compliance posture, org standardisation) |
| **Skill** | Drafted with `backend-pro-max` (search-grounded; citations in §6) |

---

## 1. Context

### 1.1 Problem

The organisation has customer signal scattered across:

- **Product** — clickstream / app events (web SDK, mobile SDKs, server-side)
- **Transactional systems** — orders, billing, subscriptions (Postgres / Aurora)
- **SaaS tools** — CRM (Salesforce), support (Zendesk), marketing (Braze, Marketo), payments (Stripe)
- **Server logs** — auth events, feature flags, A/B assignments

Today every team that wants an answer files a ticket with data engineering. Analytics throughput is gated on a 4-person team. **Marketing, Product, CX and Finance need to self-serve** against a **single, governed, fresh, trustworthy view of the customer** — and the questions they ask **change weekly**, so the platform must absorb new sources, new dimensions, and new activation targets without a re-platform every quarter.

### 1.2 Functional requirements

| # | Requirement | Notes |
|---|---|---|
| FR1 | Ingest **real-time product events** from web, mobile, server-side SDKs | <60s end-to-end freshness |
| FR2 | Ingest **CDC streams** from operational databases (Aurora Postgres, RDS MySQL) | Log-based, no app changes |
| FR3 | Ingest **SaaS sources** via managed connectors | Schema evolution handled automatically |
| FR4 | **Identity resolution** — stitch anonymous → known across devices, emails, phone, accounts | Deterministic + probabilistic, governed `golden_customer_id` |
| FR5 | **Self-serve SQL** for analysts, PMs, marketers — governed semantic layer | dbt models + BI tool with row/column ACLs |
| FR6 | **Self-serve dashboards & ad-hoc exploration** without a ticket | Sub-second BI; sub-10s ad-hoc |
| FR7 | **Activation / reverse-ETL** — push audiences and traits back to Salesforce, Braze, Marketo, ads platforms | Sub-15-min sync |
| FR8 | **ML feature store** for online (sub-10ms) + offline (training) feature consumption | Single source of truth, no train/serve skew |
| FR9 | **Right-to-deletion / consent** workflows end-to-end | GDPR / CCPA, ≤30-day SLA |
| FR10 | **Lineage + catalog + data quality** visible to every consumer | Column-level lineage |

### 1.3 Non-functional requirements (target scale, year-1)

| Dimension | Target | Notes |
|---|---:|---|
| Event ingest rate | **12k events/sec avg, 36k peak** (~1B events/day @ 3× peak factor) | Per [BPM:capacity.qps-from-daily-active-users] |
| Event payload (avg) | 2 KB | After SDK enrichment |
| Raw landed bytes | ~2 TB/day → ~720 TB/yr (Parquet/ZSTD: ~400 GB/day, ~150 TB/yr) | 5× compaction assumed |
| Customer cardinality | 50M unique resolved customers | |
| Concurrent analyst queries | 200 concurrent, 5 queries/hr each | ≈ 14 RPU-equivalents avg, sized 32 base / 256 max |
| Freshness — streaming gold | **< 60s** p95 (event → activated audience) | KDS + Flink path |
| Freshness — warehouse gold | **< 15 min** p95 (CDC + dbt incremental) | DMS + dbt micro-batches |
| Query latency — BI dashboard | **< 2s p95** | Pre-aggregated gold marts |
| Query latency — ad-hoc SQL | **< 10s p95 / < 60s p99** | Redshift Serverless on Iceberg |
| Availability | 99.9% control plane, 99.95% serving | Multi-AZ; not multi-region in v1 |
| RPO / RTO | RPO 15 min / RTO 4 hr | S3 cross-region replication for gold; warehouse rebuildable from lake |
| Compliance | GDPR, CCPA, SOC2, PCI scope minimised by tokenising PAN at SDK | Per [BPM:compliance.data-residency], [BPM:compliance.data-retention-and-deletion], [BPM:compliance.encryption-at-rest], [BPM:compliance.consent-management] |

### 1.4 What "evolving needs" means architecturally

The key word in the request is **evolving**. The platform must be cheap to **add a source**, **add a dimension**, **add a consumer**, **add a transformation**, **add a destination** — without a re-platform. That rules out:

- A monolithic warehouse with hand-coded ETL (every new source = a JIRA quarter)
- A pure-streaming Kappa stack (every new ad-hoc question = a new Flink job)
- A SaaS CDP product that locks the schema to its model (Segment-style "track/identify" forces every new dimension through a vendor envelope)

The **lakehouse + warehouse hybrid** below decouples *raw capture* (cheap, schema-on-read) from *governed serving* (warehouse, schema-on-write), so new questions are answered in SQL on top of bronze/silver, and only stable patterns get promoted to gold.

### 1.5 Anti-patterns we explicitly avoid

| Anti-pattern | How we avoid it |
|---|---|
| **Dual writes** to DB and stream [BPM:antipattern.dual-writes] | CDC from the DB log only; never write app→DB and app→Kafka in the same handler |
| **Polling instead of events** [BPM:antipattern.polling-instead-of-events] | Event-driven ingest; CDC; activation via change-stream-on-gold, not nightly diffs |
| **Shared-database integration** [BPM:antipattern.shared-database-integration] | Consumers read the warehouse / Iceberg, never the OLTP DB |
| **Missing idempotency keys** [BPM:antipattern.missing-idempotency-key] | Every event carries `event_id` (UUIDv7); SDK generates, gold layer dedupes on it |
| **Time-based cache invalidation only** [BPM:antipattern.time-based-cache-invalidation-only] | Materialised views invalidated by event arrival, not TTL |
| **Generic error swallowing** [BPM:antipattern.generic-error-swallowing] | DLQs on every Kinesis/SQS hop; quarantine bucket on dbt test failures |

---

## 2. Decision

**Build a streaming-lakehouse + warehouse CDP on AWS, with Iceberg as the open table format, Redshift Serverless as the SQL warehouse, Flink on Managed Service for Apache Flink as the streaming engine, and Lake Formation as the governance plane. Activation runs as Step Functions + Lambda jobs against gold tables. Identity resolution is a hybrid deterministic-streaming + probabilistic-batch pipeline.**

This is a **Lambda/Kappa hybrid** [BPM:architecture.lambda-kappa-architecture] (the streaming and batch paths share storage in S3/Iceberg; only the compute engines differ).

### 2.1 Architecture

```
                    ┌────────── Sources ──────────┐
                    │                              │
   Web/Mobile/Server SDKs ──► API GW ──► Lambda ──┐│
                    │                              ││
   Aurora/RDS  ──► AWS DMS (CDC, log-based)  ─────┤│
                    │                              ││           ┌────── Streaming compute ──────┐
   SaaS (Salesforce, Braze, Stripe) ──► Fivetran ┐││           │                                │
                    │ (managed EL → S3)        │  ││           │  Managed Service for Apache    │
                    │                          │  ▼▼           │  Flink (KDA Flink)             │
                    │                       ┌──────────────┐   │   - identity resolution        │
                    │                       │ Kinesis Data │──►│   - real-time aggregations     │
                    │                       │ Streams      │   │   - audience triggers          │
                    │                       │ (on-demand)  │   │                                │
                    │                       └──────┬───────┘   └─────────────┬──────────────────┘
                    │                              │                         │
                    │                              ▼                         ▼
                    │                       ┌──────────────┐         ┌──────────────────┐
                    │                       │ Kinesis      │         │ DynamoDB         │
                    │                       │ Firehose     │         │ - golden_id map  │
                    │                       │ (→ S3 raw)   │         │ - online features│
                    │                       └──────┬───────┘         └────────┬─────────┘
                    │                              │                          │
                    │                              ▼                          │
                    │       ┌────────── S3 + Apache Iceberg (lakehouse) ──────┴────┐
                    │       │  bronze/  (raw, append-only, partitioned by event_dt)│
                    │       │  silver/  (typed, deduped, conformed dims)           │
                    │       │  gold/    (modelled marts, identity-stitched)        │
                    │       │  Glue Data Catalog · Lake Formation row/col ACLs     │
                    │       └────────────┬───────────────┬────────────────┬────────┘
                    │                    │               │                │
                    │             ┌──────▼─────┐   ┌─────▼──────┐  ┌──────▼─────────┐
                    │             │ EMR        │   │ Redshift   │  │ Athena         │
                    │             │ Serverless │   │ Serverless │  │ (SQL on        │
                    │             │ (Spark:    │   │ (warehouse,│  │  Iceberg, ad-  │
                    │             │  prob.     │   │  dbt-built │  │  hoc explore)  │
                    │             │  identity, │   │  marts)    │  │                │
                    │             │  ML feats) │   │            │  │                │
                    │             └──────┬─────┘   └──┬─────┬───┘  └────────┬───────┘
                    │                    │            │     │               │
                    │                    ▼            ▼     ▼               ▼
                    │       ┌─────────────────────────────────────────────────────┐
                    │       │  Consumers                                          │
                    │       │  · QuickSight (governed BI + Q natural-language)    │
                    │       │  · Redshift Data API → Hex/Lightdash (self-serve)   │
                    │       │  · SageMaker Feature Store (online + offline)       │
                    │       │  · Step Functions + Lambda → Salesforce/Braze/...   │
                    │       │      (reverse-ETL activation)                       │
                    │       │  · MWAA (Airflow) for orchestration + dbt + EMR     │
                    │       └─────────────────────────────────────────────────────┘
                    │
                    └─ Cross-cutting: Lake Formation · Glue · Macie (PII) · KMS · CloudTrail
                       · CloudWatch + Managed Prometheus + Managed Grafana
                       · OpenLineage events → DataHub on EKS (catalog + column lineage)
```

### 2.2 Component decisions

| # | Layer | Decision | AWS service(s) | Rationale (citation) |
|---|---|---|---|---|
| **D1** | Event ingest (HTTP) | API Gateway (HTTPS) → Lambda validator → Kinesis Data Streams **on-demand mode** | API GW, Lambda, KDS | Managed log; per-shard ordering; on-demand auto-scales without capacity planning [BPM:cloud.kinesis-data-streams] [BPM:messaging.aws-kinesis-data-streams] [BPM:cloud.lambda] |
| **D2** | DB CDC | AWS DMS (binlog/WAL) → Kinesis Data Streams | DMS, KDS | Log-based CDC; preserves transactional ordering; no app changes [BPM:pattern.change-data-capture-cdc] [BPM:migration.change-data-capture-cdc] [BPM:data.debezium] |
| **D3** | SaaS ingest | Fivetran (managed EL) → S3 raw | S3, Fivetran (3rd-party SaaS, AWS-hosted) | Buy not build — connector breadth + schema-evolution handling is not a moat [BPM:data.airbyte-fivetran-stitch-meltano] |
| **D4** | Raw landing | Kinesis Firehose → S3 bronze (Parquet, ZSTD, partitioned by `event_date`/`source`) | Firehose, S3 | Strong consistency since 2020; lifecycle tiers for cost [BPM:database.s3-gcs-azure-blob] |
| **D5** | Table format | **Apache Iceberg** (bronze/silver/gold zones) | Iceberg + Glue Catalog | Strongest cross-engine momentum on AWS — Athena, Redshift, EMR Spark, Flink all read/write [BPM:data.iceberg-delta-lake-hudi] |
| **D6** | Streaming compute | **Apache Flink** on Managed Service for Apache Flink (formerly KDA) | MSAF | Best-in-class event-time semantics; exactly-once with KDS source + Iceberg sink [BPM:data.apache-flink] |
| **D7** | Batch / probabilistic ML | EMR Serverless (Spark) for nightly probabilistic identity-resolution + ML feature recompute | EMR Serverless | Pragmatic Spark choice when Flink is over-rotated for batch [BPM:data.apache-spark] [BPM:data.spark-structured-streaming-delta] |
| **D8** | Warehouse | **Redshift Serverless** (auto-scale RPUs) | Redshift Serverless | Columnar; managed; reads Iceberg natively; no cluster ops [BPM:database.snowflake-bigquery-redshift] |
| **D9** | Ad-hoc SQL on lake | Athena workgroups (per-team, per-query bytes-scanned cap) | Athena | Serverless SQL on Iceberg directly; analysts query bronze/silver without warehouse load |
| **D10** | Modelling layer | **dbt-core** on MWAA, materialising into Redshift gold marts | MWAA + dbt | SQL+Jinja transforms with tests, docs, lineage; standard for the T in EL-T [BPM:data.dbt] |
| **D11** | Orchestration | MWAA (Managed Airflow) for dbt runs, Spark jobs, activation jobs | MWAA | Mature DAG semantics; dbt + Spark + Lambda all first-class operators |
| **D12** | Identity resolution — hot path | Flink stateful job, deterministic match on hashed `email` / `phone` / `user_id` → writes `golden_id` map to **DynamoDB** (online) and Iceberg (offline) | Flink + DynamoDB + Iceberg | Sub-10ms online lookups [BPM:cloud.dynamodb] |
| **D13** | Identity resolution — cold path | Nightly EMR Serverless Spark job: probabilistic match (LSH + scoring), reconciles drift, writes to same Iceberg `golden_id_map` table | EMR Serverless | Iceberg ACID semantics make merge-with-conflict safe |
| **D14** | Self-serve BI | **QuickSight** (governed dashboards) + **QuickSight Q** (NL→SQL) on top of Redshift gold + dbt semantic layer | QuickSight | AWS-native; Lake Formation ACLs respected; Q gives marketers/PMs NL exploration |
| **D15** | Self-serve SQL workbench | Redshift Data API + a thin internal web app (Hex-style) on EKS Fargate; or Lightdash if buying | Redshift Data API + EKS | Pure-AWS path; analysts get notebook UX without the JDBC dance |
| **D16** | Activation (reverse-ETL) | Step Functions express workflows triggered by EventBridge schedule + Iceberg row-stream; per-destination Lambda adapters (Salesforce, Braze, Marketo, Meta Ads) | Step Functions + Lambda + EventBridge | Workflow engine for durable multi-step processes [BPM:pattern.process-manager-orchestrator] [BPM:cloud.sns-eventbridge] |
| **D17** | ML feature store | **SageMaker Feature Store** — online (DynamoDB-backed) + offline (S3 / Iceberg) | SageMaker FS | Single source of truth eliminates training-serving skew [BPM:ml-platform.feature-store] [BPM:ml-platform.training-serving-skew] |
| **D18** | Governance & ACLs | **Lake Formation** (row/column ACLs) + Glue Catalog + IAM Identity Center for SSO | Lake Formation, Glue, IAM IdC | Tenant- and team-level isolation without forking storage [BPM:multi-tenant.cross-tenant-analytics] |
| **D19** | PII discovery + masking | Macie scans bronze/silver; SDK-side tokenisation of `email`/`phone` (HMAC-SHA256 with per-tenant pepper); Lake Formation column-level redaction for restricted roles | Macie + KMS + Lake Formation | PII never reaches logs raw [BPM:security.privacy] |
| **D20** | Catalog + lineage | **DataHub** on EKS, fed by OpenLineage events from Spark, dbt, Airflow, Flink | EKS Fargate + DataHub | No AWS-native equivalent at column-lineage parity (Glue Catalog is metadata-only) |
| **D21** | Data quality | dbt tests + Glue Data Quality (DQDL) at silver→gold boundary; failures route to a quarantine S3 prefix + PagerDuty | dbt + Glue DQ | Catches schema/distribution drift before it hits dashboards [BPM:ml-platform.data-validation] |
| **D22** | Encryption | KMS CMKs per-tenant for S3, Redshift, DynamoDB, Firehose, Kinesis; rotation 90 days | KMS | Per [BPM:compliance.encryption-at-rest] |
| **D23** | Right-to-deletion | Iceberg row-level deletes + scheduled compaction; reverse-ETL emits suppression events to all downstream destinations within 30 days | Iceberg + Step Functions | Per [BPM:compliance.data-retention-and-deletion] |
| **D24** | Idempotency | Every event carries `event_id` (UUIDv7); silver dedupes on `(event_id, source)`; gold uses Iceberg merge-on-read | SDK + Iceberg | Per [BPM:antipattern.missing-idempotency-key] |
| **D25** | Schema management | Glue Schema Registry (Avro for KDS payloads); contract tests in CI; `expand-contract` migrations for warehouse schema | Glue Schema Registry | [BPM:api-contract.protobuf-schema-registry] [BPM:api-contract.schema-evolution-backward-compatible] [BPM:release.database-migration-safety] [BPM:migration.expand-contract-schema] |
| **D26** | Observability | CloudWatch (infra) + Managed Prometheus + Managed Grafana (app metrics) + OpenSearch Serverless (log search); SLOs per pipeline stage | CloudWatch + AMP + AMG + OpenSearch | [BPM:observability.elk-opensearch] |
| **D27** | IaC | Terraform (workspaces per env) for AWS resources + Helm for the EKS-resident services (DataHub, internal SQL workbench) | Terraform + Helm | Standard org tooling; Crossplane considered and rejected (over-rotation for a data team) [BPM:iac.crossplane] |
| **D28** | Multi-tenant model | **Pool model** for shared raw/silver with `tenant_id` partition + Lake Formation row filters; **Bridge model** for sensitive tenants (per-tenant Iceberg DB + dedicated Redshift namespace) | Lake Formation + Iceberg | [BPM:multi-tenant.pool-model-shared-everything] [BPM:multi-tenant.bridge-model-hybrid] |
| **D29** | Cost guard rails | Athena workgroup bytes-scanned cap; Redshift Serverless RPU max-cap per workgroup; daily Iceberg compaction; S3 Intelligent-Tiering on bronze, lifecycle to Glacier on >365d gold; FinOps tags `(env, team, dataset, tenant)` | — | [BPM:cost.finops-tagging-strategy] [BPM:cost.cross-az-data-transfer] [BPM:cost.internet-egress] |
| **D30** | Backups / DR | S3 versioning + cross-region replication on gold zone; Redshift snapshots (auto, 7-day retention); warehouse is rebuildable from lake (single source of truth is Iceberg gold) | S3 CRR + Redshift snapshots | RPO 15 min, RTO 4 hr [BPM:reliability.recovery] |

### 2.3 Capacity sizing (year-1 anchor)

| Subsystem | Sizing | Working |
|---|---|---|
| KDS shards | **On-demand mode**; equivalent to ~70 provisioned shards at peak | 36k events/sec × 2KB = 72 MB/s; KDS shard = 1 MB/s write → 72 shards. On-demand removes the capacity calc but informs $$. |
| KDS cost (peak) | ~$8k/mo at peak | On-demand: $0.04 / GB ingested + $0.0125 / shard-hour equivalent |
| Firehose → S3 | ~2 TB/day raw → ~400 GB/day Parquet+ZSTD (5× compaction) | Buffer: 128 MB or 60s |
| S3 storage (yr-1) | bronze ~150 TB · silver ~80 TB · gold ~10 TB | Lifecycle: bronze→IA after 90d, →Glacier after 365d |
| Redshift Serverless | base 32 RPU · max 256 RPU · two workgroups (analyst / activation) | 200 concurrent × 5 q/hr × 30s avg = 14 RPU avg load; 5× headroom for spikes |
| DynamoDB (golden_id map) | 50M items × ~200 B = ~10 GB; on-demand mode | Sub-10ms p99 lookup [BPM:cloud.dynamodb] |
| Cross-AZ transfer (KDS, Redshift, MSAF) | ~$2k/mo at peak | All in 3 AZs in one region; biggest line item after compute [BPM:cost.cross-az-data-transfer] |
| EMR Serverless (nightly identity + ML feats) | ~3 hr/night × 200 vCPU avg | Spot-equivalent pricing |
| **Total infra (yr-1, steady state)** | **~$45–60k/mo** | Dominated by Redshift Serverless + S3 + KDS + Firehose + DataHub on EKS |

---

## 3. Alternatives Considered

| # | Alternative | Why rejected |
|---|---|---|
| **A1** | **Pure-Redshift everything** — no lakehouse; load all sources directly into Redshift; transform in-warehouse | Storage and compute coupled; replays are expensive (re-load from source); cross-engine reuse impossible; ML training pulls from warehouse over the network. Loses the cheap append-only raw layer that makes "evolving needs" affordable. |
| **A2** | **Snowflake on AWS** | Best-in-class warehouse, but **violates the AWS-only constraint** (separate vendor, separate billing, separate IAM, separate audit surface, separate SOC2 attestation). Re-evaluate at year 3 if Redshift Serverless economics fail. |
| **A3** | **Pure Kappa (streaming-only)** — Flink everywhere, no warehouse; analysts query materialised stream views | Forces every new ad-hoc question through a Flink job — kills self-serve. Flink is the right tool for *known* aggregations, not exploration. We use Flink for the streaming gold path only. |
| **A4** | **Pure batch (warehouse-only, nightly EL/T)** | Cheapest option, but freshness ≥ 6 hours kills FR1, FR7. Activation against day-old audiences is operationally useless for Marketing/CX. |
| **A5** | **EMR Spark Structured Streaming + Delta Lake** | Single-engine simplicity (one Spark for batch + stream), but **Delta on AWS is a second-class citizen** vs Iceberg — Athena, Redshift, and Glue Catalog all have native Iceberg support; Delta requires a manifest-export workaround. Iceberg also has stronger cross-engine momentum [BPM:data.iceberg-delta-lake-hudi]. |
| **A6** | **MSK (managed Kafka) instead of KDS** | Higher per-shard throughput; richer ecosystem (Kafka Streams, Connect, Schema Registry). Rejected for v1 because KDS on-demand removes capacity planning entirely; KDS integrates natively with Firehose, Lambda, MSAF. **Revisit at sustained >100 MB/s** or if we need Kafka-Connect connectors not in DMS/Fivetran. [BPM:cloud.kinesis-data-streams] vs [BPM:messaging.apache-kafka]. |
| **A7** | **Self-host Kafka on EC2** | Violates "default to managed" working principle; ops cost (cluster, ZK/KRaft, rebalances) is real and unrewarded at our scale. |
| **A8** | **CDP-as-a-product (Segment / RudderStack / mParticle)** | Fast time-to-value but: (a) recurring per-event cost scales linearly — at 1B events/day we'd pay multiple $M/yr; (b) schema is locked to vendor's `track/identify/group` model — fights "evolving needs"; (c) raw-event export still needs a warehouse — we'd own the lakehouse anyway. Buy the *connectors* (Fivetran for SaaS), build the platform. |
| **A9** | **Self-hosted Hightouch/Census-style reverse-ETL** | Strong product but adds a SaaS vendor. We can build a thin Step Functions + Lambda equivalent for our 8 destinations in 2 sprints; revisit if destinations grow past 30. |
| **A10** | **Pure CQRS + Event Sourcing on the OLTP side** to feed the CDP | Architecturally elegant but forces a re-platform of OLTP for the sake of analytics. CDC delivers the same stream-of-changes signal without touching application code [BPM:architecture.cqrs-event-sourcing]. |
| **A11** | **No identity-resolution layer; rely on `user_id` only** | Fails on the cross-device, anonymous-to-known, and multi-account-per-customer cases — the entire "single view of the customer" thesis. Identity resolution is the load-bearing primitive. |
| **A12** | **Skip the warehouse; use Athena + Iceberg only** | Athena alone struggles at 200-concurrent-analyst load; per-query latency variability hurts BI dashboards. Redshift Serverless materialises the gold marts for sub-2s BI. Athena stays for ad-hoc on bronze/silver. |
| **A13** | **Single-tenant pool table for everything** | Simplest, but blocks future B2B multi-tenant SaaS use cases and complicates Lake Formation row filters. Pool + Bridge hybrid (D28) keeps the door open without paying silo cost upfront [BPM:multi-tenant.silo-model-shared-nothing]. |
| **A14** | **Multi-region active-active from day 1** | Cost and complexity ~3× for a year-1 v1. Single region (`us-east-1`) with cross-region S3 replication on gold satisfies the RPO/RTO targets. Promote to multi-region when the org has a region-redundancy requirement. |

---

## 4. Consequences

### 4.1 Positive

- **Self-serve unlocked.** Analysts, PMs, marketers query gold marts in QuickSight / Redshift Data API without filing tickets; QuickSight Q gives non-SQL users NL→SQL on the same governed semantic layer. Throughput limit is no longer the data team's headcount.
- **Evolves cheaply.** Adding a source = a Fivetran connector or a new Kinesis producer. Adding a dimension = a dbt model. Adding a destination = a Lambda. Adding a question = a SQL query against silver/gold. The platform shape doesn't change.
- **Single source of truth.** Iceberg gold is the canonical store; Redshift, SageMaker Feature Store, and reverse-ETL all read from it — eliminating the multi-warehouse-of-truth drift that kills CDPs at scale.
- **Streaming + batch share storage.** The Lambda/Kappa split is *only at the compute layer*; both write to the same Iceberg tables. No reconciliation job needed.
- **Governance-first, not bolted on.** Lake Formation row/column ACLs, Macie PII scans, OpenLineage column lineage, and SDK-side tokenisation are all in v1 — not a year-2 retrofit.
- **Idempotency, schema evolution, dedup are first-class.** Iceberg + Glue Schema Registry + UUIDv7 event IDs cover the load-bearing data-correctness primitives.
- **No dual-write hazard.** CDC on the DB log is the *only* path from OLTP → CDP [BPM:antipattern.dual-writes].

### 4.2 Negative / what we give up

- **AWS lock-in.** Mitigated partially: Iceberg is open and portable to GCP/Azure/Databricks; dbt SQL is portable; Flink is portable. The lock-in concentrates in KDS, DynamoDB, MSAF, Step Functions, QuickSight, Lake Formation, MWAA — re-platforming cost ~6 months if the org ever decides to leave AWS.
- **Operational surface is wider than a "buy a SaaS CDP" alternative.** We own MWAA, Flink jobs, EMR Serverless, dbt, Iceberg compaction, Lake Formation policies, DataHub on EKS. Mitigated by using managed flavours of every component and leaning on Terraform for repeatability.
- **Cost will surprise the org if FinOps is lazy.** Redshift Serverless RPUs and Athena bytes-scanned can run away in a weekend without per-workgroup caps. D29 is non-negotiable, not aspirational. [BPM:cost.finops-tagging-strategy].
- **Reverse-ETL on Step Functions + Lambda is less ergonomic than Hightouch/Census** for non-engineers. Marketers can't author syncs themselves; they file a request. Acceptable for v1 (8 destinations); revisit at 30+.
- **Identity resolution accuracy is a long-tail problem** with no "done" state. We need quality metrics (false-positive merges, false-negative splits) instrumented from day 1, with manual-review queues for borderline matches.
- **Glue Catalog is metadata-only** — no column-lineage UI. We carry DataHub on EKS (one more thing to operate) until AWS ships parity (DataZone is closing the gap but isn't there yet at column-lineage depth).
- **Single region in v1.** A `us-east-1` outage degrades the platform to read-only on the cross-region-replicated gold zone for the duration. Acceptable per SLA; revisit if the org commits to a multi-region OLTP plane.

### 4.3 Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Identity resolution accuracy regressions | High | Medium — wrong audiences, bad personalisation | Quality metrics in v1: precision / recall against a labelled set; nightly drift dashboard; manual-review queue |
| Redshift Serverless cost runaway | High | High | Per-workgroup RPU max-cap; query monitoring rules ("kill if > 5 min"); weekly FinOps review; QuickSight dashboards isolated from ad-hoc workgroup |
| Kinesis shard hot-keying (one tenant dominates) | Medium | Medium — head-of-line blocking | Composite partition key `(tenant_id, event_id)`; monitor `IncomingBytes` per shard; shard-split on hot-key alarm |
| Schema evolution breaks downstream dashboards | High | Medium | Glue Schema Registry compatibility checks in CI; dbt contracts on gold models; `expand-contract` migrations [BPM:release.database-migration-safety] |
| DMS replication slot growth on Postgres source | Medium | High — source DB disk fills | Alarm on `replication_slot_size`; runbook for slot drop + full reload; secondary read-replica as DMS source [BPM:incident.database-failover-incident] |
| Iceberg compaction failure → query slowness | Medium | Low–Medium | Daily compaction job on EMR Serverless; alarm on file-count-per-partition > threshold |
| PII leak via SDK or log misconfig | Low | **Critical** | SDK-side tokenisation; Macie continuous scan; structured logging with field allow-list; quarterly red-team audit [BPM:security.privacy] |
| Right-to-deletion SLA breach | Medium | High (regulatory) | Iceberg row-deletes + scheduled compaction in deletion pipeline; reverse-ETL suppression jobs; deletion-receipt audit log per request [BPM:compliance.data-retention-and-deletion] |
| Cross-AZ transfer cost balloon | Medium | Medium | Workload placement in single AZ where possible (consumers + KDS); periodic FinOps review [BPM:cost.cross-az-data-transfer] |

### 4.4 Day-2 operations

- **Runbooks** for: KDS shard rebalance, DMS replication-slot recovery, Iceberg compaction failure, Redshift Serverless WLM saturation, Lake Formation policy rollback, MWAA worker exhaustion, Macie alert triage, deletion-pipeline failure.
- **SLOs per stage**: ingest p99 < 5s, KDS → S3 < 60s, silver → gold < 15 min, dashboard query < 2s, activation sync < 15 min, deletion fulfilment < 30 days.
- **On-call**: data-platform team owns ingest, lakehouse, warehouse, governance. Per-pipeline alerting routes to dataset-owning team via PagerDuty (FinOps tag `team` is the routing key).
- **Severity matrix** per [BPM:incident.severity-matrix-definition]; data-corruption events default SEV1 [BPM:incident.data-corruption].

### 4.5 Build sequence (recommended)

| Phase | Weeks | Deliverable |
|---|---|---|
| 0 — Foundations | 1–4 | Terraform skeleton; KMS, IAM Identity Center, VPC, Glue Catalog, Lake Formation policies, S3 zones, Iceberg tables, MWAA, FinOps tags |
| 1 — Ingest | 5–10 | KDS + Firehose; SDK rollout (web first); DMS for one source DB; Fivetran for top 3 SaaS; bronze populated; observability dashboards |
| 2 — Transform & warehouse | 11–14 | dbt project skeleton; silver layer (typed + deduped); first gold marts; Redshift Serverless + QuickSight wired up; first 3 dashboards live |
| 3 — Identity | 15–18 | Flink deterministic-match job; nightly EMR probabilistic-match; `golden_id_map` in DynamoDB + Iceberg; quality metrics dashboard |
| 4 — Activation | 19–22 | Step Functions reverse-ETL; first 3 destinations (Salesforce, Braze, Marketo); suppression-event flow |
| 5 — Self-serve & ML | 23–26 | QuickSight Q; SageMaker Feature Store; DataHub catalog go-live; analyst onboarding; FinOps review cadence |
| 6 — Hardening | 27–30 | Macie tuning; deletion-pipeline drills; multi-region S3 replication on gold; load test to 2× peak; chaos drills (KDS shard loss, Redshift workgroup failover) |

Total: ~30 weeks (7 months) with a 4–5 person team.

---

## 5. Open questions

1. **dbt Cloud or dbt-core on MWAA?** Cloud is faster to onboard, but dbt-core on MWAA stays AWS-pure and is cheaper at scale. Default = dbt-core unless onboarding pain dominates.
2. **DataHub vs AWS DataZone** at month 12? DataZone is improving fast; reassess column-lineage parity at year-end.
3. **Customer-360 `golden_id_map` ownership** — does the platform team own the resolution rules, or does each domain team contribute? Recommend platform-owned with a contribution model in year 2.
4. **Multi-tenant workgroup-per-tenant isolation in Redshift** at what tenant-count threshold? Default = pool until any single tenant breaches 20% of warehouse spend, then promote to dedicated namespace (D28 bridge model).
5. **Streaming SQL surface for analysts** (e.g. Flink SQL workbench) — defer to year 2 unless analysts explicitly ask.

---

## 6. References

### 6.1 Backend Pro Max knowledge base (search-grounded)

- **Architecture** — [BPM:architecture.lambda-kappa-architecture], [BPM:architecture.event-driven-architecture], [BPM:architecture.cqrs-event-sourcing]
- **Patterns** — [BPM:pattern.change-data-capture-cdc], [BPM:pattern.transactional-outbox], [BPM:pattern.cqrs], [BPM:pattern.process-manager-orchestrator], [BPM:pattern.sharding]
- **Data** — [BPM:data.iceberg-delta-lake-hudi], [BPM:data.apache-flink], [BPM:data.apache-spark], [BPM:data.spark-structured-streaming-delta], [BPM:data.dbt], [BPM:data.debezium], [BPM:data.airbyte-fivetran-stitch-meltano], [BPM:data.dagster], [BPM:data.lakefs-nessie]
- **Cloud (AWS)** — [BPM:cloud.kinesis-data-streams], [BPM:cloud.s3], [BPM:cloud.lambda], [BPM:cloud.dynamodb], [BPM:cloud.rds-aurora], [BPM:cloud.elasticache-memorydb], [BPM:cloud.eks], [BPM:cloud.sns-eventbridge], [BPM:cloud.sqs]
- **Database** — [BPM:database.snowflake-bigquery-redshift], [BPM:database.s3-gcs-azure-blob], [BPM:database.clickhouse], [BPM:database.duckdb], [BPM:database.redis]
- **Messaging** — [BPM:messaging.aws-kinesis-data-streams], [BPM:messaging.apache-kafka], [BPM:messaging.aws-sns-eventbridge]
- **Antipatterns** — [BPM:antipattern.dual-writes], [BPM:antipattern.polling-instead-of-events], [BPM:antipattern.shared-database-integration], [BPM:antipattern.missing-idempotency-key], [BPM:antipattern.time-based-cache-invalidation-only], [BPM:antipattern.generic-error-swallowing]
- **Multi-tenant** — [BPM:multi-tenant.cross-tenant-analytics], [BPM:multi-tenant.pool-model-shared-everything], [BPM:multi-tenant.bridge-model-hybrid], [BPM:multi-tenant.silo-model-shared-nothing], [BPM:multi-tenant.tenant-data-export-and-portability]
- **API contracts** — [BPM:api-contract.protobuf-schema-registry], [BPM:api-contract.schema-evolution-backward-compatible], [BPM:api-contract.asyncapi-for-event-driven-apis]
- **ML platform** — [BPM:ml-platform.feature-store], [BPM:ml-platform.training-serving-skew], [BPM:ml-platform.data-validation], [BPM:ml-platform.model-registry]
- **Compliance** — [BPM:compliance.data-residency], [BPM:compliance.data-retention-and-deletion], [BPM:compliance.encryption-at-rest], [BPM:compliance.consent-management]
- **Security** — [BPM:security.privacy]
- **Cost** — [BPM:cost.finops-tagging-strategy], [BPM:cost.cross-az-data-transfer], [BPM:cost.internet-egress], [BPM:cost.data-transfer-between-regions]
- **Migration & release** — [BPM:migration.change-data-capture-cdc], [BPM:migration.expand-contract-schema], [BPM:release.database-migration-safety], [BPM:release.rollback-strategy]
- **Reliability & incident** — [BPM:reliability.recovery], [BPM:incident.data-corruption], [BPM:incident.database-failover-incident], [BPM:incident.severity-matrix-definition]
- **Capacity** — [BPM:capacity.qps-from-daily-active-users], [BPM:capacity.cache-size-estimation], [BPM:capacity.replication-bandwidth]
- **Observability** — [BPM:observability.elk-opensearch]
- **IaC** — [BPM:iac.crossplane]

### 6.2 AWS official documentation

- Kinesis Data Streams — https://docs.aws.amazon.com/streams/latest/dev/
- S3 — https://docs.aws.amazon.com/AmazonS3/latest/userguide/
- Lambda — https://docs.aws.amazon.com/lambda/latest/dg/
- DynamoDB — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/
- RDS / Aurora — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/
- EKS — https://docs.aws.amazon.com/eks/latest/userguide/
- SQS — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/

### 6.3 Open-source / vendor

- Apache Iceberg — https://iceberg.apache.org/docs/latest/
- Apache Flink — https://nightlies.apache.org/flink/flink-docs-stable/
- Apache Spark Structured Streaming — https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
- dbt — https://docs.getdbt.com/docs/introduction
- Airbyte — https://docs.airbyte.com/
- LakeFS — https://docs.lakefs.io/

---

> **TL;DR** — Build a streaming-lakehouse + warehouse hybrid on AWS: Kinesis + DMS + Fivetran into S3/Iceberg (bronze/silver/gold), Flink for the streaming gold path, EMR Serverless + dbt for batch, Redshift Serverless + Athena + QuickSight for self-serve, Step Functions + Lambda for activation, SageMaker Feature Store for ML. Lake Formation + Macie + DataHub provide governance, lineage, and PII safety from day 1. Open table format (Iceberg) keeps the lock-in concentrated in the compute and orchestration plane, not the data plane. ~30 weeks to v1 with a 4–5 person team; ~$45–60k/mo at year-1 scale (1B events/day, 50M customers, 200 concurrent analysts).
