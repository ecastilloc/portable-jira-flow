# Relationship Reference

Use this file when a ticket is a parent, defect, follow-up, or child ticket, or when invocation flags such as `--parent`, `--parent-ticket`, `--parent-branch`, `--use-parent-branch`, or `--no-parent-branch` are present.

Parent/child behavior is optional. Regular standalone tickets must keep the existing branch, workspace, artifact, evidence, publish, and report behavior unless a relationship is explicitly provided or safely discovered from configured Jira fields.

## Contract

The workflow tracks relationship context in `run.json.relationships`. This object is optional for older runs. When it is absent, treat the ticket as standalone.

```json
{
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
}
```

`relationshipType` values:

- `standalone`: the ticket owns its branch, workspace, and artifacts.
- `defect`: the ticket is a child defect of a parent ticket and may reuse the parent branch/workspace when policy allows it.
- `follow-up`: the ticket is linked to a parent or predecessor, but keeps its own branch/workspace unless policy explicitly says otherwise.

For defects, the child ticket owns its audit artifacts while the parent ticket may own the branch and workspace:

```json
{
  "relationshipType": "defect",
  "parentTicket": {
    "key": "ABC-100",
    "summary": "Parent feature summary",
    "source": "jira.parent",
    "runPath": "{runsRoot}/ABC-100",
    "exists": true
  },
  "branchOwnerTicket": "ABC-100",
  "workspaceOwnerTicket": "ABC-100",
  "sharedBranch": true,
  "sharedWorkspace": true
}
```

## Discovery

Resolve relationship intent in this order:

1. Explicit flags: `--parent <ticket>`, `--parent-ticket <ticket>`, `--parent-branch <branch>`, `--use-parent-branch`, or `--no-parent-branch`.
2. Existing `run.json.relationships`.
3. Configured Jira fields such as `fields.parent.key`, `fields.parent.fields.key`, and configured issue links.
4. Legacy profile compatibility keys such as `branching.parentTicketBranching`.

Do not infer a defect relationship from ticket key prefix alone. A Jira issue type alias such as `Defect`, an explicit `--parent`, or a configured relationship signal may mark the relationship type as `defect`. If signals conflict, keep the ticket standalone or `follow-up`, record an open question, and do not reuse the parent branch automatically.

## Profile Config

Profiles may define:

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

Public examples must stay generic. Machine-specific ticket prefixes, branch names, paths, and provider conventions belong in ignored local overlays. For compatibility, a profile may still have `branching.parentTicketBranching`; when `relationships` is absent, treat that legacy key as relationship policy input but write new state to `run.json.relationships`.

## Inspect

`inspect <ticket>` is read-only.

For relationship-aware tickets:

1. Fetch configured Jira relationship fields.
2. Resolve `relationshipType`, `parentTicket`, and any configured parent summary/status fields.
3. Determine the branch/workspace owner ticket without creating or switching workspaces.
4. Write `run.json.relationships`.
5. Write `relationship-map.md`.
6. Include relationship context in `context.md`, `implementation-plan.md`, and `nextAction`.

If a defect requires a parent and no parent is discoverable, keep the ticket standalone or blocked according to profile policy. The default is `standalone-with-warning`, not an automatic branch reuse guess.

## Start

`start <ticket>` may prepare/reuse workspaces and branches. It must not edit application code.

For a defect with allowed parent branch/workspace reuse:

1. Load the child run and parent run when available.
2. Confirm the parent ticket key is known and matches the explicit flag or Jira relationship.
3. Resolve `{branchTicketKey}` to the parent ticket key and `{ticketKey}` to the child ticket key.
4. Resolve the active workspace from `workspaceOwnerTicket`, normally the parent ticket.
5. Confirm the expected parent branch exists locally or remotely according to profile policy.
6. Stop if the expected parent branch is attached to a different worktree.
7. Stop if the selected worktree is dirty and the dirty strategy cannot safely preserve user work.
8. Fetch the configured base ref when `baseRefresh.fetchRemote` is true.
9. Merge the configured base ref into the active parent branch only when `baseRefresh.strategy` is `merge` and the profile allows the operation for this relationship type.
10. Stop on merge conflicts and record `base-refresh.md` plus blockers.
11. Record branch/workspace ownership in `run.json.relationships`, `workspace-map.md`, `worktree-safety.md`, and `base-refresh.md`.
12. Continue with normal reproduction evidence capture for bug-like child tickets before any code edits.

If the user passes `--no-parent-branch`, keep a child-owned branch/workspace and record the parent only as audit context.

## Implement

`implement <ticket>` edits code only for the current ticket after readiness permits it.

For defect tickets on a shared parent branch:

- Attribute `run.json.stages.implementation.filesChanged` to the child ticket.
- Keep implementation notes focused on the defect.
- Record the shared branch and workspace owner in `implementation-summary.md`.
- Do not copy parent artifacts into the child run.
- Do not treat parent ticket implementation notes as child source of truth.

## Verify, Accept, And Evidence

Validation and evidence remain ticket-scoped:

- Use the active shared workspace when `workspaceOwnerTicket` is the parent.
- Generate `manual-validation-steps.md` for the child defect.
- Store child evidence under the child ticket key.
- Keep the parent evidence unchanged unless the user explicitly runs a parent command.
- Record warnings if the child has no independent validation or evidence.

`accept` may register environment recordings as child verification evidence when the acceptance checkpoints are for the child ticket.

## Publish

Publishing remains explicit.

For defect tickets on a shared parent branch:

1. Validate the committed shared branch HEAD.
2. Confirm commits relevant to the child defect are present or recorded.
3. Reuse an existing parent-branch MR/PR when provider metadata proves it targets the expected branch, or stop and ask.
4. Do not create duplicate MRs for the same shared branch unless the user explicitly requests that exact action and policy allows it.
5. Generate the child ticket `mr-description.md` as reviewer-facing defect context only; local workflow details stay in artifacts.
6. Record MR metadata in the child run so audit tools can connect the child artifact set to the shared branch/MR.

Commit attribution remains on the current ticket unless config explicitly says otherwise.

## Report And Status

`report` and `status` must include:

- relationship type
- parent ticket key and parent run availability
- branch owner and workspace owner
- actual and expected branch
- base refresh status
- child ticket artifact status
- relationship warnings and blockers

For parent tickets, include known child tickets when they are listed in `run.json.relationships.childTickets` or discoverable from sibling runs. Do not rewrite a parent run just because a child run exists unless the user explicitly asks to refresh parent artifacts.

## Portal Indexing

Audit portals should treat `run.json.relationships` as authoritative when present.

Recommended display:

- Dashboard filter: standalone, parent, defect, follow-up, shared branch.
- Group child defects under the parent ticket when both are indexed.
- Ticket breadcrumbs: `Dashboard / {projectOrSource} / {parentTicket} / {currentTicket}`.
- Parent detail view: show related child tickets.
- Child detail view: keep child artifacts primary and show parent/shared branch context nearby.

Historical runs without `relationships` remain valid standalone tickets.
