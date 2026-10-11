# BackendPro / Context7: SWE-bench pilot comparison

**Status: completed.** Model: `claude-opus-5-5`. 18 identical tasks per arm, one attempt per task, 72 assigned attempts.

**This is an exploratory pilot, not a full leaderboard run or a universal product ranking.**

| Arm | Resolved / 18 | 95% Wilson interval | Cost upper bound | Attempts using knowledge tools |
|---|---:|---:|---:|---:|
| baseline | 12/18 | 43.7%-83.7% | $0.8859 | 0/18 |
| context7 | 14/18 | 54.8%-91.0% | $0.8018 | 0/18 |
| backendpro | 12/18 | 43.7%-83.7% | $0.8484 | 0/18 |
| both | 13/18 | 49.1%-87.5% | $1.0298 | 0/18 |

## Interpretation

No knowledge tool was invoked in any model attempt. These results compare tool availability only and do not measure the usefulness or quality of Context7 or BackendPro retrieval.

Aggregate API cost upper bound, including startup: **$3.5759** against the authorized $25 cap.

Two tasks were excluded equally before generation because their reference-patch evaluations timed out: `django__django-10097`, `sympy__sympy-16450`.

## Paired outcomes

| Comparison | Left only resolved | Right only resolved | Both resolved | Exact paired p (unadjusted) |
|---|---:|---:|---:|---:|
| baseline_vs_context7 | 0 | 2 | 12 | 0.5000 |
| baseline_vs_backendpro | 0 | 0 | 12 | 1.0000 |
| baseline_vs_both | 0 | 1 | 12 | 1.0000 |
| context7_vs_backendpro | 2 | 0 | 12 | 0.5000 |
| context7_vs_both | 1 | 0 | 13 | 1.0000 |
| backendpro_vs_both | 0 | 1 | 12 | 1.0000 |

## Method

- Official SWE-bench 4.1.0 evaluator; frozen Verified dataset revision `c104f840cc67f8b6eec6f759ebc8b2693d585d4a`.
- Same native-tool scaffold; fresh network-disabled AMD64 containers on Apple Silicon.
- Adaptive thinking with low effort; 16 turns, 2,048 output tokens/turn, $0.34 ceiling per attempt.
- No forced retrieval; knowledge-enabled arms share three retrieval calls.
- Reference patches and grading-only tests were not supplied to the coding model.
- The [approved protocol](comparison-protocol.json) records scope amendments, limits and pricing sources.

## Limitations

- Exploratory 18-task, one-attempt-per-arm comparison, not a full SWE-bench leaderboard run.
- The cohort is conditioned on infrastructure success on this Mac; two exclusions must remain visible.
- A $0.34 per-attempt ceiling is restrictive for multi-step Opus issue fixing; report limit exits.
- Native tool availability is being compared, not editor-specific MCP clients or skill auto-invocation.
- Public benchmark contamination and model sampling variability are not controlled.
- Any incomplete provider/generation/evaluation run must not be presented as a conclusive winner.
- Confidence intervals and paired tests are descriptive; six pairwise p-values are unadjusted for multiplicity.
- Do not declare a universal product winner from this small, public Python issue-fixing sample.
- Generation latency includes container setup and cleanup, but excludes queueing, dataset loading and grading.
- One interrupted conversation was continued with its exact prior messages and patch; completed attempts were not regenerated.
- Reviewed dependency pins and file-mode changes from the official images were preserved equally across arms.
- Startup/resume overhead is included in generation timings; these timings do not rank retrieval speed.
- The initial unsupported-parameter requests produced no model output; their evidence and shared ledger were retained.
- Context7 cost is an upper bound at the public overage rate, not the account's actual invoice.

Full per-task outcomes, token counts, timing, generation exits, cost accounting and hashes are in [comparison-results.json](comparison-results.json).
