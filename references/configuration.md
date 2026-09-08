# Configuration Reference

Use this file for config loading, profile selection, schema expectations, policies, commands, environments, and local profile packs.

## Load Order

Resolve `{skillRoot}` as the directory containing this skill's canonical `SKILL.md`. Load and merge config in this order:

1. `{skillRoot}/config.json` when present.
2. `{skillRoot}/config.local.json`.
3. `{skillRoot}/profiles.local/*.json`.
4. `{skillRoot}/profiles.local/*/profile.json`.
5. `{skillRoot}/profiles/*.local.json`.

Base config is merged first; local overlays win. Local overlays may contain private profile names, paths, command templates, provider settings, and env-file references. Never print local values that look private.

The distributable tracked example is `config.example.json`. For commented local-overlay examples, use `config.local.example.jsonc`; it is documentation only and is not loaded by default. Copy relevant sections into ignored `config.local.json` or ignored files under `profiles.local/` when setting up a machine-specific profile.

The minimum safe config is:

```json
{
  "schemaVersion": "1.0.0",
  "defaultProfile": null,
  "profiles": {}
}
```

## Profile Selection

Resolve the profile in this order:

1. Explicit `--profile <name>`.
2. Merged `defaultProfile`.
3. Sole configured profile when exactly one exists.
4. Ask the user when multiple profiles exist and no default is set.

For `doctor`, report only profile names and structural health unless the user asks for a specific redacted detail.

## Schema Overview

Top-level config should contain:

| Key | Purpose |
|---|---|
| `schemaVersion` | Config schema version. |
| `defaultProfile` | Optional default profile name. |
| `stageRegistry` | Canonical stage names, statuses, command mappings, mutability, and outputs. |
| `artifactRegistry` | Artifact purpose, producer, consumer, privacy, retention, and committable status. |
| `invocation` | Primary commands and legacy aliases. |
| `policy` | Enterprise gates and safety defaults. |
| `profiles` | Profile-specific Jira, repositories, workspaces, relationships, artifact roots, commands, environments, E2E, evidence, commits, and publish settings. |

`stageRegistry` and `artifactRegistry` are generic and should stay source-controlled. Company-specific commands, paths, URLs, and profile-pack references belong in ignored local overlays.

## Stage Registry

Each stage entry should define:

- `command`: primary command that normally invokes it
- `legacyAliases`: compatible legacy words
- `readOnly`: whether the stage is read-only
- `mayEditCode`: whether it can edit application code
- `mayMutateEnvironment`: whether it can mutate environment data
- `requiresExplicitUserIntent`: whether implicit invocation is forbidden
- `writesArtifacts`: artifact keys normally produced

Valid statuses:

- `pending`
- `in_progress`
- `complete`
- `blocked`
- `failed`
- `skipped`
- `not_requested`

## Artifact Registry

Each artifact entry should define:

- `path`
- `producer`
- `consumers`
- `sourceOfTruth`: `true` only for authoritative state such as `run.json`
- `derived`
- `userFacing`
- `privacyLevel`: `public`, `internal`, `private`, or `secret-redacted`
- `committable`: normally `false` for run artifacts
- `retention`: `keep`, `keep-latest`, `expire`, or `manual-cleanup`

See `references/artifacts.md` for full artifact behavior.

## Policy Gates

Policies are generic by default and may be strengthened locally. Recommended keys:

```json
{
  "policy": {
    "defaultReadOnlyEnvironments": ["dev", "stage", "prod"],
    "requireExplicitPublish": true,
    "requireExplicitCommit": true,
    "requirePrePublishValidationBeforeDraft": true,
    "blockPublishOnFailedRequiredGate": true,
    "blockPublishOnPostCommitTrackedChanges": true,
    "forbidDeployments": true,
    "forbidJiraTransitions": true,
    "skillRepositoryProvider": {
      "provider": "github",
      "verifyBeforeRemotePushOrPr": true
    }
  }
}
```

`policy` does not grant permissions by itself. It constrains stage behavior. Use top-level `policy.skillRepositoryProvider` only for publishing this skill repository. Treat legacy `policy.skillRepositoryGithub` or `policy.github` as skill-repository guard fallbacks when present. Use profile-level `gitIdentity` plus generic `provider` guards for ticket/application repositories; legacy profile-level `github` guards remain compatibility inputs.

## Jira

Profile Jira config should store handles, not credential values:

```json
{
  "jira": {
    "baseUrl": "https://example.atlassian.net",
    "credentialStorage": "environment",
    "emailEnv": "JIRA_EMAIL",
    "tokenEnv": "JIRA_API_TOKEN",
    "envFile": "~/.portable-jira-flow/example-jira.env",
    "fields": ["summary", "description", "status", "priority", "issuetype", "labels", "components", "parent", "issuelinks", "comment"]
  }
}
```

Supported credential storage strategies:

- `environment`
- `envFile`
- `keychain`
- profile-specific helper, when documented in config

## Repositories And Workspaces

Repository entries:

| Field | Meaning |
|---|---|
| `name` | Stable repo key for flags and artifacts. |
| `path` | Local repo path. In `git-worktree` mode this is canonical source repo. |
| `baseBranch` | Default base branch. |
| `branchPrefix` | Default branch prefix. |
| `required` | Whether repo participates by default. |
| `commit` | Whether explicit commit may include this repo. |

Workspace modes:

- `canonical`: repo paths are active workspaces.
- `git-worktree`: repo paths are canonical source repos; ticket worktrees are active workspaces.
- `clone`: reserved for explicitly configured full clones.

In `git-worktree` mode, `ticketWorkspaceFormat` may use `{ticketKey}`, `{branchTicketKey}`, `{repoName}`, and `{profile}`.

## Relationships

Profiles may opt in to parent/child ticket behavior without changing regular standalone tickets:

```json
{
  "relationships": {
    "enabled": true,
    "relationshipTypes": ["standalone", "defect", "follow-up"],
    "defaultRelationshipType": "standalone",
    "relationshipTypeAliases": {
      "defect": ["Defect"],
      "follow-up": ["Follow-up"]
    },
    "detectParentFrom": ["fields.parent.key", "fields.parent.fields.key", "linkedTickets.parent"],
    "parentRequiredForTypes": ["defect"],
    "reuseParentWorkspaceForTypes": ["defect"],
    "reuseParentBranchForTypes": ["defect"],
    "branchOwnerTicketSource": "parent-for-defects",
    "workspaceOwnerTicketSource": "parent-for-defects",
    "fallbackWhenNoParent": "standalone-with-warning",
    "baseRefresh": {
      "enabled": true,
      "strategy": "merge",
      "remote": "origin",
      "baseBranch": "main",
      "fetchRemote": true,
      "runOnStartForTypes": ["defect"],
      "stopOnConflict": true
    },
    "safety": {
      "requireParentRunWhenAvailable": false,
      "requireBranchMatchesOwner": true,
      "requireWorkspaceMatchesOwner": true,
      "stopWhenParentBranchAttachedElsewhere": true
    }
  }
}
```

When `relationships.enabled` is false or absent, use existing standalone behavior. When it is true, `inspect` may discover a parent ticket from configured Jira fields or explicit parent flags and write `run.json.relationships`. `start` may resolve `{branchTicketKey}` and the selected worktree from the parent only for relationship types listed in `reuseParentBranchForTypes` and `reuseParentWorkspaceForTypes`.

`baseRefresh` controls whether `start` refreshes a child defect's shared parent branch from a configured base ref before code edits. Public examples should use generic branch names; team-specific base branches belong in ignored local overlays. If older local profiles use `branching.parentTicketBranching`, preserve it as a compatibility input, but write new state to `run.json.relationships`.

## Artifact Roots

Profiles may set a workspace-level run root so generated workflow artifacts are not stored inside application repositories:

```json
{
  "artifacts": {
    "runsRoot": "~/work/.portable-jira-flow/runs",
    "legacyArchiveRoot": "~/work/.portable-jira-flow/legacy-runs",
    "migrationManifestRoot": "~/work/.portable-jira-flow/migration-manifests",
    "legacyImportPolicy": "archive-only",
    "runLayout": "ticket",
    "nonCommittable": true
  }
}
```

When `artifacts.runsRoot` is present, create and read run folders as `{runsRoot}/{ticketKey}/`. If it is absent, fall back to the repository-local `.portable-jira-flow/runs/{ticketKey}/` behavior documented in `references/artifacts.md`.

`legacyArchiveRoot` and `migrationManifestRoot` are optional handles for centralized imports from older workflow skills. New ticket work must not write active state there. With `legacyImportPolicy: "archive-only"`, imported artifacts are retained for audit and status/report context but are not upgraded in place or treated as current stage state. Use `"disabled"` when a profile should ignore historical archives entirely.

## Git Identity And Provider Guards

Ticket profiles may require a specific work identity for commits and pushes:

```json
{
  "gitIdentity": {
    "verifyBeforeCommit": true,
    "requiredEmailDomain": "company.example",
    "allowedEmailPatterns": ["*@company.example"]
  },
  "provider": {
    "name": "github",
    "scope": "ticketRepositories",
    "verifyBeforeRemotePushOrPr": true,
    "requiredAccountDomain": "company.example",
    "allowedRemoteHosts": ["github.com"],
    "allowedRemoteOwners": ["example-org"]
  }
}
```

These guards apply to selected ticket workspaces only. They do not apply to commits or pushes for the skill repository itself. A profile may use a legacy `github` guard instead of `provider`; preserve it when reading older local overlays, but prefer `provider` in new examples.

## Commands

Validation, readiness, acceptance, and publish commands must be configured. Each command should include:

- `name`
- `stage`
- `repo` or `environment`
- `command`
- `runner`
- `workdir`
- `mutability`: `read-only`, `local-disposable-mutation`, `environment-mutation`, or `destructive`
- `requiredForPublish`
- `artifacts`
- `nonCommittableArtifacts`
- `backupBeforeRun`
- `compareOnFailure`

Do not run broad tests, migrations, seeders, installers, deployments, restarts, or publish commands unless explicitly configured and allowed by stage and policy.

Command templates for E2E and evidence capture may use:

| Placeholder | Meaning |
|---|---|
| `{ticketKey}` | Original ticket key. |
| `{environment}` | Target environment for the command. |
| `{specPaths}` | Ticket-scoped E2E spec paths. |
| `{evidencePhase}` | `reproduction` or `verification`. |
| `{evidenceOutputDir}` | Output directory for Playwright videos, traces, screenshots, and reports. |
| `{playwrightConfigPath}` | Run-local Playwright wrapper config path. |

## E2E

Profile E2E config describes how to map `manual-validation-steps.md` into ticket-scoped browser scenarios. Keep project-specific workspace paths and commands in local overlays.

Common keys:

```json
{
  "e2e": {
    "enabled": true,
    "mode": "isolated-playwright",
    "workspacePath": "~/work/app-e2e",
    "basePlaywrightConfig": "playwright.config.js",
    "defaultEnvironment": "local",
    "specDir": "tests",
    "specFilePattern": "{ticketKeyLower}-{shortSummary}.spec.ts",
    "runCommandTemplate": "npx playwright test {specPaths} --config {playwrightConfigPath} --output {evidenceOutputDir}",
    "createMissingTicketSpecs": true,
    "generatedSpecSource": "manual-validation-steps.md",
    "mapSpecsToAcceptanceCriteria": true,
    "commitGeneratedSpecs": false
  }
}
```

`basePlaywrightConfig` is optional and may be relative to `workspacePath`.
When omitted, evidence preparation may auto-detect a CommonJS Playwright config
such as `playwright.config.js` or `playwright.config.cjs` in the E2E workspace.
Ticket-scoped `{specPaths}` must resolve to specific specs or directories; an
empty value must not be treated as permission to run the entire E2E suite.

## Ticket Type Classification

Profiles classify each ticket into a canonical internal type, independent of the ticket key prefix. `ticketPrefixes` on a profile identifies which profile owns a ticket key; it never determines the ticket's *type*. Type classification instead comes from `ticketTypes`:

```json
{
  "ticketTypes": {
    "aliases": {
      "bug": ["Bug", "Defect"],
      "performance": ["Performance", "Optimization"]
    },
    "canonicalTypes": ["feature", "bug", "performance", "unknown"],
    "bugLikeTypes": ["bug", "regression", "production-bug", "hotfix"],
    "performanceLikeTypes": ["performance"],
    "typeOverrideFlags": {
      "--bug": "bug",
      "--performance": "performance"
    },
    "detection": {
      "primaryField": "fields.issuetype.name",
      "fieldsToConsider": ["fields.issuetype.name", "fields.summary", "fields.description", "fields.labels", "fields.components", "linkedTickets"],
      "secondarySignals": ["fields.labels", "fields.components"],
      "weakFallbackSignals": ["fields.summary"],
      "keywordSignals": {
        "performance": ["optimize", "slow", "latency", "timeout", "N+1"]
      },
      "parentSummaryKeywords": {
        "performance": ["Performance Backlog"]
      },
      "conflictBehavior": "unknown-with-open-question"
    }
  }
}
```

- `aliases`: literal Jira `issuetype.name` values that map to each canonical type. Not every company has a dedicated issue type for every kind of work (e.g. performance tickets are often filed as a generic "Story"), so this alone may be insufficient.
- `canonicalTypes`: the closed set of types this profile actually distinguishes. Classification that cannot be resolved to one of these is `unknown`, not a guess.
- `bugLikeTypes` / `performanceLikeTypes`: which canonical types trigger bug-oriented (reproduction evidence, RCA) or performance-oriented (baseline/comparison, optimization plan) stages. A type can be added to `canonicalTypes` without adding it to either list if it needs neither treatment.
- `typeOverrideFlags`: explicit CLI flags a user can pass to force classification when detection is wrong or ambiguous.
- `detection`: the signal-resolution order when `aliases` alone doesn't resolve a type. `primaryField` is checked first; `secondarySignals` (labels/components) and `weakFallbackSignals` (free-text summary/description) are checked next; `keywordSignals` maps a canonical type to keywords that count as evidence for that type in the weak-fallback text; `parentSummaryKeywords` does the same against a linked parent ticket's summary, useful when tickets are filed under a themed epic (e.g. a shared performance backlog) regardless of the ticket's own issue type. `conflictBehavior: "unknown-with-open-question"` means: if signals disagree, classify as `unknown` and raise an open question rather than silently pick one.

This mechanism is what lets a ticket be recognized as performance work from its summary and parent epic even when its Jira issue type is a generic "Story" — see `references/performance.md`.

## Performance Measurement

Profile performance config controls the optimization-plan/baseline/comparison stages described in `references/performance.md`. Public examples must remain generic; machine-specific benchmark tooling belongs in ignored local overlays.

Common keys:

```json
{
  "ticketTypes": {
    "performanceLikeTypes": ["performance"],
    "performance": {
      "attemptLocalBaseline": true,
      "stopIfNoBaselineCommand": false,
      "metrics": ["responseTimeMs", "queryCount", "payloadBytes"],
      "regressionThresholds": {}
    }
  }
}
```

Baseline and comparison commands are not a separate config surface — they are ordinary entries in the profile's `commands[]` array (see "Commands" below) tagged `"stage": "performanceBaseline"` or `"stage": "performanceComparison"`, exactly like `lint`/`unit-tests` are tagged `"stage": "validation"`. When no such command is configured for a performance-like ticket, the baseline/comparison stages record `not_configured` with a warning; they never block on a missing benchmark tool under the default `warn` policy.

These commands may use one additional placeholder: `{performanceTarget}`, the endpoint/query/job under test resolved from `optimization-plan.md`'s Target field. Unlike `{ticketKey}` or `{selectedWorkspacePath}`, this value is ticket-specific and cannot be hardcoded once in config — the assistant substitutes it at runtime before running the configured command. A profile's `command` value is free to combine it with a fixed base URL or wrap it in its own script; see `references/performance.md`.

## Evidence Capture

Profile evidence config controls before/after Playwright evidence. Public examples must remain generic. Machine-specific central evidence roots belong in ignored local overlays.

Common keys:

```json
{
  "evidence": {
    "enabled": true,
    "storage": "central",
    "missingPolicy": "warn",
    "centralEvidenceRoot": null,
    "requireReproductionForTicketTypes": ["bug", "regression", "production-bug", "hotfix"],
    "mediaExtensions": ["webm", "mp4", "mov"],
    "playwright": {
      "generatedConfigPattern": "playwright-evidence-{evidencePhase}.config.cjs",
      "outputDirPattern": "{centralEvidenceRoot}/{ticketKey}/{evidencePhase}",
      "video": "on",
      "screenshot": "only-on-failure",
      "trace": "retain-on-failure"
    }
  }
}
```

`evidence.storage: "central"` writes media outside application repositories while keeping run-local summaries beside `run.json`. Missing evidence is a warning by default. Strengthen `missingPolicy` only in a local profile when the team wants evidence gaps to block publish or report workflows.

## Environments

Define shared environment metadata once and reference it from readiness, QA guide, and acceptance behavior. `ready` treats every environment as read-only. `accept` requires `--allow-mutations` for configured mutating acceptance commands.

## Local Profile Packs

Local profile packs live under ignored `profiles.local/` directories. A local profile may route extra references through `referenceFiles`:

```json
{
  "referenceFiles": {
    "ready:local": ["profiles.local/company/references/local-readiness.md"],
    "accept:stage": ["profiles.local/company/references/stage-acceptance.md"],
    "status": ["profiles.local/company/references/status-notes.md"]
  }
}
```

Read those files only when the selected profile and command match the route. Never copy local profile-pack content into tracked public files.

## Context Adapters

Adapters such as Confluence, Slack, Teams, related PR/MR, and related tickets default to placeholders. Do not call external APIs unless a profile explicitly enables a safe adapter and supplies a configured connector or command.

## Doctor Checks

`doctor` should check:

- JSON parse validity
- local overlay load order
- required keys and schema version
- profile selection result
- credential handles present, not values
- repo paths exist when configured
- stage registry and artifact registry consistency
- profile artifact root shape, including ignored-file coverage for any configured local run root
- relationship config shape, parent discovery fields, branch/workspace owner policy, and base refresh policy when relationships are enabled
- evidence config shape, storage root handle, media extensions, and E2E placeholder availability when evidence is enabled
- local ignored-file coverage
- command mutability metadata
- publish policy and target-specific Git/provider guards

`doctor` should not run ticket stages.
