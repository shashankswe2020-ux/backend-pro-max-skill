# Merged P0-P4 benchmark verification (2026-10-14)

Machine-readable measurements and provenance are in
[`merged-p0-p4-verification-2026-10-14.json`](./merged-p0-p4-verification-2026-10-14.json).
The report was collected after merge commit
`ccdb56e519cb8c3de4ebc8f9a4ffc1a0b915b499`, and compares default retrieval with
pre-upgrade commit `930e99a0ee918801804ece48dcb68cc71b3f6385`.

## Findings

- The same eight-query author-labeled ranking set and identical corpus produced
  Recall@5, MRR and nDCG of `1.00` at both revisions. There is no measured
  retrieval-ranking improvement on this saturated, incomplete set.
- With the same default top-five BM25 call, single-host warm latency medians
  were about `0.103 ms` at baseline and `0.139 ms` after merge. These are
  diagnostic timings without uncertainty estimates; do not interpret them as a
  statistically established regression.
- The merged hybrid and reranking ablations also scored `1.00` for all ranking
  metrics. Their warm p50 latency was materially higher, with no observed
  ranking benefit on these labels.
- In one authored local-Python fixture at 2,500 JSON characters, bounded AST
  context retained all eight labeled relevant lines and all critical lines;
  literal windows retained four of eight relevant lines and zero critical
  lines. At 4,000 and 6,000 characters both retained all labeled critical lines.
  This is a two-case collector diagnostic, not independent code-context
  evaluation.
- Four authored, version-specific Pydantic cases retained all labeled critical
  fields within actual pinned-tokenizer budgets of 1,000, 2,000 and 4,000
  tokens. Label precision was low at the larger budgets; independent
  applicability and coding-outcome gates remain open.
- Merged-main CI's P0 Docker self-test passed all 40 references and rejected
  all 40 faulty starters. It made zero model attempts. Independent task review,
  model calibration and a disjoint evaluation cohort remain pending.
- P4 memory efficacy was not evaluated. No recurring-pattern evidence was
  approved; memory remains disabled absent operator approval.

## Reproduction and boundaries

The JSON records revisions, source/dataset/corpus hashes, tokenizer identity,
budgets, response hashes and the downloaded P0 CI artifact provenance. It also
records the command parameters and measurement limitations. The exact raw
retrieval, token-retention, repository-context and CI artifacts were retained
in the session's benchmark bundle at collection time; the summary does not
bundle large individual P0 grading artifacts.

No paid model calls were made. These diagnostics establish neither improved
coding success nor superiority over other context tools. The next outcome
evaluation requires an authorized frozen protocol, no-context/pre-upgrade/merged
comparison, calibrated model headroom, independent task review and a separate
held-out cohort.
