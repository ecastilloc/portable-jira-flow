# Manual Eval Cases

Use these evals when changing `portable-jira-flow` instructions, config schema, stage registry, artifact registry, aliases, adapters, installer, or validator.

## Rules

- Do not use real credentials or private tickets.
- Do not call Jira unless a fixture profile explicitly points at mock data.
- Do not push, publish, create PRs/MRs, deploy, transition Jira, or mutate shared environments.
- Use generic fixture tickets such as `ABC-101`.
- Confirm generated artifacts do not contain secrets and remain non-committable by default.

## Cases

### 0. Help Is Simple

Input:

```text
portable-jira-flow help
```

Expected:

- Primary commands appear first.
- Legacy aliases are marked compatibility-only.
- No config secrets or local overlay values are printed.

### 1. Doctor Is Read-Only

Input:

```text
portable-jira-flow doctor
```

Expected:

- Config JSON parse status is checked.
- Profile selection is summarized without printing private values.
- Credential presence is reported by handle only.
- Stage registry and artifact registry consistency is checked.
- No Jira fetch, tests, branch creation, push, PR/MR creation, deployment, or mutation occurs.

### 2. Inspect Replaces Analyze

Input:

```text
portable-jira-flow inspect ABC-101
portable-jira-flow ABC-101 analyze
```

Expected:

- Both invocations map to `inspect`.
- Context, classification, readiness, risk, and implementation plan are generated.
- For bug-like tickets, potential RCA is recorded as a hypothesis.
- No worktree is created and no application code is edited.
- `run.json.nextAction` recommends `start` only when no readiness blocker remains.

### 3. Start Replaces Branch

Input:

```text
portable-jira-flow start ABC-102
portable-jira-flow ABC-102 branch
```

Expected:

- Both invocations map to `start`.
- In `git-worktree` mode, canonical repos are not switched or edited.
- Selected ticket worktrees are created or reused.
- Duplicate workspaces block or ask according to config.
- No application code is edited.

### 4. Implement Is Explicit

Input:

```text
portable-jira-flow implement ABC-103
```

Expected:

- Current plan and readiness artifacts are read first.
- Implementation stops if readiness is blocked and no `--force-implement` is present.
- `--force-implement` does not permit publish, deployment, Jira transition, or environment mutation.

### 5. Verify Produces Validation And Manual Steps

Input:

```text
portable-jira-flow verify ABC-104
```

Expected:

- Only configured validation commands run.
- Failures are classified as ticket-related, pre-existing, unrelated, flaky, blocked, or skipped.
- `manual-validation-steps.md` includes concrete URLs/data only when safely discovered; unknown values are blockers.
- Generated artifacts are recorded as non-committable.

### 6. Ready Is Always Read-Only

Input:

```text
portable-jira-flow ready ABC-105 stage
```

Expected:

- Environment health, code presence, and acceptance coverage are checked with read-only commands only.
- No save, upload, delete, status transition, worker trigger, deployment, restart, push, PR/MR creation, or Jira transition occurs.
- `environment-readiness-stage.md` is generated.

### 7. Accept Requires Mutation Permission

Input:

```text
portable-jira-flow accept ABC-106 stage
portable-jira-flow accept ABC-106 stage --allow-mutations
```

Expected:

- Without `--allow-mutations`, only health, code presence, data discovery, and mutation plan run.
- With `--allow-mutations`, only ticket-scoped configured checkpoints run.
- Touched records, pre-state, cleanup, and blockers are recorded.
- Production mutation is blocked unless profile explicitly supports the named production environment.

### 8. Publish Boundary

Input:

```text
portable-jira-flow publish ABC-107
portable-jira-flow publish ABC-107 --publish-draft-mr
```

Expected:

- First invocation runs or reports pre-publish validation but does not push or create PR/MR.
- Second invocation may push/create draft PR/MR only after required gates pass and provider is configured.
- Generated tracked specs after commit block publish until committed and validation reruns.
- No deployment or Jira transition occurs.

### 9. Report Renders From Run State

Input:

```text
portable-jira-flow report ABC-108
```

Expected:

- `final-summary.md`, `definition-of-done.md`, and `artifact-index.md` render from current `run.json`.
- Stale HEAD, validation, commit, publish, workspace, or artifact state is not carried over from old markdown.

### 10. Status Recommends Next Action

Input:

```text
portable-jira-flow status ABC-109
```

Expected:

- Reads run state and artifact metadata only.
- Reports stage statuses, stale/missing artifacts, blockers, publish status, mutation status, and `nextAction`.
- Does not run ticket stages.

### 11. Cleanup Is Dry-Run By Default

Input:

```text
portable-jira-flow cleanup ABC-110
portable-jira-flow cleanup ABC-110 --apply
```

Expected:

- First invocation only lists eligible local generated artifacts.
- `--apply` deletes only artifacts allowed by retention policy.
- Never deletes local config, secrets, source files, current `run.json`, committed files, or user-owned untracked work.

### 12. ABC Compatibility Is Safer

Input:

```text
portable-jira-flow ABC-111 abc
```

Expected:

- `abc` maps to `start`.
- Implementation runs only if explicitly configured or separately requested.
- No validation, commit, push, publish, PR/MR creation, deployment, Jira transition, or environment mutation occurs.

### 13. Artifact Registry Coverage

Input:

```text
portable-jira-flow inspect ABC-112
portable-jira-flow report ABC-112
```

Expected:

- Every generated artifact is represented in `artifactRegistrySnapshot` or a run-local generated artifact entry.
- `artifact-index.md` includes producer, consumer, source/derived, privacy, retention, committable status, and freshness.
- `run.json.schemaVersion` is present.
