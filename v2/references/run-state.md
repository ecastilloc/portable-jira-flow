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
  "behaviorSpec": {
    "status": "draft",
    "path": "behavior-spec.md",
    "digestAlgorithm": "sha256",
    "digest": "",
    "storage": "local-run-artifact",
    "durable": false,
    "selectedAt": "2026-01-01T00:00:00Z",
    "sourceRevision": null,
    "warnings": []
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
    "command": "portable-jira-flow-v2 inspect ABC-123",
    "reason": "Review and refine the generated behavior contract before implementation.",
    "blocked": false
  },
  "artifacts": [],
  "artifactRegistrySnapshot": {}
}
```

Old v1 runs remain readable as historical context. V2 must not rewrite a v1 run to schema `2.0.0`.
