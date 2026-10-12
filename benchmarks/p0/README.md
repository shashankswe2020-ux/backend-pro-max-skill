# P0: evaluation readiness, not a competitive result

This offline extension of [M3](../m3/results/2026-10-11/README.md) implements
development-cohort preparation, multi-file grading, baseline-calibration
ingestion, independent-review/held-out intake gates, and retrieval diagnosis.
It makes no paid requests and does not change the original 24-task smoke suite
or historical results.

**Status:** 40 public development tasks, not independently reviewed and not
calibrated on a coding model. The tasks cover eight related repository/family
fixtures, five fault combinations per family. They are **not 40 independent
repositories**. Increased task complexity is a hypothesis until calibration
measures baseline headroom.

| Track | Families | Cases |
|---|---|---:|
| Backend | SQLite ledger atomicity/idempotency; leased queue fencing | 10 |
| Framework | Pydantic v2 validation/serialization; HTTPX pagination | 10 |
| Mixed | Starlette conditional writes; asyncio single-flight cache | 10 |
| No-retrieval controls | Locally specified CSV reporting; catalog selection/rendering | 10 |

Each task changes at least two files, preserves public entry points, and has
executable acceptance checks. The controls deliberately require no external
documentation. Concurrency cases use barriers/events and injected logical
time, not timing-dependent sleeps. `asyncio.sleep(0)` yields to schedule a
waiter; it is not used to assume a wall-clock race.

## Prepare and validate

Use the repository's existing environment or install the declared dev extra.
The grading environment is the existing M3 image: Python 3.12.13, Pydantic
2.14.0, Starlette 1.7.0, HTTPX 0.28.1.

```bash
python scripts/run_p0.py freeze \
  --image backendpro-m3:offline-v1 --output /absolute/run/p0-development
python scripts/run_p0.py self-test \
  --frozen /absolute/run/p0-development --output /absolute/run/self-test
python scripts/run_p0.py readiness \
  --frozen /absolute/run/p0-development \
  --validation /absolute/run/self-test/summary.json \
  --output /absolute/run/readiness.json
```

`freeze` pins image/environment, product sources/corpus, task artifacts,
schemas, schedules and separate optional/required protocols. It refuses an
existing destination. `self-test` runs all references and all starters through
the existing M3 Docker grader and retains 80 per-case artifacts. Containers
are non-root, network-disabled, resource-limited, read-only-root, with no
host mounts or credentials. The temporary bundle adapter expands submitted
Python files only inside the container.

The readiness command writes an explicit blocked report and exits 1 until
all prerequisites are supplied. In particular, passing reference/starter
tests does not prove model headroom or independent review. Even a fully ready
report says `paid_generation_authorized: false`.

For a model calibration snapshot, pass `--settings /absolute/settings.json`
at freeze time:

```json
{
  "model": "exact-provider-model-id",
  "harness": "collector-name",
  "harness_revision": "immutable-reviewed-revision",
  "parameters": {
    "reasoning_effort": "explicit-provider-setting",
    "temperature": 0
  }
}
```

These values are user-supplied records, not provider availability checks.
Use settings appropriate to the selected provider; do not copy the example
parameters blindly. A snapshot with missing settings cannot establish headroom.
The inherited counterbalanced schedule uses the separately recorded M3
`schedule_seed`; the P0 seed identifies this protocol and calibration bootstrap.

### Agent/grader boundary

Copy **only** `agent/<task-id>/` into an isolated agent workspace. Do not give
the agent the checkout, sibling `grading/` directory, manifest, task generator,
reference JSON, test code, or review artifacts. Public development tasks cannot
be called contamination-free even when their grading files are hidden at runtime.

Submit the complete mapping of declared editable filenames to source strings:

```json
{
  "app.py": "from store import Store\n...",
  "store.py": "..."
}
```

```bash
python scripts/run_p0.py grade --frozen /absolute/run/p0-development \
  --task ledger-01 --input /absolute/run/submission.json \
  --output /absolute/run/submission.grade.json
```

Paths must be normalized relative Python filenames. Extra/missing files,
traversal paths and oversized bundles fail before container execution.
Grade hashes bind both the multi-file submission and the M3 wrapper. This
retains the existing grader trust model; it is not an adversarial test-forging
defense or a production sandbox certification.

The old paid `run_m3_live.py` collector is intentionally **not** repurposed:
it is frozen to 24 submission-only tasks. P0 provides preparation, grading and
observation ingestion, not a newly authorized paid generation client. A future
collector must honor the frozen multi-file protocol, isolation boundary and
budget authorization.

## Difficulty calibration

Collect the baseline assignments from the frozen schedule, three repetitions
per task. Keep all 120 assigned attempts, including time limits, provider errors
and not-started attempts. No best-of-N, substitutions, or selective reruns.
Use only the development cohort; evaluation-cohort calibration is rejected.

An observations object contains:

```json
{
  "protocol_sha256": "sha256-of-optional.protocol.json",
  "collection_kind": "model",
  "model_settings": {"model": "...", "harness": "...", "harness_revision": "...", "parameters": {}},
  "attempts": [
    {
      "id": "ledger-01.baseline.r1",
      "status": "completed",
      "knowledge_calls": 0,
      "candidate_file": "ledger-01.baseline.r1.candidate.json",
      "candidate_sha256": "sha256-of-candidate-file",
      "grade_file": "ledger-01.baseline.r1.grade.json",
      "grade_sha256": "sha256-of-grade-file",
      "cost_micro_usd": 0,
      "input_tokens": 100,
      "output_tokens": 100,
      "seconds": 1.0
    }
  ]
}
```

The example is abbreviated, not valid complete model evidence. Artifact paths
are relative to the observations directory. Outcomes are `completed`,
`time_limit`, `provider_error`, or `not_started`. Completed attempts require
bound candidate/grade artifacts; all attempts require nonnegative accounting.

```bash
python scripts/run_p0.py calibrate --frozen /absolute/run/p0-development \
  --input /absolute/run/observations.json --output /absolute/run/calibration.json
```

The headroom diagnostic is **30-80% resolution on non-control development
tasks**. All four tracks, all attempts, and costs remain reported. A model
time limit is a retained failure; provider/missing/invalid-grading outcomes
block readiness rather than manufacturing headroom. Related cases are
clustered by repository/family for descriptive bootstrap intervals.

Readiness replays calibration from hash-bound observations and candidate/grade
artifacts, not just a supplied `"headroom_observed"` flag. Submitted records
still do not prove the collector's identity; independent run review is needed.
Save the calibration report beside its observations.

## Independent review and held-out intake

Do not label self-authored development cases as independently reviewed.
A reviewer must verify discoverability, source applicability at the pinned
versions, runnable tests, and authorized usage. Linked documentation is an
authoring reference, not a claim that independent version review occurred.

Review format:

```json
{
  "cohort_sha256": "cohort-hash",
  "reviewer": "independent-reviewer",
  "reviewed_at": "ISO-date",
  "rubric": "locked-review-rubric-reference",
  "independence_attested": true,
  "tasks": {
    "task-id": {
      "requirements_discoverable": true,
      "sources_verified": true,
      "tests_verified": true,
      "usage_authorized": true,
      "rationale": "Sources, version constraints, invariants and test observations."
    }
  }
}
```

Every task must be reviewed. For development, bind `cohort_sha256` from its
manifest. For evaluation intake, bind the SHA-256 of the exact external JSON
cohort file. Reviewer identity must differ from all task authors; this is
structural validation of an attestation, not identity verification.

The evaluation JSON is a list with the same task fields as the public
[development generator](tasks.py), but `split: "evaluation"`. It must have
independent authors, disjoint task IDs, repositories and families, all four
tracks, sources/usage metadata, and no identical renamed development reference.
Reviewers must also check semantic near-duplicates, which hashes cannot detect.

```bash
python scripts/run_p0.py freeze --image backendpro-m3:offline-v1 \
  --cohort /private/evaluation.json --review /private/evaluation-review.json \
  --development /absolute/run/p0-development --settings /absolute/settings.json \
  --output /private/p0-evaluation
```

Evaluation output inside the checkout is refused. Keep raw intake and exports
outside the checkout and inaccessible to generation. Freeze before model
outputs; do not remove held-out tasks because the baseline passes them.

Run self-test on the evaluation snapshot too. For evaluation readiness, provide
its validation summary, the development calibration report and `--development`.
The calibrated settings must exactly match evaluation settings. Development
readiness always names the missing separate evaluation cohort; it cannot
certify itself as held out.

## Retrieval failure diagnosis

Preserve original M3 observations. Generate a new sidecar report:

```bash
python scripts/run_p0.py diagnose --input /retained/run/observations.json \
  --output /absolute/run/diagnosis.json
```

Each call starts `unknown`. Available labels:

| Label | Required reviewer evidence |
|---|---|
| `scope_error` | Intended task scope versus actual query scope |
| `corpus_gap` | Source-checked missing coverage, not merely an empty reply |
| `lexical_miss` | Relevant corpus row plus lexical-candidate absence |
| `rank_miss` | Relevant candidate retrieved but below delivery cutoff |
| `packing_loss` | Relevant retrieved evidence omitted from model-visible output |
| `version_mismatch` | Pinned task version versus source applicability |
| `evidence_misapplication` | Delivered applicable evidence versus submitted patch/test behavior |
| `appropriate_abstention` | Unanswerable/out-of-scope request, including legitimate controls |
| `no_failure` | Reviewed relevant and correctly applied evidence |
| `unknown` | Insufficient evidence; do not infer a cause |

Use `--review review.json` for a sidecar containing `observations_sha256`,
`reviewer`, `rubric`, and an `events` object. Keys are
`<attempt-id>:<zero-based-index-in-entire-trace>`. Each item has `cause`,
`output_sha256`, `rationale`, and `evidence: [{"path": "...json", "sha256": "..."}]`.
Supporting JSON artifacts are relative to the review directory. Preserve stage
observations, relevant source/row IDs, candidate rankings, source applicability,
and patch/grade bindings there as required by the rubric. Unknowns may remain
unreviewed. Payload/output tampering and unsupported labels are rejected.

Historical aggregates do not identify individual causes:

```bash
python scripts/run_p0.py historical-audit \
  --input benchmarks/m3/results/2026-10-11/retrieval-summary.json \
  --output /absolute/run/historical-audit.json
```

Without retained raw traces this reports **21 unknown causes**, not 21 corpus
gaps. The published aggregate is preserved byte-for-byte.

## External benchmark access

[benchmark-access.json](benchmark-access.json) records external candidates with
pending availability, license, revision, and usage authorization. Nothing is
downloaded or scheduled by this implementation. Validate a reviewed copy before
any external scheduling:

```bash
python scripts/run_p0.py check-access --input /absolute/reviewed-access.json \
  --benchmark contextbench --output /absolute/access-gate.json
```

Each selected record needs verified availability, authorized usage, license and
license URL, immutable revision, reviewer/date, and permitted-use scope. Unknown
or incomplete records fail closed; an access pass is not a spending approval.

## Tests

```bash
python -m pytest tests/test_p0.py tests/test_m3.py tests/test_m3_live.py
python -m ruff check scripts/run_p0.py scripts/run_m3.py benchmarks/p0/tasks.py tests/test_p0.py
```

Unit tests mock Docker and model observations; do not publish them as measured
headroom. Use the real isolated `self-test` for reference/starter validation.
Original M3 fixtures continue to verify legacy behavior and historical reports.
