# V2 Command Reference

V2 keeps the stable command model and adds behavior-contract state to the existing stages. Do not introduce new ticket commands until repeated use shows that a separate command is worth the extra surface area.

## MVP Commands

| Command | V2 behavior |
|---|---|
| `doctor` | Validates merged runtime config using the shared loader, then checks v2 schemas and optional `workflowV2` profile keys. It is read-only and reports structural facts only. |
| `inspect <ticket>` | Reads ticket/source context through the selected profile, drafts or selects `behavior-spec.md`, records requirement/scenario placeholders, provenance, unresolved decisions, and the spec digest in v2 `run.json`. |
| `status <ticket>` | Reads v2 `run.json`, reports spec digest, scenario coverage state, stale inputs, blockers, and next action. It does not run stages. |

## Later Commands

| Command | V2 addition |
|---|---|
| `start <ticket>` | Pins the selected spec digest alongside workspace, branch, base SHA, and baseline inputs. |
| `implement <ticket>` | Requires a selected behavior spec unless overridden by policy. Meaningful edits trace to a requirement, scenario, assumption, or technical constraint. |
| `verify <ticket>` | Records actual assertion results by scenario ID and keeps expected behavior independent from implementation outcome. |
| `publish <ticket>` | Adds spec/code/test consistency and stale-digest checks to the existing committed-HEAD gates. |
| `ready <ticket> <environment>` | Reuses scenario IDs for read-only readiness and QA guide generation. |
| `accept <ticket> <environment>` | Maps configured acceptance checkpoints to scenario IDs while preserving mutation gates. |
| `report <ticket>` | Renders summaries from v2 `run.json` plus the selected behavior spec. |
| `cleanup <ticket>` | Cleans disposable v2 run artifacts only when retention policy allows it. Durable specs are never cleaned as run artifacts. |

V1 aliases remain compatibility inputs for v1. V2 should prefer primary command names in new output.
