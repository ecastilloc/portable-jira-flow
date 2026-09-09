# V2 Command Reference

V2 uses spec-development command names while sharing the same profile, safety, repository, and artifact infrastructure as v1. Keep v1 command names intact; v2 may keep selected old words as compatibility aliases.

## MVP Commands

| Command | V2 behavior |
|---|---|
| `doctor` | Validates merged runtime config using the shared loader, then checks v2 schemas and optional `workflowV2` profile keys. It is read-only and reports structural facts only. |
| `specify <ticket>` | Ingests supplied local source material, writes the source pack, behavior facts, machine-readable behavior spec, rendered review spec, provenance, unresolved decisions, coverage summary, and freshness digests in v2 `run.json`. |
| `trace <ticket>` | Reads v2 `run.json`, reports spec digest, scenario coverage state, plan status, stale source/spec digests, blockers, and next action. It does not run stages. |
| `plan <ticket>` | Pins the selected behavior contract digests, checks source/spec freshness, writes implementation task scaffolds, records blocking open decisions, and updates v2 `run.json`. It does not prepare workspaces, create branches, fetch Jira, or edit product code. |

## Later Commands

| Command | V2 addition |
|---|---|
| `implement <ticket>` | Requires a selected behavior spec unless overridden by policy. Meaningful edits trace to a requirement, scenario, assumption, or technical constraint. |
| `verify <ticket>` | Records actual assertion results by scenario ID and keeps expected behavior independent from implementation outcome. |
| `publish <ticket>` | Adds spec/code/test consistency and stale-digest checks to the existing committed-HEAD gates. |
| `ready <ticket> <environment>` | Reuses scenario IDs for read-only readiness and QA guide generation. |
| `accept <ticket> <environment>` | Maps configured acceptance checkpoints to scenario IDs while preserving mutation gates. |
| `report <ticket>` | Renders summaries from v2 `run.json` plus the selected behavior spec. |
| `cleanup <ticket>` | Cleans disposable v2 run artifacts only when retention policy allows it. Durable specs are never cleaned as run artifacts. |

Compatibility aliases:

| Alias | Primary v2 command |
|---|---|
| `inspect` | `specify` |
| `status` | `trace` |
| `start` | `plan` |

V1 aliases remain compatibility inputs for v1. V2 should prefer spec-development command names in new output.

## Specify Inputs

The MVP helper accepts local, redacted source inputs only:

```text
python3 scripts/v2_contract.py specify ABC-123 --source redacted-jira.json
python3 scripts/v2_contract.py specify ABC-123 --source notes.md --source existing-spec.md
python3 scripts/v2_contract.py specify ABC-123 --source-note "As a user, I want the saved filter to persist."
```

Do not fetch live Jira during this slice. A caller may pass exported/redacted Jira JSON, markdown/text notes, existing reviewed specs, test files, code snippets, or assistant-collected context as source files. The helper treats code and existing tests as evidence of current behavior, not authority for intended behavior.

`specify` writes these local, non-committable artifacts under `{profile.artifacts.runsRoot}/v2/{ticketKey}/`, or `.portable-jira-flow/runs/v2/{ticketKey}/` when no run root is configured:

- `source-pack.json`
- `behavior-facts.json`
- `behavior-spec.json`
- `behavior-spec.md`
- `run.json`

`plan` writes these local, non-committable artifacts in the same v2 run directory:

- `implementation-plan.json`
- `implementation-plan.md`

`init` remains a compatibility/debug alias for the older scaffold behavior that only creates a local behavior-spec draft and v2 run state.

## Plan Gate

`plan` requires a completed v2 `specify` run. It loads `source-pack.json`, `behavior-facts.json`, `behavior-spec.json`, `behavior-spec.md`, and `run.json`; recomputes source, facts, contract, and markdown digests; and blocks when any dependent input is stale. It also blocks implementation readiness when contradictions exist or open decisions affect expected behavior.

A successful plan updates `stages.plan`, stores pinned digests under `plan.selectedBehaviorSpec`, and sets `nextAction` to `portable-jira-flow-v2 implement <ticket>`. A blocked plan still writes the plan artifacts and sets `nextAction` back to `portable-jira-flow-v2 specify <ticket>` with the blocker reason.

## Trace Freshness

`trace` compares recorded source and behavior-spec digests with the current local files. If a supplied source file changes after `specify`, trace reports `stale_sources` so downstream v2 stages know their behavior contract may need regeneration or review. Inline notes cannot be re-read from disk and are therefore not freshness-checked.
