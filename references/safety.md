# Safety Reference

Read this file before executing any ticket stage beyond `help`.

## Secret Handling

- Never print credential values, passwords, cookies, private browser codes, bearer values, auth URLs with credentials, private payloads, or full env files.
- Store only environment variable names, keychain service names, helper labels, or env-file paths in config.
- Redact Jira payloads before writing artifacts when sensitive fields are present.
- Do not copy private local overlay values into tracked files.

## Side-Effect Boundaries

| Operation | Allowed only when |
|---|---|
| Fetch Jira | Profile config and credentials are available. |
| Fetch git refs | Stage allows read-only base inspection or branch prep. |
| Create/reuse worktree | `start` or later stage requires it and policy allows it. |
| Merge latest base into an active branch | `start` is preparing an allowed child-defect relationship, the profile enables relationship base refresh, the merge runs only in the selected ticket worktree, and the user requested or policy requires that relationship flow. |
| Edit application code | `implement` is explicit and readiness permits it. |
| Run validation | Command is configured or explicitly requested. |
| Commit | User explicitly requests commit and profile allows commits. |
| Push/create PR/MR | User explicitly requests draft publish and all required gates pass. |
| Mutate local disposable data | Acceptance/manual validation requires it and profile allows it. |
| Mutate shared environment data | Only `accept` with `--allow-mutations` and explicit environment support. |
| Capture local browser evidence | Evidence is enabled, commands are configured, output stays in approved local artifact roots, and the stage allows validation/evidence execution. |

Never deploy, restart services, run migrations, seed data, transition Jira, or mutate production unless a profile explicitly supports the exact action and the user names the target environment. The default behavior is to stop.

## Workspace Safety

In `git-worktree` mode:

- Treat configured repository `path` values as canonical source repos for fetch/ref inspection only.
- Do not switch, reset, stash, pull, merge, or edit canonical source repo worktrees during `inspect`, `start`, `implement`, or `verify`.
- Use deterministic ticket worktrees derived from config for active work.
- Dirty canonical repos are recorded, not modified.
- Dirty selected ticket worktrees follow `dirtyStrategy`.
- Preserve untracked files.
- Parent/child defect reuse may resolve the active worktree from `workspaceOwnerTicket` and the active branch from `branchOwnerTicket`. Record that ownership in `run.json.relationships` and `workspace-map.md`.
- A relationship base refresh merge is allowed only inside the selected ticket worktree. Never run it in a canonical source repo.
- Before a child defect reuses a parent branch, verify the selected branch matches the expected parent-owned branch. Stop on mismatch unless the user explicitly selects a different relationship strategy.
- If the configured base refresh merge conflicts, stop with blockers and record `base-refresh.md`. Do not resolve conflicts or continue implementation unless the user explicitly asks for conflict resolution.

When a branch is already attached to a different worktree, stop and report the path. Do not move, remove, reset, or reuse it implicitly.

## Readiness And Mutation

- `inspect` and `ready` are always read-only.
- `implement` stops on blocked readiness unless `--force-implement` is explicit.
- `--force-implement` never permits publish, deploy, Jira transition, or environment mutation.
- `accept` without `--allow-mutations` stops before save/update/upload/delete/status-transition checkpoints.
- `--allow-mutations` applies only to `accept`, not `ready`.
- Shared-environment acceptance must capture pre-state when possible and record cleanup/restore status.

## SSO And Login Refresh

For environment helpers that depend on expiring SSO:

1. Use only configured login/refresh commands or documented helper login commands.
2. Run the refresh before the first SSO-backed `ready`, QA guide discovery, or `accept` command when configured.
3. If a command fails with an expired-credential signal, refresh once and retry the original command once.
4. Record only the refresh command label/path, exit status, and sanitized error summary.
5. If refresh is absent or fails, mark the affected stage blocked.

Do not use login refresh as permission to broaden commands or mutate data.

## Git And Provider Account Guards

Resolve the target before applying an identity guard:

- For this skill repository, use `policy.skillRepositoryProvider`, or the legacy `policy.skillRepositoryGithub` / `policy.github` fallback.
- For ticket/application repositories, use the selected profile's `gitIdentity` guard before commits and the generic `provider` guard, or legacy `github` guard, before pushes or PR/MR creation.
- Before committing ticket work, verify the selected worktree's effective Git author identity matches `gitIdentity`.
- Before pushing ticket work or creating a PR/MR, verify the active provider account and target remote match the selected profile's provider guard.
- Stop on identity, account, remote owner, or remote host mismatch. Do not switch accounts, rewrite remotes, push, or create PRs/MRs unless the user explicitly asks and the target policy allows it.
- Do not apply the skill-repository identity guard to ticket repositories.

## Generated Artifacts

- Local run artifacts, logs, screenshots, videos, traces, downloaded files, and raw Jira payloads are non-committable by default.
- Playwright evidence recordings are private local artifacts and must stay under configured run or central evidence roots.
- Evidence capture does not permit broader environment mutation; `accept` still needs `--allow-mutations` for ticket-scoped mutating checkpoints.
- Generated E2E specs created after commit block publishing when they are intended to be tracked.
- `artifact-index.md` is derived from `run.json` and the artifact registry.
