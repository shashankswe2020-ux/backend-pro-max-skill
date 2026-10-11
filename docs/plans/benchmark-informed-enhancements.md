# Benchmark-informed enhancement plan

Status: M1, the authorized offline portions of M2/M3, and M4's local coverage fixes
are implemented and validated. A separately approved 96-attempt, required-retrieval
live exploratory run completed on 2026-10-11. The planned larger optional/required
study, independent review, and held-out validation remain pending.

### M1 delivery

- Canonical domain/stack schemas shared by the manifest and actual MCP discovery/validation.
- Real stdio known-answer retrieval and error-contract checks, plus signature/catalogue parity tests.
- Pre-spend image/source checks and budget-accounted provider capability probes, implemented
  and tested with offline fixtures; live provider probes require separate spending approval.
- Retrieval provenance, delivery/truncation/error/cost traces and review-bound report gates.
- Legacy pilot compatibility verified without rewriting the original artifacts.

See [contributor instructions](../../CONTRIBUTING.md#m1-integration-and-evaluation-gates)
for commands, the MCP error compatibility change, and the evidence-review format.
Actual installed-editor activation, independent relevance review, and a new required-use
generation treatment remain later milestones, not claims made by the M1 smoke check.

### M2 offline delivery

- Harmonized installed/project skill guidance and canonical MCP descriptions with concrete
  triggers, negative controls, and conditional stack-first behavior.
- Opt-in `compact-v1` search responses in CLI/MCP, using existing intent classification and
  verbatim evidence fields; raw defaults and decision/design paths remain unchanged.
- Bounded JSON with whole-unit omission, explicit missing metadata, and no inferred confidence.
- Draft 40-prompt activation and 20-case retrieval suite, offline response ablation bundles,
  and scoring for externally collected MCP observations.

The draft cases were exposed during development and are not genuine held-out evidence.
Independent label/source review and real model experiments remain pending; the 80%/10%
activation goals and 90% applicability goal have not been demonstrated.
See [M2 contributor instructions](../../CONTRIBUTING.md#m2-activation-guidance-and-opt-in-evidence-responses)
for contracts, formats, and reproducible offline commands.

### M3 offline delivery

- Added 24 draft executable tasks, balanced across backend, pinned framework,
  mixed, and negative-control tracks, with separate agent and grading exports.
- Added independently frozen optional/required protocol snapshots and reproducible,
  counterbalanced schedules of 288 assignments each.
- Implemented required-source gates, a shared three-call allowance, actual local
  BackendPro MCP transport, and explicitly fixture-only Context7 replay.
- Added isolated Docker grading, reference/starter validation, artifact-bound reports,
  task-cluster statistics, and within-policy Holm adjustment.
- Verified all 24 references pass and all 24 buggy starters fail their acceptance checks.

These are infrastructure/workflow results, not model comparison outcomes. The task set
is author-created and public, sources/labels still need independent review, and the
offline CLI neither implements paid model execution nor authorizes spending.
See [M3 contributor instructions](../../CONTRIBUTING.md#m3-balanced-exploratory-suite-offline).

### M3 live exploratory result (2026-10-11)

The user subsequently approved a smaller live treatment: 24 tasks x four arms x
one repetition, required retrieval, and retrieval-then-submit coding without
shell access or test feedback. A new post-M4 snapshot was frozen before execution.
The original M2/M3 snapshots and SWE-bench results were preserved.
See the [published assessment and evidence exports](../../benchmarks/m3/results/2026-10-11/README.md).

| Arm | Passed / assigned | Actual retrieval calls | Empty calls |
|---|---|---|---|
| Baseline | 24/24 | 0 | 0 |
| Context7 | 24/24 | 24 | 0 |
| BackendPro | 24/24 | 48 | 14 |
| Both | 24/24 | 48 | 7 |

All 120 retrieval calls were delivered to a subsequent successful model request;
all 96 attempts completed and passed isolated grading, with no provider errors,
noncompliance, or unsettled reservations. Total incremental API cost upper bound
including capability probes: **$2.911524**, within the separately approved $35
ceiling. All 680 retained evidence-file hashes and ledger totals were verified,
and the machine-readable report reproduced exactly.

**Decision:** this suite saturated at ceiling, including the no-tool baseline.
It cannot establish a coding benefit, equivalence, or superiority. The degenerate
paired bootstrap interval at zero reflects these all-pass observations, not
proof of equal population performance. Context7 returned nonempty evidence on
48/48 calls across its two arms; BackendPro returned nonempty evidence on 51/72,
with 21 empty calls. Relevance/application remain unreviewed, and 22/48 Context7
responses needed truncation under the common delivery bound. These are useful
retrieval diagnostics, not a product ranking.

Before further spending, develop a harder independently reviewed task set with
nontrivial baseline headroom and version-specific source needs. Do not tune on
this public all-pass set or simply repeat it and claim more statistical power.
See [live collector instructions](../../CONTRIBUTING.md#live-m3-exploratory-collector).

### M4 local coverage delivery

The unchanged M2 retrieval suite exposed three reproducible empty scoped searches.
None had matching topical tokens in that scope's searchable columns. These were
coverage omissions, not demonstrated BM25 ranking failures:

| Query and scope | Narrow addition | Before / after matches |
|---|---|---|
| `graceful shutdown`, `container` | Kubernetes Pod termination: shared preStop/shutdown budget, stop signals, concurrent endpoint updates | 0 / 1 |
| `transaction`, `java-spring` | Spring proxy transaction boundaries and explicit checked-exception rollback rules | 0 / 1 |
| `proxy`, `nodejs-express` | Topology-specific proxy trust and forwarded-header handling | 0 / 1 |

Generic shutdown advice already existed in `reliability`; the container entry
adds Kubernetes-specific applicability rather than silently widening the scope.
Each new row was checked against linked official documentation. Existing row
bytes, search code, synonyms, defaults, and the original benchmark artifacts
were preserved.

Validation: 336 targeted tests pass, including existing golden queries, new
literal/paraphrase regressions, strict schemas, CLI, compact responses, and real
MCP transport. A fresh bundle of the same 20 queries has zero empty results
(previously three); the other 17 cases retain their ordered result citations.
All responses remain within 6000 characters. Compact remains smaller than pretty
raw in 12/20 cases and minified raw in 6/20; no additional size gain is claimed.

These development regressions are not independently held out. No model tasks
were rerun and no paid calls were made during that M4 implementation; the later
live treatment above does not directly test these additions, so their coding
benefit remains unmeasured.
Independent source/applicability review and broader trace-supported changes
remain gated. The preserved M3 snapshot describes the old corpus: freeze a new
snapshot before evaluating this version rather than updating historical hashes.
See [M4 contributor instructions](../../CONTRIBUTING.md#m4-evidence-backed-local-coverage).

## 1. What we learned

Primary evidence: [comparison report](../../benchmarks/swebench-pilot/comparison-results.md),
[machine-readable results](../../benchmarks/swebench-pilot/comparison-results.json),
and [comparison protocol](../../benchmarks/swebench-pilot/comparison-protocol.json).

| Observation | Supported conclusion | Not supported |
|---|---|---|
| Baseline 12/18; Context7 available 14/18; BackendPro available 12/18; both available 13/18 | These are the observed outcomes of this optional-tool pilot | A retrieval-quality ranking or product winner |
| Zero knowledge-tool calls across 72 attempts | The pilot did not exercise either knowledge base | BackendPro content is poor, or Context7 content is better |
| Custom native tools, rather than installed skill/MCP client workflows | This measures selection of these particular tool definitions | Installed skills or actual MCP clients fail to activate |
| All 72 generations finished without budget/time/turn-limit exits; no grading errors | The completed comparison produced usable coding outcomes | Spending limits explain the unresolved tasks |
| Two of the original 20 reference-patch tasks timed out and were excluded equally | Environment validation and transparent cohort amendments matter | The retained 18 tasks represent every backend use case |
| Aggregate API cost upper bound was $3.575932 | This particular pilot was inexpensive | A forced-retrieval or larger experiment will cost the same |

**Main decision:** first make tool selection, evidence retrieval, and evidence application
observable. Do not replace BM25, expand the corpus indiscriminately, or advertise a winner
based on this run.

Separate repository inspection found a confirmed integration gap:
[gen_tools_schema.py](../../src/backend-pro-max/scripts/gen_tools_schema.py)
enumerates only 20 domains while the canonical registry in
[core.py](../../src/backend-pro-max/scripts/core.py) contains 34.
The omitted domains are `antipattern`, `api-contract`, `capacity`, `compliance`,
`cost`, `edge`, `incident`, `interview`, `latency`, `migration`, `ml-platform`,
`mobile-backend`, `multi-tenant`, and `release`.
This is a surface-parity defect, **not an established cause of the pilot's non-use**.

## 2. Prioritized work

All numerical acceptance targets below are prospective engineering goals, not measured results.
Effort estimates are engineering days for one maintainer; model runs and independent review
may add elapsed time.

### P0-A: fix integration parity (1-2 days)

**Owner:** product/integration maintainer. **Dependency:** none.

- Derive domain and stack enums from `CSV_CONFIG` and `STACK_CONFIG`; regenerate
  [tools.json](../../tools.json) instead of maintaining parallel lists.
- Compare all eight tools across the generator and actual MCP discovery:
  names, required arguments, enums, defaults, and supported output formats.
  Check CLI registries and installed documentation against the same canonical values.
- Extend [MCP tests](../../tests/test_mcp_server.py), including the existing stdio
  handshake/list/call integration test; do not duplicate an integration test that already exists.
- Specify invalid-input, transport-error, and no-results behavior. Verify errors are recognizable
  as failures by a real client, not merely successful calls carrying an ambiguous dictionary.
  Preserve existing consumer contracts or provide a documented compatibility path.
- Correct generator documentation that implies signature-derived schemas while definitions
  remain manually maintained.

**Acceptance:** every current domain and stack is represented (34 and 12 today), with
set-equality tests against the registries; all eight tools have matching definitions;
invalid-input and transport-error cases are distinguishable from legitimate empty results.
Existing API/CLI behavior and targeted tests remain passing.

### P0-B: add evaluation readiness and trace gates (2-3 days)

**Owner:** evaluation maintainer. **Dependency:** P0-A for canonical product-surface checks.

Extend the existing [runner](../../scripts/run_swebench_comparison.py) and
[reporter](../../scripts/report_swebench_comparison.py), retaining the durable ledger,
isolation policy, evidence hashes, and official grading.

- Preflight the selected model's actual request parameters and tool support, not only its
  presence in the model catalog. Count any paid probe against the approved budget.
- Before generation, validate image architecture, reviewed source adjustments, harness/dataset
  compatibility, credentials without exposing them, and the selected grading cohort.
- Smoke-test actual product transport/discovery and a known-answer retrieval fixture.
  A successful HTTP request or tool listing alone is not a retrieval readiness check.
- Record tool availability, selection, query, returned evidence identifiers, errors, empty results,
  truncation, latency, and cost separately. Label evidence application using an explicit rubric;
  a call or citation alone does not prove useful application.
- Add separate report outcomes for **activation measured** and **retrieval comparison evaluable**.
  Zero-call optional runs remain valid activation observations, but cannot produce retrieval
  superiority claims.
- For retrieval-required experiments, verify the prescribed calls happened before coding.
  Retain and count failures/noncompliance; never silently drop attempts or retry for a better score.

**Acceptance:** offline fixtures cover zero calls, irrelevant results, empty results, transport
failure, useful evidence, and unconsumed evidence. Reports cannot describe a zero-call run as
a content-quality comparison. Every attempt has an auditable status and cost record.

### P1-A: improve task-appropriate activation (2-3 days)

**Owner:** skill/MCP maintainer. **Dependencies:** P0-A and P0-B.

Hypothesis: clearer tool descriptions and installation guidance may help agents select useful
tools. The pilot did not establish why agents skipped retrieval.

- Improve descriptions in [mcp_server.py](../../src/backend-pro-max/scripts/mcp_server.py)
  and the generated manifest with concrete triggers: transaction boundaries, retries,
  idempotency, schema migrations, framework-specific behavior, and operational failure handling.
- Harmonize [skill-content.md](../../src/backend-pro-max/templates/base/skill-content.md),
  the [base skill](../../src/backend-pro-max/templates/base/SKILL.md), and the
  [project skill](../../.claude/skills/backend-pro-max/SKILL.md).
  Stack-first guidance should apply when a relevant named stack is known; do not invent a stack.
- Include counterexamples: typo fixes, link changes, and self-contained local edits do not
  automatically need knowledge retrieval. Do not impose "always call BackendPro."
- Reuse existing `classify_intent`, decision/design functions, and intent-aware formatting
  after invocation. Changing a post-invocation router cannot itself cause initial tool selection.
- Test one supported real installed-client workflow first, with pinned client/model/settings.
  Keep skill-driven, MCP-driven, and simplified native-tool results separately labeled.

**Acceptance experiment:** freeze 40 independently reviewed prompts before tuning:
20 where retrieval is useful and 20 negative controls. On a held-out evaluation split, aim for
at least 80% appropriate activation and no more than 10% unnecessary activation.
Report exact counts, repeated-run variability, and confidence intervals; these small-set goals
are engineering gates, not product superiority evidence.

### P1-B: make retrieved evidence easier to apply (2-3 days)

**Owner:** retrieval/output maintainer. **Dependency:** P0-B; can proceed alongside P1-A.

Hypothesis: concise, task-relevant evidence may improve application once tools are actually used.

- Evaluate existing intent-aware outputs before adding another response abstraction.
- Prototype an opt-in compact response containing supported recommendations, applicability,
  constraints, failure modes, verification steps, source URLs, and available freshness metadata.
  Distinguish retrieved facts from suggested verification; do not manufacture missing guidance.
- Preserve complete evidence/citation units under response limits and explicitly report truncation.
  Keep structured output parseable and cite only sources actually returned.
- Preserve existing default output shapes and the zero-dependency BM25 path.
  BM25 `_score` is a ranking signal, not a calibrated probability of correctness.
- Measure evidence relevance and correct application independently from invocation rate.

**Acceptance:** existing output-contract tests pass; bounded structured outputs remain parseable;
all returned citations map to retrieved sources; missing metadata is explicit.
On at least 20 held-out, source-checked retrieval cases, target at least 90% reviewer-rated
applicability. Compare compact versus existing output on the same cases before changing defaults.

### P2: build a balanced comparison suite (3-5 days, plus review/run time)

**Owner:** evaluation maintainer and an independent task reviewer.
**Dependencies:** P0-A/P0-B; freeze the product version being evaluated.

Keep SWE-bench as a coding control/regression track. Add these complementary tracks without
claiming that a custom suite is an established industry standard:

| Track | Example | Acceptance evidence |
|---|---|---|
| Backend correctness/reliability | Duplicate delivery, timeout/retry behavior, transaction races | Hidden runnable tests, concurrency/fault scenarios, invariants |
| Version-sensitive framework/API usage | Supported API migration or configuration for a pinned release | Version-pinned execution and official source checks |
| Mixed backend/framework tasks | Implementing an idempotent endpoint using a particular framework | Both correctness tests and framework compatibility |
| Negative controls | Small local edits requiring no external knowledge | Correct patch plus unnecessary-call and cost measurements |

Start by authoring and independently reviewing 24 tasks, six per track. Separate development
examples from held-out tasks; freeze task statements, expected versions, rubrics, and hidden
tests before collecting model outputs. Do not select only BackendPro-friendly problems.

Run two **separate, preregistered experiments**:

1. **Natural selection:** baseline, Context7, BackendPro, and both are available as assigned;
   retrieval is optional. Measure adoption, task outcomes, and overhead.
2. **Retrieval-required:** baseline remains tool-free; each single-tool arm must retrieve before
   coding; the combined arm must retrieve from both. Use the same total retrieval-call and
   response-size allowance across knowledge-enabled arms, documenting its allocation.
   This tests usefulness under prescribed use, not natural adoption.

Use canonical definitions and verified product adapters. Record whether each invocation goes
through MCP or another documented API; do not describe a direct Python wrapper as an MCP test.
Pin tool, corpus, model, client, dependency, and API versions where available.
Context7's live index may not be reproducible exactly: retain permitted evidence and timestamps,
record hashes/identifiers, and disclose this limitation.

**Protocol requirements:**

- Equal model settings, task context, generation limits, and per-attempt ceilings; a shared
  total retrieval allowance in the combined arm; randomized/counterbalanced execution order.
- Budget-approved repetitions (target three per task/arm), with no best-of-N selection.
  Derive the next spending cap from measured retrieval costs and obtain approval before calls.
- Report all attempts, including tool failures and empty results. Separate total treatment
  outcomes from descriptive analyses of successful retrieval; do not condition headline
  results on only successful calls.
- Report per-track solve rate, invocation rate, relevant-evidence rate, correct application,
  regressions, token/currency cost, and latency. Do not label generation time as retrieval latency.
- Use blinded, source-checked judgments with two reviewers and disagreement resolution for
  non-executable design answers. Do not let either product supply the grading rubric.
- Predeclare a primary outcome, practical-effect threshold, paired analysis, confidence
  intervals, and correction for multiple comparisons. Account for repeated observations of
  the same task rather than treating repetitions as independent tasks.
- Treat the 24-task study as exploratory. Use observed discordance/variance for a power analysis
  before any larger confirmatory study or public superiority claim.

**Acceptance:** protocol and rubric locked before execution; four arms receive the same cohort;
knowledge tools are genuinely exercised in the required-use experiment; all outcomes and
deviations are retained. A winner is not required for a useful report.

## 3. Invest in retrieval only when traces identify the failure

Existing intent classification, optional hybrid search, reranking, MCP, and citations are
already documented in the [Tier 2](tier-2-retrieval-quality.md) and
[Tier 3](tier-3-agent-mcp.md) plans. Do not propose rebuilding them as missing capabilities.

| Diagnosed failure | Next intervention | Evidence required before accepting the change |
|---|---|---|
| Tool not selected | Descriptions, skill guidance, client integration | Held-out activation improvement without excessive unnecessary calls |
| Relevant knowledge absent | Add source-verified rows to the relevant domain/stack | Coverage tests and source/freshness review |
| Knowledge exists but query/ranking misses it | Query formulation, existing expansion/hybrid/reranker ablations | Held-out relevance/recall gains and end-to-end validation |
| Relevant evidence retrieved but ignored | Compact output or application guidance | Trace-reviewed increase in correct application |
| Evidence applied incorrectly | Applicability constraints, examples, verification guidance | Reproducible regression/fault tests and source checks |
| General coding or infrastructure failure | Fix harness/environment or classify model failure | Reproducer showing the actual failing layer |

Any diagnosed corpus or ranking change must pass existing ranking-quality tests plus new
held-out cases. Re-run affected end-to-end tasks; relevance gains alone do not prove coding gains.

## 4. Delivery order and decision gates

| Milestone | Deliverable | Go/no-go decision |
|---|---|---|
| M1: trustworthy integration, roughly 3-5 days | Canonical schema parity, real transport smoke checks, trace/report gates | No larger paid comparison until integration and reporting gates pass |
| M2: activation and evidence, roughly 4-6 days | Held-out activation results and compact-output ablation | Tune only the failing layer; keep defaults if improvements are unproven |
| M3: balanced exploratory evaluation | Reviewed suite, locked protocols, approved budget, per-track report | Run a larger confirmatory study only if effect sizes justify it |
| M4: conditional product changes | Trace-supported corpus/ranking improvements | Merge only with regression evidence and documented tradeoffs |

The recommended first implementation is **M1**, not a search-engine rewrite.
M1, M2/M3's offline work, and M4's local coverage slice were subsequently authorized
and implemented locally. No new paid run, commit, or push was performed as part
of these implementations.

## 5. Publication policy

- Preserve the original manifest, comparison protocol, exclusions, and 72-attempt report.
  New treatments get new versioned protocols and reports; never overwrite the pilot.
- Link future summaries to raw counts, actual retrieval use, limitations, and approved budgets.
- Do not promote the observed 77.8% versus 66.7% difference as evidence that Context7 retrieval
  is superior: neither product was invoked.
- Treat complementarity as a hypothesis too. Publish mixed-task results before claiming that
  using both is better.
- Until informative evidence exists, describe BackendPro's curated backend guidance and
  Context7's library-documentation role without an unsupported winner claim.
