# Antipattern Domain Review

Review date: 2026-09-29. Scope: `src/backend-pro-max/data/anti-patterns.csv` only, plus this ledger. Reviewed all 15 existing rows; added 3 rows (18 total). Existing names, order, 12-column header, categories, and severity conventions are preserved. No shared files or tests were edited; no terminal, commit, or push was used.

Every row dated 2026-09-29 was individually checked against fetched primary-source content listed below. This is a review date, not a source publication date. No benchmark figures or measured performance guarantees were added. Primary sources include vendor/project documentation and original authors' engineering articles; the latter remain classified as `engineering-blog` rather than being presented as specifications.

## Per-Row Ledger

| Row | Verified sources | Correction and scope/uncertainty |
| --- | --- | --- |
| Distributed Monolith | [Microsoft service boundaries][boundaries] | Replaced universal co-deployment/failure claims with observable coupling. Async messaging is not a sufficient cure; cohesive strongly consistent operations may belong together. Synchronous calls and shared libraries are not inherently defects. |
| Shared Database Integration | [Richardson's shared-database pattern][shared-db] | Retained schema/runtime coupling risks and acknowledged local ACID and operational benefits. Splitting ownership is conditional on independence needs, not a mandate for separate physical servers. Cross-service consistency costs remain application-specific. |
| God Service | [Microsoft service boundaries][boundaries] | Removed unsupported 80% traffic threshold and automatic single-point-of-failure claim. Use mixed domain responsibilities and inability to evolve independently as evidence; size alone is insufficient. |
| Sync-over-Async | [Microsoft ThreadPool diagnostics][threadpool] | Defined blocking waits on async operations and the async/await remedy. Source examples are .NET-specific; this is not a claim that every synchronous network call or every runtime exhibits identical starvation behavior. No tutorial benchmark numbers imported. |
| Dual Writes | [AWS transactional outbox][outbox] | Added same-local-transaction requirement, committed-event relay, consumer deduplication, and required ordering. Outbox does not make downstream side effects exactly once. CDC suitability and end-to-end ordering require implementation-specific checks. |
| Chatty Microservices | [Microsoft chatty I/O][chatty], [service boundaries][boundaries] | Replaced aggressive caching with measurement, bounded batching, coarse operations, and freshness constraints. A gateway alone does not remove downstream calls; batching can overfetch. |
| Unbounded Retry | [Amazon timeouts/retries article][retries] | Added retry eligibility, safe repetition, bounded attempts/elapsed time, jitter, budget, and one retry owner including SDK behavior. Circuit breakers and DLQs are not universal remedies; no universal retry count or delay asserted. |
| Missing Idempotency Key | [Stripe API contract][idempotency] | Scoped keys to logical non-idempotent operations; added stable retry key, parameter matching, recorded result, retention, and concurrency contract. Stripe's retention duration and error-caching semantics are not universalized. Atomic deduplication with effects remains an implementation obligation, not guaranteed by a header. |
| Premature Microservices | [Fowler's original article][monolith] | Allowed modular monoliths or coarse services while boundaries evolve; acknowledged experienced teams with known boundaries. Source explicitly describes anecdotal, tentative architectural advice, not a universal rule. |
| Log-and-Throw | [Oracle fault barrier article][exceptions2], [logging discussion][exceptions3] | Assigned one fault-reporting boundary and preserved propagated context. Removed entry-point-only absolute; distinct business/audit events may be logged locally. These older Java articles support the principle, not current framework API recommendations. |
| Generic Error Swallowing | [Microsoft exception guidance][exceptions] | Focused on absent recovery/failure reporting rather than broad catch syntax alone. Added state restoration and resource cleanup; explicit error boundaries may catch broadly. No unconditional process-crash recommendation. |
| N+1 Query | [EF Core efficient querying][queries] | Query count, not guaranteed linear endpoint latency, is the diagnostic. Removed claim that all ORMs default to lazy loading. Added projection, pagination, and join/split-query tradeoffs; framework/provider details vary. |
| Secrets in Environment Variables | [OWASP secrets management][secrets] | Qualified exposure by deployment permissions; distinguished secret storage from runtime delivery. Added runtime retrieval/mounts, lifecycle, least privilege, and image ENV/ARG risks. Files and process memory also need protection; no universally visible process-list claim. |
| Time-Based Cache Invalidation Only | [Microsoft cache-aside][cache] | TTL-only is acceptable when freshness tolerance permits. Removed exact-TTL inconsistency bound and conflation with write-through/stale-while-revalidate. Added store-before-invalidate ordering and explicit lack of strong consistency; invalidation races and delivery reliability remain application-specific. |
| Polling Instead of Events | [Microsoft asynchronous request-reply][polling] | Removed legacy-only polling restriction. Added status resource, Retry-After, terminal states, timeout/cancellation, and workload-based push selection. Polling is valid when callbacks or persistent connections are impractical. |
| Missing Remote Call Deadlines (added) | [gRPC deadlines][deadlines], [Amazon timeouts][retries] | Covers missing/reset deadlines independently of retry loops. Use load-tested budgets, remaining-time propagation, and cooperative cancellation. Defaults and propagation vary by language; verify DNS/connect/TLS/request timeout coverage in the chosen client. Cancellation is not rollback of committed effects. |
| Unbounded Work Queues (added) | [Google SRE cascading failures][cascades] | Covers admission/queue bounds, in-flight limits, expiry, overload rejection, and recovery testing. Queue size depends on bursts and resource costs; expiry/discard advice applies only where operation semantics permit, not indiscriminately to durable business messages. |
| Per-Request Client Construction (added) | [Microsoft improper instantiation][clients] | Covers shareable client/handler reuse, DNS lifetime, and mutable-state hazards. Not a rule to share non-thread-safe sessions or hold database connections indefinitely; respect each SDK's lifecycle contract. |

## Citation Repairs And Gaps

- The original Amazon retry URL redirected to the fetched Builder Center article; the CSV now uses that readable destination. The original AWS idempotency URL yielded no extractable content; it was replaced with Stripe's fetched API documentation. This extraction failure does not establish that AWS's page is broken for browsers.
- Sonar's S2139 rendered page was not extractable, and three attempted raw rule paths returned 404. None is used as verified evidence. Oracle's fetched original technical articles instead support the logging correction.
- Other replaced citations were replaced for specificity or primary-source quality, not labeled dead without evidence. All final CSV citations have source content verified in this review; the polling URL uses the canonical URL reported by the fetched `async-request-reply` alias.
- Completeness is bounded: separate treatments of poison-message replay, destructive schema migrations, cache stampedes/cold-cache capacity, authorization bypass, and unbounded metric cardinality remain possible follow-ups. They were not added to avoid exceeding the requested 2-4 additions or expanding into other agents' domains.
- Source review does not certify application-specific timeout/TTL/queue values, severity, cancellation safety, secret exposure, or atomic side-effect handling. Existing `critical` severities are risk labels, not a finding that every use of the named technique causes an outage.

## Schema And Validation

- Header unchanged: `Name,Category,Symptom,Root Cause,Why It's Tempting,Fix,Related Patterns,Severity,Keywords,Last Updated,Source URL,Source Type`. Existing 15 names retained; 3 distinct names appended. No new columns or source-type values introduced.
- Repository guidance mismatch: CONTRIBUTING describes `Low/Medium/High/Critical`, while this domain uses lowercase `warning/critical`. Preserved the domain's existing convention; the inspected validator does not enforce a severity enum. Resolving shared guidance is outside this ownership scope.
- Validator limitation: `_validate_file` detects surplus CSV fields but does not explicitly reject every underfilled row. Parent validation should assert exactly 12 fields for every record, in addition to schema validation. No malformed row is intentionally introduced.
- Immediate `get_errors` checks after each CSV patch reported no errors. Editor diagnostics do not replace executable CSV parsing or tests. Full tests are reserved for the parent agent; no tests were run here.
- Suggested focused parent check: `pytest tests/test_antipatterns.py tests/test_validation.py tests/test_provenance.py`, followed by strict schema validation for the `antipattern` configuration via `_validate_file(..., strict=True)`. Also assert 18 unique row names, all 15 original names, 12 fields per record, and nonempty source/date values. Run the parent's full suite afterward as planned.

[boundaries]: https://learn.microsoft.com/en-us/azure/architecture/microservices/model/microservice-boundaries
[shared-db]: https://microservices.io/patterns/data/shared-database.html
[threadpool]: https://learn.microsoft.com/en-us/dotnet/core/diagnostics/debug-threadpool-starvation
[outbox]: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
[chatty]: https://learn.microsoft.com/en-us/azure/architecture/antipatterns/chatty-io/
[retries]: https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter
[idempotency]: https://docs.stripe.com/api/idempotent_requests
[monolith]: https://martinfowler.com/bliki/MonolithFirst.html
[exceptions2]: https://www.oracle.com/technical-resources/articles/enterprise-architecture/effective-exceptions-part2.html
[exceptions3]: https://www.oracle.com/technical-resources/articles/enterprise-architecture/effective-exceptions-part3.html
[exceptions]: https://learn.microsoft.com/en-us/dotnet/standard/exceptions/best-practices-for-exceptions
[queries]: https://learn.microsoft.com/en-us/ef/core/performance/efficient-querying
[secrets]: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
[cache]: https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside
[polling]: https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply
[deadlines]: https://grpc.io/docs/guides/deadlines/
[cascades]: https://sre.google/sre-book/addressing-cascading-failures/
[clients]: https://learn.microsoft.com/en-us/azure/architecture/antipatterns/improper-instantiation/