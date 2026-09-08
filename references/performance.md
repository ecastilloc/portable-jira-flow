# Performance Reference

Use this file for performance/optimization ticket handling: the optimization hypothesis, before/after measurement, regression guard, and performance status in `inspect`, `start`, `verify`, `publish`, `report`, and `status`.

Performance work is a **content-classified**, not prefix-classified, ticket type. A ticket qualifies when its classified canonical type is listed in `ticketTypes.performanceLikeTypes` (see "Ticket Type Classification" in `references/configuration.md`), which is normally driven by Jira issue-type aliases plus keyword/summary/parent-epic signals in `ticketTypes.detection`. Never infer performance work from the ticket key prefix.

## Contract

Performance measurement is local-only, non-committable workflow output, parallel to (but distinct from) the Playwright-based evidence described in `references/evidence.md`. It supports optimizing a slow endpoint, query, or job without changing Jira, Git, application environments, or generated artifacts outside the run directory.

The workflow tracks three performance concepts:

| Field | Produced by | Purpose |
|---|---|---|
| `optimizationPlan` | `inspect` | Hypothesis, candidate change, correctness risk, measurement plan, and regression guard plan for performance-like tickets. |
| `performanceBaseline` | `start` | Before-implementation measurement of the current, unoptimized behavior. |
| `performanceComparison` | `verify` | After-implementation measurement compared against the baseline, with a verdict. |

`inspect` writes the optimization plan only. It does not run benchmark commands.

## Policy

Profiles may define:

```json
{
  "ticketTypes": {
    "performanceLikeTypes": ["performance"],
    "performance": {
      "attemptLocalBaseline": true,
      "stopIfNoBaselineCommand": false,
      "metrics": ["responseTimeMs", "queryCount", "payloadBytes"],
      "regressionThresholds": {}
    }
  }
}
```

Default behavior:

- If the classified ticket type is not in `ticketTypes.performanceLikeTypes`, skip all three stages below and set their status to `not_requested`.
- Baseline and comparison measurement run only through `commands[]` entries tagged `"stage": "performanceBaseline"` or `"stage": "performanceComparison"` for the active repo — the same mechanism used for `validation` commands (see "Commands" in `references/configuration.md`). Do not invent ad hoc benchmark commands.
- If no such command is configured, record `not_configured` plus a warning. This is expected and common until a profile wires in a real profiling/benchmark tool; it never blocks `start`, `verify`, or `publish` under the default `warn` missing-policy.
- `regressionThresholds` (per metric, e.g. `{"responseTimeMs": 10}` meaning "no more than 10% slower") are optional. Without them, the comparison stage still reports raw before/after numbers and a qualitative verdict, but cannot fail a specific numeric threshold.

## Storage

Run-local artifacts stay under:

```text
.portable-jira-flow/runs/{ticketKey}/optimization-plan.md
.portable-jira-flow/runs/{ticketKey}/performance-baseline.md
.portable-jira-flow/runs/{ticketKey}/performance-comparison.md
```

Register each in `run.json.artifacts` the same way as other derived artifacts: artifact key, path, producer stage, privacy level, retention, exists/missing, generated timestamp, freshness, notes or warnings.

## Run State

When the classified ticket type is performance-like, update `run.json.performance`:

```json
{
  "policy": {
    "performanceLikeTypes": ["performance"],
    "metrics": ["responseTimeMs", "queryCount", "payloadBytes"],
    "regressionThresholds": {}
  },
  "baseline": {
    "required": true,
    "status": "complete",
    "command": "endpoint-baseline-timing",
    "measurements": {},
    "warnings": [],
    "updatedAt": "2026-01-01T00:00:00Z"
  },
  "comparison": {
    "required": true,
    "status": "complete",
    "command": "endpoint-comparison-timing",
    "measurements": {},
    "delta": {},
    "verdict": "improved",
    "warnings": [],
    "updatedAt": "2026-01-01T00:00:00Z"
  }
}
```

Keep this object optional for historical runs and absent entirely for non-performance tickets. Never store credential values, cookies, or raw auth URLs in performance state.

## Inspect: Optimization Plan

For tickets classified as performance-like, `inspect` writes `optimization-plan.md` instead of (or, for a hybrid ticket, alongside) `root-cause.md`. Cover:

- **Hypothesis**: the suspected bottleneck (e.g. full entity hydration, N+1 queries, missing index, oversized serialization).
- **Candidate Change**: the smallest change likely to resolve it, and what existing behavior must be preserved.
- **Correctness Risk**: what could break if the response shape, contract, or side effects change.
- **Measurement Plan**: what to compare before/after (same account/data/environment), and which metrics from `ticketTypes.performance.metrics` apply.
- **Regression Guard**: what test coverage should protect the optimized path going forward.

If the ticket lacks a measurable target (no defined p95/p99, no baseline), say so explicitly rather than inventing one — this is a normal, expected gap to surface, not a blocker.

## Start: Performance Baseline

`start <ticket>` captures a performance baseline after workspace preparation and before implementation, when the classified ticket type is performance-like per `ticketTypes.performanceLikeTypes`.

Procedure:

1. Confirm the ticket type is performance-like; otherwise set `required: false`, `status: not_requested`.
2. Resolve the target (endpoint, query, job) from `optimization-plan.md`.
3. Look up `commands[]` entries for the active repo tagged `"stage": "performanceBaseline"`.
4. If none exist, record `status: not_configured` with a warning and continue — do not block `start`.
5. If configured, substitute the `{performanceTarget}` placeholder in the command with the target resolved in step 2 (e.g. `/api/tech-clock/today?timeclockVersion=2`), run only that command, capture the metrics named in `ticketTypes.performance.metrics`, and write `performance-baseline.md` plus `run.json.performance.baseline`.

## Verify: Performance Comparison

`verify <ticket>` captures the after-implementation measurement and compares it to the baseline, when the classified ticket type is performance-like.

Procedure:

1. Look up `commands[]` entries for the active repo tagged `"stage": "performanceComparison"`.
2. If none exist (or no baseline was captured), record `status: not_configured` or `blocked` with a warning; validation/verify still completes.
3. If configured, substitute the same `{performanceTarget}` value used for the baseline, and run only that command under the same conditions used for the baseline (same account/data/environment where feasible).
4. Compute the delta per metric and compare against `ticketTypes.performance.regressionThresholds` when set.
5. Record a verdict: `improved`, `no_regression`, `regressed`, or `inconclusive`. A `regressed` verdict against a configured threshold is a validation failure, classified like any other (`ticket-related`, `pre-existing`, `unrelated`, `flaky`, `blocked`, `skipped`); without a configured threshold, treat it as a warning surfaced in the report, not a hard failure.
6. Write `performance-comparison.md` and update `run.json.performance.comparison`.

## Publish, Report, And Status

`publish`, `report`, and `status` should include, when `run.json.performance` exists:

- whether the ticket type was performance-like
- baseline and comparison status and warnings
- headline before/after metrics and verdict
- `not_configured` state when no benchmark command exists — this is an audit warning, not a publish blocker, under the default policy

## Security

- Treat measurement output the same as other internal artifacts: no credentials, cookies, or raw auth URLs in recorded commands or notes.
- Do not run mutating or destructive commands to obtain a measurement; baseline/comparison commands must be `mutability: read-only` (or an explicitly allowed low-risk local-disposable mutation) per `references/configuration.md` "Commands".
