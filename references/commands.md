# Command Reference

Use this file for command parsing, stage ordering, user-facing behavior, and legacy compatibility. Normalize Unicode dash variants to `--` before parsing. Accept command words before or after the ticket key when unambiguous.

## Primary Commands

| Command | Stages | Mutation boundary |
|---|---|---|
| `help` | `help` | No filesystem or network side effects except reading skill/config files. |
| `doctor` | `doctor` | Read-only checks; do not fetch Jira issues or run workflow commands. |
| `inspect <ticket>` | `context`, `classification`, `reproductionHypothesis`, `readinessCheck`, `plan` | Read-only; may fetch Jira and inspect refs if configured. |
| `start <ticket>` | `inspect`, `prepareWorkspace` | May create/reuse configured ticket workspaces/branches. No application edits. |
| `implement <ticket>` | `implementation` | Edits code only after current plan and readiness allow it. |
| `verify <ticket>` | `validation`, `manualValidation` | Runs configured local checks and writes validation artifacts. |
| `ready <ticket> <environment>` | `environmentReadiness`, optional `qaGuide` | Read-only in all environments. |
| `accept <ticket> <environment>` | `environmentAcceptance` | Mutating checkpoints require `--allow-mutations`. |
| `publish <ticket>` | `commit` when explicit, `prePublishValidation`, optional `publishDraft` when explicit | Never deploys or transitions Jira. |
| `report <ticket>` | `finalReport` | Renders from `run.json`. |
| `status <ticket>` | `status` | Reads `run.json` and artifacts only. |
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
- target-specific Git/provider guards are present for skill-repo publishing and ticket-repo publishing

Do not fetch Jira issues, run tests, prepare branches, push, publish, or mutate data.

### `inspect <ticket>`

Run read-only ticket analysis:

1. Resolve profile.
2. Validate credential availability without printing values.
3. Fetch Jira context using configured fields.
4. Classify ticket type.
5. Resolve repository and workspace intent.
6. Inspect latest base refs when configured without switching canonical worktrees.
7. For bug-like tickets, write a potential root cause hypothesis and reproduction plan; run reproduction only when reproduction commands are configured or explicitly requested.
8. Write readiness, risk, implementation plan, and `nextAction`.

Stop before implementation if readiness is blocked.

### `start <ticket>`

Run `inspect` if required artifacts are missing or stale, then prepare workspaces. In `git-worktree` mode, repository `path` values are canonical source repos; active work happens in selected ticket worktrees. Do not switch, reset, stash, pull, merge, or edit canonical source worktrees.

If multiple ticket workspaces exist and config cannot disambiguate, stop and ask. If the selected ticket worktree is dirty, apply the configured dirty strategy.

### `implement <ticket>`

Read the current plan, readiness, blockers, and workspace map. Implement only when:

- readiness is ready or acceptable by policy
- no open blocker affects implementation
- selected workspaces are resolved
- the user explicitly requested implementation

Use `--force-implement` only to override readiness. It never overrides publish, deployment, mutation, or credential boundaries.

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

### `publish <ticket>`

Publishing has two gates:

1. Committed-HEAD pre-publish validation.
2. Explicit draft PR/MR publishing.

`publish` may run pre-publish validation, but pushing or PR/MR creation still requires explicit publish intent such as `--publish-draft-mr` or `--create-draft-pr`. If generated E2E specs appear after commit and are intended to be tracked, block publishing until the user commits them and reruns validation.

### `report <ticket>`

Render `final-summary.md`, `definition-of-done.md`, and user-facing summary from `run.json`. Do not trust stale markdown over current run state.

### `status <ticket>`

Read `.portable-jira-flow/runs/{ticketKey}/run.json`, artifact metadata, and known generated files. Return:

- current stage status
- blocked or failed gates
- stale or missing artifacts
- dirty/post-commit state if known
- publish and mutation status
- `nextAction` with a short reason

Do not run workflow stages unless the user asks.

### `cleanup <ticket>`

Default to dry-run. List artifacts eligible for cleanup based on `artifactRegistry.retention` and privacy level. Only delete local generated artifacts when the user supplies an explicit cleanup flag such as `--apply`, and never delete source files, committed files, local config, secrets, or user-owned untracked work.

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
| `env-ready`, `ready-for-testing`, `--env-ready`, `--ready-for-testing` | `ready` |
| `qa-guide`, `validation-guide`, `--qa-guide`, `--validation-guide` | `ready` with QA guide |
| `acceptance-validation`, `--acceptance-validation` | `accept` |
| `pre-publish-validation`, `publish-check`, `--pre-publish-validation`, `--publish-check` | `publish` pre-publish gate |
| `complete`, `--complete`, `--final-report` | `report` |
| `abc`, `--abc` | `start`; implement only when explicitly configured or requested |

No alias implies commit, push, PR/MR creation, deployment, Jira transition, or environment mutation unless the alias explicitly requests that exact action and policy allows it.
