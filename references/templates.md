# Template Reference

Use these concise templates for generated artifacts. Expand sections only when the ticket requires the detail. Render derived final artifacts from `run.json`.

## artifact-index.md

```markdown
# Artifact Index

Rendered from: run.json

| Artifact | Producer | Consumers | Source | User-facing | Privacy | Committable | Freshness | Retention | Status |
|---|---|---|---|---:|---|---:|---|---|---|
| {path} | {producer} | {consumers} | source/derived | yes/no | {privacyLevel} | yes/no | current/stale/missing | {retention} | {status} |
```

## context.md

```markdown
# Context

## Ticket
{ticketKey}

## Jira
- Link: {jiraLink}
- Status: {status}
- Issue type: {rawIssueType}
- Priority: {priority}

## Summary
{summary}

## Acceptance Criteria
{acceptanceCriteria}

## Potential Root Cause
- Status: hypothesis / confirmed / unknown / not applicable
- Evidence: {evidence}
- Confidence: low / medium / high / unknown
- Gaps: {gaps}

## Sources
{sources}
```

## readiness-check.md

```markdown
# Readiness Check

## Ticket
{ticketKey}

## Result
Ready / Partially ready / Blocked

## Checklist
- [ ] Acceptance criteria present
- [ ] Expected behavior clear
- [ ] Current behavior clear for bug-like work
- [ ] UI/design impact clarified
- [ ] Data/API impact clarified
- [ ] Tests and validation expectations clear
- [ ] Dependencies and rollout risks identified
- [ ] Security/privacy risk identified

## Blockers
{blockers}

## Next Action
{nextAction}
```

## implementation-plan.md

```markdown
# Implementation Plan

## Ticket
{ticketKey}

## Classification
{classification}

## Summary
{summary}

## Acceptance Criteria
{acceptanceCriteria}

## Workspaces
{workspaces}

## Likely Files
{likelyFiles}

## Impact
- Data model: none / possible / required / unknown
- API contract: none / possible / required / unknown
- Frontend: none / possible / required / unknown

## Validation Plan
{validationPlan}

## Risk
Low / Medium / High / Unknown

## Open Questions
{openQuestions}

## Recommendation
Proceed / Proceed with caution / Blocked
```

## manual-validation-steps.md

```markdown
# Manual Validation Steps

## Ticket
{ticketKey}

## Environment
local

## Data To Use
| Purpose | ID / Record | Source | Notes |
|---|---|---|---|
| {purpose} | {dataId} | {source} | {notes} |

## Exact URLs
- UI: {uiUrl}
- API: {apiUrl}

## Browser Steps
| Step | Action | Expected Result | Failure Looks Like | Acceptance Criterion |
|---:|---|---|---|---|
| 1 | {action} | {expected} | {failure} | {ac} |

## Verification Commands
{commands}

## E2E Mapping
{e2eMapping}

## Blockers
{blockers}
```

## environment-readiness-{environment}.md

```markdown
# Environment Readiness

## Verdict
Ready for Testing / Not Ready for Testing / Blocked

## Target
- Ticket: {ticketKey}
- Environment: {environment}
- URLs/pods/images/commits inspected: {targets}

## Health
{health}

## Code Presence
{codePresence}

## Acceptance Criteria Coverage
| Acceptance Criterion | Status | Evidence | Gap |
|---|---|---|---|
| {ac} | passed/failed/blocked/not checked | {evidence} | {gap} |

## Commands Run
{commands}

## Blockers
{blockers}
```

## environment-acceptance-{environment}.md

```markdown
# Environment Acceptance

## Verdict
Acceptance Passed / Acceptance Failed / Blocked

## Mutation Permission
- `--allow-mutations`: yes/no
- Touched records: {records}
- Cleanup/restore status: {cleanup}

## Checkpoints
| Checkpoint | Expected | Actual | Evidence | Status |
|---|---|---|---|---|
| {checkpoint} | {expected} | {actual} | {evidence} | passed/failed/blocked |

## Blockers
{blockers}
```

## pre-publish-validation.md

```markdown
# Pre-Publish Validation

## Verdict
Pre-Publish Validation Passed / Pre-Publish Validation Failed / Blocked

## Committed HEAD
- Repository: {repo}
- Branch: {branch}
- SHA: {sha}
- Message: {message}

## Post-Commit Working Tree
{postCommitState}

## Commands
| Command | Scope | Result | Classification | Evidence |
|---|---|---|---|---|
| {command} | {scope} | passed/failed/blocked/skipped | ticket-related/pre-existing/unrelated/flaky | {evidence} |

## E2E
{e2e}

## Acceptance Criteria Coverage
{coverage}

## Publish Blockers
{blockers}
```

## mr-description.md

```markdown
# {ticketKey}: {summary}

## What Changed
{workCompleted}

## Validation
{validation}

## Risk
{risk}

## Notes
{notes}
```

## final-summary.md

```markdown
# Final Summary

Rendered from: run.json

## Ticket
{ticketKey}

## Work Completed
{workCompleted}

## RCA
{rca}

## Validation
{validation}

## Readiness / Acceptance
{environment}

## Publish Status
{publishStatus}

## Risk
{risk}

## Artifacts
{artifactIndex}

## Next Action
{nextAction}
```
