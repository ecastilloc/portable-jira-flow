# V2 Run State Reference

V2 run state is separate from v1 run state.

```text
{runsRoot}/v2/{ticketKey}/run.json
```

The `schemaVersion` is `2.0.0` and `skillName` is `portable-jira-flow-v2`.

Minimum v2 state:

```json
{
  "schemaVersion": "2.0.0",
  "skillName": "portable-jira-flow-v2",
  "ticketKey": "ABC-123",
  "profile": "example",
  "workflowVersion": "v2",
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z",
  "invocation": {
    "rawArgs": [],
    "normalizedArgs": [],
    "primaryCommand": "specify",
    "legacyAliasesExpanded": []
  },
  "stages": {},
  "policy": {
    "publishExplicitlyRequested": false,
    "commitExplicitlyRequested": false,
    "mutationsAllowed": false,
    "blockedGates": []
  },
  "behaviorSpec": {
    "status": "draft",
    "path": "behavior-spec.md",
    "digestAlgorithm": "sha256",
    "digest": "",
    "storage": "local-run-artifact",
    "durable": false,
    "selectedAt": "2026-01-01T00:00:00Z",
    "sourceRevision": null,
    "warnings": [],
    "contractPath": "behavior-spec.json",
    "contractDigest": "",
    "sourcePackPath": "source-pack.json",
    "sourcePackDigest": "",
    "factsPath": "behavior-facts.json",
    "factsDigest": "",
    "openDecisionCount": 0,
    "contradictionCount": 0
  },
  "coverage": {
    "requirements": [],
    "scenarios": [],
    "results": [],
    "summary": {
      "planned": 0,
      "implemented": 0,
      "passed": 0,
      "failed": 0,
      "blocked": 0,
      "skipped": 0,
      "unknown": 0
    }
  },
  "provenance": {
    "sources": [],
    "assumptions": [],
    "decisions": []
  },
  "nextAction": {
    "command": "portable-jira-flow-v2 specify ABC-123",
    "reason": "Review and refine the generated behavior contract before implementation.",
    "blocked": false
  },
  "plan": {
    "status": "ready",
    "path": "implementation-plan.json",
    "digestAlgorithm": "sha256",
    "digest": "",
    "markdownPath": "implementation-plan.md",
    "markdownDigest": "",
    "selectedBehaviorSpec": {},
    "implementationTaskCount": 0,
    "blockingOpenDecisionCount": 0
  },
  "artifacts": [],
  "artifactRegistrySnapshot": {}
}
```

Old v1 runs remain readable as historical context. V2 must not rewrite a v1 run to schema `2.0.0`.

## Specify State

`specify` is the first v2 command that writes the full behavior pipeline. It updates:

- `behaviorSpec.path` and `behaviorSpec.digest` for the rendered `behavior-spec.md`
- `behaviorSpec.contractPath` and `behaviorSpec.contractDigest` for `behavior-spec.json`
- `behaviorSpec.sourcePackPath` and `behaviorSpec.sourcePackDigest` for `source-pack.json`
- `behaviorSpec.factsPath` and `behaviorSpec.factsDigest` for `behavior-facts.json`
- `coverage.requirements`, `coverage.scenarios`, and `coverage.summary`
- `provenance.sources`, `provenance.decisions`, and `provenance.contradictions`
- `stages.specify.status`, which is `blocked` when contradictions exist
- `nextAction`, which points to review, specify, or plan depending on open decisions

## Plan State

`plan` pins the current `source-pack.json`, `behavior-facts.json`, `behavior-spec.json`, and `behavior-spec.md` digests and writes `implementation-plan.json` plus `implementation-plan.md`. It updates:

- `stages.plan.status`, which is `complete` only when the behavior contract is fresh, contradictions are absent, and no open decision blocks implementation
- `stages.plan.sourcePackDigest`, `factsDigest`, `contractDigest`, and `behaviorSpecDigest`
- `stages.plan.implementationPlanPath` and `implementationPlanMarkdownPath`
- `plan.selectedBehaviorSpec`, `plan.digest`, and `plan.markdownDigest`
- `nextAction`, which points to `implement` when ready or back to `specify` when blocked

`start` is a v2 compatibility alias for `plan`; v2 must not write a `stages.start` entry or create v1 run directories.

`run.json` remains the execution authority. The behavior spec is the behavior contract; it does not grant permission to commit, push, publish, mutate environments, or update external systems.
