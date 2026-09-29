# API Contract Domain Review

Review date: 2026-09-29.

## Scope and Outcome

- Reviewed and revised all **12 existing rows** in [src/backend-pro-max/data/api-contract.csv](../../src/backend-pro-max/data/api-contract.csv).
- Added **4 source-backed topics**, for **16 total rows**. Preserved the 11-column header and all 12 original primary names and their order.
- Changed only the domain CSV and this new report. No terminal commands, shared tests, commits, or pushes were used.
- Read the backend-pro-max skill. Its terminal-based search was not run because this task explicitly prohibits terminal use.
- All 16 rows have live-fetched primary evidence supporting their revised core guidance. Their `Last Updated` values are `2026-09-29`; this is the verification date, not a claim that the source was published that day. `Source Type` is `official-docs`.

## Main Corrections

Compatibility is a relationship between particular producers, consumers, encodings, and supported versions, not a property of the word "additive." For an old client against a new server, previously valid requests must remain accepted and new responses must satisfy the client's expectations. New-client/old-server compatibility is a separate direction; persisted messages and rollback paths add further combinations.

The cheapest discriminating checks were official counterexamples: JSON Schema rejects undeclared properties when `additionalProperties` is false; protobuf documents binary-safe enum additions that break exhaustive application switches; ProtoJSON rejects unknown fields by default. These disprove blanket backward-compatibility claims without requiring a local runtime. Buf's category checks do not replace application or mixed-version verification.

Other corrections remove the prohibition on checking in generated code, the prohibition on versioning internal APIs, automatic documentation-sync claims, unqualified browser streaming claims, and claims that gateways or BFFs must only route or transform. The old header example incorrectly added `version=2` to the JSON:API media type; JSON:API 1.1 permits only `ext` and `profile` media type parameters.

## Per-Row Evidence Ledger

Every entry below was verified through live page content on **2026-09-29**, before its final CSV revision. Source labels resolve to the exact fetched documents below. Architectural recommendations are review judgments grounded in those documents, not requirements imposed by an HTTP standard.

| # | Primary Name | Outcome | Evidence and Revision | Remaining Qualification |
| --- | --- | --- | --- | --- |
| 1 | OpenAPI Code Generation | Reviewed | [Generator customization][generator] documents templates, selective generation, overwrite controls, and language-dependent mappings; [OAS 3.1.1][oas] Introduction describes client/server and documentation generation. Replaced automatic sync and no-check-in rules with reproducible generation and CI advice. | No generator was executed; pinning and repository policy are recommendations, not specification mandates. |
| 2 | GraphQL Federation | Reviewed | [Apollo composition][apollo] defines subgraph-to-supergraph composition and demonstrates conflicting field types causing composition failure. Narrowed tooling to the verified Apollo workflow and distinguished composition from client/runtime compatibility. | No operation-history check, resolver execution, entity-key analysis, or performance benchmark was run. |
| 3 | Schema Evolution (Backward Compatible) | Reviewed | [Buf][buf] defines FILE, PACKAGE, WIRE_JSON, and WIRE categories. [Proto3][proto3] Updating A Message Type explicitly distinguishes wire safety from application-source safety. [JSON Schema objects][objects] and [ProtoJSON][protojson] supply closed-reader and unknown-field counterexamples. | Schema checks do not prove semantic equivalence or guarantee compatibility for every old/new deployment pair; deprecation is not permission for safe removal. |
| 4 | API Versioning via URL Path | Reviewed | [Microsoft API design][api-design] Implement versioning describes retaining old URI representations and the routing/maintenance costs of URI versions; no-versioning only works for some internal APIs. Removed the categorical internal-API ban. | A path version does not isolate shared data-model or business-behavior changes; retirement policy remains application-specific. |
| 5 | API Versioning via Headers | Reviewed | [RFC 9110][http] sections 12.5.1 and 12.5.5 define Accept and Vary; [Microsoft API design][api-design] shows custom headers and vendor media types; [JSON:API 1.1][jsonapi] sections 5 and 6 disallow the original version parameter. | Header selection is not inherently uncacheable. Vary does not itself authorize caching; cache directives and actual CDN behavior still require verification. |
| 6 | Contract Testing | Reviewed | [Pact introduction][pact] distinguishes consumer-driven examples from provider-only schema conformance. [Can I Deploy][deploy] defines the version verification matrix, target environments, and deployment/release recording. Narrowed tooling and added deployment evidence requirements. | Unrepresented consumers, interactions, and infrastructure behavior remain untested; a passing matrix depends on accurate version and environment records. |
| 7 | Protobuf Schema Registry | Reviewed | [BSR][bsr] documents versioned modules, dependencies, generated SDKs, and checks. [Proto3][proto3] Deleting Fields requires reserving removed numbers and discusses names. [ProtoJSON][protojson] Wire Safety and JSON Options describe staged additions and default unknown-field rejection. | Buf policy categories are not interchangeable with another registry's backward/forward/transitive settings. Reserving a name does not make runtime JSON parsers accept a deleted field. |
| 8 | AsyncAPI for Event-Driven APIs | Reviewed | [AsyncAPI migration][asyncapi] documents v3 operation/channel/message separation, arbitrary channel IDs with address fields, and application-perspective send/receive actions. Replaced ecosystem-maturity claims with concrete migration risks. | Document conversion does not prove producer/consumer payload compatibility, broker behavior, ordering, or delivery semantics; tool support must be checked per version. |
| 9 | BFF (Backend for Frontend) Pattern | Reviewed | [Microsoft BFF pattern][bff] explicitly permits client-specific logic, describes frontend ownership, and lists duplication, latency, and service-lifecycle tradeoffs. Replaced the blanket business-logic ban. | Keeping shared domain rules in their owning services is an architectural recommendation; a BFF is unnecessary when interfaces have essentially the same needs. |
| 10 | API Gateway Pattern | Reviewed | [Microsoft API gateways][gateway] covers routing, aggregation, offloading, transformations among selection concerns, and managed deployment choices. Replaced routing-only and inevitable-single-point-of-failure claims. | Availability depends on deployment design. Reviewing policies as contracts and keeping domain workflows in services are recommendations, not protocol constraints. |
| 11 | gRPC-Web | Reviewed | [Official grpc-web README][grpcweb] Streaming Support and Wire Format Mode specify unary plus server streaming in grpcwebtext, binary-mode unary only, and no client/bidirectional streaming in that client. Ecosystem lists server-side support as well as proxies. | This is a client-implementation limit, not a universal browser or native-gRPC limit. Other clients such as Connect require separate verification; no standard WebSocket fallback is promised. |
| 12 | Hypermedia APIs (HATEOAS) | Reviewed | [JSON:API 1.1][jsonapi] sections 7.2.2 and 7.6 distinguish relationship self/related links and link metadata; [Microsoft API design][api-design] Implement HATEOAS explains navigation and transitions. Removed unsupported rarity and comparative-value claims. | JSON:API is one concrete hypermedia format, not the definition of all HATEOAS. Clients still depend on relation and payload semantics; no universal evolution guarantee follows from adding links. |
| 13 | JSON Schema Contract Evolution | Added | [JSON Schema objects][objects] Properties, Required Properties, Additional Properties, and Unevaluated Properties establish optional-by-default properties, null/absence distinctions, and composition-aware closure. | The linked page is official explanatory documentation. `unevaluatedProperties` requires a supporting dialect/validator; optional field definitions can also narrow a previously unconstrained property. |
| 14 | OpenAPI 3.1 Schema Dialects | Added | [OAS 3.1.1][oas] sections 4.4, 4.8.24, and 4.8.25 define the 2020-12-based dialect, dialect overrides, annotations, and discriminator validation limits; OpenAPI/Info Objects distinguish version metadata. | Explicitly scoped to 3.1 using a fixed 3.1.1 reference, not a claim that 3.1.1 is the newest release. Generator support and application enforcement of annotations were not tested. |
| 15 | Protobuf Field Presence | Added | [Field Presence][presence] Semantic Differences and Considerations for Merging explain skipped implicit defaults; Considerations for change-compatibility provides a lossy explicit/implicit round-trip example. | Repeated fields and maps lack presence; binary compatibility does not preserve all presence-sensitive application behavior. FieldMask/update semantics need service-specific tests. |
| 16 | gRPC Deadline and Cancellation Contracts | Added | [Deadlines][deadlines] documents no default deadline, implementation-dependent propagation, and application cleanup responsibility. [Status Codes][status] says DEADLINE_EXCEEDED may follow successful mutation and warns against non-idempotent retries. | No timeout budget was benchmarked. Cancellation is not transactional rollback; deduplication/reconciliation is design advice, not built-in gRPC exactly-once execution. |

## Validation and Limitations

- Validation in this pass is limited to `get_errors` immediately after each `apply_patch`. Editor diagnostics do not replace parsed CSV/schema validation, retrieval checks, lint, or tests. The parent executes full gates; no shared test or configuration files were modified.
- Source-backed means the stated mechanism and compatibility caveat were checked against the fetched text. Qualitative operational tradeoffs and recommendations are not measured performance or availability guarantees.
- No clients, providers, generators, registries, brokers, browsers, or validators were executed. A deployment needs old-client/new-server and new-client/old-server checks in each supported encoding, plus persisted-message replay and rollback coverage where relevant.
- OpenAPI evidence is pinned to 3.1.1 and JSON:API to 1.1. No comprehensive latest-release certification or third-party tooling feature matrix is claimed. Unversioned project pages can change after this review; no immutable archive of them was created.
- Two attempted sources returned HTTP 404: `https://docs.pact.io/getting_started/what_is_pact` and `https://docs.spring.io/spring-hateoas/reference/fundamentals.html`. They are not evidence. Successful replacements were the Pact documentation root and JSON:API plus Microsoft hypermedia guidance. Spring HATEOAS-specific claims were not retained.
- Tooling lists were narrowed to verified projects or generic capabilities rather than implying identical support among all previously listed products. No unrelated domain was reviewed or enriched.

## Live Sources

[generator]: https://openapi-generator.tech/docs/customization/
[oas]: https://spec.openapis.org/oas/v3.1.1.html
[apollo]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/composition
[buf]: https://buf.build/docs/breaking/
[proto3]: https://protobuf.dev/programming-guides/proto3/
[objects]: https://json-schema.org/understanding-json-schema/reference/object
[protojson]: https://protobuf.dev/programming-guides/json/
[api-design]: https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design
[http]: https://www.rfc-editor.org/rfc/rfc9110.html
[jsonapi]: https://jsonapi.org/format/1.1/
[pact]: https://docs.pact.io/
[deploy]: https://docs.pact.io/pact_broker/can_i_deploy
[bsr]: https://buf.build/docs/bsr/
[asyncapi]: https://www.asyncapi.com/docs/migration/migrating-to-v3
[bff]: https://learn.microsoft.com/en-us/azure/architecture/patterns/backends-for-frontends
[gateway]: https://learn.microsoft.com/en-us/azure/architecture/microservices/design/gateway
[grpcweb]: https://github.com/grpc/grpc-web
[presence]: https://protobuf.dev/programming-guides/field_presence/
[deadlines]: https://grpc.io/docs/guides/deadlines/
[status]: https://grpc.io/docs/guides/status-codes/