# Mobile Backend Correctness and Completeness Review

Review date: 2026-09-29.

Scope: [src/backend-pro-max/data/mobile-backend.csv](../../src/backend-pro-max/data/mobile-backend.csv) and this ledger only. Read the backend-pro-max skill. No terminal commands, shared-file edits, commits, or pushes. Parent owns executable validation and tests.

## Outcome

- Reviewed and corrected all 10 existing rows; preserved their exact Name identities, Category values, relative order, and the 10-column header order.
- Appended 3 actionable topics: Background Work Scheduling; Native OAuth Authorization Code with PKCE; Mobile Request Retries and Idempotency. Final total: 13 rows.
- All 13 rows have reviewed source metadata dated 2026-09-29. This is the actual source-review date, not a claim that the upstream document was published or updated that day.
- Source types: 8 official-docs; 4 rfc; 1 engineering-blog. Each CSV URL has been fetched with meaningful content, including redirects documented below. Supporting sources are retained here because the CSV has one Source URL column.

## Row Ledger

Every entry below was reviewed on 2026-09-29. Recommendations synthesized from multiple sources are design guidance, not platform guarantees or verbatim normative requirements.

| Row identity | Disposition and evidence | Remaining qualification |
| --- | --- | --- |
| Backend for Frontend (BFF) | Corrected mandatory per-platform split and aggregation-only absolute. S1 describes both shared iOS/Android BFFs and separate BFFs; also client-aware partial responses and domain-oriented reuse. Added explicit downstream deadlines as design guidance. | Service boundaries depend on experience and ownership; no universal BFF count or latency improvement. |
| Offline-First Sync | Replaced automatic conflict-detection claim and blanket vector-clock/CRDT prescription. S2 distinguishes offline reads from optional queued/lazy writes and requires conflict policy; S3 documents Firestore same-document last-write-wins and potentially incomplete cached reads. S16 supports conditional version checks for other HTTP backends. | Last-write-wins may discard concurrent edits; no universal merge strategy. Queue durability and process-death tests remain implementation responsibilities. |
| Push Notification Delivery | Removed instant delivery and legacy feedback-service advice. S4 documents registration freshness and FCM error handling; S5 documents APNs 410 and re-registration. S6 and S7 establish delayed/dropped background delivery and Android priority constraints. Added foreground reconciliation as recovery guidance. | Acceptance by a provider is not device receipt or user display. Notification permission and device state require real-device testing. |
| GraphQL for Mobile | Replaced elimination of over-fetching with conditional benefits. S8 documents pagination, depth, breadth, batch limits, cost/rate controls, timeouts, and trusted-document allowlists. | Depth alone does not bound expensive fields; resolver authorization and backend workload remain separate concerns. |
| CDN for API Responses | Replaced vague aggressive-mobile-cache claim with S9 caching semantics: private versus no-store versus no-cache; shared-cache freshness and representation keys. Removed personalized feature flags from public-cache examples. | RFC 9111 section 6 distinguishes application caches from HTTP caches; configure both. CDN behavior must be tested, not assumed. |
| API Versioning for Mobile | Removed fixed 1-7 day review estimate and unconditional v1/v2 requirement. S10 supports compatible evolution and preserving field types/defaults; S11 confirms app-version review as a separate release step. Added old-client tests and telemetry-based retirement as design guidance. | No replacement review-time statistic was verified; no fixed review SLA is asserted. Compatibility windows are product policy. |
| Optimistic UI Updates | Removed zero-latency claim. S12 documents a separate optimistic layer, canonical server reconciliation, error rollback, and temporary IDs. S16/S18 support treating timeout outcomes as uncertain rather than definite rejection. | Apollo React is an implementation example, not a guarantee about every native SDK; durable offline queues and concurrent mutation handling must be implemented separately. |
| Token Refresh Flow | Removed guaranteed background refresh and uninterrupted login. S13 sections 2.2.2 and 4.14 require public-client refresh rotation or sender constraint and discuss storage, expiration, revocation, and replay detection. S15 establishes execution constraints. Retained serialized refresh and added persist-before-release and terminal-error handling as design guidance. | Provider rotation, lost refresh responses, secure storage accessibility, logout races, and reauthentication behavior need SDK-specific tests. |
| Image Optimization Pipeline | Removed unsupported 50-80% savings, native Core Web Vitals claim, mandatory origin shield, and Android/WebP versus iOS/AVIF mapping. S14 documents size/format transformations, Accept negotiation, encoding tradeoffs, and fallback; S9 supports variant-aware caching. | Native decoder capability must be advertised accurately and tested; no full OS/codec support matrix or percentage saving was verified. |
| App Startup Optimization | Removed universal sub-second launch and fixed retention implication. S17 distinguishes cold/warm/hot launch, TTID, TTFD, and deferred initialization; S2 supports immediate local reads. Added account-scoped bootstrap cache and empty-cache handling as design guidance. | Set budgets from representative-device measurements; Android metrics are not asserted as Apple metrics or guaranteed backend outcomes. |
| Background Work Scheduling | Added. S19 documents WorkManager constraints, stopped/retried work, inexact scheduling, and 15-minute periodic minimum. S15 describes Apple system-selected runtime and API selection; S6 supplies background-push headers and up-to-30-second handler budget. S7 limits Android high priority to user-visible urgency. | The 15-minute minimum is not a schedule guarantee; the 30-second budget is not a promise of delivery or a universal limit for every Apple background API. |
| Native OAuth Authorization Code with PKCE | Added. S20 sections 6-8 require external user-agents and public-client PKCE; shared bundled secrets are not confidential. S13 supports S256 and redirect/CSRF protections. | Claimed HTTPS redirect availability and ownership need platform/provider configuration; the loopback-port exception does not permit arbitrary redirect matching. |
| Mobile Request Retries and Idempotency | Added. S16 section 9.2.2 restricts automatic non-idempotent replay; section 10.2.3 defines Retry-After. S18 supports bounded retry/backoff/jitter and uncertain timeout outcomes. S21 provides a concrete same-key/same-parameters result-replay and expiration contract. Caller scoping and atomic deduplication/effect handling are design requirements for a custom service. | HTTP does not supply exactly-once processing or a universal idempotency-key contract. Retention must cover the intended replay window; multi-service effects need their own recovery design. |

## Primary Sources

All S1-S21 returned meaningful content through fetch_webpage during this review on 2026-09-29.

| ID | Source and reviewed material |
| --- | --- |
| S1 | [Sam Newman: Backends for Frontends](https://samnewman.io/patterns/architectural/bff/), How Many BFFs, downstream calls, reuse, autonomy. First-person architectural guidance, classified engineering-blog rather than official platform documentation. |
| S2 | [Android: Build an offline-first app](https://developer.android.com/topic/architecture/data-layer/offline-first), local source of truth, reads/writes, synchronization, conflicts, WorkManager. |
| S3 | [Firebase: Access data offline](https://firebase.google.com/docs/firestore/manage-data/enable-offline), persistence, same-document last-write-wins, cache metadata and incomplete offline results. |
| S4 | [Firebase: Registration management](https://firebase.google.com/docs/cloud-messaging/manage-tokens), registration freshness, UNREGISTERED and valid-payload qualification for INVALID_ARGUMENT. |
| S5 | [Apple: Handling notification responses from APNs](https://developer.apple.com/documentation/usernotifications/handling-notification-responses-from-apns), device-token 410, invalidation timestamp, Unregistered, permanent versus retryable errors. |
| S6 | [Apple: Pushing background updates](https://developer.apple.com/documentation/usernotifications/pushing-background-updates-to-your-app), no delivery guarantee, conditional throttling, headers, held-notification replacement/discard, 30-second processing window. |
| S7 | [Firebase: Android message priority](https://firebase.google.com/docs/cloud-messaging/android-message-priority), Doze, limited handler time, WorkManager handoff, deprioritization of non-user-visible high-priority traffic. Also checked [cross-platform priority](https://firebase.google.com/docs/cloud-messaging/customize-messages/setting-message-priority), including normal priority for Apple data messages. |
| S8 | [GraphQL Foundation: Security](https://graphql.org/learn/security/), demand controls and transport/authorization caveats. |
| S9 | [IETF RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html), sections 3.5, 4.1, 5.2.2 and 6 on authenticated/shared caching, Vary, directives, application caches. |
| S10 | [Google AIP-180](https://google.aip.dev/180), source/wire/semantic compatibility and field/default changes. Google API guidance, not a universal protocol mandate. |
| S11 | [Apple: Overview of submitting for review](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/), per-version submissions and review process. |
| S12 | [Apollo: Optimistic mutation results](https://www.apollographql.com/docs/react/performance/optimistic-ui), optimistic layer lifecycle, rollback and temporary IDs. |
| S13 | [IETF RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html), sections 2.1, 2.2.2 and 4.14 on PKCE, redirect validation and refresh-token protection. |
| S14 | [Cloudflare: Image transformations](https://developers.cloudflare.com/images/transform-images/transform-via-url/), resolved to [optimization features](https://developers.cloudflare.com/images/optimization/features/); size, format, Accept, fallback and caching sections reviewed. |
| S15 | [Apple: Choosing background strategies](https://developer.apple.com/documentation/backgroundtasks/choosing-background-strategies-for-your-app), bounded continuation, system-scheduled refresh/processing, URLSession transfers and expiration handling. |
| S16 | [IETF RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2), sections 9.2.2, 10.2.3 and 13.1.1 on idempotency, Retry-After and If-Match. |
| S17 | [Android: App startup time](https://developer.android.com/topic/performance/vitals/launch-time), resolved to [startup performance issues](https://developer.android.com/topic/performance/issues/launch-time); TTID/TTFD, launch states and initialization guidance reviewed. |
| S18 | [AWS Builders' Library: Timeouts, retries, and backoff with jitter](https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter), fetched after following the redirect from the original AWS Builders' Library URL; timeout side effects, retry amplification, caps and jitter. |
| S19 | [Android: Define work requests](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work), periodic minimum, inexact timing, constraints, expedited quotas and retry policy. |
| S20 | [IETF RFC 8252](https://www.rfc-editor.org/rfc/rfc8252.html), native public clients, external user-agents, PKCE, redirects, state and bundled-secret limitations. Historical platform API names in its appendix were not promoted as current recommendations. |
| S21 | [Stripe: Idempotent requests](https://docs.stripe.com/api/idempotent_requests), repeated keys/parameters, saved results and pruning. Stripe-specific behavior is evidence of a concrete contract, not a universal HTTP rule. |

## Caveats and Unresolved Gaps

- Apple [App Store review](https://developer.apple.com/app-store/review/) returned no extractable content. S11 verified the review process but not turnaround statistics. The old 1-7 day assertion was removed, not replaced with an unverified number.
- The old Apollo URL with a trailing slash returned 404; S12 without the slash returned the relevant article and is now the CSV source.
- Apple [handling error responses](https://developer.apple.com/documentation/usernotifications/handling-error-responses-from-apns) returned broadcast/channel guidance. It was not used to infer device-token behavior; S5 was fetched for that purpose.
- S4 currently describes FID-based registrations alongside legacy tokens. The CSV deliberately uses registration terminology without prescribing SDK migration APIs whose version-by-version availability was not reviewed. Its 270-day Android inactivity expiration is not an APNs/iOS expiry rule; a staleness cleanup window is an operational policy rather than a universal expiration timer.
- S6 advises no more than two or three background pushes per hour under condition-dependent throttling. This is not a guaranteed quota; the CSV does not present it as one. Force-quit and power restrictions mean push cannot be the only synchronization path.
- Idempotency retention is backend-specific. Stripe permits pruning after at least 24 hours; this is not sufficient evidence to impose a universal mobile-offline replay window. Persisted operations surviving longer require status reconciliation or a longer backend contract.
- Deferred completeness topics: resumable large-file uploads; account deletion and local-cache erasure; app attestation and abuse controls; purchase/entitlement reconciliation. These were not added or source-reviewed as standalone topics in this bounded pass.
- Real-device behavior, secure-storage APIs, notification permission flows, OEM restrictions, conflict invariants and performance budgets remain deployment checks. Documentation review does not substitute for integration tests.

## Validation Handoff

The local review hypothesis was that unqualified platform guarantees and generic implementation prescriptions were misleading; primary-source checks confirmed conditional delivery/execution, explicit conflict policy and stronger public-client OAuth protections. All edits use apply_patch followed immediately by get_errors. The preliminary CSV diagnostics checks reported no errors; the final two-file check is performed after this ledger is written. Editor diagnostics are not a CSV schema or ranking test.

Parent should run the repository CSV validator and applicable tests, checking 13 data records, 10 fields per record, unique Name values, preserved original identities/order, valid Source Type values, and review dates of 2026-09-29. No executable tests were run in this worker, per the shared-shell restriction.