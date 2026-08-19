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

Use configured commit message templates. For parent-ticket branch reuse, branch naming may use the parent ticket, but commit attribution remains on the current ticket unless config says otherwise.

## Pre-Publish Validation

Pre-publish validation checks the committed local HEAD before any push or draft PR/MR creation.

Required evidence:

- repository, branch, commit SHA, and commit message
- changed files in the committed HEAD
- post-commit dirty state separated from validated changes
- configured local commands and outcomes
- ticket-scoped E2E status when configured
- generated specs status: existing, created, updated, stale, missing, skipped
- QA video artifact status when configured
- local service reachability when required
- acceptance criteria coverage
- blockers, skipped checks, and final verdict

Verdicts:

- `Pre-Publish Validation Passed`
- `Pre-Publish Validation Failed`
- `Blocked`

If a required command fails, classify the failure as ticket-related, pre-existing, unrelated, flaky, blocked, or skipped. Do not silently pass based on code inspection.

## Generated Specs After Commit

When pre-publish validation creates or updates tracked E2E specs after commit:

- record them as post-commit changes
- do not treat them as part of the validated committed HEAD
- block publishing until the user commits them and reruns validation

If the selected profile marks generated specs as disposable isolated validation artifacts, record them as non-committable artifacts instead.

## Draft PR/MR Creation

Before draft PR/MR creation:

1. Generate `mr-description.md` from the configured template.
2. Run required pre-publish validation and publish gates.
3. Stop if required gates fail or are blocked.
4. Verify the provider/account guard for the target repository.
5. Push only the intended branch.
6. Create a draft PR/MR through the configured provider or workflow.

Provider-specific behavior must come from config. Do not assume GitHub, GitLab, Bitbucket, reviewers, labels, project paths, or API commands.

## Target-Specific Provider Guard

Publishing identity depends on what is being published:

- For this skill repository, use `policy.skillRepositoryProvider`, or the legacy `policy.skillRepositoryGithub` / `policy.github` fallback.
- For ticket/application repositories, use the selected profile's generic provider guard, or legacy `github` guard.
- Ticket profiles may require a company account, organization, remote owner, remote host, or account domain.
- The skill-repo guard must not override a ticket repository's configured account guard.
- If the active provider identity, token handle, remote, or repository owner cannot be verified against the target guard, stop before pushing or opening PRs/MRs.

Do not run provider commands unless the user explicitly asks for publish/setup work.
