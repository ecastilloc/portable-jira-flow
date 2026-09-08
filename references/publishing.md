# Publishing Reference

Read this file only for `publish`, pre-publish validation, commit, push, or future PR/MR work.

## Explicit Publishing

Publishing is never implied by `inspect`, `start`, `implement`, `verify`, `ready`, `accept`, `report`, `status`, `abc`, `--commit`, or pre-publish validation. Draft PR/MR creation requires explicit user intent such as:

```text
portable-jira-flow publish ABC-123 --publish-draft-mr
```

or another configured explicit publish flag.

## Commit Rules

Commit only when:

- the user explicitly requests commit
- the selected profile allows commits for the affected repository
- there are relevant ticket changes
- no blocking readiness, validation, or policy gate remains
- generated non-committable artifacts are excluded

Use configured commit message templates. For parent-ticket branch reuse, branch naming may use the parent ticket, but commit attribution remains on the current ticket unless config says otherwise. See `references/relationships.md` for defect child branch/workspace ownership.

## Pre-Publish Validation

Pre-publish validation checks the committed local HEAD before any push or draft PR/MR creation.

Required evidence:

- repository, branch, commit SHA, and commit message
- changed files in the committed HEAD
- post-commit dirty state separated from validated changes
- configured local commands and outcomes
- ticket-scoped E2E status when configured
- reproduction and verification evidence status when configured
- generated specs status: existing, created, updated, stale, missing, skipped
- QA video artifact status when configured
- missing evidence warnings or explicit evidence waivers
- local service reachability when required
- acceptance criteria coverage
- blockers, skipped checks, and final verdict

Verdicts:

- `Pre-Publish Validation Passed`
- `Pre-Publish Validation Failed`
- `Blocked`

If a required command fails, classify the failure as ticket-related, pre-existing, unrelated, flaky, blocked, or skipped. Do not silently pass based on code inspection.

Evidence status participates in the pre-publish report. Under the default evidence policy, missing reproduction or verification media is an audit warning, not a publish blocker. Block only when the selected profile explicitly sets a blocking evidence policy or when missing generated E2E specs are tracked deliverables that must be committed before publish.

## Generated Specs After Commit

When pre-publish validation creates or updates tracked E2E specs after commit:

- record them as post-commit changes
- do not treat them as part of the validated committed HEAD
- block publishing until the user commits them and reruns validation

If the selected profile marks generated specs as disposable isolated validation artifacts, record them as non-committable artifacts instead.

## Draft PR/MR Creation

Before draft PR/MR creation:

1. Resolve the target branch. An explicit user-requested target wins; otherwise use the provider project `targetBranch` from the selected profile. A configured project target takes precedence over the repository `baseBranch`.
2. Generate `mr-description.md` from the configured template (see "Description Template Selection" below).
3. Run required pre-publish validation and publish gates.
4. Stop if required gates fail or are blocked.
5. Verify the provider/account guard for the target repository.
6. Push only the intended branch.
7. Create a draft PR/MR through the configured provider or workflow.

Provider-specific behavior must come from config. Do not assume GitHub, GitLab, Bitbucket, reviewers, labels, project paths, or API commands.

For child defects on a shared parent branch, first look for an existing open draft/non-draft PR/MR for the parent-owned branch when the profile provides a safe provider query. If one exists and targets the configured branch, record its metadata in the child run and do not create a duplicate. If no safe query is configured, stop and ask before creating another PR/MR for the same branch.

## Description Template Selection

`publishing.descriptionTemplate` (or the legacy fragment form `references/templates.md#mr-description.md`) is the default MR/PR description template. A profile may override it per classified ticket type with `publishing.descriptionTemplateByTicketType`, a map from canonical ticket type to template path:

```json
{
  "publishing": {
    "descriptionTemplate": "references/templates.md#mr-description.md",
    "descriptionTemplateByTicketType": {
      "bug": "references/templates/mr-bug-description.md",
      "performance": "references/templates/mr-performance-description.md"
    },
    "descriptionTemplateFallback": "references/templates.md#mr-description.md"
  }
}
```

Resolve the template in this order: exact match in `descriptionTemplateByTicketType` for the classified canonical ticket type, else `descriptionTemplateFallback`, else `descriptionTemplate`. Bug-like and performance-like ticket types commonly use dedicated templates (`references/templates/mr-bug-description.md`, `references/templates/mr-performance-description.md`); everything else typically falls back to the generic `mr-description.md`. See `references/templates.md` for each template's fields.

## MR Description Content

Treat `mr-description.md` as a reviewer-facing implementation overview, not a local execution log. Unless the user explicitly asks for these details in the MR body, do not include:

- browser automation tool names, evidence tooling, screenshots, videos, traces, or browser reports
- local URLs, local services, local setup/running notes, cache/vendor readiness notes, or workstation-specific details
- local test command names, local command output, log paths, or local validation tables

Keep those details in `pre-publish-validation.md`, evidence artifacts, logs, and `run.json`. The MR overview should focus on the ticket link, what changed, acceptance coverage, risk, rollback notes, and deployment notes.

For child defects, the MR overview may mention the parent ticket and shared branch only as reviewer context. It must still focus on the current child defect's implementation and acceptance coverage.

## Target-Specific Provider Guard

Publishing identity depends on what is being published:

- For this skill repository, use `policy.skillRepositoryProvider`, or the legacy `policy.skillRepositoryGithub` / `policy.github` fallback.
- For ticket/application repositories, use the selected profile's generic provider guard, or legacy `github` guard.
- Ticket profiles may require a company account, organization, remote owner, remote host, or account domain.
- The skill-repo guard must not override a ticket repository's configured account guard.
- If the active provider identity, token handle, remote, or repository owner cannot be verified against the target guard, stop before pushing or opening PRs/MRs.

Do not run provider commands unless the user explicitly asks for publish/setup work.
