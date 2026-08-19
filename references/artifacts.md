# Artifact Reference

Use this file when creating, refreshing, reading, reporting, indexing, or cleaning ticket artifacts.

## Artifact Root

For meaningful ticket stages, create artifacts under:

```text
.portable-jira-flow/runs/{ticketKey}/
```

Prefer the invocation git root. If unavailable, use the first selected repository root. If no repository root is available, ask before writing artifacts.

## Source Of Truth

`run.json` is authoritative. Markdown artifacts summarize details but must not contradict current run state. When writing `final-summary.md`, `definition-of-done.md`, `worktree-safety.md`, or `artifact-index.md`, render from current `run.json` and the artifact registry.

## Run State Contract

`run.json` must include:

```json
{
  "schemaVersion": "1.0.0",
  "skillName": "portable-jira-flow",
  "ticketKey": "ABC-123",
  "profile": "example",
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z",
  "invocation": {
    "rawArgs": [],
    "normalizedArgs": [],
    "primaryCommand": "inspect",
    "legacyAliasesExpanded": []
  },
  "stages": {},
  "policy": {
    "publishExplicitlyRequested": false,
    "commitExplicitlyRequested": false,
    "mutationsAllowed": false,
    "blockedGates": []
  },
  "nextAction": {
    "command": "start ABC-123",
    "reason": "Inspection is complete and no readiness blockers remain.",
    "blocked": false
  },
  "artifacts": [],
  "artifactRegistrySnapshot": {},
  "workspaces": {},
  "classification": {},
  "readiness": {},
  "risk": "Unknown",
  "validation": {},
  "prePublishValidation": {},
  "environmentReadiness": {},
  "environmentAcceptance": {},
  "finalReport": {}
}
```

Do not store secrets in `run.json`.

## Artifact Registry

The config `artifactRegistry` should cover at least:

| Artifact | Source | User-facing | Committable | Retention |
|---|---|---:|---:|---|
| `run.json` | source of truth | no | no | keep |
| `artifact-index.md` | derived | yes | no | keep |
| `jira.json` | redacted source | no | no | keep |
| `context.md` | derived | yes | no | keep |
| `repo-map.md` | derived | internal | no | keep |
| `workspace-map.md` | derived | internal | no | keep |
| `base-snapshot.md` | derived | internal | no | keep |
| `classification.md` | derived | internal | no | keep-latest |
| `root-cause.md` | derived | yes for bugs | no | keep |
| `readiness-check.md` | derived | yes | no | keep |
| `implementation-plan.md` | derived | yes | no | keep |
| `blockers.md` | derived | yes | no | keep-latest |
| `assumptions.md` | derived | yes | no | keep-latest |
| `validation-plan.md` | derived | internal | no | keep |
| `validation-results.md` | derived | yes | no | keep |
| `manual-validation-steps.md` | derived/source for QA/E2E | yes | no | keep |
| `environment-readiness-{environment}.md` | derived | yes | no | keep |
| `qa-validation-guide-{environment}.md` | derived | yes | no | keep |
| `qa-validation-guide-all-envs.md` | derived | yes | no | keep |
| `environment-acceptance-{environment}.md` | derived | yes | no | keep |
| `pre-publish-validation.md` | derived | yes | no | keep |
| `qa-validation-video-{ticketKey}.{ext}` | generated media | yes | no | manual-cleanup |
| `definition-of-done.md` | derived | yes | no | keep-latest |
| `worktree-safety.md` | derived | internal | no | keep |
| `mr-description.md` | derived | yes | no by default | keep |
| `deployment-notes.md` | derived | yes | no | keep |
| `rollback-plan.md` | derived | yes | no | keep |
| `qa-notes.md` | derived | yes | no | keep |
| `final-summary.md` | derived | yes | no | keep |

Additional generated logs, traces, screenshots, downloads, raw Jira snapshots, and related-ticket files must be registered before final output or cleanup.

## Artifact Index

Generate `artifact-index.md` from `run.json.artifacts` and the registry. Include:

- artifact path
- producer stage
- consumer stages
- source-of-truth or derived
- user-facing or internal
- privacy level
- committable status
- freshness
- retention
- exists/missing
- notes or blockers

## Freshness

Mark artifacts stale when:

- `run.json.updatedAt` is newer than a derived artifact timestamp and the artifact claims current state
- the artifact references an old HEAD after commit or validation
- stage status changed after artifact generation
- selected workspace, environment, or profile changed
- manual validation is older than implementation changes

`status` should surface stale artifacts and recommend the next action to refresh them.

## Cleanup

`cleanup` is dry-run by default. It may propose cleanup for:

- expired logs
- screenshots
- videos
- traces
- raw downloaded artifacts
- stale derived markdown when safely regenerable

Never clean:

- local config or secrets
- source files
- committed files
- current `run.json`
- user-owned untracked work
- artifacts required by active blockers or current validation evidence
