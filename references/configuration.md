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
| `profiles` | Profile-specific Jira, repositories, workspaces, commands, environments, E2E, commits, and publish settings. |

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
- local ignored-file coverage
- command mutability metadata
- publish policy and target-specific Git/provider guards

`doctor` should not run ticket stages.
