# Multi-Tenant Domain Review

Review date: 2026-09-29. Scope: this ledger and [src/backend-pro-max/data/multi-tenant.csv](../../src/backend-pro-max/data/multi-tenant.csv) only.

## Outcome

- Preserved the 11-column schema and all 12 existing names in their original order.
- Reviewed and revised all 12 stale rows; added 4 entries for 16 total data rows.
- All 16 rows carry `2026-09-29` and `official-docs` after substantive source retrieval. This is the review date, not the source publication date or a deployment certification.
- Read the backend-pro-max skill. Its executable search workflow was not run because this task explicitly prohibits terminal commands. No shared tests or other files were edited.
- Principal corrections: resource isolation is not necessarily physical isolation; RLS has privileged and operation-specific exceptions; cache prefixes are not authorization; rate caps differ from fairness; portability rights are not an unconditional whole-company export obligation.

## Evidence Ledger

Source links below were fetched during this review. Recommendations derived from those sources are implementation guidance, not vendor guarantees. Each row's date is 2026-09-29.

| Row | Entry | Evidence and correction | Limits and recommended check |
| --- | --- | --- | --- |
| 1 | Pool Model (Shared Everything) | [AWS pool isolation][pool] describes shared compute/storage and the need for isolation beyond network/IAM boundaries; [OWASP][owasp] supplies verified context and access-path controls. Removed the implication that a tenant column plus query filters alone suffices. | Pooling does not require one literal SQL schema. Classify tenant-owned resources and test alternate API, raw-query, and background access paths. |
| 2 | Silo Model (Shared Nothing) | [AWS silo isolation][silo] defines an encapsulated resource stack and its management costs. Removed schema-as-silo and automatic compliance claims. | Dedicated resources need not mean dedicated hardware. Residual shared control-plane and regional risks are an architectural qualification; inventory actual dependencies and test cross-stack denial. |
| 3 | Bridge Model (Hybrid) | [AWS bridge model][bridge] explicitly combines pool and silo at different tiers or services. Replaced the unusable old bridge URL and arbitrary tenant-count range. | Does not establish residency or a universal cost optimum. Routing, migration, replica, and export-location checks are engineering recommendations for the chosen boundaries. |
| 4 | Row-Level Security (RLS) | [PostgreSQL row security][rls] documents default deny, owner/FORCE behavior, superuser/BYPASSRLS bypass, USING/WITH CHECK, OR-combined permissive policies, and TRUNCATE/REFERENCES and integrity-check exceptions. | PostgreSQL-specific semantics, not a blanket claim about SQL Server. FORCE is not a defense against an owner able to alter policies. Audit runtime role, privileged functions, policy coverage, and existence leaks; test allowed and denied writes as well as reads. |
| 5 | Noisy Neighbor Mitigation | [Azure noisy neighbor][noisy] recommends governance, downstream controls, query limits, monitoring, reserved capacity, and selective isolation; [OWASP][owasp] covers concurrency, queue, and global budgets. | Mitigates rather than eliminates contention. Test quiet-tenant tail latency during an expensive noisy workload and during aggregate load from many compliant tenants. |
| 6 | Per-Tenant Rate Limiting | [AWS API Gateway usage plans][limits] explicitly says quotas are best effort and API keys must not serve as authentication; [OWASP][owasp] recommends tenant and service-wide controls. Removed mandatory Redis and IP-only framing. | AWS caveat applies to usage plans, not every limiter. Atomic admission accounting and replica/outage tests are recommendations for hard caps; define consistency and availability trade-offs rather than assuming a distributed counter guarantees them. |
| 7 | Tenant-Aware Caching | [Azure Redis multitenancy][cache] documents collision-resistant prefixes, application-enforced separation, shared resources, and key-pattern permissions; [OWASP][owasp] requires authorization before cache access and all response-varying key dimensions. | The Azure URL now resolves to Managed Redis documentation; ACL availability is product-specific. Prefixes do not enforce memory quotas or prevent misuse by broad shared credentials. Test identical resource IDs across tenants and differing permissions within one tenant. |
| 8 | Tenant Onboarding Automation | [AWS onboarding][onboarding] verifies multi-component orchestration for both self-service and provider-managed provisioning; [OWASP][owasp] requires secure provisioning and audit trails. Removed the unsupported ten-tenant threshold. | Durable state, stable provisioning keys, inactive-until-verified status, and reconciliation are engineering recommendations, not guarantees supplied by the short AWS overview. Inject failures between steps and check retries for duplicate resources and premature activation. |
| 9 | Tenant Data Export and Portability | [ICO portability guidance][portability] limits the right to provided personal data, automated processing, and consent/contract basis; requires secure transfer and consideration of others' rights. [OWASP][owasp] distinguishes contractual, regulatory, and product export requirements. | ICO guidance is UK-specific and displayed an under-review notice related to the Data (Use and Access) Act. No universal EU/UK deadline or legal-compliance certification is asserted. Obtain jurisdiction-specific advice; organizational exports and individual access requests may have different scopes. |
| 10 | Schema-Per-Tenant | [PostgreSQL schemas][schemas] says schemas are not rigidly separated and that adding a writable schema to search_path trusts its creators. Documents public CREATE differences in older/upgraded databases. | search_path is name resolution, not access control or dedicated capacity. Test explicit schema qualification against grants and audit inherited roles, public privileges, and writable search paths. |
| 11 | Tenant-Aware Logging and Observability | [Prometheus instrumentation][metrics] explains the multiplicative cost of label sets and recommends reducing dimensions or moving detailed analysis elsewhere; [OWASP][owasp] scopes audit context and read access. | Recording rules cannot undo raw-series ingestion cost; this follows from the ingestion model, not a universal crash threshold. Verify series budgets before ingestion and telemetry tenant access; sampled telemetry is not complete billing evidence. |
| 12 | Cross-Tenant Analytics | [NIST SP 800-226 publication overview][privacy] describes quantified privacy loss; [NIST's release explanation][privacy-news] warns of noise/utility trade-offs and small-group risk. Removed mandatory precomputation and a blanket differential-privacy-or-k-anonymity prescription. | Reviewed the publication overview and official explanation, not the complete PDF or a concrete privacy mechanism. No epsilon, minimum cohort size, or zero-reidentification guarantee is prescribed. Protected-entity choice and linked-release review are engineering recommendations requiring privacy expertise. |
| 13 (new) | Verified Tenant Context | [OWASP tenant context and IDOR guidance][owasp] treats client tenant identifiers as selectors, binds context to verified membership/service scope, and requires resource authorization. | Authentication alone is insufficient; signed but stale claims may need current membership checks. Test header/path spoofing, tenant switching, object ownership, and explicitly authorized platform access. |
| 14 (new) | Transaction-Scoped Tenant Context | [PostgreSQL configuration functions][admin] documents transaction-local set_config and missing-setting behavior; [OWASP pooled RLS guidance][owasp] requires per-transaction context and connection-reuse tests. | A freely writable custom setting does not protect against arbitrary SQL executed as the same application role. Require explicit transaction boundaries and fail-closed policies; test rollback, cancellation, and tenant switching with the production pooling mode. |
| 15 (new) | Tenant-Aware Async Fairness | [SQS fair queues][fairness] uses MessageGroupId on standard queues to reduce quiet-tenant dwell time without ordering or per-tenant consumption caps; [OWASP async guidance][owasp] covers trusted producer context, consumer authorization, and tenant-scoped retries/deduplication. | Fairness is not a hard quota or authorization mechanism. Test stale membership at consumption, duplicate deliveries, forged tenant metadata, and expensive jobs that occupy workers after dequeue. |
| 16 (new) | Tenant Export Snapshot and Delivery | [PostgreSQL snapshot synchronization][admin] requires the exporting transaction to remain open until other readers import its snapshot; [OWASP file-storage guidance][owasp] requires exact-object authorization before signing bounded URLs. | A snapshot does not span independent services. Manifests, per-store cutoffs, resumability, and artifact cleanup are engineering recommendations; test a concurrent writer, incomplete part, expired URL, and cross-tenant download. |

## Retrieval Limits

- The original AWS `bridge-isolation.html` and attempted whitepaper bridge URL yielded no meaningful content. The successfully retrieved SaaS Lens `bridge-model.html` is used instead.
- The AWS Builders' Library idempotency page yielded no meaningful content; an alternate documentation URL was not found. Neither is treated as verified support. Onboarding retry recommendations are explicitly identified as engineering synthesis above.
- EUR-Lex's official EU GDPR URL yielded no meaningful content. A secondary Article 20 transcription was readable but is not used as the CSV authority; the row explicitly scopes its legal statement to the successfully retrieved ICO guidance.
- PostgreSQL `current` resolved to PostgreSQL 18 during retrieval. Reconfirm deployment-version behavior, especially role inheritance and privileged access paths.
- Successful page-content retrieval is not an HTTP HEAD validation or a promise that redirects remain stable.

## Validation and Parent Gates

Editor diagnostics are checked with `get_errors` after CSV edits and for both owned files at completion. This does not prove CSV parsing, source reachability, ranking quality, or runtime tenant isolation. No terminal commands or executable tests were run; the parent owns executable gates.

Recommended parent checks:

1. Parse the CSV with the repository validator in strict mode; assert 16 rows, exactly 11 fields per row, preserved original names/order, valid source types, and the review date on every row.
2. Run applicable schema, provenance/citation, freshness, lint, and duplicate-content gates, plus source-URL checks that account for redirects and HEAD restrictions.
3. Exercise retrieval for RLS bypass, cache authorization, hard quota versus fairness, bridge isolation, and individual versus tenant export scope.
4. Treat deployed-role RLS tests, pooled-session reuse, cache-hit authorization, mixed-tenant load, delayed-job authorization, and export/download isolation as priority implementation test recommendations. This knowledge-base-only change does not implement those tests or certify any service.

[pool]: https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/pool-isolation.html
[silo]: https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-isolation.html
[bridge]: https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/bridge-model.html
[rls]: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
[schemas]: https://www.postgresql.org/docs/current/ddl-schemas.html
[admin]: https://www.postgresql.org/docs/current/functions-admin.html
[noisy]: https://learn.microsoft.com/en-us/azure/architecture/antipatterns/noisy-neighbor/
[limits]: https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html
[cache]: https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/service/cache-redis
[onboarding]: https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/tenant-onboarding.html
[portability]: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/individual-rights/right-to-data-portability/
[metrics]: https://prometheus.io/docs/practices/instrumentation/
[privacy]: https://csrc.nist.gov/pubs/sp/800/226/final
[privacy-news]: https://www.nist.gov/news-events/news/2025/03/nist-finalizes-guidelines-evaluating-differential-privacy-guarantees-de
[owasp]: https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html
[fairness]: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-fair-queues.html