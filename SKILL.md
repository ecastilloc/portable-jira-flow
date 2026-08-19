---
name: portable-jira-flow
description: Portable, policy-aware Jira ticket workflow for Codex, Claude, Cursor, and other skill-capable AI coding assistants. Use when the user invokes portable-jira-flow or asks for Jira ticket inspection, workspace start, implementation, verification, environment readiness, acceptance validation, committed-HEAD publish checks, status, doctor, cleanup, or final reporting with safe legacy command compatibility.
---

# Portable Jira Flow

Use this skill to work from Jira tickets through a stable, assistant-neutral command model. Keep this public core generic; machine-specific paths, credentials, internal URLs, company commands, and environment playbooks belong in ignored local config or profile packs.

## Core Contract

- Never print secrets, credential values, passwords, cookies, bearer values, auth URLs with credentials, private payloads, private env files, or private local config values.
- Never push, publish, create a PR/MR, transition Jira, deploy, restart services, run migrations, seed data, or mutate shared environments unless the selected command, config, and explicit user request allow the exact operation.
- Treat working-tree changes as user-owned. Preserve untracked files.
- Run only configured commands or commands explicitly requested by the user.
- Use `run.json` as the source of truth for stage state, artifacts, policy gates, and `nextAction`.
- Keep generated run artifacts local and non-committable unless the user explicitly requests otherwise and policy allows it.

## Command Model

Use these primary commands:

| Command | Purpose |
|---|---|
| `help` | Show concise command help. |
| `doctor` | Validate config shape, credential handles, repo paths, ignored files, artifact safety, and command availability. |
| `inspect <ticket>` | Read-only Jira context, classification, readiness, plan, risk, and bug/RCA hypothesis. |
| `start <ticket>` | `inspect` plus prepare or reuse ticket workspaces/branches. No code changes. |
| `implement <ticket>` | Implement from the current plan only when readiness and policy allow it. |
| `verify <ticket>` | Run configured validation and generate manual validation steps. |
| `ready <ticket> <environment>` | Read-only environment readiness plus optional QA guide. |
| `accept <ticket> <environment>` | Acceptance validation; mutating checkpoints require `--allow-mutations`. |
| `publish <ticket>` | Committed-HEAD pre-publish validation and explicit draft PR/MR only when configured and requested. |
| `report <ticket>` | Final summary rendered from `run.json`. |
| `status <ticket>` | Summarize run state, stale artifacts, blockers, and next safest action. |
| `cleanup <ticket>` | Propose or perform safe local artifact cleanup according to explicit flags and retention config. |

Legacy command words are compatibility aliases only. Prefer primary command names in new output. See `references/commands.md`.

## Reference Routing

Read only the reference files needed for the requested command:

- `references/commands.md`: command semantics, aliases, ordering, `status`, `doctor`, and `cleanup`.
- `references/safety.md`: safety rules, worktree handling, SSO refresh, mutation boundaries, and privacy.
- `references/configuration.md`: config loading, profile selection, schema, policy gates, commands, environments, local profile packs, and overlays.
- `references/artifacts.md`: `run.json`, artifact registry, artifact index, freshness, retention, and `nextAction`.
- `references/templates.md`: artifact templates and output contracts.
- `references/publishing.md`: pre-publish validation, explicit draft PR/MR creation, provider rules, and identity guards.

For most ticket work, read `commands.md`, `safety.md`, `configuration.md`, and `artifacts.md` first. Read `templates.md` when writing user-facing artifacts. Read `publishing.md` only for `publish`, commit, push, or PR/MR work. Read additional profile-pack references only when the selected local profile explicitly routes to them.

## Workflow Invariants

- `inspect` is read-only and never creates branches, commits, PRs/MRs, deployments, or environment mutations.
- `start` may prepare or reuse configured workspaces/branches but never edits application code.
- `implement` stops when readiness is blocked unless `--force-implement` is explicitly present.
- `verify` runs configured local checks only and classifies failures as ticket-related, pre-existing, unrelated, flaky, blocked, or skipped.
- `ready` is read-only for every environment.
- `accept` may mutate only ticket-scoped checkpoints with `--allow-mutations`; never mutate production unless the profile explicitly supports that environment and the user names it.
- `publish` never implies deployment or Jira transition. It only pushes or creates a draft PR/MR when the user explicitly requests that and policy gates pass.
- Generated E2E specs created after commit block publishing until committed, or until recorded as disposable according to config.
- `report`, `definition-of-done.md`, and derived summaries must be refreshed from current `run.json`, not stale narrative text.

## Invocation Examples

Use the assistant-specific adapter trigger when available:

```text
$portable-jira-flow help
$portable-jira-flow inspect ABC-123
/portable-jira-flow start ABC-123
portable-jira-flow verify ABC-123
```

## Final Output

Keep user-facing summaries concise. Include ticket, profile, command, verdict, blockers, next action, files changed, validation or readiness status, and artifact paths when useful. Do not paste long generated guides unless the user explicitly asks for copy-paste output.
