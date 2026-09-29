# Release Domain Review - 2026-09-29

Scope: only `src/backend-pro-max/data/release.csv` and this ledger. Read the
backend-pro-max skill. Reviewed all 15 existing rows and added 3 rows (18 total).
Existing names, order, and all 11 columns are preserved. All 18 rows were checked
against retrieved primary sources and dated `2026-09-29`; this is the review date,
not a claim about a source's publication date. Source Type is `official-docs`.

## Per-Row Ledger

| Exact row name | Action and source-backed correction | Sources | Remaining limitation |
| --- | --- | --- | --- |
| Blue-Green Deployment | Reviewed; removed atomic switching and instant rollback claims; retain old capacity through routing convergence. | [Argo blue-green][bg]; [AWS compatibility][compat] | Service selectors propagate asynchronously; Argo specifically warns of possible ALB downtime. Database compatibility and actual router timing need deployment-specific tests. |
| Canary Deployment | Reviewed; removed fixed initial percentages and automatic safety assumptions; distinguish replica ratios from traffic routing and provision matching capacity. | [Argo canary][canary]; [Google canarying][sre] | Routing weights are not guaranteed user percentages. Low volume, affinity, and shared dependencies can invalidate the intended exposure or observations. |
| Rolling Update | Reviewed; added readiness, surge/unavailable controls, retained revisions, and explicit recovery for stalled rollouts. | [Kubernetes Deployments][deploy]; [AWS compatibility][compat] | ProgressDeadlineExceeded is a status, not automatic rollback. Availability checks do not prove application or data compatibility. |
| Feature Flags | Reviewed; replaced instant disable with SDK propagation/reevaluation conditions; distinguish off variation and fallback; preserve temporary-flag retirement guidance. | [SDK architecture][sdk]; [Offline behavior][offline]; [Flag lifecycle][flags] | Offline/cache behavior varies by SDK and version. A toggle cannot undo writes; old clients and prerequisite flags can prevent safe retirement. |
| Dark Launch | Reviewed; replaced zero impact and exact doubled-load claims with sampled read comparison and explicit timeout/side-effect hazards. | [GitHub Scientist][scientist]; [Google traffic teeing][sre] | Scientist runs candidate and control sequentially and does not protect against timeouts; shadow systems require their own isolation and capacity controls. |
| A/B Testing Release | Reviewed; added guardrails, sample ratio mismatch, multiple exposures, minimum data, and engine-appropriate stopping rules. | [GrowthBook statistics][ab] | Statistical evidence is not an availability guarantee. Sequential testing must be configured; sample sizes and decision thresholds remain experiment-specific. |
| Recreate Deployment | Reviewed; scoped stop-before-start ordering to Deployment upgrades and removed blanket non-production-only advice. | [Kubernetes Recreate][recreate] | Manually deleted Pods may be replaced before termination finishes. Recreate is not singleton fencing; outage tolerance is a workload decision. |
| GitOps | Reviewed; distinguished desired-state revert from data recovery and direct Argo CD rollback; documented opt-in self-heal/pruning. | [OpenGitOps principles][gitops]; [Argo CD auto-sync][sync] | Reconciliation may fail; external state is not restored. ApplicationSet-managed auto-sync changes must be made at the controlling configuration. |
| Progressive Delivery | Reviewed; removed fully automated safety and seconds-to-recovery guarantees; flags are optional and analysis outcomes are explicit. | [Argo analysis][analysis] | Failed analysis can abort, inconclusive results pause, and dry-run metrics do not gate. Controller/router configuration determines actual recovery. |
| Ring-Based Deployment | Reviewed; replaced fixed ring percentages and mandatory automatic-only promotion with representative cohorts, health/usage gates, bake time, and approvals. | [Azure safe deployments][safe] | No universal ring size or bake time. Azure recommends hours/days for representative usage; emergencies need explicit authority and accelerated checks. |
| Immutable Infrastructure | Reviewed; removed always-available artifacts and eliminated-drift guarantees; require retained artifacts, replacement capacity, and drift controls. | [AWS immutable infrastructure][immutable]; [Kubernetes images][images] | IaC alone does not enforce immutability. Stateful dependencies, artifact retention, and provisioning time are outside the pattern's guarantees. |
| Database Migration Safety | Reviewed; expanded sequencing through verified backfill, compatible readers/writers, and deferred contract; identified concurrent-write and rollback-window hazards. | [Prisma expand-contract][db]; [AWS compatibility][compat]; [Azure recovery][safe] | Prisma's retrieved example is PostgreSQL/ORM-version-specific. It does not establish universal online-DDL, locking, transactional, or backfill guarantees. Reconciliation and restore tests remain workload-specific. |
| Rollback Strategy | Reviewed; replaced generic down-script advice with mixed-version upgrade/downgrade testing and compatibility-bounded recovery. | [AWS compatibility][compat]; [Azure recovery][safe]; [Kubernetes rollback][deploy] | After activation, rollback before the prepared-reader version may be unsafe. Kubernetes undo restores only the Pod template, not database state or separately changed resources. |
| Deployment Freeze | Reviewed; made enforcement explicit: a GitLab freeze supplies CI_DEPLOY_FREEZE, which deployment jobs must consume. | [GitLab deploy freeze][freeze]; [Azure emergency protocols][safe] | Other deployment paths may bypass the gate; check time zones and authorize emergency exceptions. A freeze cannot guarantee incident prevention. |
| Release Train | Reviewed; removed low-risk batch and hours-to-rollback claims; tied inclusion to readiness, stabilization, reviewed exceptions, and urgent fixes. | [Kubernetes release cycle][train]; [Google release engineering][release]; [Google feature separation][sre] | Kubernetes is a concrete cadence example, not a universal schedule or SAFe definition. Publication cadence does not require simultaneous feature exposure. |
| Canary Analysis Gates | Added; version-specific concurrent comparison plus absolute SLOs, representative observations, and explicit handling of missing/invalid metrics. | [Argo analysis][analysis]; [Google canarying][sre] | Rejecting missing evidence is this review's recommended policy, not an Argo default. Expressions can accept empty/NaN results; dry-run and premature completion can weaken gates. |
| Graceful Shutdown and Connection Draining | Added; connect readiness, traffic draining, preStop, and termination grace to release availability. | [Kubernetes Pod termination][termination]; [Argo propagation][bg] | preStop uses the same grace budget; force-kill can interrupt work. Router propagation and long-lived connections must be tested under load. |
| Digest-Pinned Artifact Promotion | Added; promote the tested image digest and track compatible configuration and recovery artifacts. | [Kubernetes image identity][images]; [Google packaging/configuration][release] | Digest pinning fixes content identity, not authenticity, retention, external configuration, or state compatibility. Registry access can still fail. |

## Review Boundaries and Validation

- Risk and recovery-time cells now state conditions, not universal ratings or
  measured SLAs. No runtime recovery benchmarks or statistical thresholds were
  invented. Listed tooling was narrowed to the implementations actually reviewed.
- Primary-source mechanisms are distinguished above from conservative operational
  recommendations. Sources are live documentation, not archived snapshots; check
  the deployed product/SDK/database version before applying version-specific details.
- The AWS rollback article redirected to Builder Center; its destination was
  retrieved successfully. The attempted LaunchDarkly `feature-flag-best-practices`
  page returned Page Not Found; the retrieved SDK, offline, and lifecycle docs
  supply the evidence instead. Neither a failed fetch nor a redirect alone was
  counted as review evidence.
- Editor `get_errors` ran immediately after each patch. No terminal commands,
  schema execution, test execution, commits, pushes, or changes to other domains
  were made. The parent owns schema/tests; editor diagnostics do not establish
  CSV schema validity or retrieval quality.

## Source URLs

[bg]: https://argo-rollouts.readthedocs.io/en/stable/features/bluegreen/
[canary]: https://argo-rollouts.readthedocs.io/en/stable/features/canary/
[deploy]: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
[recreate]: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#recreate-deployment
[analysis]: https://argo-rollouts.readthedocs.io/en/stable/features/analysis/
[sdk]: https://launchdarkly.com/docs/sdk/concepts/client-side-server-side
[offline]: https://launchdarkly.com/docs/sdk/features/offline-mode
[flags]: https://launchdarkly.com/docs/home/flags/flag-status
[scientist]: https://github.com/github/scientist
[ab]: https://docs.growthbook.io/statistics/overview
[sync]: https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/
[gitops]: https://opengitops.dev/
[db]: https://www.prisma.io/docs/guides/data-migration
[safe]: https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/safe-deployments
[freeze]: https://docs.gitlab.com/user/project/releases/#prevent-unintentional-releases-by-setting-a-deploy-freeze
[train]: https://kubernetes.io/releases/release/
[immutable]: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_tracking_change_management_immutable_infrastructure.html
[images]: https://kubernetes.io/docs/concepts/containers/images/
[termination]: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination-flow
[release]: https://sre.google/sre-book/release-engineering/
[sre]: https://sre.google/workbook/canarying-releases/
[compat]: https://builder.aws.com/content/3F04j2yRAAMBuPSPs50xwXZqg01/ensuring-rollback-safety-during-deployments