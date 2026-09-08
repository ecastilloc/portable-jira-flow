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

## legacy-artifact-index.md

```markdown
# Legacy Artifact Index

Generated: {generatedAt}

Imported legacy runs are immutable audit archives. Active workflow state remains under `runs/{ticketKey}/`.

## Totals

- Sources: {sourceCount}
- Tickets: {ticketCount}
- Files: {fileCount}
- Bytes: {byteCount}

## Imported Runs

| Source | Ticket | Files | Bytes | Path |
|---|---|---:|---:|---|
| {sourceSlug} | {ticketKey} | {fileCount} | {byteCount} | `{archivePath}` |

## Migration Manifests

- `{manifestPath}`
```

## migration-manifest-{timestamp}.json

```json
{
  "schemaVersion": "1.0.0",
  "tool": "portable-jira-flow legacy artifact migration",
  "command": "copy",
  "generatedAt": "{generatedAt}",
  "dryRun": false,
  "targetRoot": "{portableStateRoot}",
  "legacyArchiveRoot": "{portableStateRoot}/legacy-runs",
  "migrationManifestRoot": "{portableStateRoot}/migration-manifests",
  "summary": {
    "sourceCount": 1,
    "ticketCount": 1,
    "fileCount": 1,
    "byteCount": 1,
    "skippedCount": 0,
    "copied": 1,
    "unchanged": 0,
    "conflictCount": 0
  },
  "sources": [
    {
      "label": "{sourceSlug}",
      "sourceRoot": "{legacyRunsRoot}",
      "ticketCount": 1,
      "fileCount": 1,
      "byteCount": 1,
      "skipped": [],
      "tickets": [
        {
          "ticketKey": "{ticketKey}",
          "sourcePath": "{legacyRunsRoot}/{ticketKey}",
          "targetPath": "{portableStateRoot}/legacy-runs/{sourceSlug}/{ticketKey}",
          "fileCount": 1,
          "byteCount": 1,
          "skipped": [],
          "files": [
            {
              "relativePath": "run.json",
              "bytes": 1,
              "sha256": "{sha256}",
              "modifiedAt": "{modifiedAt}"
            }
          ]
        }
      ]
    }
  ],
  "copy": {
    "copied": 1,
    "unchanged": 0,
    "conflictCount": 0,
    "conflicts": []
  }
}
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
- Parent: {parentTicket}
- Relationship: standalone / defect / follow-up

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

## relationship-map.md

```markdown
# Relationship Map

Rendered from: run.json.relationships

## Ticket
{ticketKey}

## Relationship
- Type: standalone / defect / follow-up
- Parent: {parentTicket}
- Branch owner: {branchOwnerTicket}
- Workspace owner: {workspaceOwnerTicket}
- Shared branch: yes/no
- Shared workspace: yes/no

## Branch
- Expected: {expectedBranch}
- Actual: {actualBranch}
- Target base: {targetBase}
- Base refresh: not_requested / pending / complete / blocked / failed / skipped

## Child Tickets
| Ticket | Summary | Status | Run |
|---|---|---|---|
| {childTicket} | {summary} | {status} | {runPath} |

## Warnings
{warnings}
```

## base-refresh.md

```markdown
# Base Refresh

Rendered from: run.json.relationships.branch.baseRefresh

## Ticket
{ticketKey}

## Relationship
- Type: {relationshipType}
- Parent: {parentTicket}
- Branch owner: {branchOwnerTicket}

## Refresh
- Strategy: merge
- Base ref: {baseRef}
- Worktree: {worktreePath}
- Command: {command}
- Status: not_requested / pending / complete / blocked / failed / skipped
- Updated: {updatedAt}

## Result
{result}

## Warnings
{warnings}
```

## optimization-plan.md

```markdown
# Optimization Plan

## Hypothesis
{bottleneckHypothesis}

## Candidate Change
{candidateChange}

## Correctness Risk
{correctnessRisk}

## Measurement Plan
{measurementPlan}

## Regression Guard
{regressionGuard}
```

## performance-baseline.md

```markdown
# Performance Baseline

## Target
{target}

## Metrics
{metrics}

## Method
{method}

## Status
not_configured / pending / complete / blocked / skipped

## Warnings
{warnings}
```

## performance-comparison.md

```markdown
# Performance Comparison

## Target
{target}

## Before
{beforeMetrics}

## After
{afterMetrics}

## Delta
{delta}

## Verdict
improved / no_regression / regressed / inconclusive / not_configured

## Warnings
{warnings}
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

## Relationship
{relationship}

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

## implementation-summary.md

```markdown
# Implementation Summary

Rendered from: run.json.stages.implementation

## Ticket
{ticketKey}

## Changed Files
| Repository | Path | Change |
|---|---|---|
| {repo} | {path} | {change} |

## Change Notes
{changeNotes}

## Repositories
{repositories}

## Relationship
{relationship}

## Validation
{validation}
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

## Evidence Scenarios
{evidenceScenarios}

## Proof Artifact Plan
- Canonical video: one narrative browser session from login through final acceptance evidence
- Canonical screenshot: verification-screenshot-{ticketKey}.png at the clearest proof moment
- Supplemental diagnostics: extra videos, screenshots, traces, reports, and logs only when unavoidable

## Blockers
{blockers}
```

## reproduction-evidence.md

```markdown
# Reproduction Evidence

Rendered from: run.json.evidence.reproduction

## Ticket
{ticketKey}

## Policy
- Required: yes/no
- Missing policy: warn/block/off
- Status: pending/in_progress/complete/blocked/failed/skipped/not_requested

## Capture
- Phase: reproduction
- Environment: {environment}
- Command: {command}
- Output directory: {evidenceOutputDir}
- Updated: {updatedAt}

## Artifacts
| Artifact | Path | Exists | Timestamp | Notes |
|---|---|---:|---|---|
| {artifactName} | {path} | yes/no | {timestamp} | {notes} |

## Reproduction Notes
{notes}

## Warnings
{warnings}
```

## verification-evidence.md

```markdown
# Verification Evidence

Rendered from: run.json.evidence.verification

## Ticket
{ticketKey}

## Policy
- Required: yes/no
- Missing policy: warn/block/off
- Status: pending/in_progress/complete/blocked/failed/skipped/not_requested

## Capture
- Phase: verification
- Environment: {environment}
- Command: {command}
- Output directory: {evidenceOutputDir}
- Updated: {updatedAt}

## Canonical Proof
| Artifact | Path | Exists | Timestamp | Notes |
|---|---|---:|---|---|
| verificationVideo | {verificationVideoPath} | yes/no | {timestamp} | single narrative session from login through proof |
| verificationScreenshot | {verificationScreenshotPath} | yes/no | {timestamp} | clearest proof moment |

## Artifacts
| Artifact | Path | Exists | Timestamp | Notes |
|---|---|---:|---|---|
| {artifactName} | {path} | yes/no | {timestamp} | {notes} |

## Validation Notes
{notes}

## Warnings
{warnings}
```

## evidence-manifest.json

```json
{
  "schemaVersion": "1.0.0",
  "ticketKey": "{ticketKey}",
  "generatedAt": "{generatedAt}",
  "policy": {
    "enabled": true,
    "storage": "central",
    "missingPolicy": "warn",
    "requireReproductionForTicketTypes": ["bug", "regression", "production-bug", "hotfix"]
  },
  "phases": {
    "reproduction": {
      "required": false,
      "status": "not_requested",
      "environment": "local",
      "command": null,
      "outputDir": "{evidenceOutputDir}",
      "artifacts": [],
      "warnings": [],
      "updatedAt": null
    },
    "verification": {
      "required": false,
      "status": "not_requested",
      "environment": "local",
      "command": null,
      "outputDir": "{evidenceOutputDir}",
      "artifacts": [],
      "warnings": [],
      "updatedAt": null
    }
  }
}
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

## Evidence
{evidence}

## Relationship
{relationship}

## Acceptance Criteria Coverage
{coverage}

## Publish Blockers
{blockers}
```

## mr-description.md

MR descriptions are reviewer-facing overviews. Keep local command execution, local testing, browser automation/evidence tooling, log paths, screenshots, videos, traces, and local URLs out of the MR body unless the user explicitly requests them there.

```markdown
# {ticketKey}: {summary}

## Overview
{implementationDetails}

## Acceptance Coverage
{acceptanceCriteriaCoverage}

## Risk
{riskLevel}

## Rollback / Deployment Notes
{rollbackPlan}

{deploymentNotes}

## Notes
{notes}
```

## mr-bug-description.md

Selected via `publishing.descriptionTemplateByTicketType` for bug-like ticket types (see `references/publishing.md`). Same reviewer-facing content rules as `mr-description.md`, plus root cause and impact.

```markdown
# {ticketKey}: {bugSummary}

## Overview
{fixSummary}

## Root Cause
{rootCause}

## Impact
- Affected workflow: {affectedWorkflow}
- Affected users: {affectedUsers}
- Severity: {severity}
- Priority: {priority}

## Acceptance Coverage
{acceptanceCriteriaCoverage}

## Risk
{riskLevel}

## Rollback / Deployment Notes
{rollbackPlan}

{deploymentNotes}
```

## mr-performance-description.md

Selected via `publishing.descriptionTemplateByTicketType` for performance-like ticket types (see `references/publishing.md` and `references/performance.md`). Same reviewer-facing content rules as `mr-description.md`, plus before/after metrics and regression guard. Keep raw profiler/benchmark tool output out of the MR body; summarize the headline metrics only.

```markdown
# {ticketKey}: {summary}

## Overview
{implementationDetails}

## Baseline (Before)
{performanceBaseline}

## Bottleneck
{bottleneck}

## Optimization Approach
{optimizationApproach}

## After Metrics
{performanceComparison}

## Regression Guard
{regressionGuard}

## Acceptance Coverage
{acceptanceCriteriaCoverage}

## Risk
{riskLevel}

## Rollback / Deployment Notes
{rollbackPlan}

{deploymentNotes}
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

## Evidence
{evidence}

## Relationship
{relationship}

## Publish Status
{publishStatus}

## Risk
{risk}

## Artifacts
{artifactIndex}

## Next Action
{nextAction}
```
