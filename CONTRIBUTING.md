# Contributing to Backend Pro Max

Thanks for helping make this skill smarter. The bar for contributions is:

> **Would a staff engineer be glad this row exists when an AI assistant
> surfaces it during an architecture review?**

## TL;DR

```bash
python -m pip install -e ".[dev]"
pytest                                 # regression suite must pass
python -m backendpro.scripts.validate  # every CSV must validate cleanly
ruff check src tests                   # lint
```

Open a PR on a branch (never push to `main`).

## Repository layout

```
src/backend-pro-max/
├── data/                # Domain CSVs (the knowledge base)
│   └── stacks/          # Per-language stack CSVs
└── scripts/
    ├── core.py          # BM25 engine, caching, synonyms, compare, stale
    ├── search.py        # CLI (search / compare / interactive / stale)
    └── validate.py      # CSV schema validator (used by CI)
tests/                   # pytest suite
.github/workflows/ci.yml # lint + validate + test + smoke test
```

## Adding a new row

1. Pick the right CSV in `src/backend-pro-max/data/`.
2. Match the existing column order **exactly**. If a value contains a
   comma or a newline, **wrap the field in double quotes** (escape inner
   quotes with `""`, never `\"`). The validator will reject misaligned
   rows.
3. Set `Last Updated` (where the column exists) to today's date in
   `YYYY-MM-DD` format. This powers the `--max-age-months` and
   `--stale` flags.
4. Run the validator locally: `python -m backendpro.scripts.validate`.
5. Run the tests: `pytest`.

### Severity / quality guidance

When a CSV has a `Severity` column, use one of: `Low`, `Medium`, `High`,
`Critical`. Reserve `Critical` for things that cause data loss, security
incidents, or outages.

### Keywords column

The `Keywords` column is the single biggest lever for search quality.
Include:

- The canonical name and common aliases (`postgres`, `postgresql`, `pg`).
- The acronym and the expansion (`cdc`, `change data capture`).
- Common misspellings if widely used (`kuberentes`).
- Adjacent jargon a staff engineer might query with.

## Adding a new domain

1. Create `src/backend-pro-max/data/<domain>.csv`.
2. Register it in `CSV_CONFIG` in `core.py` (declare `search_cols` and
   `output_cols`).
3. Add a keyword bag in `_DOMAIN_KEYWORDS` (used by auto-detection).
4. Add at least one row, then run `pytest`.
5. Update `README.md` and `CLAUDE.md`.

## Adding a new stack

1. Create `src/backend-pro-max/data/stacks/<stack>.csv` with the canonical
   columns: `Category, Guideline, Description, Do, Don't, Code Good,
   Code Bad, Severity, Docs URL`.
2. Register it in `STACK_CONFIG`.
3. Update docs.

## Search-quality tests

If you add a domain or noticeably change ranking behavior, please add a
ranking-quality test in `tests/test_search.py`. The contract is:
"this canonical query must rank this canonical row at #1." Example:

```python
def test_search_saga_finds_saga_in_patterns():
    res = core.search("saga", domain="pattern")
    assert any("saga" in str(v).lower() for v in res["results"][0].values())
```

## Coverage targets and retrieval diagnostics

Coverage targets live in [coverage-targets.yml](coverage-targets.yml). Keep
the bundled [defaults](src/backend-pro-max/data/coverage-targets.yml) in sync;
tests enforce parity so wheel installations use the same targets. Broad
targets may map to exact category labels or primary row names through
[coverage-aliases.json](src/backend-pro-max/data/coverage-aliases.json).
Do not map arbitrary description text or unrelated categories just to remove
a gap. JSON reports include `target_matches` as supporting evidence.

Review the linked source before updating a row's review date. URL presence
or a successful HTTP response does not establish factual correctness.

```bash
python -m pip install -e ".[dev,mcp,semantic,rerank]"
python -m pytest tests/test_mcp_server.py tests/test_semantic.py tests/test_rerank.py
python -m backendpro.scripts.benchmark tests/retrieval-benchmark.json --output benchmark.json
python -m pip wheel --no-deps --wheel-dir dist .
python scripts/smoke_wheel.py dist/backendpro-0.9.0-py3-none-any.whl
```

The benchmark reports binary Recall@K, MRR@K, nDCG@K, and warm-query p50/p95
latency for BM25, hybrid, and hybrid-plus-reranking. Downloads, model loading,
and index creation are excluded from latency. Use `--modes bm25` without ML
dependencies, or `--max-p95-ms N` to enforce your environment's latency budget.
The supplied eight-query set is an author-labeled diagnostic, not a held-out
evaluation; review broader relevance labels independently before making
retrieval-quality claims. CI retains the model benchmark as an artifact.

### Context7 comparison: SWE-bench Verified pilot

The [pilot protocol](benchmarks/swebench-pilot/protocol.json) preregisters
20 tasks and four paired arms: baseline coding tools, Context7, BackendPro,
and both. Baseline still has repository editing and test tools; it has no
supplemental knowledge retrieval. The authorized aggregate paid-service cap
is $25. The requested model ID is recorded verbatim but is not yet verified.

Freeze a selection from an immutable dataset revision:

```bash
uv run --no-project --python 3.12 --with-requirements benchmarks/swebench-pilot/requirements.txt \
  python scripts/prepare_swebench_pilot.py --output pilot-manifest.json
```

Use `--revision <dataset_sha>` from a previous manifest to reproduce its
task selection. Selection ranks all 500 IDs by a fixed seeded SHA-256 hash,
not by BackendPro coverage or observed performance. The manifest includes
20 task IDs, base commits, all 80 scheduled attempts, corpus hashes, and
credential-presence/Docker checks. It excludes gold patches and grading
tests, refuses to overwrite an existing selection, and makes no paid calls.

**The preparation command alone does not generate or grade model patches.**
The actual comparison runner described below requires `ANTHROPIC_API_KEY`
and `CONTEXT7_API_KEY`, verified model access/pricing, working isolated Docker
execution, pinned agent/harness versions, tested tool isolation, and a
pre-request spending gate. Never put credentials in a manifest or chat.
Do not run generated patches directly on the host.

Once those prerequisites are implemented and verified, submit each arm's
predictions to the [official SWE-bench evaluator](https://www.swebench.com/SWE-bench/guides/evaluation/).
Report resolved/20, paired outcomes, uncertainty, costs, and all incomplete
attempts. Do not present preparation tests as benchmark results, or this
small Python issue-fixing pilot as evidence of universal product superiority.

Infrastructure validation on 2026-10-10 attempted all 20 frozen tasks:
**18 reference patches passed; 2 evaluations timed out at 600 seconds**
(`django__django-10097` and `sympy__sympy-16450`). The passing tasks account
for 31 FAIL_TO_PASS and 2,492 PASS_TO_PASS checks. See the
[complete validation report](benchmarks/swebench-pilot/infrastructure-validation-all.json);
the [initial smoke-test record](benchmarks/swebench-pilot/infrastructure-validation.json)
is retained as historical evidence. These are not BackendPro or Context7
scores. Investigate and revalidate the two failed environments before
claiming the full pilot is ready; do not silently drop or replace them.

For this frozen dataset schema, use `swebench==4.1.0` with
`datasets==4.2.0` in an isolated Python 3.12 environment. Version 5.0.2
requires newer dataset fields and cannot directly grade the frozen rows.
On Apple Silicon, the validated path uses x86 emulation: explicitly pull
the task image with `docker pull --platform linux/amd64` before evaluation.
The 4.1.0 evaluator otherwise tries the host architecture when pulling,
even though its container specification requests x86. Record the image
digest and use a fresh run ID after a failed attempt; do not reuse
reference-patch results as model results. Images were retained for reuse;
validation containers and temporary gold dataset input files were removed.
Two image-prefetch workers overlapped downloads with sequential evaluation;
test execution remained at one worker throughout.

The user-approved [comparison amendment](benchmarks/swebench-pilot/comparison-protocol.json)
retains the same 18 validated tasks in every arm (72 attempts), uses the
verified direct API ID `claude-opus-5-5`, and records the two exclusions.
It does not overwrite the original 20-task preregistration. The native-tool
runner is an author-built scaffold, not an official SWE-bench agent.

Run generation and grading separately so reference patches never enter
the agent inputs:

```bash
export DOCKER_HOST="$(docker context inspect --format '{{.Endpoints.docker.Host}}')"
uv run --no-project --python 3.12 --with-editable . \
  --with-requirements benchmarks/swebench-pilot/comparison-requirements.txt \
  python scripts/run_swebench_comparison.py generate --output /absolute/path/to/new-run
uv run --no-project --python 3.12 --with-editable . \
  --with-requirements benchmarks/swebench-pilot/comparison-requirements.txt \
  python scripts/run_swebench_comparison.py grade --output /absolute/path/to/new-run
python scripts/report_swebench_comparison.py /absolute/path/to/new-run \
  --output /absolute/path/to/new-run-report.json
```

Generation reads an owner-only credentials JSON file at
`~/.config/backendpro/benchmark-credentials.json` (override with
`--credentials`). Never commit that file. It refuses an existing run
directory, reserves charges in a durable SQLite ledger before requests,
and stops on ambiguous provider errors without automatic retries.
The aggregate cap is $25; each attempt has the same $0.34 ceiling,
16-turn limit, and 2,048 output tokens per turn, using Opus 5.5's required
adaptive thinking with low effort. Knowledge-enabled arms
share a three-call retrieval limit. Two generation workers use separate,
network-disabled containers without host mounts or credentials.

Context7 calls are accounted at the conservative published overage price
of $0.005 each, even if covered by an account allowance. Anthropic charges
are reconciled against returned token usage; ambiguous requests retain
their reservations. This accounting bounds API charges, not subscriptions,
taxes, currency conversion, or unrelated account usage. Inspect provider
errors, budget exits, actual tool usage, and evaluator error counts before
interpreting scores; a successful process exit alone is not a graded result.
If startup requests were rejected before any model output, retain that run
as evidence and pass `--ledger /path/to/original-run/spending.sqlite3` to the
corrected run. This preserves the original aggregate budget rather than
granting another $25. Do not restart successful attempts as best-of-N.
The guarded `resume` mode preserves completed attempts, replays an
interrupted conversation with its own partial patch, and retains the
original per-attempt/global spend. It refuses changed model protocols.
Official images can contain dependency pins or file-mode changes relative
to their base commit; inspect and fingerprint those environment adjustments
before permitting them, rather than treating arbitrary source changes as safe.

The reporting command verifies all 72 assignments, patch hashes, returned
token usage, shared-ledger accounting, and official per-task grading
results. It writes JSON and Markdown summaries with paired outcomes,
uncertainty intervals, and actual knowledge-tool invocation counts. Tool
availability without invocation is not evidence about retrieval quality.

The [completed pilot report](benchmarks/swebench-pilot/comparison-results.md)
contains 72 real model attempts and 72 official grading outcomes, with no
evaluator errors. The baseline, Context7-available, BackendPro-available,
and both-available arms resolved 12, 14, 12, and 13 of 18 tasks respectively.
No model attempt invoked a knowledge tool. Do not present the numerical
differences as a retrieval-quality ranking or a product superiority claim.
The aggregate API cost upper bound was $3.575932, including startup checks.

### M1 integration and evaluation gates

The [enhancement plan](docs/plans/benchmark-informed-enhancements.md) separates
tool activation from evidence usefulness. M1 adds offline integration checks
and trace-aware reporting without changing the published pilot.

Run the local, **no-provider-call** check after installing the optional MCP extra:

```bash
python -m pip install -e ".[dev,mcp]"
python src/backend-pro-max/scripts/gen_tools_schema.py --check
python -m backendpro.scripts.check_tools
pytest tests/test_tools_schema.py tests/test_mcp_server.py \
  tests/test_retrieval_evidence.py tests/test_swebench_comparison.py \
  tests/test_comparison_report.py tests/test_swebench_pilot.py
```

The stdio check starts the real installed MCP module, compares all eight
discovered tool contracts, retrieves known Kafka evidence with citations,
and distinguishes empty results from invalid inputs and tool errors. It
does not certify an editor's skill activation or either provider's availability.
The canonical schemas derive all domain and stack enums from core registries.

**Compatibility:** successful MCP results retain their dictionary shape.
MCP invalid arguments and domain/tool failures now set `isError=true`;
clients must check this flag instead of assuming every response is successful.
Unknown arguments, invalid enums, non-positive result limits, empty ADR domain
lists, and negative freshness thresholds are rejected. Explicit `null` domains
still mean auto-detection. Direct Python calls retain their normal returned
error dictionaries, but unexpected runtime exceptions now propagate rather
than being converted into success-shaped dictionaries. No-results searches
remain successful responses with zero results.

For a **new, separately authorized paid generation**, startup first checks
MCP integration, pinned dependencies, the frozen cohort/corpus, image identity
and Linux AMD64 architecture, clean image working trees, and reviewed source
adjustments. Supply inspected fingerprints using
`--image-adjustments /absolute/path/to/image-source-adjustments.json`.
Images are checked read-only in isolated containers before any provider call;
adjustments are never automatically accepted. Unsettled ledger reservations
block further paid requests.

Then a budget-accounted model probe uses the same model, tool definitions,
thinking/effort, and token settings as generation and must return a native
`finish` call. A Context7 probe must return recognizable Django evidence,
not merely HTTP success or an echoed query. Unknown response shapes fail
closed for inspection. Both probe responses and costs are retained. This
probe is a transport/content sanity check, not a human relevance rating.
The successful startup is recorded in `readiness.json`; the benchmark still
uses its explicitly labeled custom native-tool adapters, **not MCP**.
No provider probes are performed by the offline check above.

New retrieval traces record model call identity, payload hashes, stable
evidence IDs, citations, empty/error/unclassified status, elapsed time, cost,
and model-visible truncation. `delivered=true` means a subsequent successful
model request included that output; a search immediately followed by `finish`
is not counted as consumed. Delivery never implies correct application.
Provider errors and budget-blocked calls remain in the trace.

The reporter verifies raw retrieval artifacts and their bounded tool outputs,
alongside the existing patch/grading/accounting checks. Its JSON and Markdown
separate `activation_measured` from `retrieval_comparison_evaluable`.
Zero calls, missing/unclassified evidence, incomplete runs, or missing
relevance/application reviews block a content comparison. All assigned
attempts and failures remain in the outcome denominator.

To assess evidence, an independent reviewer can add `evidence-review.json`
inside a **new** run directory, using a locked rubric and these fields:

```json
{
  "reviewer": "reviewer identifier",
  "rubric": "locked rubric version or reference",
  "events": {
    "INSTANCE_ID.backendpro:0": {
      "output_sha256": "hash from the tool event",
      "relevance": "relevant",
      "application": "not_applied",
      "rationale": "Explain applicability and cite the observed patch or behavior."
    }
  }
}
```

The event suffix is the zero-based index in the attempt's entire `tool_calls`
list, including shell calls. Relevance accepts `relevant`, `irrelevant`, or
`unknown`; application accepts `correct`, `incorrect`, `not_applied`, or
`unknown`. Unknown judgments block the gate. Reviews bind to the actual
bounded output, not unseen portions of the full artifact. Do not label
metadata-only hints in a truncated response as useful evidence.
Every knowledge-enabled arm/tool pair needs at least one verified,
delivered, relevant response, and every returned response needs a completed
review. Passing this readiness threshold does not establish statistical
power, good task coverage, correct application, or superiority.

The reporter can also flag noncompliance for a future `retrieval_policy:
required` protocol: prescribed tools must be attempted before the first
shell/finish call (a conservative boundary that includes inspection).
The current generator explicitly rejects required-use protocols; that
separate experimental treatment is deferred to M3. Failed/empty retrieval
is retained, not silently retried or excluded.

Legacy runs without trace metadata remain readable and explicitly lack
readiness evidence; no relevance judgments are invented. The reporter
refuses to overwrite either an existing JSON or Markdown report. Use a new
output path and retain the original protocol, report, and evidence.

### M2 activation guidance and opt-in evidence responses

The installed skill templates and MCP manifest now describe concrete retrieval
triggers and negative controls. Stack-first is conditional on a known supported
stack **and** a task that warrants retrieval. Existing intent, compare, decide,
ADR, and design code is reused; no keyword router is claimed to cause activation.
The original native-tool pilot scaffold is unchanged and does not measure
these installed-skill/MCP guidance changes.

Raw output and BM25 defaults remain unchanged. Opt in to bounded evidence:

```bash
backendpro "circuit breaker" --domain pattern --compact
backendpro "context cancellation" --stack go --compact
backendpro "idempotency" --all --compact
```

The equivalent MCP option is `response_format: "compact"` on
`backendpro_search`, `backendpro_search_stack`, and `backendpro_search_all`.
Other MCP tools retain their existing output contracts. CLI compact output
is JSON, can be combined with `--json`, and rejects incompatible modes such
as `--jsonl`, compare, design, ADR, stale, and interactive mode.

`compact-v1` quotes selected original field names and values in `facts`, with
source URLs, citation tokens, row freshness, missing categories, and omitted
field names. It does not infer recommendations or verification steps from
unrelated fields. `Last Updated` is source-row metadata, not a fresh URL check.
BM25 scores are omitted rather than converted into confidence probabilities.

Canonical minified JSON text is limited to 6000 Unicode characters, excluding
the CLI newline and the MCP protocol envelope/duplicate structured content.
Trailing evidence units are dropped whole, never sliced; `matched_count`,
`omitted_count`, and `truncated` disclose that loss. `budget_exhausted` means
matches existed but no whole unit fit; it is not `no_matches`. A query too
large for the metadata envelope raises an explicit error. Compact is an
experimental bounded evidence format, not a guarantee of fewer tokens or
greater relevance than raw output.

The [draft M2 suite](benchmarks/m2/suite.json) has 40 activation prompts
(20 positive, 20 negative, balanced across development/evaluation candidate
splits) and 20 retrieval cases. These are author-constructed and exposed during
development: **not independently reviewed, source-verified, or genuinely held
out**. A reviewer must approve/replace and separately lock cases before a
confirmatory study; do not tune on purported held-out outcomes.

Build a no-network/no-provider bundle:

```bash
python scripts/evaluate_m2.py bundle --output /absolute/path/to/new-m2-bundle
```

This snapshots the suite, code/guidance and corpus hashes, raw responses,
existing intent-formatted responses, and compact responses. The summary records
character lengths, actual omissions, zero matches, and pending reviews. Both
pretty and minified raw sizes are retained so whitespace savings cannot be
mistaken for content-quality improvements. No model activation, relevance,
source correctness, or application score is manufactured.

For future exploratory MCP-client observations, the offline scorer accepts:

```json
{
  "suite_sha256": "hash of the exact suite bytes",
  "surface": "mcp",
  "client": "actual client name",
  "client_version": "exact version",
  "model": "exact model identifier",
  "settings": {"record": "actual model and client settings"},
  "tool_manifest_sha256": "64-character hash of the exact exposed manifest",
  "repetitions": 3,
  "observations": [
    {
      "case_id": "activate-01",
      "repeat": 0,
      "status": "completed",
      "tool_calls": [{"name": "backendpro_search", "is_error": false}]
    }
  ]
}
```

Supply every assigned case/repeat, use an explicit empty call list for no
invocation, and record `client_error` for failed attempts. The snippet is a
shape example, not a complete observation set or a result. Do not label native
wrappers or skill-shell workflows as MCP. Retain original client traces:
this scorer summarizes supplied observations, not certifies their provenance.

```bash
python scripts/evaluate_m2.py activation --suite /path/to/frozen-draft-suite.json \
  --observations /path/to/observations.json --output /path/to/new-activation-summary.json
```

The scorer reports exact counts, missing/client/tool failures, per-repeat Wilson
intervals, and variability without pooling repeated tasks as independent samples.
The prospective 80% positive-activation / 10% unnecessary-activation gates are
tested at their exact boundaries; incomplete or failed runs cannot pass them.
Draft reports always keep acceptance unverified. Independently reviewed
activation experiments and the 90% applicability study remain pending, with no
paid calls authorized by the offline implementation.

### M3 balanced exploratory suite (offline)

[M3 task definitions](benchmarks/m3/tasks.py) contain 24 author-created,
executable tasks: six backend correctness/reliability tasks, six framework/API
tasks, six mixed tasks, and six negative controls. The framework cases pin
Pydantic 2.14.0, Starlette 1.7.0, and HTTPX 0.28.1 on Python 3.12.13.
References and acceptance checks are separated from agent-visible inputs.
These small, public tasks are **draft evaluation candidates**, not independent
held-out evidence or a replacement for SWE-bench.

Prepare the local grading image and freeze a new snapshot:

```bash
python -m pip install -e ".[dev,mcp]"
docker build -t backendpro-m3:offline-v1 benchmarks/m3/environment
python scripts/run_m3.py freeze --image backendpro-m3:offline-v1 \
  --output /absolute/path/to/m3/frozen
python scripts/run_m3.py self-test --frozen /absolute/path/to/m3/frozen \
  --output /absolute/path/to/m3/validation
```

Image construction may download public packages; grading, workflow replay,
and reporting make no paid provider calls. Freeze checks installed versions
and records the actual Docker image ID, architecture, all installed package
versions, corpus/code/guidance hashes, and every snapshot file hash. It emits
**separate optional and required protocol files** with identical limits and
cohorts. Each protocol schedules 24 tasks x four arms x three repetitions =
288 assignments (576 across both experiments), with deterministic task
shuffling and counterbalanced arm order.

The snapshot is not reviewer approval or spending authorization. Model identity
may be recorded with `--model`, but model settings, current prices, a new budget,
and independent task/source review must be locked before any real generation.
The previous pilot's budget must not be reused as approval for M3. No paid-model
executor or Context7 network call is exposed by this offline CLI.

`agent/<task-id>/` contains only the problem/environment metadata and starter
`solution.py`. Supply only that directory to a model, never the snapshot root,
`grading/`, task-definition source, reference solutions, or validation logs.
The code examples and tests are public in this repository, so contamination
remains possible even when the agent workspace is correctly isolated.

Self-test submits every reference and starter independently. It requires all
24 references to pass and all 24 buggy starters to fail assertions/errors.
A grader timeout or malformed report does not count as successful infrastructure
validation. This validates the environments and regression checks, **not
BackendPro/Context7 effectiveness**.

Candidate code runs only in a new non-root Docker container with no network,
no host mounts or credentials, a read-only root filesystem, bounded tmpfs,
dropped capabilities, a 512 MiB memory limit, one CPU, PID limit, bounded logs,
and a 15-second grading deadline. Candidate bytes and frozen checks enter as
data; the host never imports the candidate. Containers are removed in `finally`.
This is conventional executable-test grading, not a claim of resistance to a
candidate intentionally forging or introspecting its own test process.

```bash
python scripts/run_m3.py grade --frozen /absolute/path/to/m3/frozen \
  --task backend-01 --candidate /path/to/submitted/solution.py \
  --output /path/to/new-grade.json
```

The `RetrievalWorkflow` API enforces the treatment before an external collector
executes any `shell` or `finish` action. Required arms must attempt each assigned
source first, including before inspection. Both-source runs reserve calls for
any missing source and share the same three-call total as single-source runs.
Failures and empty responses consume calls; no automatic retry or selective
regeneration occurs. Successful retrieval is distinct from relevant evidence.
Inputs use canonical MCP schemas, and transports must be explicitly labeled.
Payloads and model-visible outputs are hash-bound; oversized output is a
parseable, explicitly truncated excerpt envelope capped at 6000 characters.

Exercise that gate with actual local BackendPro MCP and fixture-only Context7:

```bash
python scripts/run_m3.py replay --policy required --arm both --real-backendpro \
  --input benchmarks/m3/replay-example.json --output /path/to/new-replay.json
```

The example retains an initially blocked shell action and a blocked finish,
then an empty Context7 fixture. No shell command is executed and no Context7
request is sent. Without `--real-backendpro`, every knowledge action requires
an explicit `fixture` object. Replay reports are always labeled non-model
execution and cannot be passed off as model retrieval evidence.

For future externally collected model runs, reporting accepts a JSON object
with `protocol_sha256` (hash of the chosen frozen protocol file) and `attempts`.
Each attempt records:

- `id` from the frozen assignments, such as `backend-01.backendpro.r1`;
- `status`: `completed`, `budget_limit`, `time_limit`, `client_error`, or
  `not_started`;
- integer `cost_micro_usd`, `input_tokens`, `output_tokens`, and nonnegative
  finite `generation_seconds` (record zeros explicitly for genuinely unstarted attempts);
- `grade_file` (a basename beside the observation file), `grade_sha256`, and
  `candidate_sha256` for submitted candidates; completed attempts require grading;
- an ordered `trace`: shell/finish actions, retrieval actions with the full
  `RetrievalWorkflow.retrieve` event, and explicitly rejected actions with
  `status: "rejected"` plus an error. Record actual adapter time and transport;
  never relabel an offline fixture as a real provider response.

```bash
python scripts/run_m3.py report --frozen /absolute/path/to/m3/frozen \
  --policy required --input /path/to/observations.json --output /path/to/new-report.json
```

Reports verify assignment uniqueness, protocol/grade/candidate/environment
hashes, grader consistency, and retrieval payload/output hashes. They retain
all assigned denominators, missing attempts, failed/empty retrieval,
noncompliance, rejected actions, regressions versus baseline, measured cost,
tokens, and separate generation/retrieval latency. Incomplete solve fractions
are explicitly lower bounds. Relevant-evidence and correct-application rates
remain null until a separately reviewed evidence-evaluation workflow exists.

Complete reports average repetitions within each task, use a paired
task-cluster bootstrap and sign-flip test, and apply Holm correction to the
six overall pairwise tests within each policy. Track outcomes and cross-policy
comparisons remain descriptive. Frozen protocols predeclare a 10-percentage-point
practical-effect threshold; it is a proposed decision criterion, not an observed
improvement. Even complete imported runs remain unreviewed and cannot support a
superiority claim through this CLI alone.

Independent review of labels, version-specific sources, model-client provenance,
evidence applicability, and grading adequacy is still required. Non-executable
design answers are not scored in v1; adding them requires a separately locked
rubric, two blinded reviewers, and disagreement resolution.

### M4 evidence-backed local coverage

The three empty searches in the original M2 bundle were local coverage gaps:
`graceful shutdown` in `container`, `transaction` in `java-spring`, and `proxy`
in `nodejs-express`. One official-source-backed row was appended to each
affected CSV. No search engine, synonym, routing, or output-default change was
needed; explicit scopes still do not fall back to other domains.

The new guidance covers Kubernetes termination budgets and endpoint draining,
Spring transaction proxy boundaries and checked-exception rollback, and Express
proxy trust topology and forwarded-header handling. Source checks used live
official documentation on 2026-10-11, not an independent review or a certification
for every framework version. Check deployment/version applicability before use.

Reproduce the scoped, transport, and ranking checks, then generate a new bundle:

```bash
python -m pytest tests/test_m4_retrieval.py tests/test_golden_queries.py \
  tests/test_compact.py tests/test_m2_evaluation.py tests/test_mcp_server.py \
  tests/test_search.py
python scripts/evaluate_m2.py bundle --output /absolute/path/to/new-post-m4-bundle
```

The unchanged 20-query suite went from three empty cases to zero, with the other
17 ordered result-citation lists preserved and all compact responses within
6000 characters. The new tests include author-written paraphrases and
unexpanded queries; they are regressions, **not held-out relevance evidence**.
More content necessarily makes the three formerly empty responses larger;
this is a coverage fix, not a size optimization.

Keep original M2/M3/pilot artifacts and hashes unchanged. A new corpus requires
a fresh M3 snapshot before a future comparison, not revised historical hashes.
No paid model execution or end-to-end coding benefit is established by M4's
local checks. Independent review and informative model comparisons remain
pending.

### Live M3 exploratory collector

[run_m3_live.py](scripts/run_m3_live.py) is a separate, opt-in paid collector.
The offline CLI above remains offline. The first live protocol uses **24 tasks
x four arms x one repetition = 96 attempts**, required retrieval, and a
submission-only workflow: the model receives the public problem and starter,
retrieves, then submits the entire corrected file. There is no shell, test
feedback, hidden-test access, or selective regeneration. Grading reuses the
isolated M3 Docker grader.

Prepare a **new** snapshot without making provider calls:

```bash
python scripts/run_m3_live.py prepare --root /absolute/path/to/new-live-study
```

Preparation freezes the current post-M4 corpus and collector, canonical search
schemas, system prompt, single-repetition assignments, pinned grading image,
model/settings/prices, and the required protocol. It validates all references
and starters and performs a local MCP known-answer check. The original M2/M3
snapshots are not changed. The reusable Python freeze API now accepts
`repetitions=1`; its default and the offline CLI remain three repetitions.

The fixed model is `claude-opus-5-5`, adaptive thinking/low effort, standard tier,
2048 output tokens per turn, at most 16 turns/600 seconds. BackendPro uses its
actual local MCP search tools. Context7 uses Search API v3 with automatic
library selection and a Python language preference; the model can include
library/version names in its query. Raw Context7 responses are retained, and
documented snippets are mapped losslessly with source URLs for shared evidence
accounting. Unknown response formats stop execution for inspection.

Both providers share three retrieval calls and a 6000-character delivery limit.
Required source responses must reach a subsequent successful model request
before submission. Errors/empty results count as attempts, not useful evidence.
The negative-control track therefore measures imposed retrieval overhead, not
natural activation. This small public mutation suite may saturate at ceiling;
it does not directly evaluate M4's three new rows.

After explicit user approval, supply the exact hash from the preparation result:

```bash
python scripts/run_m3_live.py run --root /absolute/path/to/new-live-study \
  --approve-protocol EXACT_FROZEN_PROTOCOL_SHA256 --approve-budget-usd 35 \
  --accept-unreviewed-exploratory
```

The fresh **$35 incremental API ceiling**, including probes, and **$0.34
per-attempt ceiling** are enforced by the shared durable reservation ledger.
Rates checked on 2026-10-11: Opus 5.5 $4/$20 per million input/output tokens;
Context7 requests conservatively charged at the Pro overage rate of $0.005,
even if covered by the account's free quota. Subscription seats and local
compute are excluded. This does not authorize spending without user approval.
Credentials are read from the existing owner-only external credential file;
they are never passed to the model, MCP child, or grading container.

Model and Context7 capability probes must pass before any assigned task runs.
Provider failures/unsettled reservations stop the run without retries. Partial
observations and all 96 assigned denominators remain recorded. A started run
directory cannot be reused; do not erase it or rerun failures as best-of-N.
If execution stops, diagnose/reconcile before requesting any amended run.

Complete runs write `run/comparison.json` and `run/comparison.md`, plus raw
requests/responses, retrieval traces, submitted candidates, grading records and
spending. To report a stopped run without further provider calls:

```bash
python scripts/run_m3_live.py report --root /absolute/path/to/stopped-study
```

Reports preserve missing/noncompliant attempts and separate invocation,
response delivery, errors, empty results, cost, and generation/retrieval latency.
Source relevance and correct application remain unreviewed. User approval to
run exploratory tasks is not independent task/source review. No superiority,
standard-benchmark certification, or general coding benefit is implied.

## Synonyms

If a class of queries consistently misses the right row (e.g.,
"partial failure" not finding "Saga"), add a synonym in `_SYNONYMS` in
`core.py`. Keep it conservative — over-expansion hurts precision.

## Releasing

This repo uses GitHub Actions CI. A PR is mergeable when:

- All tests pass on Python 3.9, 3.11, and 3.12.
- `ruff check src tests` passes.
- `python -m backendpro.scripts.validate` returns 0.
- The CLI smoke tests in `ci.yml` succeed.

### Preparing the Python/CLI release

Check both [PyPI](https://pypi.org/project/backendpro/) and
[GitHub releases](https://github.com/shashankswe2020-ux/backend-pro-max-skill/releases):
their latest versions may differ. A version bump or merged PR does not publish
a package.

For the pending **0.9.0** release:

1. Keep `pyproject.toml` and `src/backend-pro-max/__init__.py` at the same version.
   Skill-marketplace and editor-extension manifests are outside this Python
   release; do not bump them without validating those distribution channels.
2. Update the 0.9.0 changelog section. Leave it marked **Unreleased** until
   publication is approved, then set the actual release date.
3. Run the CI checks above and the landing build tests. Regenerate the two
   website pages if their template changes.
4. Build into a version-specific directory, so old artifacts cannot be uploaded
   accidentally:

   ```bash
   python -m pip install build twine
   python -m build --outdir dist/0.9.0
   python -m twine check --strict dist/0.9.0/backendpro-0.9.0.tar.gz dist/0.9.0/backendpro-0.9.0-py3-none-any.whl
   python scripts/smoke_wheel.py dist/0.9.0/backendpro-0.9.0-py3-none-any.whl
   python -m pip hash dist/0.9.0/backendpro-0.9.0.tar.gz dist/0.9.0/backendpro-0.9.0-py3-none-any.whl
   ```

   The default `build` command builds the wheel from a fresh source distribution.
   The smoke check installs that wheel in a temporary environment, outside this
   checkout, and checks runtime version parity, search, CSV schemas, and bundled
   coverage targets.
5. Open a release-preparation PR and wait for the Python matrix, MCP, retrieval,
   and wheel checks. Preserve the verified artifacts and their hashes.

### Publishing after approval

Do not publish, tag, or create a public release as part of preparation alone.
When publication is approved, finalize the release date through a PR. After
merging, build and validate artifacts from that exact approved commit, and upload
**only** those two files:

```bash
python -m twine upload dist/0.9.0/backendpro-0.9.0.tar.gz dist/0.9.0/backendpro-0.9.0-py3-none-any.whl
```

Use local credential storage or a trusted publisher; never put tokens in source,
release notes, or command arguments. Tag that same approved commit as `v0.9.0`,
create the GitHub release using the 0.9.0 changelog section, and attach the verified
packages. Check the published PyPI version and file hashes before announcing it.
If any packaged file changes after verification, rebuild and rerun the checks.

The website is deployed separately to Netlify. Publish the complete `sites/`
directory using the [site deployment guide](designs/README.md#5-shipping-it);
a PyPI upload or GitHub release does not deploy it.

## Code style

- Pure standard library only for runtime code (no new deps).
- Python 3.8+ compatible (no walrus-only syntax in core, etc.).
- Public functions in `core.py` must keep their existing signatures
  backwards-compatible — add new behavior behind keyword-only args.
