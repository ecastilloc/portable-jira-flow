# Artifact Reference

Use this file when creating, refreshing, reading, reporting, indexing, or cleaning ticket artifacts.

## Artifact Root

For meaningful ticket stages, create artifacts under the selected profile's configured run root when present:

```text
{profile.artifacts.runsRoot}/{ticketKey}/
```

If `profile.artifacts.runsRoot` is absent, fall back to:

```text
.portable-jira-flow/runs/{ticketKey}/
```

Resolve fallback roots from the invocation git root first, then the first selected repository root. If no configured or fallback root is available, ask before writing artifacts. Prefer workspace-level or central run roots over repository-local folders when the local profile defines them.

## Central State Layout

When a profile uses a central state root, keep active workflow state and imported history separate:

```text
{portableStateRoot}/runs/{ticketKey}/
{portableStateRoot}/legacy-runs/{sourceSlug}/{ticketKey}/
{portableStateRoot}/migration-manifests/
```

`runs/{ticketKey}/` contains the current portable workflow state. `legacy-runs/{sourceSlug}/{ticketKey}/` contains archived copies of historical artifacts from older skill folders or repository-local run roots. `migration-manifests/` contains checksum manifests proving what was copied and from where.

Imported legacy archives are audit material, not active workflow state. Do not rewrite their `run.json` files to the portable schema, do not use their markdown as current source of truth, and do not collapse duplicate ticket keys from different sources. Keep the source slug so repeated ticket keys remain attributable.

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
  "relationships": {
    "relationshipType": "standalone",
    "parentTicket": null,
    "childTickets": [],
    "branchOwnerTicket": "ABC-123",
    "workspaceOwnerTicket": "ABC-123",
    "sharedBranch": false,
    "sharedWorkspace": false,
    "branch": {
      "expected": "feature/ABC-123",
      "actual": "feature/ABC-123",
      "targetBase": "origin/main",
      "baseRefresh": {
        "required": false,
        "status": "not_requested",
        "strategy": "merge",
        "command": null,
        "updatedAt": null,
        "warnings": []
      }
    },
    "warnings": []
  },
  "classification": {},
  "implementation": {
    "filesChanged": []
  },
  "readiness": {},
  "risk": "Unknown",
  "validation": {},
  "prePublishValidation": {},
  "environmentReadiness": {},
  "environmentAcceptance": {},
  "evidence": {
    "policy": {
      "enabled": true,
      "storage": "central",
      "missingPolicy": "warn",
      "requireReproductionForTicketTypes": ["bug", "regression", "production-bug", "hotfix"]
    },
    "reproduction": {
      "required": false,
      "status": "not_requested",
      "artifacts": [],
      "warnings": [],
      "command": null,
      "environment": "local",
      "updatedAt": null
    },
    "verification": {
      "required": false,
      "status": "not_requested",
      "artifacts": [],
      "warnings": [],
      "command": null,
      "environment": "local",
      "updatedAt": null
    }
  },
  "finalReport": {}
}
```

The `relationships` and `evidence` objects are optional for older historical runs. New runs should write `relationships` when relationship config is present or when Jira/flags identify parent context. New runs should write `evidence` when evidence config is present. Do not store secrets in `run.json`.

Evidence phase `status` values should use the stage status vocabulary when possible: `pending`, `in_progress`, `complete`, `blocked`, `failed`, `skipped`, or `not_requested`. Use warnings for missing media under the default `warn` policy rather than converting the whole workflow to blocked.

## Artifact Registry

The config `artifactRegistry` should cover at least:

| Artifact | Source | User-facing | Committable | Retention |
|---|---|---:|---:|---|
| `run.json` | source of truth | no | no | keep |
| `behavior-spec.md` | v2 behavior contract draft | yes | no | keep |
| `behavior-coverage.json` | v2 scenario coverage | no | no | keep |
| `artifact-index.md` | derived | yes | no | keep |
| `legacy-artifact-index.md` | derived legacy archive index | yes | no | keep |
| `migration-manifests/migration-manifest-{timestamp}.json` | source migration manifest | no | no | keep |
| `jira.json` | redacted source | no | no | keep |
| `context.md` | derived | yes | no | keep |
| `repo-map.md` | derived | internal | no | keep |
| `workspace-map.md` | derived | internal | no | keep |
| `relationship-map.md` | derived relationship index | yes | no | keep |
| `base-refresh.md` | derived parent-branch base refresh record | internal | no | keep |
| `base-snapshot.md` | derived | internal | no | keep |
| `classification.md` | derived | internal | no | keep-latest |
| `root-cause.md` | derived | yes for bugs | no | keep |
| `readiness-check.md` | derived | yes | no | keep |
| `implementation-plan.md` | derived | yes | no | keep |
| `implementation-summary.md` | derived | yes | no | keep |
| `blockers.md` | derived | yes | no | keep-latest |
| `assumptions.md` | derived | yes | no | keep-latest |
| `validation-plan.md` | derived | internal | no | keep |
| `validation-results.md` | derived | yes | no | keep |
| `manual-validation-steps.md` | derived/source for QA/E2E | yes | no | keep |
| `reproduction-evidence.md` | derived evidence summary | yes | no | keep |
| `verification-evidence.md` | derived evidence summary | yes | no | keep |
| `evidence-manifest.json` | derived evidence index | no | no | keep |
| `playwright-evidence-{evidencePhase}.config.cjs` | generated capture config | internal | no | keep |
| `reproduction-video-{ticketKey}.{ext}` | generated media | yes | no | manual-cleanup |
| `verification-video-{ticketKey}.{ext}` | generated media | yes | no | manual-cleanup |
| `verification-screenshot-{ticketKey}.{ext}` | generated media | yes | no | manual-cleanup |
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

## Legacy Artifact Imports

Use `scripts/migrate_legacy_artifacts.py` when centralizing older run artifacts. The importer supports:

- `inventory`: checksum and count legacy sources without writing files
- `copy`: copy each source into `legacy-runs/{sourceSlug}/{ticketKey}/`, then write a migration manifest and refresh `legacy-artifact-index.md`
- `verify`: re-check copied files against a migration manifest

Source roots must be run roots whose immediate children are ticket folders. The importer may copy any historical file type, including older `run.json` contracts, markdown summaries, screenshots, videos, traces, logs, and draft publish notes. It does not delete, normalize, redact, or reinterpret source files.

For each import, record:

- source root
- source slug
- target archive path
- ticket count
- file count and bytes
- skipped non-regular files
- SHA-256 checksum per copied file
- copy result, unchanged count, and conflicts

If a target file already exists with the same checksum, treat it as unchanged. If it exists with a different checksum, stop before overwriting and surface the conflict. To intentionally replace a legacy archive, the user must explicitly request an archive maintenance action.

## Artifact Index

Generate `artifact-index.md` from `run.json.artifacts` and the registry. Include:

- artifact path
- source root or configured storage root when known
- producer stage
- command or stage source
- consumer stages
- source-of-truth or derived
- user-facing or internal
- privacy level
- committable status
- generated timestamp when known
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
- parent ticket, branch owner, workspace owner, expected branch, or shared-workspace policy changed
- relationship base refresh is older than the latest configured base ref fetched during `start`
- manual validation is older than implementation changes
- reproduction evidence was captured after implementation began instead of before code edits
- verification evidence is older than the latest implementation, validation, committed HEAD, or environment acceptance state it claims to verify
- a registered central evidence file is missing at status/report time

`status` should surface stale artifacts and recommend the next action to refresh them.

## V2 State Isolation

The opt-in v2 pilot writes active state under:

```text
{profile.artifacts.runsRoot}/v2/{ticketKey}/
```

When no configured run root exists, helpers may fall back to `.portable-jira-flow/runs/v2/{ticketKey}/` in the selected working root. V2 artifacts use the same non-committable default as v1 run artifacts. A v2 `behavior-spec.md` is a local draft until a profile explicitly configures durable storage and the user asks to update it.

V2 status and publish checks use `run.json.behaviorSpec.digest` to decide whether implementation, verification, and derived summaries still match the selected behavior. Changing `behavior-spec.md` makes dependent results stale until refreshed.

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
- imported legacy archives and migration manifests unless the user explicitly requests legacy archive maintenance
- user-owned untracked work
- artifacts required by active blockers or current validation evidence
- current reproduction or verification evidence referenced by `run.json.evidence` unless the user explicitly requests evidence cleanup
