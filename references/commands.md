# Command Reference

Use this file for command parsing, stage ordering, user-facing behavior, and legacy compatibility. Normalize Unicode dash variants to `--` before parsing. Accept command words before or after the ticket key when unambiguous.

## Primary Commands

| Command | Stages | Mutation boundary |
|---|---|---|
| `help` | `help` | No filesystem or network side effects except reading skill/config files. |
| `doctor` | `doctor` | Read-only checks; do not fetch Jira issues or run workflow commands. |
| `inspect <ticket>` | `context`, `classification`, `reproductionHypothesis`, `optimizationHypothesis`, `readinessCheck`, `plan` | Read-only; may fetch Jira and inspect refs if configured. |
| `start <ticket>` | `inspect`, `prepareWorkspace`, optional `reproductionEvidence`, optional `performanceBaseline` | May create/reuse configured ticket workspaces/branches and capture before evidence/baseline. No application edits. |
| `implement <ticket>` | `implementation` | Edits code only after current plan and readiness allow it. |
| `verify <ticket>` | `validation`, `manualValidation`, optional `verificationEvidence`, optional `performanceComparison` | Runs configured local checks and writes validation, after-evidence, and performance-comparison artifacts. |
| `ready <ticket> <environment>` | `environmentReadiness`, optional `qaGuide` | Read-only in all environments. |
| `accept <ticket> <environment>` | `environmentAcceptance`, optional verification evidence registration | Mutating checkpoints require `--allow-mutations`. |
| `publish <ticket>` | `commit` when explicit, `prePublishValidation`, optional `publishDraft` when explicit | Never deploys or transitions Jira; missing evidence warns by default. |
| `report <ticket>` | `finalReport` | Renders from `run.json`, including evidence status when present. |
| `status <ticket>` | `status` | Reads `run.json`, evidence state, and artifacts only. |
| `cleanup <ticket>` | `cleanup` | Dry-run by default; destructive local cleanup requires explicit cleanup flag. |

## Command Details

### `help`

Return concise usage with primary commands first and legacy aliases second. Do not dump full config. Include the selected profile only when it can be resolved without printing private values.

### `doctor`

Validate:

- config files parse and merge in the documented order
- required keys exist for the selected profile
- credentials are present by variable name, keychain label, or storage handle only
- repository paths exist when configured
- local overlays and run artifacts are ignored by `.gitignore`
- artifact registry marks private/generated files as non-committable
- configured command names include runner, workdir, mutability, and required-for-publish metadata
- relationship config is structurally valid when enabled, including parent discovery fields, branch/workspace owner policy, base refresh policy, and parent-branch override flags
- evidence config is structurally valid when enabled, including storage policy, central evidence root handle, media extensions, and E2E command placeholders
- legacy archive roots are structurally safe when configured, and migration manifests are parseable without printing private file contents
- target-specific Git/provider guards are present for skill-repo publishing and ticket-repo publishing

Do not fetch Jira issues, run tests, prepare branches, push, publish, or mutate data.

### `inspect <ticket>`

Run read-only ticket analysis:

1. Resolve profile.
2. Validate credential availability without printing values.
3. Fetch Jira context using configured fields.
4. Classify ticket type.
5. Resolve repository, workspace intent, and optional parent/child relationship context. See `references/relationships.md`.
6. Inspect latest base refs when configured without switching canonical worktrees.
7. For bug-like tickets, write a potential root cause hypothesis and reproduction plan. Do not record video during `inspect`; local reproduction commands may run only when configured or explicitly requested.
7b. For performance-like tickets (per `ticketTypes.performanceLikeTypes`), write `optimization-plan.md` instead of/alongside the bug RCA: hypothesis, candidate change, correctness risk, measurement plan, and regression guard. Do not run benchmark commands during `inspect`. See `references/performance.md`.
8. Write readiness, risk, relationship map, implementation plan, and `nextAction`.

Stop before implementation if readiness is blocked.

### `start <ticket>`

Run `inspect` if required artifacts are missing or stale, then prepare workspaces. In `git-worktree` mode, repository `path` values are canonical source repos; active work happens in selected ticket worktrees. Do not switch, reset, stash, pull, merge, or edit canonical source worktrees.

If relationship policy identifies the ticket as a defect child that may reuse a parent branch/workspace, resolve `{branchTicketKey}` and the workspace owner from `run.json.relationships` before creating or reusing worktrees. When configured, merge the latest configured base ref into the parent-owned branch after the worktree is selected and before reproduction evidence or implementation. This merge is allowed only in the selected ticket worktree, must preserve untracked work, and must stop on conflicts. Record the result in `run.json.relationships.branch.baseRefresh`, `base-refresh.md`, `workspace-map.md`, and `worktree-safety.md`. See `references/relationships.md`.

If multiple ticket workspaces exist and config cannot disambiguate, stop and ask. If the selected ticket worktree is dirty, apply the configured dirty strategy.

After workspaces are ready and before any code edits, capture reproduction evidence when evidence is enabled and the classified ticket type is bug-like according to `ticketTypes.bugLikeTypes` or `evidence.requireReproductionForTicketTypes`. Use only configured E2E/evidence commands. Register videos, traces, screenshots, and written notes in `run.json.evidence.reproduction`, `run.json.artifacts`, `reproduction-evidence.md`, and `evidence-manifest.json`. If capture is unavailable or no video is found, record a warning and continue unless the profile sets a blocking evidence policy.

Also after workspaces are ready and before any code edits, capture a performance baseline when the classified ticket type is performance-like according to `ticketTypes.performanceLikeTypes`. Use only `commands[]` entries tagged `"stage": "performanceBaseline"` for the active repo. Register measurements and notes in `run.json.performance.baseline` and `performance-baseline.md`. If no such command is configured, record `not_configured` with a warning and continue. See `references/performance.md`.

### `implement <ticket>`

Read the current plan, readiness, blockers, and workspace map. Implement only when:

- readiness is ready or acceptable by policy
- no open blocker affects implementation
- selected workspaces are resolved
- the user explicitly requested implementation

Use `--force-implement` only to override readiness. It never overrides publish, deployment, mutation, or credential boundaries.

When implementation completes, update `run.json.stages.implementation.filesChanged` with one record per changed source file: `repo`, workspace-relative `path`, and a short `change` note. Also write `implementation-summary.md` from that structured state so audit tools can show file details without re-reading Git history.

For child defects on a shared parent branch/workspace, keep implementation attribution on the current defect ticket. Record the shared branch/workspace metadata, but do not merge parent artifacts into the child run.

### `verify <ticket>`

Run configured validation commands and generate concrete local manual validation steps. Use active ticket workspaces, not canonical repos. Validation command failures must be classified as:

- `ticket-related`
- `pre-existing`
- `unrelated`
- `flaky`
- `blocked`
- `skipped`

When E2E is configured, use `manual-validation-steps.md` as the source for ticket-scoped scenarios and map each scenario back to acceptance criteria.

Before assuming a validation command is blocked for lack of a local toolchain, check the active profile for configured runners such as `host`, `shell`, `docker-exec`, or a named helper. Run only configured setup commands for that runner.

After implementation validation, capture verification evidence when evidence and E2E are enabled for the ticket. Generate or reuse the run-local Playwright wrapper config, run the configured ticket-scoped specs, and store output under the configured evidence destination. Verification specs should prefer one narrative browser session that begins at login, uses one Playwright `page` when feasible, navigates through the target workflow, captures one deliberate canonical screenshot at the clearest proof moment, and ends after all acceptance evidence is verified. Avoid extra proof-only pages or popups; for new-tab link requirements, verify `target="_blank"` and `rel` in the DOM and verify destinations by same-page navigation, request checks, or another no-video method when that preserves the requirement. Register exactly one canonical `verificationVideo` and one canonical `verificationScreenshot` as primary proof in `run.json.evidence.verification`, `run.json.artifacts`, `verification-evidence.md`, and `evidence-manifest.json`; mark any extra media as supplemental diagnostics. Missing canonical verification proof warns by default.

When the ticket is a child defect, validation and evidence remain child-scoped even though commands may run from the parent-owned workspace.

Also after implementation validation, capture a performance comparison when the classified ticket type is performance-like according to `ticketTypes.performanceLikeTypes`. Use only `commands[]` entries tagged `"stage": "performanceComparison"` for the active repo, under the same conditions used for the baseline where feasible. Compute the delta against `performance-baseline.md` and any `ticketTypes.performance.regressionThresholds`, and record a verdict of `improved`, `no_regression`, `regressed`, or `inconclusive` in `run.json.performance.comparison` and `performance-comparison.md`. A `regressed` verdict against a configured threshold is a validation failure classified the same way as other failures; without a configured threshold it is a warning, not a hard failure. If no comparison command is configured, record `not_configured` with a warning. See `references/performance.md`.

### `ready <ticket> <environment>`

Read-only readiness for the named environment. Required evidence:

- target health
- code presence
- targeted read-only checks when configured
- acceptance criteria coverage
- blockers and gaps

Generate `environment-readiness-{environment}.md`. Generate a QA guide when `--qa-guide`, `--validation-guide`, or profile policy asks for one. Do not save, update, upload, delete, export by mutation, restart services, deploy, transition Jira, push, publish, commit, run migrations, seed data, or otherwise mutate environment data.

### `accept <ticket> <environment>`

Acceptance validation exercises real workflows. Without `--allow-mutations`, run only preparation: health, code presence, data discovery, and mutation plan. With `--allow-mutations`, run only ticket-scoped checkpoints from `manual-validation-steps.md` or configured acceptance commands. Capture pre-state when possible and record cleanup/restore status.

Before the first mutating checkpoint in a shared environment, confirm the profile allows that environment, the user named that environment, and the checkpoint is ticket-scoped.

When acceptance commands produce Playwright recordings, screenshots, or traces, register them as verification evidence for the named environment. Do not rerun or broaden acceptance capture just to fill evidence gaps unless the user asks and the configured environment policy allows it.

### `publish <ticket>`

Publishing has two gates:

1. Committed-HEAD pre-publish validation.
2. Explicit draft PR/MR publishing.

`publish` may run pre-publish validation, but pushing or PR/MR creation still requires explicit publish intent such as `--publish-draft-mr` or `--create-draft-pr`. If generated E2E specs appear after commit and are intended to be tracked, block publishing until the user commits them and reruns validation.

Include reproduction and verification evidence status in pre-publish validation. Missing evidence is a warning under the default `warn` policy; only block when the selected profile explicitly sets a blocking evidence policy or when a missing generated E2E spec is intended to be tracked and uncommitted.

For child defects on a shared parent branch, validate the committed shared branch HEAD and record the existing parent-branch MR/PR metadata in the child run when it exists. Do not create a duplicate MR/PR for the same shared branch unless the user explicitly requests that exact action and policy allows it.

### `report <ticket>`

Render `final-summary.md`, `definition-of-done.md`, and user-facing summary from `run.json`. Do not trust stale markdown over current run state.

Include evidence policy, capture status, missing evidence warnings, media artifact paths, and freshness in the report when `run.json.evidence` or registered evidence artifacts exist.

Include relationship type, parent ticket, branch owner, workspace owner, base refresh status, child artifact status, and relationship warnings when `run.json.relationships` exists.

If `legacy-artifact-index.md` or migration manifests exist for the ticket, include a short historical note with source slug and archive path. Do not merge legacy stage status into the current report verdict.

### `status <ticket>`

Read `.portable-jira-flow/runs/{ticketKey}/run.json`, artifact metadata, and known generated files. Return:

- current stage status
- blocked or failed gates
- stale or missing artifacts
- reproduction/verification evidence status and warnings when present
- imported legacy archive presence when `legacy-runs/{sourceSlug}/{ticketKey}/` exists
- relationship type, parent/child ticket links, branch owner, workspace owner, branch mismatch, and base refresh status when present
- dirty/post-commit state if known
- publish and mutation status
- `nextAction` with a short reason

Do not run workflow stages unless the user asks.

### `cleanup <ticket>`

Default to dry-run. List artifacts eligible for cleanup based on `artifactRegistry.retention` and privacy level. Only delete local generated artifacts when the user supplies an explicit cleanup flag such as `--apply`, and never delete source files, committed files, local config, secrets, or user-owned untracked work.

Never delete `legacy-runs`, `migration-manifests`, or `legacy-artifact-index.md` during ordinary ticket cleanup. Archive maintenance requires an explicit legacy cleanup request.

## Legacy Compatibility

Support these words as aliases, but prefer primary command names in help and final output:

| Legacy | Primary |
|---|---|
| `analyze`, `a`, `--analyze`, `--context`, `--plan`, `--readiness-check` | `inspect` |
| `repro`, `r`, `--reproduce` | `inspect` with reproduction stage |
| `branch`, `b`, `--branch`, `--prepare-branches` | `start` |
| `code`, `c`, `--code`, `--implement` | `implement` |
| `check`, `--check`, `--validate` | `verify` |
| `manual-validation`, `--manual-validation` | `verify` manual validation |
| `--capture-reproduction-evidence`, `--record-before` | `start` reproduction evidence capture |
| `--capture-verification-evidence`, `--record-after` | `verify` verification evidence capture |
| `--parent`, `--parent-ticket`, `--parent-branch`, `--use-parent-branch`, `--no-parent-branch` | relationship flags; they do not change the primary command |
| `env-ready`, `ready-for-testing`, `--env-ready`, `--ready-for-testing` | `ready` |
| `qa-guide`, `validation-guide`, `--qa-guide`, `--validation-guide` | `ready` with QA guide |
| `acceptance-validation`, `--acceptance-validation` | `accept` |
| `pre-publish-validation`, `publish-check`, `--pre-publish-validation`, `--publish-check` | `publish` pre-publish gate |
| `complete`, `--complete`, `--final-report` | `report` |
| `abc`, `--abc` | `start`; implement only when explicitly configured or requested |

No alias implies commit, push, PR/MR creation, deployment, Jira transition, or environment mutation unless the alias explicitly requests that exact action and policy allows it.
