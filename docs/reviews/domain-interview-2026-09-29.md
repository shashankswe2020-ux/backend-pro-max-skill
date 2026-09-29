# Interview Domain Review - 2026-09-29

## Scope and Outcome

Reviewed all 12 existing entries in [interview.csv](../../src/backend-pro-max/data/interview.csv) and added 3 design-reasoning topics: 15 entries total. Preserved all existing names, categories, levels, and the nine-column schema. All 15 entries have source-reviewed content dated `2026-09-29` and an allowed source type; no entry received a date-only refresh.

Read the backend-pro-max skill. Used `fetch_webpage` for primary documentation and author-written publications. Sources support the concepts; the interview signals and evaluation questions are this repository's editorial synthesis, not externally validated hiring standards. A review date is not a source publication date.

## Per-Entry Source Ledger

All linked sources below returned substantive content during this review. Supplementary sources support claims beyond the CSV's single source URL.

| Entry | Reviewed primary evidence | Change and qualification |
| --- | --- | --- |
| Requirements Gathering | Google [NALSD][nalsd], initial requirements and design process | Testable goals, explicit assumptions, scope and budget; example SLOs are not defaults. |
| Back-of-Envelope Estimation | [NALSD][nalsd], why non-abstract and calculations | Requests per user, units, peaks and overhead; distinguish estimates from measured capacity. No hardware example promoted to a benchmark. |
| High-Level Architecture | [NALSD][nalsd], one-machine starting point and iterative design | Simplest feasible baseline; read/write service separation, queues and microservices need justification. |
| Database Schema Design | PostgreSQL [constraints][constraints] and [indexes][indexes] | Add invariant enforcement and index costs; referencing foreign-key columns are not automatically indexed in PostgreSQL. No universal denormalization rule. |
| API Design | Google [AIP-180][compat] and [AIP-158][pagination] | Source/wire/semantic compatibility and bounded pagination; tokens are not authorization. AIPs describe Google's conventions, not a universal REST/RPC schema. |
| Scaling Discussion | [NALSD][nalsd]; Google [cascading failures][cascades] | Allow vertical scaling and optimization; challenge linear scaling, uniform load and failover-capacity assumptions. |
| Trade-off Analysis | [NALSD][nalsd], design process and conclusion | Compare feasible alternatives against requirements and disconfirming evidence; remove mandatory alternative counts. |
| Failure Mode Analysis | [Cascading failures][cascades]; AWS [timeouts and retries][retries] | Deadline budgets, bounded jittered retries, overload and recovery; circuit breakers and failover can introduce failure modes. Timeout does not prove rollback. |
| Consistency vs Availability | Eric Brewer [CAP retrospective][cap]; Daniel Abadi [original PACELC post][pacelc] | Partition-specific CAP choices, normal-operation latency tradeoffs, invariants and recovery. Mixed models are optional. Brewer's IEEE article is classified as `paper`; no historical product classifications carried forward. |
| Operational Concerns | Google [monitoring][monitoring] and [canarying][canary] | Actionable user-impact signals, tail latency, incident ownership and release decisions; shared dependencies and traffic selection limit canary evidence. |
| Cost Awareness | [FinOps Foundation Framework][finops]; [NALSD][nalsd] | Business value and usage-based estimates plus operational effort; no provider prices or savings benchmarks asserted. Adapted conceptually from the FinOps Foundation's CC BY 4.0 framework. |
| Communication and Structure | US OPM [structured interviews][opm] | Job-related evidence and consistent assessment; remove mandatory STAR as a proxy for competence. Exact prompts remain editorial. |
| Idempotency and Ambiguous Outcomes (new) | Stripe [idempotent requests][idempotency]; AWS [timeouts and retries][retries] | Lost response after commit, retry identity, mismatched parameters, expiry and concurrent duplicates. Stripe behavior is an example contract, not a universal deduplication implementation. |
| Threat Modeling and Trust Boundaries (new) | OWASP [threat modeling][threats] | Evaluate trust boundaries, plausible threats, authorization, testable mitigations and residual risk. No mandated modeling notation or security product. |
| Recovery Objectives and Restore Validation (new) | AWS [DR planning][dr], [recovery strategies][recovery] and [recovery tests][drtests] | Business-derived RTO/RPO, corruption-safe recovery, dependency/capacity checks and failback. Multi-region active-active is conditional; source recovery-time examples are not guarantees. |

## Evidence Limits and Unverified Gaps

- No benchmark was run or adopted. Workload, hardware throughput, cost, retry limits, retention windows and recovery performance require deployment-specific measurements. Source examples are not interview answer constants.
- Existing `Level` labels are preserved for compatibility, not validated seniority thresholds. Predictive hiring validity, scoring weights and inter-rater reliability remain unverified. Do not grade technology choice, use of multiple consistency models, or answer-template compliance as inherently correct.
- PostgreSQL details and Google/Stripe/AWS contracts have their stated scope. Verify the chosen engine, API version and provider before applying implementation details. Cross-store atomicity and external side-effect reconciliation need scenario-specific designs; idempotency keys alone do not establish end-to-end exactly-once execution.
- This is a bounded conceptual review, not exhaustive coverage. Online schema/data migration, backfill reconciliation, data retention/deletion and quantitative queueing analysis remain candidates for future depth. Little's Law was removed from the old estimation prompt rather than retained without a reviewed explanation of its assumptions.
- Abadi's PDF at `https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf` could not be extracted. The initially attempted blog slug ending `little-known.html` returned 404; the actual author's post [linked here][pacelc] was fetched successfully. No PDF-only claims are marked verified.
- Amazon Jobs interview-prep and behavioral-interview pages and the AWS Builders' Library `making-retries-safe-with-idempotent-APIs/` page could not be extracted. OPM and Stripe provide the reviewed alternatives. The VA preparation URL redirected but its destination was not reviewed or used. The AWS timeout article redirected to the [fetched Builder Center version][retries].

## Validation Boundary

Edits were applied only to the CSV and this ledger using `apply_patch`, with immediate `get_errors` checks. No terminal commands, shared-file edits, commits or pushes. CSV parsing/schema validation, knowledge-base lint, deduplication and retrieval tests are deferred to the parent; editor diagnostics do not substitute for those gates.

[nalsd]: https://sre.google/workbook/non-abstract-design/
[constraints]: https://www.postgresql.org/docs/current/ddl-constraints.html
[indexes]: https://www.postgresql.org/docs/current/indexes.html
[compat]: https://google.aip.dev/180
[pagination]: https://google.aip.dev/158
[cascades]: https://sre.google/sre-book/addressing-cascading-failures/
[retries]: https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter
[cap]: https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed/
[pacelc]: https://dbmsmusings.blogspot.com/2010/04/problems-with-cap-and-yahoos-little.html
[monitoring]: https://sre.google/sre-book/monitoring-distributed-systems/
[canary]: https://sre.google/workbook/canarying-releases/
[finops]: https://www.finops.org/framework/
[opm]: https://www.opm.gov/policy-data-oversight/assessment-and-selection/structured-interviews/
[idempotency]: https://docs.stripe.com/api/idempotent_requests
[threats]: https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html
[dr]: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/plan-for-disaster-recovery-dr.html
[recovery]: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html
[drtests]: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_dr_tested.html