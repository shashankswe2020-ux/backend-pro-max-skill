# Incident Domain Review - 2026-09-29

## Scope and Method

- Owned files: `src/backend-pro-max/data/incident.csv` and this ledger only.
- Reviewed all 15 original entries against primary SRE, cloud, tool, and standards sources fetched with `fetch_webpage`; added 4 entries for a total of 19.
- Preserved the 11-column schema and original row names, order, categories, and severity labels. Severity labels are examples to map to local impact policy, not universal classifications.
- Set all 19 reviewed rows to `2026-09-29` and populated `Source Type` using the repository enum. This is a review date, not a source publication date or proof that a production runbook has been exercised.
- Read the backend-pro-max skill. Its CLI search workflow was not run because this task explicitly prohibits terminal commands. No tests, shared files, commits, or pushes were touched.
- Primary sources establish behavior and operational principles. Additional containment, authorization, confidentiality, and verification safeguards are conservative reviewer synthesis, not promises that a vendor provides those controls automatically.

## Findings Addressed

1. Failover advice did not establish write ownership or acknowledge topology-specific behavior. Added verified fencing, client reconnection, uncertain-commit reconciliation, authorized regional failover, and safe failback conditions. Removed blanket synchronous-replication and monthly-test prescriptions.
2. Kafka scaling advice omitted partition and offset hazards. Removed blind partition increases and unsupported no-loss assurances; added polling, downstream capacity, retention, and ordering checks.
3. Unqualified heap capture and fleet restarts could worsen availability. Added explicit Node.js snapshot risk and controlled mitigation with capacity safeguards.
4. DNS IP fallback and blanket partner exemptions could bypass safety boundaries. Replaced them with scoped diagnosis, rehearsed routing, retained TLS validation, and bounded throttling changes.
5. Binary rollback was presented without persistent-state compatibility. Added compatibility checks and separate data repair when needed.
6. Incident templates asserted recovery actions, cause, data safety, or ETA without evidence. Replaced assertions with verified-state placeholders and explicit unknowns. Removed universal communication and postmortem deadlines.

## Source Ledger

Every source identifier below refers to content successfully fetched on 2026-09-29. Each CSV row retains one primary URL; this ledger records supporting sources and limits. Original rows are listed in their retained order.

| Entry | Sources and verified basis | Revision and unresolved deployment details |
| --- | --- | --- |
| Severity Matrix Definition | S3: measurable local severity definitions and audience-specific escalation; S1: early incident declaration. | SEV1-SEV4 is a convention. Exact impact thresholds and escalation deadlines require local policy. |
| IMOC/Incident Commander Role | S1: commander owns undelegated roles; separate operations and communications; coordinated changes and live state document. | Removed absolute prohibition on debugging. Staffing and rotation arrangements remain local. |
| Database Failover Incident | S4: RDS Multi-AZ DB instance failover events, transaction recovery delays, DNS changes, and reconnection; S5: old-primary fencing; S8: unknown side effects and safe retries. | RDS instance behavior is not generalized to Aurora, Multi-AZ clusters, or asynchronous read replicas. Engine, topology, recovery time, and possible lost or uncertain commits must be measured. |
| Kafka Consumer Lag Spike | S10: partition parallelism, per-partition offsets, partition changes do not redistribute old data, offset-reset controls; S9: polling configuration and delivery-loss risk with new partitions and `latest`. | Advice is scoped to ordinary consumer groups, not share groups. Kafka 4.1 docs were reviewed; deployed client/broker version, retention, skew, commit semantics, and downstream capacity are unknown. |
| Memory Leak in Production | S11: Node.js snapshots block the main thread, may double heap memory, and may crash the process; S6: overload memory growth and restart/cold-cache risks. | Node.js-specific behavior is labeled. Other runtime profiling costs, actual leak cause, and safe spare capacity require runtime evidence. Snapshot confidentiality is an operational safeguard. |
| Certificate Expiration | S12: renewal scheduling uses issued lifetime; Secret deletion is not the recommended manual rotation method; applications must reload changed certificate material. | Monitor served certificates as well as renewal. Issuer, installed cert-manager version, renewal margin, chain, and application reload behavior remain deployment-specific. No fixed certificate lifetime or key-rotation default is asserted. |
| DNS Resolution Failure | S13: resolver versus authoritative diagnosis, delegation/DNSSEC failures, filtering, and cached answers. | Removed generic IP fallback. Preserving private DNS and TLS identity is a safety requirement; no untested multi-provider switch or DNSSEC-disable production fix is prescribed. Exact cache convergence is unknown. |
| Cascading Failure | S6: overload feedback, retry amplification, load shedding, cold-cache risks, canary restarts, and gradual recovery. | Mitigation uses already tested controls. Traffic priorities, capacity, and acceptable degraded behavior are local decisions. |
| Deployment Rollback | S14: mixed-version compatibility, persistent-format hazards, two-phase changes, and upgrade/downgrade testing. | Binary rollback is conditional and does not reverse data mutations. The safe target, migration reversibility, and any forward repair require application-owner review. |
| Cloud Region Outage | S17: RPO/RTO-based strategy, recovery capacity, caution with automatic triggers, prepared recovery controls, and data resynchronization before failback; S5: single-writer fencing. | Multi-AZ is not region-loss protection. Targets are distinguished from observed recovery and loss. Active-active conflict handling differs from single-writer fencing; actual topology and failover authority remain local. |
| Rate Limiting Incident | S15: aggregation keys, rule logs, preview mode, false-positive bans, and approximate enforcement; S16: 429 may include Retry-After; S8: bounded safe retries. | No automatic Retry-After support is assumed for Cloud Armor. Identity trust, rule precedence, capacity, and exception lifetime require verification. Retain overload protection rather than blanket exemptions. |
| Data Corruption | S7: replication propagates corrupt writes, recovery-point limitations, cross-store invariants, and end-to-end restore tests; S1: containment and evidence preservation. | Removed guarantee that all corrupt writes have stopped. Containment effectiveness, clean recovery point, later valid writes, and downstream repairs require evidence. |
| Third-Party API Outage | S8: connection/request timeouts, retry amplification, idempotency, uncertain side effects, and circuit-breaker tradeoffs; S6: pretested degraded modes. | Do not attribute a local failure to the provider prematurely. Stale-data permission and authorization safety are reviewer safeguards; exact API idempotency contracts must be checked before replay. |
| Blameless Postmortem Process | S2: predefined triggers, contributing causes, constructive review, follow-up actions, sharing, and exclusion of identifying user information. | Removed universal 48-hour requirement. Owner, due date, publication scope, and effectiveness checks need local agreement. |
| Status Page Communication | S3: prompt acknowledgment, named communications role, known impact, ongoing updates, audience selection, and security/legal coordination. | Removed universal five-minute acknowledgment and 48-hour RCA promises. A vendor cadence recommendation is not a contractual SLA. Local cadence, disclosure obligations, and recovery evidence remain required. |
| Split-Brain Containment and Writer Fencing (added) | S5: restarted old primary must not retain primary status; external HA tooling and tested procedures are needed; former primary must be prepared as standby. | Explicit single-writer scope. DNS routing is not writer fencing. Actual fencing proof and divergent-write reconciliation require the installed HA system's runbook; no generic promotion command is offered. |
| Point-in-Time Recovery Verification (added) | S18: RDS instance PITR creates a separate instance, available restore window, configuration defaults, and engine caveats; S7: end-to-end recovery and invariant checks; S6: gradual traffic restoration. | A completed restore is not a verified application recovery. Isolation, keys/access, configuration, side-effect reconciliation, and cutover must be checked. RDS instance mechanics do not cover Aurora clusters or every database engine. |
| Incident Shift Handoff (added) | S1: live briefing, explicit acceptance before departure, announced command transfer, and planned relief. | Local shift overlap and escalation coverage are unspecified; assigning a new name without acknowledgment is not sufficient. |
| Incident Communications Dependency Failure (added) | S1: recognized command post, live incident log, and avoiding reliance on the service being repaired; S3: preplanned layered communication channels. | Fallback independence must include real access dependencies and rehearsal. Approved channel, contact availability, record reconciliation, and confidentiality are local operational safeguards. |

## Primary References

- S1: [Google SRE - Managing Incidents](https://sre.google/sre-book/managing-incidents/) (`book`): roles, declaration, live state, handoffs, evidence, and coordination dependencies.
- S2: [Google SRE - Postmortem Culture](https://sre.google/sre-book/postmortem-culture/) (`book`): triggers, blameless review, actions, and sanitized sharing.
- S3: [Atlassian - Incident Communication](https://www.atlassian.com/incident-management/incident-communication) (`official-docs`): local severity definitions, audiences, communication roles, templates, and cadence.
- S4: [Amazon RDS - Multi-AZ DB Instance Failover](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.Failover.html) (`official-docs`): events, recovery variability, DNS, and connections.
- S5: [PostgreSQL - Warm Standby Failover](https://www.postgresql.org/docs/current/warm-standby-failover.html) (`official-docs`): fencing, external HA tooling, standby recreation, and rehearsal. The fetched `current` page identified PostgreSQL 18; this alias can move.
- S6: [Google SRE - Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) (`book`): retries, overload, cold caches, mitigation, and recovery ramps.
- S7: [Google SRE - Data Integrity](https://sre.google/sre-book/data-integrity/) (`book`): replication limits, recovery points, invariants, and restore testing.
- S8: [AWS Builders' Library - Timeouts, Retries, and Backoff with Jitter](https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter) (`engineering-blog`): timeout semantics, retry budgets, idempotency, and uncertain side effects.
- S9: [Apache Kafka 4.1 - Consumer Configs](https://kafka.apache.org/41/configuration/consumer-configs/) (`official-docs`): polling, offset reset, and group-protocol distinctions.
- S10: [Apache Kafka 4.1 - Basic Kafka Operations](https://kafka.apache.org/41/operations/basic-kafka-operations/) (`official-docs`): partition changes, position inspection, and offset resets.
- S11: [Node.js - Using Heap Snapshot](https://nodejs.org/en/learn/diagnostics/memory/using-heap-snapshot) (`official-docs`): pause, memory, crash, and diagnostic endpoint risks.
- S12: [cert-manager - Certificate Resource](https://cert-manager.io/docs/usage/certificate/) (`official-docs`): renewal, Secrets, and serving renewed certificates.
- S13: [Google Public DNS - Troubleshooting](https://developers.google.com/speed/public-dns/docs/troubleshooting) (`official-docs`): resolution, delegation, DNSSEC, and caching diagnosis.
- S14: [AWS Builders' Library - Ensuring Rollback Safety During Deployments](https://builder.aws.com/content/3F04j2yRAAMBuPSPs50xwXZqg01/ensuring-rollback-safety-during-deployments) (`engineering-blog`): compatibility and upgrade/downgrade tests.
- S15: [Google Cloud Armor - Rate Limiting Overview](https://docs.cloud.google.com/armor/docs/rate-limiting-overview) (`official-docs`): keys, logs, preview, bans, and enforcement scope.
- S16: [RFC 6585 Section 4 - HTTP 429](https://www.rfc-editor.org/rfc/rfc6585.html#section-4) (`rfc`): Retry-After is optional, not guaranteed.
- S17: [AWS Well-Architected REL13-BP02 - Recovery Strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html) (`official-docs`): DR selection, safe initiation, routing, and failback.
- S18: [Amazon RDS - Point-in-Time Restore](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html) (`official-docs`): separate target, restore window, defaults, and engine-specific restrictions.

## Fetch Gaps and Validation Limits

- The attempted AWS whitepaper URL `https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/recovery-options-in-the-cloud.html` produced no extractable content. It was not counted as verified; S17 supplied the regional recovery evidence instead.
- The legacy AWS Builders' Library retry and rollback URLs redirected. The destination articles S8 and S14 were fetched successfully and are the URLs retained in the CSV.
- Kafka 4.1 pages explicitly identify themselves as older documentation and link to 4.3. No claim of latest-version certification is made. Group behavior must be checked against installed versions, particularly share groups.
- The cert-manager page contains both a version-specific note that key-rotation defaults changed in 1.18 and older default wording. This review deliberately avoids relying on a universal rotation default or newly documented renewal-window fields.
- Source review cannot establish actual RPO/RTO, data-loss scope, fencing effectiveness, backup integrity, contractual communication deadlines, or regulatory notification obligations. These remain explicitly unknown until measured or supplied by the service owner.
- `get_errors` immediately after the initial incident-command edit reported no errors. The final CSV and ledger patch is followed immediately by the same editor diagnostic check. Editor diagnostics are not CSV schema validation or a runtime test.
- No terminal commands or tests were run. Parent must run the repository CSV validator and relevant tests; structural acceptance criteria are 19 data rows, 11 fields per row, unique names, unchanged original identities, valid source-type values, and 19 review dates of `2026-09-29`.