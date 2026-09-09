"""Planning gate for portable-jira-flow v2 behavior contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pjf.contracts import ContractError
from pjf.state_writer import write_json_atomic
from pjf.v2_contracts import digest_text, now_iso, upsert_artifact
from pjf.v2_specify import artifact_record, canonical_digest, status_freshness


BLOCKING_DECISION_KINDS = {
    "contradiction",
    "missing_goal",
    "missing_source",
    "nfr_acceptance",
    "unknown_expected_result",
}


def _resolve_artifact_path(run_dir: Path, path_text: str | None, fallback_name: str) -> Path:
    path = Path(path_text) if path_text else Path(fallback_name)
    if not path.is_absolute():
        path = run_dir / path
    return path.expanduser().resolve()


def _read_json(path: Path, name: str) -> dict[str, Any]:
    if not path.exists():
        raise ContractError(f"{name}: missing required artifact {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"{name}: invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(f"{name}: expected object in {path}")
    return data


def _source_pack_digest(source_pack: dict[str, Any]) -> str:
    digest_input = [
        {
            "sourceId": source.get("sourceId"),
            "kind": source.get("kind"),
            "authority": source.get("authority"),
            "pathOrLocator": source.get("pathOrLocator"),
            "revision": source.get("revision"),
            "digest": source.get("digest"),
            "content": source.get("content"),
        }
        for source in source_pack.get("sources") or []
    ]
    return canonical_digest(digest_input)


def _facts_digest(facts: dict[str, Any]) -> str:
    return canonical_digest({key: value for key, value in facts.items() if key not in {"generatedAt", "digest"}})


def _spec_digest(spec: dict[str, Any]) -> str:
    return canonical_digest({key: value for key, value in spec.items() if key != "digest"})


def _load_required_artifacts(run_dir: Path, state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path, Path, Path, Path]:
    spec_state = state.get("behaviorSpec") or {}
    source_pack_path = _resolve_artifact_path(run_dir, spec_state.get("sourcePackPath"), "source-pack.json")
    facts_path = _resolve_artifact_path(run_dir, spec_state.get("factsPath"), "behavior-facts.json")
    spec_json_path = _resolve_artifact_path(run_dir, spec_state.get("contractPath"), "behavior-spec.json")
    spec_md_path = _resolve_artifact_path(run_dir, spec_state.get("path"), "behavior-spec.md")

    source_pack = _read_json(source_pack_path, "source-pack")
    facts = _read_json(facts_path, "behavior-facts")
    spec = _read_json(spec_json_path, "behavior-spec")
    if not spec_md_path.exists():
        raise ContractError(f"behavior-spec.md: missing required artifact {spec_md_path}")
    return source_pack, facts, spec, source_pack_path, facts_path, spec_json_path, spec_md_path


def _artifact_staleness(
    *,
    state: dict[str, Any],
    source_pack: dict[str, Any],
    facts: dict[str, Any],
    spec: dict[str, Any],
    spec_md_path: Path,
) -> dict[str, Any]:
    spec_state = state.get("behaviorSpec") or {}
    markdown_digest = digest_text(spec_md_path.read_text(encoding="utf-8"))
    source_digest = _source_pack_digest(source_pack)
    facts_digest = _facts_digest(facts)
    spec_digest = _spec_digest(spec)
    freshness = status_freshness(state)

    stale_artifacts: list[str] = []
    if source_pack.get("digest") != source_digest or spec_state.get("sourcePackDigest") != source_digest:
        stale_artifacts.append("source-pack.json")
    if facts.get("digest") != facts_digest or spec_state.get("factsDigest") != facts_digest:
        stale_artifacts.append("behavior-facts.json")
    if spec.get("digest") != spec_digest or spec_state.get("contractDigest") != spec_digest:
        stale_artifacts.append("behavior-spec.json")
    if spec_state.get("digest") != markdown_digest:
        stale_artifacts.append("behavior-spec.md")

    return {
        "sourcePackDigest": source_digest,
        "factsDigest": facts_digest,
        "behaviorSpecDigest": spec_digest,
        "behaviorSpecMarkdownDigest": markdown_digest,
        "staleSources": freshness.get("staleSources", []),
        "staleArtifacts": sorted(stale_artifacts),
        "specMarkdownStale": bool(freshness.get("specMarkdownStale") or "behavior-spec.md" in stale_artifacts),
        "specContractStale": bool(freshness.get("specContractStale") or "behavior-spec.json" in stale_artifacts),
    }


def _decision_blocks_implementation(decision: dict[str, Any]) -> bool:
    if decision.get("status") != "open_decision":
        return False
    kind = str(decision.get("kind") or "")
    if kind in BLOCKING_DECISION_KINDS:
        return True
    return "scenario" in str(decision.get("question") or "").lower()


def _scenario_title(scenario: dict[str, Any]) -> str:
    expected = str(scenario.get("expectedResult") or "").strip()
    if expected and expected != "unknown":
        return expected[:96]
    trigger = str(scenario.get("trigger") or "").strip()
    if trigger and trigger != "unknown":
        return trigger[:96]
    return str(scenario.get("id") or "scenario")


def _implementation_task(task_index: int, scenario: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    use_case_ids = [use_case.get("id") for use_case in spec.get("useCases") or [] if use_case.get("id")]
    return {
        "id": f"TASK-{task_index:03d}",
        "type": "implementation",
        "status": "planned",
        "title": f"Implement {scenario.get('id')}: {_scenario_title(scenario)}",
        "requirementIds": list(scenario.get("requirementIds") or []),
        "useCaseIds": use_case_ids[:1],
        "scenarioIds": [scenario.get("id")],
        "sourceRefs": list(scenario.get("sourceRefs") or []),
        "preconditions": list(scenario.get("preconditions") or []),
        "trigger": scenario.get("trigger"),
        "expectedResult": scenario.get("expectedResult"),
        "successGuarantee": scenario.get("successGuarantee"),
        "failureGuarantee": scenario.get("failureGuarantee"),
        "coverageRequired": bool(scenario.get("required")),
        "verificationIntent": "Add or update verification that proves this scenario by ID before publish.",
    }


def _decision_task(task_index: int, decision: dict[str, Any]) -> dict[str, Any]:
    blocks = _decision_blocks_implementation(decision)
    return {
        "id": f"DECISION-TASK-{task_index:03d}",
        "type": "decision",
        "status": "blocked" if blocks else "pending",
        "title": str(decision.get("question") or "Resolve open behavior decision."),
        "decisionId": decision.get("id"),
        "decisionKind": decision.get("kind"),
        "sourceRefs": list(decision.get("sourceRefs") or []),
        "blocksImplementation": blocks,
    }


def build_implementation_plan(
    *,
    ticket: str,
    profile_name: str | None,
    source_pack: dict[str, Any],
    facts: dict[str, Any],
    spec: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    contradictions = list((spec.get("provenance") or {}).get("contradictions") or facts.get("contradictions") or [])
    open_decisions = list((spec.get("provenance") or {}).get("openDecisions") or [])
    decision_tasks = [_decision_task(index, decision) for index, decision in enumerate(open_decisions, start=1)]
    blocking_decisions = [task for task in decision_tasks if task.get("blocksImplementation")]
    planned_scenarios = [scenario for scenario in spec.get("scenarios") or [] if scenario.get("status") == "planned"]
    implementation_tasks = [
        _implementation_task(index, scenario, spec) for index, scenario in enumerate(planned_scenarios, start=1)
    ]

    blockers: list[dict[str, Any]] = []
    if freshness.get("staleSources") or freshness.get("staleArtifacts"):
        blockers.append(
            {
                "kind": "stale_behavior_contract",
                "message": "Refresh specify before planning because source or behavior artifacts changed.",
                "staleSources": freshness.get("staleSources", []),
                "staleArtifacts": freshness.get("staleArtifacts", []),
            }
        )
    if contradictions:
        blockers.append(
            {
                "kind": "contradiction",
                "message": "Resolve contradictory source statements before implementation planning is ready.",
                "count": len(contradictions),
            }
        )
    if blocking_decisions:
        blockers.append(
            {
                "kind": "blocking_open_decisions",
                "message": "Resolve open behavior decisions that affect expected implementation behavior.",
                "decisionTaskIds": [task["id"] for task in blocking_decisions],
                "count": len(blocking_decisions),
            }
        )
    if not implementation_tasks:
        blockers.append(
            {
                "kind": "no_planned_scenarios",
                "message": "No planned scenarios are available to implement.",
            }
        )

    readiness_status = "blocked" if blockers else "ready"
    required_scenario_ids = list((spec.get("coverage") or {}).get("requiredScenarioIds") or [])
    planned_scenario_ids = [scenario.get("id") for scenario in planned_scenarios if scenario.get("id")]
    unknown_scenario_ids = [
        scenario.get("id") for scenario in spec.get("scenarios") or [] if scenario.get("status") == "unknown" and scenario.get("id")
    ]

    plan = {
        "schemaVersion": "1.0.0",
        "ticketKey": ticket,
        "profile": profile_name,
        "generatedAt": now_iso(),
        "selectedBehaviorSpec": {
            "status": spec.get("status"),
            "path": "behavior-spec.md",
            "contractPath": "behavior-spec.json",
            "sourcePackPath": "source-pack.json",
            "factsPath": "behavior-facts.json",
            "sourcePackDigest": freshness["sourcePackDigest"],
            "factsDigest": freshness["factsDigest"],
            "contractDigest": freshness["behaviorSpecDigest"],
            "markdownDigest": freshness["behaviorSpecMarkdownDigest"],
            "pinnedAt": now_iso(),
        },
        "readiness": {
            "status": readiness_status,
            "implementationReady": readiness_status == "ready",
            "blockers": blockers,
            "openDecisionCount": len(open_decisions),
            "blockingOpenDecisionCount": len(blocking_decisions),
            "contradictionCount": len(contradictions),
            "freshness": freshness,
        },
        "implementationTasks": implementation_tasks,
        "decisionTasks": decision_tasks,
        "coveragePlan": {
            "requiredScenarioIds": required_scenario_ids,
            "plannedScenarioIds": planned_scenario_ids,
            "unknownScenarioIds": unknown_scenario_ids,
            "summary": (spec.get("coverage") or {}).get("summary") or {},
        },
        "baselineInputs": {
            "liveJiraFetched": False,
            "workspacePrepared": False,
            "branchPrepared": False,
            "sourceAuthorityOrder": (source_pack.get("policy") or {}).get("authorityOrder", []),
        },
        "nextActions": [],
        "digestAlgorithm": "sha256",
    }
    if blockers:
        plan["nextActions"].append(
            {
                "command": f"portable-jira-flow-v2 specify {ticket}",
                "reason": "Refresh or resolve behavior contract blockers before implementation.",
                "blocked": True,
            }
        )
    else:
        plan["nextActions"].append(
            {
                "command": f"portable-jira-flow-v2 implement {ticket}",
                "reason": "Spec digests are pinned and scenario tasks are ready.",
                "blocked": False,
            }
        )
    plan["digest"] = _plan_digest(plan)
    return plan


def _plan_digest(plan: dict[str, Any]) -> str:
    stable = json.loads(json.dumps(plan, sort_keys=True))
    stable.pop("generatedAt", None)
    stable.pop("digest", None)
    selected = stable.get("selectedBehaviorSpec")
    if isinstance(selected, dict):
        selected.pop("pinnedAt", None)
    return canonical_digest(stable)


def render_implementation_plan_markdown(plan: dict[str, Any]) -> str:
    selected = plan.get("selectedBehaviorSpec") or {}
    readiness = plan.get("readiness") or {}
    coverage = plan.get("coveragePlan") or {}
    blockers = readiness.get("blockers") or []
    implementation_tasks = plan.get("implementationTasks") or []
    decision_tasks = plan.get("decisionTasks") or []

    blocker_rows = "\n".join(
        f"| {item.get('kind', '')} | {item.get('message', '')} |" for item in blockers
    ) or "| none |  |"
    implementation_rows = "\n".join(
        "| {id} | {status} | {scenarios} | {requirements} | {title} |".format(
            id=item.get("id", ""),
            status=item.get("status", ""),
            scenarios=", ".join(str(value) for value in item.get("scenarioIds") or []),
            requirements=", ".join(str(value) for value in item.get("requirementIds") or []),
            title=item.get("title", ""),
        )
        for item in implementation_tasks
    ) or "| none |  |  |  |  |"
    decision_rows = "\n".join(
        "| {id} | {status} | {blocks} | {decision} | {title} |".format(
            id=item.get("id", ""),
            status=item.get("status", ""),
            blocks="yes" if item.get("blocksImplementation") else "no",
            decision=item.get("decisionId", ""),
            title=item.get("title", ""),
        )
        for item in decision_tasks
    ) or "| none |  |  |  |  |"
    next_actions = "\n".join(
        f"- `{item.get('command')}` — {item.get('reason')}" for item in plan.get("nextActions") or []
    ) or "- none"

    return f"""# {plan.get('ticketKey')} V2 Implementation Plan

Readiness: {readiness.get('status')}
Plan digest: {plan.get('digest')}

## Pinned Behavior Contract

- Source pack digest: {selected.get('sourcePackDigest')}
- Facts digest: {selected.get('factsDigest')}
- Behavior spec digest: {selected.get('contractDigest')}
- Behavior spec markdown digest: {selected.get('markdownDigest')}

## Readiness Blockers

| Kind | Message |
|---|---|
{blocker_rows}

## Implementation Tasks

| ID | Status | Scenario IDs | Requirement IDs | Task |
|---|---|---|---|---|
{implementation_rows}

## Decision Tasks

| ID | Status | Blocks implementation | Decision ID | Question |
|---|---|---:|---|---|
{decision_rows}

## Coverage Plan

- Required scenarios: {len(coverage.get('requiredScenarioIds') or [])}
- Planned scenarios: {len(coverage.get('plannedScenarioIds') or [])}
- Unknown scenarios: {len(coverage.get('unknownScenarioIds') or [])}

## Next Actions

{next_actions}
"""


def write_plan_artifacts(
    *,
    run_dir: Path,
    ticket: str,
    profile_name: str | None,
    existing_state: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not existing_state:
        raise ContractError("run.json: missing v2 state; run portable-jira-flow-v2 specify first")
    if existing_state.get("schemaVersion") != "2.0.0" or existing_state.get("skillName") != "portable-jira-flow-v2":
        raise ContractError("run.json: expected portable-jira-flow-v2 state; v1 runs are not migrated by plan")
    if existing_state.get("ticketKey") != ticket:
        raise ContractError(f"run.json.ticketKey: expected {ticket}, got {existing_state.get('ticketKey')}")

    run_dir.mkdir(parents=True, exist_ok=True)
    source_pack, facts, spec, _, _, _, spec_md_path = _load_required_artifacts(run_dir, existing_state)
    freshness = _artifact_staleness(
        state=existing_state,
        source_pack=source_pack,
        facts=facts,
        spec=spec,
        spec_md_path=spec_md_path,
    )
    plan_data = build_implementation_plan(
        ticket=ticket,
        profile_name=profile_name,
        source_pack=source_pack,
        facts=facts,
        spec=spec,
        freshness=freshness,
    )
    markdown = render_implementation_plan_markdown(plan_data)
    markdown_digest = digest_text(markdown)

    plan_json_path = run_dir / "implementation-plan.json"
    plan_md_path = run_dir / "implementation-plan.md"
    write_json_atomic(plan_json_path, plan_data)
    plan_md_path.write_text(markdown, encoding="utf-8")

    state = dict(existing_state)
    state["updatedAt"] = now_iso()
    state.setdefault("invocation", {})["primaryCommand"] = "plan"
    state.setdefault("stages", {}).pop("start", None)
    readiness = plan_data.get("readiness") or {}
    blockers = readiness.get("blockers") or []
    stage_status = "blocked" if blockers else "complete"
    state["stages"]["plan"] = {
        "status": stage_status,
        "updatedAt": now_iso(),
        "sourcePackDigest": freshness["sourcePackDigest"],
        "factsDigest": freshness["factsDigest"],
        "behaviorSpecDigest": freshness["behaviorSpecMarkdownDigest"],
        "contractDigest": freshness["behaviorSpecDigest"],
        "implementationPlanPath": str(plan_json_path),
        "implementationPlanDigest": plan_data["digest"],
        "implementationPlanMarkdownPath": str(plan_md_path),
        "implementationPlanMarkdownDigest": markdown_digest,
        "implementationTaskCount": len(plan_data.get("implementationTasks") or []),
        "openDecisionCount": readiness.get("openDecisionCount", 0),
        "blockingOpenDecisionCount": readiness.get("blockingOpenDecisionCount", 0),
        "contradictionCount": readiness.get("contradictionCount", 0),
        "staleSources": freshness.get("staleSources", []),
        "staleArtifacts": freshness.get("staleArtifacts", []),
    }
    state["plan"] = {
        "status": readiness.get("status"),
        "path": str(plan_json_path),
        "digestAlgorithm": "sha256",
        "digest": plan_data["digest"],
        "markdownPath": str(plan_md_path),
        "markdownDigest": markdown_digest,
        "selectedBehaviorSpec": plan_data.get("selectedBehaviorSpec", {}),
        "implementationTaskCount": len(plan_data.get("implementationTasks") or []),
        "blockingOpenDecisionCount": readiness.get("blockingOpenDecisionCount", 0),
    }
    if plan_data.get("nextActions"):
        state["nextAction"] = dict(plan_data["nextActions"][0])
    upsert_artifact(state, artifact_record("behaviorImplementationPlanData", plan_json_path, "plan", plan_data["digest"]))
    upsert_artifact(state, artifact_record("behaviorImplementationPlanDraft", plan_md_path, "plan", markdown_digest))
    return state, plan_data
