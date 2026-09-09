# Behavior Contract Reference

The behavior contract is the small durable unit that connects request intent to implementation and verification. It records what behavior should exist, why that behavior is believed to be intended, and which scenarios must be checked.

## Authority

The behavior contract describes intended product behavior. It does not authorize side effects. `run.json` remains authoritative for workflow execution, permissions, observed results, blockers, and next action.

User instructions, configured policy, and platform safety rules outrank any behavior spec. If sources disagree, record the contradiction and ask only when the missing decision changes product behavior, scope, authorization, or a required action.

## Storage

The MVP stores draft behavior specs as local run artifacts:

```text
{profile.artifacts.runsRoot}/v2/{ticketKey}/behavior-spec.md
```

Durable product specs require explicit configuration, for example a profile-owned docs path in an application repository. V2 must not write durable specs during `inspect` or `start`.

## Minimum Fields

A behavior spec should include:

- stable use-case or requirement ID
- linked change request
- status
- source provenance
- domain terms
- scope and out-of-scope notes
- preconditions
- trigger
- main success flow
- alternative and failure flows
- success guarantees
- failure guarantees
- required coverage
- unresolved decisions

IDs should be stable across tickets that modify the same behavior. Jira keys identify change requests; they are not durable behavior IDs.

## Freshness

Every v2 result that depends on intended behavior records the selected spec digest. If the spec content changes, dependent implementation, verification, publish, status, and report views become stale until refreshed.
