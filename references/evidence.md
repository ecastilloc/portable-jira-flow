# Evidence Reference

Use this file for local before/after Playwright evidence capture, evidence manifests, media artifact registration, and evidence status in `start`, `verify`, `accept`, `publish`, `report`, and `status`.

Use `scripts/evidence.py` when a deterministic helper is useful for preparing wrapper configs, updating `run.json.evidence`, writing evidence summaries, and registering discovered media. Run configured Playwright commands separately through the normal command policy; the helper does not execute browser tests.

## Contract

Evidence is local-only, non-committable workflow output. It supports later audit and reproduction without changing Jira, Git, application environments, or generated artifacts outside the run/evidence directories.

The workflow tracks three evidence concepts:

| Field | Produced by | Purpose |
|---|---|---|
| `reproductionEvidence` | `start` | Before-implementation notes and media proving the current behavior for bug-like tickets. |
| `verificationEvidence` | `verify`; updated by `accept` | After-implementation notes and media proving the implemented behavior. |
| `evidenceManifest` | `start`, `verify`, `accept`, `report` | Machine-readable summary of captured, expected, missing, and stale evidence. |

Within `verificationEvidence`, the primary proof artifact set is exactly one canonical `verificationVideo` and one canonical `verificationScreenshot`. Register any extra videos, screenshots, traces, reports, or logs as supplemental diagnostic artifacts, not primary user-facing proof.

`inspect` writes the root-cause and reproduction plan only. It does not need to record video.

## Policy

Profiles may define:

```json
{
  "evidence": {
    "enabled": true,
    "storage": "central",
    "missingPolicy": "warn",
    "centralEvidenceRoot": null,
    "requireReproductionForTicketTypes": ["bug", "regression", "production-bug", "hotfix"]
  }
}
```

Default behavior:

- If evidence is disabled, set both evidence phases to `not_requested`.
- If evidence is enabled but not configured enough to run, record `skipped` plus warnings.
- Missing evidence warns by default. Block only when `evidence.missingPolicy` is explicitly stronger than `warn`.
- Reproduction video is required only for bug-like tickets, using `ticketTypes.bugLikeTypes` plus `evidence.requireReproductionForTicketTypes`.
- The verification proof artifact set is expected when ticket-scoped E2E is configured. Acceptance Playwright recordings may update verification evidence, but should not broaden capture solely to fill proof gaps unless explicitly allowed.

Set `centralEvidenceRoot` in an ignored local overlay when using central storage. Do not commit, upload, publish, delete, or rewrite evidence unless the user explicitly asks and the selected policy allows that exact action.

## Storage

When `evidence.storage` is `central`, store media under:

```text
{centralEvidenceRoot}/{ticketKey}/reproduction/
{centralEvidenceRoot}/{ticketKey}/verification/
```

Run-local summaries stay under:

```text
.portable-jira-flow/runs/{ticketKey}/reproduction-evidence.md
.portable-jira-flow/runs/{ticketKey}/verification-evidence.md
.portable-jira-flow/runs/{ticketKey}/evidence-manifest.json
```

Register every evidence file in `run.json.artifacts` with:

- artifact key
- absolute path or storage-root-relative path
- source root when known
- producer stage
- privacy level
- retention
- exists/missing
- generated timestamp
- freshness
- notes or warnings

## Run State

When evidence is enabled, update `run.json.evidence`:

```json
{
  "policy": {
    "enabled": true,
    "storage": "central",
    "missingPolicy": "warn",
    "requireReproductionForTicketTypes": ["bug", "regression", "production-bug", "hotfix"]
  },
  "reproduction": {
    "required": true,
    "status": "complete",
    "artifacts": [],
    "warnings": [],
    "command": "e2e-reproduction",
    "environment": "local",
    "updatedAt": "2026-01-01T00:00:00Z"
  },
  "verification": {
    "required": true,
    "status": "complete",
    "artifacts": [],
    "warnings": [],
    "command": "e2e-verification",
    "environment": "local",
    "updatedAt": "2026-01-01T00:00:00Z"
  }
}
```

Keep this object optional for historical runs. Never store credential values, cookies, raw auth URLs, private payloads, or environment file contents in evidence state.

## Start: Reproduction Evidence

`start <ticket>` captures reproduction evidence after workspace preparation and before implementation.

Procedure:

1. Confirm evidence is enabled.
2. Determine whether the classified ticket type is bug-like.
3. If reproduction evidence is not required, set `required: false` and `status: not_requested` or `skipped`.
4. If required, derive ticket-scoped scenarios from `root-cause.md`, `implementation-plan.md`, or configured reproduction commands.
5. Generate a run-local Playwright wrapper config if E2E is configured.
6. Run only configured evidence/E2E commands.
7. Discover media under the evidence output directory.
8. Register media and supporting artifacts, write `reproduction-evidence.md`, update `evidence-manifest.json`, and update `run.json`.

If the reproduction command exits nonzero but media exists and demonstrates the defect, record the status as `complete` with notes such as `captured failing behavior`. If no media exists, record `skipped`, `blocked`, or `failed` according to the reason and policy, then add a warning. If the configured E2E workspace is missing or no ticket-scoped `{specPaths}` value is available, record the command as non-runnable rather than running the entire suite.

## Verify: Verification Evidence

`verify <ticket>` captures verification evidence after implementation and validation.

When generating or adapting Playwright verification specs, prefer a single narrative browser session:

- Start at the login page before authentication, include login, navigate to the target workflow, verify every acceptance-relevant proof point, and finish after the last evidence assertion.
- Use one Playwright `page` for the proof flow whenever feasible.
- Capture exactly one canonical screenshot at the clearest proof moment showing the requirement on screen. Deliberately name it under the evidence output directory, preferably `verification-screenshot-{ticketKey}.png`, and register it as `verificationScreenshot`.
- Avoid opening extra Playwright pages or popups solely for proof, because each page can create another video.
- For links that should open in a new tab, verify `target="_blank"` and `rel` in the DOM, then verify destinations by same-page navigation, request checks, or another no-video method when that preserves the requirement.
- If extra pages, videos, or screenshots are unavoidable, keep one `verificationVideo` and one `verificationScreenshot` as canonical proof; mark all extra media as supplemental diagnostic artifacts.

Procedure:

1. Generate or refresh `manual-validation-steps.md`.
2. Resolve ticket-scoped E2E specs from `manual-validation-steps.md` and profile E2E settings.
3. Generate a run-local Playwright wrapper config for phase `verification`.
4. Run the configured command using `{specPaths}`, `{playwrightConfigPath}`, `{evidencePhase}`, `{evidenceOutputDir}`, `{ticketKey}`, and `{environment}` placeholders.
5. Discover videos, screenshots, traces, logs, and generated reports under the evidence output directory.
6. Register exactly one canonical `verificationVideo` and one canonical `verificationScreenshot` as primary proof. Register all other discovered files as supplemental diagnostics.
7. Update `run.json.evidence.verification`, `verification-evidence.md`, and `evidence-manifest.json`.

A failing verification command remains a validation failure or blocker when appropriate, but captured media must still be registered. Missing canonical verification video or screenshot warns by default.

## Accept: Environment Recordings

`accept <ticket> <environment>` may update verification evidence when configured acceptance commands produce Playwright media.

- Without `--allow-mutations`, do not run mutating acceptance checkpoints just to capture evidence.
- With `--allow-mutations`, capture only ticket-scoped checkpoints already allowed by the acceptance contract.
- Register existing acceptance recordings as verification evidence with the named environment.
- Preserve pre-state, cleanup, and restore notes in `environment-acceptance-{environment}.md`.
- Do not broaden the scenario set beyond `manual-validation-steps.md` or configured acceptance commands.

## Playwright Wrapper Config

When E2E is enabled, generate wrapper configs under the run folder, for example:

```text
.portable-jira-flow/runs/{ticketKey}/playwright-evidence-{evidencePhase}.config.cjs
```

The wrapper should extend the configured base Playwright config when one exists, then force local artifact capture:

- output directory: `{evidenceOutputDir}`
- video: `on`
- screenshots: `only-on-failure`
- traces: `retain-on-failure`

Profiles may set `e2e.basePlaywrightConfig` relative to `e2e.workspacePath`.
When that key is absent, the evidence helper may auto-detect a require-compatible
`playwright.config.js` or `playwright.config.cjs` in the E2E workspace. If only a
non-CommonJS config is present, pass a compatible config explicitly instead of
guessing.
When the base config uses relative paths such as `testDir`, the generated wrapper
must preserve those paths relative to the base config directory.

Keep automatic screenshots at `only-on-failure`; the proof screenshot should be an explicit `page.screenshot()` at the chosen proof moment so the verification run has one deliberate canonical screenshot instead of broad ambient screenshot capture.

Run command templates may use:

| Placeholder | Meaning |
|---|---|
| `{ticketKey}` | Original ticket key. |
| `{environment}` | Evidence target environment, commonly `local` for `verify`. |
| `{specPaths}` | Shell-safe ticket-scoped spec path list. |
| `{evidencePhase}` | `reproduction` or `verification`. |
| `{evidenceOutputDir}` | Evidence phase output directory. |
| `{playwrightConfigPath}` | Generated wrapper config path. |

Do not add project-specific paths or private command values to public config. Put them in local overlays.

## Publish, Report, And Status

`publish`, `report`, and `status` should include:

- policy: enabled/disabled, missing policy, and reproduction requirement rule
- reproduction evidence status and warnings
- verification evidence status and warnings
- current, stale, missing, or externally stored artifact status
- media paths or storage-root-relative paths
- freshness checks against implementation, validation, committed HEAD, and environment acceptance timestamps

Under the default `warn` policy, missing evidence does not block publish/report/status. It must still be visible as an audit warning and appear in `nextAction` when it is the most useful next step.

## Security

- Treat evidence media as private.
- Do not expose evidence outside configured artifact roots.
- Do not follow symlinks or path traversal outside configured roots when reading, indexing, or serving media.
- Redact terminal output and URLs before writing evidence notes.
- Preserve central evidence and current run-local summaries during cleanup unless the user explicitly requests evidence cleanup.
