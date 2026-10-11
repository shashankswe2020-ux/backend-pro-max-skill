# Context7 vs BackendPro: live exploratory results

**All four arms passed 24/24 tasks. No coding-performance winner was established.**

![Strengths, limits and all-pass task chart](../../../../docs/readme/context7-vs-backendpro.svg)

## Results

| Arm | Passed / assigned | Retrieval calls | Empty calls | Incremental API cost upper bound |
|---|---:|---:|---:|---:|
| Baseline | 24/24 | 0 | 0 | $0.223340 |
| Context7 | 24/24 | 24 | 0 | $0.691280 |
| BackendPro | 24/24 | 48 | 14 | $0.914836 |
| Both | 24/24 | 48 | 7 | $1.071908 |

All **96 attempts completed and passed** isolated acceptance tests. Every track
(backend, framework, mixed, control) scored 6/6 in every arm. All **120 retrieval
responses reached a subsequent successful model request** before submission.
There were no provider errors, grading errors, required-use violations, or
unsettled spending reservations.

Total incremental API cost upper bound including probes: **$2.911524**, within
the separately approved $35 cap. Anthropic usage was $2.666524; Context7 was
conservatively accounted at $0.005/request ($0.245000 including its probe),
even if requests were covered by the account's free quota. This is not an
invoice; subscription seats and local compute are excluded.

## Strengths and limits

| | Context7 | BackendPro |
|---|---|---|
| Evidence role | Library/API documentation and version-aware lookup | Curated backend patterns, operational failure guidance and stack rules |
| Strengths | Source-linked snippets; library/version lookup options | Offline deterministic BM25 retrieval; citations and explicit trade-offs |
| Limits | Remote API/quota dependency; changing live index; response truncation | Curated coverage/freshness maintenance; not a complete API reference |
| Best-fit decision | Retrieve library details, then check version applicability | Retrieve engineering guidance, then check system applicability |

Different roles do not prove complementarity: the both arm did not improve the
observed pass rate. See the official [Context7 API guide](https://context7.com/docs/api-guide)
and [plans](https://context7.com/plans) for its capabilities and quotas; see the
[BackendPro implementation](../../../../src/backend-pro-max/scripts/core.py) and
[corpus](../../../../src/backend-pro-max/data/) for local retrieval scope.

## Retrieval diagnostics

Provider totals below include both single-source and combined arms. Queries
were model-selected, not a matched-query retrieval-quality test.

| Provider | Calls | Nonempty | Empty | Truncated | Mean retrieval latency |
|---|---:|---:|---:|---:|---:|
| Context7 | 48 | 48 | 0 | 22 | 5.263 seconds |
| BackendPro | 72 | 51 | 21 | 0 | 0.225 seconds |

Timings measure adapters in this environment, including local MCP startup
versus a remote network/API call. They are not general latency guarantees.
BackendPro's 21 empty calls were spread across framework (9), backend (5),
mixed (4), and control (3) tasks. Some queries chose mismatched scopes; empty
results need diagnosis rather than automatic attribution to missing content.

**Nonempty is not a relevance score.** Neither relevance nor correct application
was independently judged. Context7's 22 truncated replies need review of the
bounded evidence actually delivered, not just the full raw response.

## Frozen method

- Date: 2026-10-11. Model: `claude-opus-5-5`, adaptive thinking, low effort,
  standard tier, 2048 output tokens/turn, at most 16 turns/600 seconds.
- 24 public author-created Python tasks: six backend, six framework, six mixed,
  six trivial negative controls. Four arms, one repetition, counterbalanced order.
- Identical task and starter; retrieval then full-file submission. No shell,
  hidden-test access, or grading feedback before submission.
- BackendPro: actual local MCP search tools, BM25 defaults, compact output
  recommended in the prompt. Context7: live Search API v3 with automatic
  library selection and a Python language preference.
- Required source responses had to reach a subsequent model request before
  submission. Three calls total per knowledge-enabled arm, including both.
  Common 6000-character delivery bound with explicit truncation.
- Pinned Python 3.12.13, Pydantic 2.14.0, Starlette 1.7.0, HTTPX 0.28.1.
  Non-root Docker grading, network disabled, read-only root, no host mounts or
  credentials. All 24 references passed and 24 buggy starters failed beforehand.
- $0.34 per-attempt ceiling; $35 incremental API cap including probes.
  No provider retries, task substitutions or selective regeneration.

## What the results do not establish

The no-tool baseline also passed every task: a **ceiling effect**. The suite was
too easy for this model/scaffold to distinguish coding benefit. The observed
Context7-minus-BackendPro difference is zero; the paired bootstrap interval
`[0, 0]` and Holm-adjusted p-value `1.0` reflect the all-pass sample, **not
population equivalence**.

This custom exploratory suite is not SWE-bench or an industry-standard
certification. Public tasks are not held out; independent task/source/evidence
review remains pending. One repetition does not measure run-to-run variance.
Required retrieval on trivial controls measures imposed overhead, not natural
activation. These tasks do not directly exercise M4's three new corpus rows.

Before further paid comparisons, use a harder independently reviewed cohort
with baseline headroom and realistic version-specific documentation needs.
Do not repeatedly run this all-pass set to advertise a winner.

The [earlier SWE-bench pilot](../../../swebench-pilot/comparison-results.md)
invoked neither tool in any of its 72 attempts. Its score differences cannot
establish retrieval quality either.

## Published evidence and reproduction limits

- [Machine-readable report](comparison.json): unmodified export from the run,
  including all 96 per-attempt outcomes, timing, token/cost totals, paired
  statistics and 680 retained artifact hashes.
- [Frozen protocol](protocol.json): unmodified export, SHA-256
  `1e78a6ebde1dce6febcbb5ecdd91f0a1bb6b00cc5f387621f2f6c703c7164f8c`.
- [Provider diagnostics](retrieval-summary.json): aggregate projection of the
  retained observations; includes source artifact hashes.
- [Collector](../../../../scripts/run_m3_live.py),
  [draft tasks](../../tasks.py), and
  [execution instructions](../../../../CONTRIBUTING.md#live-m3-exploratory-collector).

The original request/response bodies, submitted files, individual grading
artifacts and spending database remain in the maintainer's retained local run,
not this repository. All 680 evidence hashes, source/corpus and validation hashes,
candidate/grade bindings, ledger totals, and exact report regeneration were
verified locally after execution. Hashes are not a substitute for publicly
available raw evidence: this publication alone does not enable an independent
full replay audit. Credentials and machine-specific paths are not published.

The exported protocol/report retain an inherited limitation about the original
offline M3 tool not executing models. That refers to the reused offline
infrastructure, not the separately authorized live collector used for this run.
Historical wording and results have not been rewritten.
