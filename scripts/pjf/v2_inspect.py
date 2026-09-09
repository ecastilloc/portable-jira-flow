"""Source ingestion and scenario extraction for portable-jira-flow v2 inspect."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pjf.state_writer import write_json_atomic
from pjf.v2_contracts import digest_text, now_iso, upsert_artifact


NEGATIVE_TERMS = {
    "already",
    "cannot",
    "closed",
    "inactive",
    "invalid",
    "missing",
    "must not",
    "not allowed",
    "outside",
    "unless",
}
RULE_TERMS = {
    " can ",
    " cannot ",
    " must ",
    " must not ",
    " only ",
    " required ",
    " should ",
    " should not ",
    " unless ",
    " when ",
}
NFR_TERMS = {
    "latency",
    "performance",
    "p95",
    "p99",
    "query count",
    "response time",
    "slow",
    "timeout",
}
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(password|secret|bearer|api[_-]?token)\s*[=:]\s*['\"][A-Za-z0-9_./+=-]{8,}['\"]"
)
USER_STORY = re.compile(r"(?is)\bas an?\s+([^,.]+?)[,.]\s*i want(?: to)?\s+([^.\n]+)")


@dataclass(frozen=True)
class SourceInput:
    content: str
    kind: str
    authority: str
    locator: str
    revision: str | None


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)


def canonical_digest(data: Any) -> str:
    return digest_text(canonical_json(data))


def sanitize_content(text: str) -> str:
    cleaned = text.replace("\x00", "")
    return SECRET_ASSIGNMENT.sub(r"\1=<redacted>", cleaned)


def infer_file_kind(path: Path, parsed_json: Any | None) -> str:
    lower = path.name.lower()
    if isinstance(parsed_json, dict) and ("fields" in parsed_json or "key" in parsed_json):
        return "redacted-jira-json"
    if "test" in lower or path.suffix in {".spec", ".feature"}:
        return "existing-test"
    if "spec" in lower:
        return "existing-spec"
    if "attachment" in lower:
        return "attachment"
    if path.suffix.lower() in {".py", ".php", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go", ".rb"}:
        return "current-code"
    if path.suffix.lower() in {".json", ".md", ".txt"}:
        return "text"
    return "file"


def authority_for_kind(kind: str) -> str:
    if kind == "redacted-jira-json":
        return "jira_description"
    if kind == "existing-spec":
        return "existing_reviewed_spec"
    if kind == "attachment":
        return "attachments"
    if kind == "existing-test":
        return "existing_tests"
    if kind == "current-code":
        return "current_code"
    if kind == "inline-note":
        return "user_request"
    return "assistant_context"


def flatten_json_strings(value: Any, prefix: str = "") -> list[str]:
    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(flatten_json_strings(item, next_prefix))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            lines.extend(flatten_json_strings(item, f"{prefix}[{index}]"))
    elif isinstance(value, str) and value.strip():
        lines.append(f"{prefix}: {value.strip()}" if prefix else value.strip())
    elif isinstance(value, (int, float, bool)):
        lines.append(f"{prefix}: {value}")
    return lines


def jira_json_to_text(data: dict[str, Any]) -> str:
    fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
    lines: list[str] = []
    if data.get("key"):
        lines.append(f"key: {data['key']}")
    for key in ["summary", "description", "status", "priority", "issuetype", "labels", "components", "environment"]:
        value = fields.get(key)
        if value is None:
            continue
        if isinstance(value, dict):
            lines.extend(flatten_json_strings({key: value}))
        elif isinstance(value, list):
            rendered = ", ".join(str(item.get("name", item)) if isinstance(item, dict) else str(item) for item in value)
            lines.append(f"{key}: {rendered}")
        else:
            lines.append(f"{key}: {value}")
    for key in ["comment", "comments", "issuelinks", "parent", "attachment"]:
        if key in fields:
            lines.extend(flatten_json_strings({key: fields[key]}))
    return "\n".join(lines)


def load_source_file(path: Path) -> SourceInput:
    resolved = path.expanduser().resolve()
    text = resolved.read_text(encoding="utf-8")
    parsed: Any | None = None
    content = text
    if resolved.suffix.lower() == ".json":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict) and ("fields" in parsed or "key" in parsed):
            content = jira_json_to_text(parsed)
        elif parsed is not None:
            content = "\n".join(flatten_json_strings(parsed))
    kind = infer_file_kind(resolved, parsed)
    stat = resolved.stat()
    return SourceInput(
        content=sanitize_content(content),
        kind=kind,
        authority=authority_for_kind(kind),
        locator=str(resolved),
        revision=f"mtimeNs:{stat.st_mtime_ns};size:{stat.st_size}",
    )


def load_source_inputs(paths: list[str], notes: list[str]) -> list[SourceInput]:
    sources: list[SourceInput] = []
    for raw_path in paths:
        sources.append(load_source_file(Path(raw_path)))
    for index, note in enumerate(notes, start=1):
        sources.append(
            SourceInput(
                content=sanitize_content(note),
                kind="inline-note",
                authority="user_request",
                locator=f"inline-note:{index}",
                revision=None,
            )
        )
    return sources


def build_source_pack(
    *,
    ticket: str,
    profile_name: str | None,
    profile: dict[str, Any],
    source_inputs: list[SourceInput],
) -> dict[str, Any]:
    workflow = profile.get("workflowV2") or {}
    ingestion = workflow.get("sourceIngestion") or {}
    authority_order = ingestion.get("authorityOrder") or [
        "user_request",
        "existing_reviewed_spec",
        "jira_acceptance_criteria",
        "jira_description",
        "jira_comments",
        "attachments",
        "existing_tests",
        "current_code",
        "assistant_context",
    ]
    attachment_policy = ingestion.get("attachmentInstructionPolicy", "reference-only")
    sources = []
    for index, item in enumerate(source_inputs, start=1):
        source_id = f"SRC-{index:03d}"
        sources.append(
            {
                "sourceId": source_id,
                "kind": item.kind,
                "authority": item.authority,
                "pathOrLocator": item.locator,
                "revision": item.revision,
                "digestAlgorithm": "sha256",
                "digest": digest_text(item.content),
                "capturedAt": now_iso(),
                "instructionPolicy": "reference-only" if item.kind == "attachment" else attachment_policy,
                "executableInstructions": False,
                "content": item.content,
            }
        )
    digest_input = [
        {
            "sourceId": source["sourceId"],
            "kind": source["kind"],
            "authority": source["authority"],
            "pathOrLocator": source["pathOrLocator"],
            "revision": source["revision"],
            "digest": source["digest"],
            "content": source["content"],
        }
        for source in sources
    ]
    digest = canonical_digest(digest_input)
    return {
        "schemaVersion": "1.0.0",
        "ticketKey": ticket,
        "profile": profile_name,
        "generatedAt": now_iso(),
        "policy": {
            "authorityOrder": authority_order,
            "attachmentInstructionPolicy": attachment_policy,
        },
        "sources": sources,
        "digestAlgorithm": "sha256",
        "digest": digest,
    }


def split_candidate_lines(source_pack: dict[str, Any]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for source in source_pack.get("sources") or []:
        source_id = source.get("sourceId", "SRC-000")
        authority = str(source.get("authority") or "")
        kind = str(source.get("kind") or "")
        content = str(source.get("content") or "")
        for raw_line in re.split(r"[\n\r]+|(?<=[.!?])\s+", content):
            line = raw_line.strip(" -*\t")
            if not line:
                continue
            candidates.append({"text": line, "sourceRef": source_id, "authority": authority, "kind": kind})
    return candidates


def is_intended_behavior_source(candidate: dict[str, str]) -> bool:
    return candidate.get("authority") not in {"existing_tests", "current_code"}


def fact(fact_id: str, kind: str, text: str, source_refs: list[str], confidence: str = "medium") -> dict[str, Any]:
    return {
        "id": fact_id,
        "kind": kind,
        "text": text,
        "sourceRefs": sorted(set(source_refs)),
        "confidence": confidence,
    }


def next_id(prefix: str, values: list[dict[str, Any]]) -> str:
    return f"{prefix}-{len(values) + 1:03d}"


def is_rule(text: str) -> bool:
    normalized = f" {text.lower()} "
    return any(term in normalized for term in RULE_TERMS)


def has_negative_term(text: str) -> bool:
    normalized = text.lower()
    return any(term in normalized for term in NEGATIVE_TERMS)


def is_nfr(text: str) -> bool:
    normalized = text.lower()
    return any(term in normalized for term in NFR_TERMS)


def nfr_has_required_parts(text: str) -> bool:
    normalized = text.lower()
    has_metric = any(term in normalized for term in ["latency", "p95", "p99", "response time", "query count", "payload"])
    has_threshold = bool(re.search(r"\b\d+(\.\d+)?\s*(ms|s|sec|seconds|queries|kb|mb|%)\b", normalized))
    has_workload = any(term in normalized for term in ["for ", "under ", "with ", "during "])
    has_environment = any(term in normalized for term in ["local", "dev", "stage", "staging", "prod", "production"])
    return has_metric and has_threshold and has_workload and has_environment


def normalize_tokens(text: str) -> set[str]:
    stop = {
        "a",
        "an",
        "and",
        "be",
        "can",
        "cannot",
        "must",
        "not",
        "only",
        "or",
        "should",
        "the",
        "to",
        "when",
    }
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in stop and len(token) > 2}


def find_contradictions(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contradictions: list[dict[str, Any]] = []
    for left_index, left in enumerate(rules):
        left_text = left["text"]
        left_negative = has_negative_term(left_text) or "must not" in left_text.lower() or "should not" in left_text.lower()
        left_tokens = normalize_tokens(left_text)
        for right in rules[left_index + 1 :]:
            right_text = right["text"]
            right_negative = has_negative_term(right_text) or "must not" in right_text.lower() or "should not" in right_text.lower()
            if left_negative == right_negative:
                continue
            right_tokens = normalize_tokens(right_text)
            overlap = left_tokens & right_tokens
            smaller = min(len(left_tokens), len(right_tokens)) or 1
            if len(overlap) / smaller >= 0.45:
                contradictions.append(
                    {
                        "id": f"CONTRADICTION-{len(contradictions) + 1:03d}",
                        "sourceRefs": sorted(set(left.get("sourceRefs", []) + right.get("sourceRefs", []))),
                        "statements": [left_text, right_text],
                        "status": "open_decision",
                    }
                )
    return contradictions


def extract_behavior_facts(source_pack: dict[str, Any]) -> dict[str, Any]:
    candidates = split_candidate_lines(source_pack)
    actors: list[dict[str, Any]] = []
    goals: list[dict[str, Any]] = []
    domain_terms: list[dict[str, Any]] = []
    business_rules: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    nfrs: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    open_decisions: list[dict[str, Any]] = []

    for candidate in candidates:
        text = candidate["text"]
        source_ref = candidate["sourceRef"]
        if is_intended_behavior_source(candidate):
            story = USER_STORY.search(text)
            if story:
                actors.append(fact(next_id("ACTOR", actors), "actor", story.group(1).strip(), [source_ref], "high"))
                goals.append(fact(next_id("GOAL", goals), "goal", story.group(2).strip(), [source_ref], "high"))
            elif text.lower().startswith("summary:"):
                goals.append(fact(next_id("GOAL", goals), "goal", text.split(":", 1)[1].strip(), [source_ref], "medium"))

            if is_rule(text):
                business_rules.append(fact(next_id("RULE", business_rules), "business_rule", text, [source_ref], "medium"))
            if is_nfr(text):
                nfr = fact(next_id("NFR", nfrs), "non_functional_requirement", text, [source_ref], "medium")
                nfr["completeForAcceptance"] = nfr_has_required_parts(text)
                nfrs.append(nfr)
                if not nfr["completeForAcceptance"]:
                    open_decisions.append(
                        {
                            "id": next_id("DECISION", open_decisions),
                            "kind": "nfr_acceptance",
                            "question": "Define metric, unit, threshold, workload, and environment for this quality requirement.",
                            "sourceRefs": [source_ref],
                            "status": "open_decision",
                        }
                    )
            if any(term in text.lower() for term in ["out of scope", "not included", "not part of"]):
                exclusions.append(fact(next_id("EXCLUSION", exclusions), "exclusion", text, [source_ref], "medium"))
            if any(term in text.lower() for term in ["security", "permission", "role", "access", "audit", "integrity"]):
                constraints.append(fact(next_id("CONSTRAINT", constraints), "constraint", text, [source_ref], "medium"))

        for term in re.findall(r"\b[A-Z][A-Za-z0-9]{2,}\b", text):
            if term.upper() == term and len(term) <= 4:
                continue
            if term in {"Acceptance", "Criteria", "Given", "When", "Then"}:
                continue
            if not any(existing["text"] == term for existing in domain_terms):
                domain_terms.append(fact(next_id("TERM", domain_terms), "domain_term", term, [source_ref], "low"))

    if not candidates:
        open_decisions.append(
            {
                "id": next_id("DECISION", open_decisions),
                "kind": "missing_source",
                "question": "Provide redacted ticket, spec, or context source material before implementation.",
                "sourceRefs": [],
                "status": "open_decision",
            }
        )
    if not goals and candidates:
        open_decisions.append(
            {
                "id": next_id("DECISION", open_decisions),
                "kind": "missing_goal",
                "question": "Clarify the user-visible goal or behavior outcome.",
                "sourceRefs": [candidates[0]["sourceRef"]],
                "status": "open_decision",
            }
        )

    contradictions = find_contradictions(business_rules)
    for contradiction in contradictions:
        open_decisions.append(
            {
                "id": next_id("DECISION", open_decisions),
                "kind": "contradiction",
                "question": "Resolve contradictory source statements before treating behavior as reviewed.",
                "sourceRefs": contradiction["sourceRefs"],
                "status": "open_decision",
            }
        )

    facts = {
        "schemaVersion": "1.0.0",
        "ticketKey": source_pack["ticketKey"],
        "generatedAt": now_iso(),
        "sourcePackDigest": source_pack["digest"],
        "actors": actors,
        "goals": goals,
        "domainTerms": domain_terms,
        "businessRules": business_rules,
        "constraints": constraints,
        "nonFunctionalRequirements": nfrs,
        "exclusions": exclusions,
        "contradictions": contradictions,
        "openDecisions": open_decisions,
    }
    facts["digestAlgorithm"] = "sha256"
    facts["digest"] = canonical_digest({key: value for key, value in facts.items() if key not in {"generatedAt", "digest"}})
    return facts


def ticket_prefix(ticket: str) -> str:
    return ticket.split("-", 1)[0].upper() if "-" in ticket else "REQ"


def scenario_status(expected: str) -> str:
    return "unknown" if expected.lower() == "unknown" else "planned"


def build_behavior_spec(source_pack: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    ticket = source_pack["ticketKey"]
    prefix = ticket_prefix(ticket)
    use_case_id = f"{prefix}-UC-001"
    rules = facts.get("businessRules") or []
    goals = facts.get("goals") or []
    actors = facts.get("actors") or []
    nfrs = facts.get("nonFunctionalRequirements") or []

    requirements: list[dict[str, Any]] = []
    for index, rule in enumerate(rules[:8], start=1):
        requirements.append(
            {
                "id": f"{prefix}-FR-{index:03d}",
                "text": rule["text"],
                "kind": "functional",
                "sourceRefs": rule.get("sourceRefs", []),
                "status": "draft",
            }
        )
    if not requirements and goals:
        requirements.append(
            {
                "id": f"{prefix}-FR-001",
                "text": goals[0]["text"],
                "kind": "functional",
                "sourceRefs": goals[0].get("sourceRefs", []),
                "status": "draft",
            }
        )
    if not requirements:
        requirements.append(
            {
                "id": f"{prefix}-FR-001",
                "text": "unknown",
                "kind": "functional",
                "sourceRefs": [],
                "status": "unknown",
            }
        )

    for nfr in nfrs:
        requirements.append(
            {
                "id": f"{prefix}-NFR-{len([r for r in requirements if r['kind'] == 'quality']) + 1:03d}",
                "text": nfr["text"],
                "kind": "quality",
                "sourceRefs": nfr.get("sourceRefs", []),
                "status": "draft" if nfr.get("completeForAcceptance") else "open_decision",
                "completeForAcceptance": bool(nfr.get("completeForAcceptance")),
            }
        )

    actor = actors[0]["text"] if actors else "actor"
    trigger = goals[0]["text"] if goals else "unknown"
    main_expected = requirements[0]["text"] if requirements[0]["text"] != "unknown" else "unknown"
    scenarios: list[dict[str, Any]] = [
        {
            "id": f"{use_case_id}-MAIN",
            "type": "main",
            "requirementIds": [requirements[0]["id"]],
            "actor": actor,
            "preconditions": ["source behavior is available for review"] if source_pack.get("sources") else ["unknown"],
            "trigger": trigger,
            "steps": [
                "Actor initiates the requested behavior.",
                "System evaluates the applicable rules.",
                "System returns the expected result.",
            ],
            "expectedResult": main_expected,
            "successGuarantee": main_expected,
            "failureGuarantee": "unknown",
            "required": True,
            "sourceRefs": requirements[0].get("sourceRefs", []),
            "status": scenario_status(main_expected),
        }
    ]

    alternative_index = 1
    for rule in rules:
        if not has_negative_term(rule["text"]):
            continue
        expected = rule["text"] if any(term in rule["text"].lower() for term in ["reject", "prevent", "preserve", "unchanged", "must not", "cannot"]) else "unknown"
        scenarios.append(
            {
                "id": f"{use_case_id}-A{alternative_index}",
                "type": "alternative",
                "requirementIds": [requirements[0]["id"]],
                "actor": actor,
                "preconditions": [rule["text"]],
                "trigger": trigger,
                "steps": ["System evaluates the alternative or failure condition."],
                "expectedResult": expected,
                "successGuarantee": "not_applicable",
                "failureGuarantee": expected,
                "required": True,
                "sourceRefs": rule.get("sourceRefs", []),
                "status": scenario_status(expected),
            }
        )
        alternative_index += 1

    for nfr in nfrs:
        scenarios.append(
            {
                "id": f"{use_case_id}-Q{len([s for s in scenarios if s['type'] == 'quality']) + 1}",
                "type": "quality",
                "requirementIds": [req["id"] for req in requirements if req.get("text") == nfr["text"]],
                "actor": actor,
                "preconditions": ["measurement conditions are defined"] if nfr.get("completeForAcceptance") else ["unknown"],
                "trigger": "quality requirement is evaluated",
                "steps": ["Run the configured measurement under the specified workload and environment."],
                "expectedResult": nfr["text"] if nfr.get("completeForAcceptance") else "unknown",
                "successGuarantee": "quality target is met" if nfr.get("completeForAcceptance") else "unknown",
                "failureGuarantee": "quality target is reported as unverified or failed",
                "required": bool(nfr.get("completeForAcceptance")),
                "sourceRefs": nfr.get("sourceRefs", []),
                "status": "planned" if nfr.get("completeForAcceptance") else "unknown",
            }
        )

    open_decisions = list(facts.get("openDecisions") or [])
    for scenario in scenarios:
        if scenario["status"] == "unknown":
            open_decisions.append(
                {
                    "id": f"DECISION-{len(open_decisions) + 1:03d}",
                    "kind": "unknown_expected_result",
                    "question": f"Clarify expected result for scenario {scenario['id']}.",
                    "sourceRefs": scenario.get("sourceRefs", []),
                    "status": "open_decision",
                }
            )

    coverage_summary = {
        "planned": sum(1 for scenario in scenarios if scenario["status"] == "planned"),
        "implemented": 0,
        "passed": 0,
        "failed": 0,
        "blocked": 0,
        "skipped": 0,
        "not_applicable": 0,
        "unknown": sum(1 for scenario in scenarios if scenario["status"] == "unknown"),
    }
    spec = {
        "schemaVersion": "1.0.0",
        "ticketKey": ticket,
        "id": use_case_id,
        "status": "draft",
        "changeRequests": [ticket],
        "sourcePackDigest": source_pack["digest"],
        "factsDigest": facts["digest"],
        "requirements": requirements,
        "useCases": [
            {
                "id": use_case_id,
                "name": goals[0]["text"] if goals else f"{ticket} behavior",
                "actor": actor,
                "scope": "unknown" if not goals else goals[0]["text"],
                "outOfScope": [item["text"] for item in facts.get("exclusions") or []],
                "sourceRefs": sorted({ref for goal in goals for ref in goal.get("sourceRefs", [])}),
            }
        ],
        "scenarios": scenarios,
        "coverage": {
            "requiredScenarioIds": [scenario["id"] for scenario in scenarios if scenario.get("required")],
            "summary": coverage_summary,
        },
        "provenance": {
            "sources": [
                {
                    "sourceId": source["sourceId"],
                    "authority": source["authority"],
                    "digest": source["digest"],
                }
                for source in source_pack.get("sources") or []
            ],
            "openDecisions": open_decisions,
            "contradictions": facts.get("contradictions") or [],
        },
    }
    spec["digestAlgorithm"] = "sha256"
    spec["digest"] = canonical_digest({key: value for key, value in spec.items() if key != "digest"})
    return spec


def render_behavior_spec_markdown(spec: dict[str, Any]) -> str:
    requirements = "\n".join(
        f"| {item['id']} | {item.get('kind', '')} | {item.get('status', '')} | {item.get('text', '')} |"
        for item in spec.get("requirements") or []
    )
    scenarios = "\n".join(
        "| {id} | {type} | {status} | {required} | {expected} |".format(
            id=item.get("id", ""),
            type=item.get("type", ""),
            status=item.get("status", ""),
            required="yes" if item.get("required") else "no",
            expected=item.get("expectedResult", ""),
        )
        for item in spec.get("scenarios") or []
    )
    decisions = "\n".join(
        f"| {item.get('id', '')} | {item.get('kind', '')} | {item.get('status', '')} | {item.get('question', '')} |"
        for item in (spec.get("provenance") or {}).get("openDecisions") or []
    )
    if not decisions:
        decisions = "| none |  |  |  |"
    sources = "\n".join(
        f"| {item.get('sourceId', '')} | {item.get('authority', '')} | {item.get('digest', '')[:12]} |"
        for item in (spec.get("provenance") or {}).get("sources") or []
    )
    if not sources:
        sources = "| none |  |  |"
    coverage = spec.get("coverage", {}).get("summary", {})
    return f"""# {spec.get('ticketKey')} Behavior Contract

Status: {spec.get('status')}
Spec ID: {spec.get('id')}
Digest: {spec.get('digest')}

## Change Request

- Ticket: {spec.get('ticketKey')}
- Source pack digest: {spec.get('sourcePackDigest')}
- Facts digest: {spec.get('factsDigest')}

## Requirements

| ID | Kind | Status | Text |
|---|---|---|---|
{requirements}

## Scenarios

| ID | Type | Status | Required | Expected result |
|---|---|---|---:|---|
{scenarios}

## Coverage Summary

- Planned: {coverage.get('planned', 0)}
- Implemented: {coverage.get('implemented', 0)}
- Passed: {coverage.get('passed', 0)}
- Failed: {coverage.get('failed', 0)}
- Blocked: {coverage.get('blocked', 0)}
- Skipped: {coverage.get('skipped', 0)}
- Not applicable: {coverage.get('not_applicable', 0)}
- Unknown: {coverage.get('unknown', 0)}

## Open Decisions

| ID | Kind | Status | Question |
|---|---|---|---|
{decisions}

## Sources

| Source | Authority | Digest |
|---|---|---|
{sources}
"""


def artifact_record(key: str, path: Path, producer: str, digest: str | None = None) -> dict[str, Any]:
    record = {
        "key": key,
        "path": str(path),
        "producer": producer,
        "privacyLevel": "internal",
        "committable": False,
        "freshness": "current",
        "timestamp": now_iso(),
    }
    if digest:
        record["digest"] = digest
    return record


def write_inspect_artifacts(
    *,
    run_dir: Path,
    ticket: str,
    profile_name: str | None,
    profile: dict[str, Any],
    source_paths: list[str],
    source_notes: list[str],
    existing_state: dict[str, Any] | None,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    source_inputs = load_source_inputs(source_paths, source_notes)
    source_pack = build_source_pack(ticket=ticket, profile_name=profile_name, profile=profile, source_inputs=source_inputs)
    facts = extract_behavior_facts(source_pack)
    spec = build_behavior_spec(source_pack, facts)
    markdown = render_behavior_spec_markdown(spec)
    markdown_digest = digest_text(markdown)

    source_pack_path = run_dir / "source-pack.json"
    facts_path = run_dir / "behavior-facts.json"
    spec_json_path = run_dir / "behavior-spec.json"
    spec_md_path = run_dir / "behavior-spec.md"

    write_json_atomic(source_pack_path, source_pack)
    write_json_atomic(facts_path, facts)
    write_json_atomic(spec_json_path, spec)
    spec_md_path.write_text(markdown, encoding="utf-8")

    from pjf.v2_contracts import build_v2_run_state

    state = build_v2_run_state(
        existing=existing_state,
        ticket=ticket,
        profile_name=profile_name,
        command="inspect",
        spec_path=spec_md_path,
        spec_digest=markdown_digest,
    )
    state["behaviorSpec"].update(
        {
            "contractPath": str(spec_json_path),
            "contractDigest": spec["digest"],
            "sourcePackPath": str(source_pack_path),
            "sourcePackDigest": source_pack["digest"],
            "factsPath": str(facts_path),
            "factsDigest": facts["digest"],
            "openDecisionCount": len((spec.get("provenance") or {}).get("openDecisions") or []),
            "contradictionCount": len((spec.get("provenance") or {}).get("contradictions") or []),
        }
    )
    state["coverage"] = {
        "requirements": spec.get("requirements", []),
        "scenarios": spec.get("scenarios", []),
        "results": [],
        "summary": spec.get("coverage", {}).get("summary", {}),
    }
    state["provenance"] = {
        "sources": source_pack.get("sources", []),
        "assumptions": [],
        "decisions": (spec.get("provenance") or {}).get("openDecisions", []),
        "contradictions": (spec.get("provenance") or {}).get("contradictions", []),
    }
    state["stages"]["inspect"] = {
        "status": "blocked" if state["behaviorSpec"]["contradictionCount"] else "complete",
        "updatedAt": now_iso(),
        "sourcePackDigest": source_pack["digest"],
        "behaviorSpecDigest": markdown_digest,
        "openDecisionCount": state["behaviorSpec"]["openDecisionCount"],
        "contradictionCount": state["behaviorSpec"]["contradictionCount"],
    }
    if state["behaviorSpec"]["contradictionCount"]:
        state["nextAction"] = {
            "command": f"portable-jira-flow-v2 inspect {ticket}",
            "reason": "Resolve contradictory source statements before implementation.",
            "blocked": True,
        }
    elif state["behaviorSpec"]["openDecisionCount"]:
        state["nextAction"] = {
            "command": f"portable-jira-flow-v2 inspect {ticket}",
            "reason": "Resolve open behavior decisions or continue only within known scenario boundaries.",
            "blocked": False,
        }
    else:
        state["nextAction"] = {
            "command": f"portable-jira-flow-v2 start {ticket}",
            "reason": "Behavior contract is drafted with planned scenario coverage.",
            "blocked": False,
        }
    for key, path, digest in [
        ("sourcePack", source_pack_path, source_pack["digest"]),
        ("behaviorFacts", facts_path, facts["digest"]),
        ("behaviorSpecData", spec_json_path, spec["digest"]),
        ("behaviorSpecDraft", spec_md_path, markdown_digest),
    ]:
        upsert_artifact(state, artifact_record(key, path, "inspect", digest))
    return state


def recompute_file_digest(path_text: str) -> str | None:
    path = Path(path_text).expanduser()
    if not path.exists() or not path.is_file():
        return None
    return digest_text(load_source_file(path).content)


def status_freshness(state: dict[str, Any]) -> dict[str, Any]:
    spec_state = state.get("behaviorSpec") or {}
    stale_sources = []
    for source in state.get("provenance", {}).get("sources", []) or []:
        locator = str(source.get("pathOrLocator") or "")
        if locator.startswith("inline-note:"):
            continue
        current_digest = recompute_file_digest(locator)
        if current_digest and current_digest != source.get("digest"):
            stale_sources.append(source.get("sourceId"))
    spec_path = spec_state.get("path")
    contract_path = spec_state.get("contractPath")
    current_spec_digest = recompute_file_digest(spec_path) if spec_path else None
    current_contract_digest = None
    if contract_path and Path(contract_path).exists():
        try:
            current_contract_digest = canonical_digest(
                {key: value for key, value in json.loads(Path(contract_path).read_text(encoding="utf-8")).items() if key != "digest"}
            )
        except Exception:
            current_contract_digest = None
    return {
        "staleSources": sorted(stale_sources),
        "specMarkdownStale": bool(current_spec_digest and current_spec_digest != spec_state.get("digest")),
        "specContractStale": bool(current_contract_digest and current_contract_digest != spec_state.get("contractDigest")),
    }
