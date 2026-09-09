"""Behavior-contract helpers for the opt-in v2 workflow."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pjf.state_writer import write_json_atomic


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def expand_path(value: str | None, relative_to: Path | None = None) -> Path | None:
    if not value:
        return None
    expanded = Path(os.path.expandvars(os.path.expanduser(value)))
    if not expanded.is_absolute() and relative_to:
        expanded = relative_to / expanded
    return expanded


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def default_v2_run_dir(skill_root: Path, profile: dict[str, Any], ticket: str) -> Path:
    artifacts = profile.get("artifacts") or {}
    runs_root = expand_path(artifacts.get("runsRoot"))
    if runs_root:
        return runs_root / "v2" / ticket
    return skill_root / ".portable-jira-flow" / "runs" / "v2" / ticket


def behavior_template_path(skill_root: Path, profile: dict[str, Any]) -> Path:
    workflow_v2 = profile.get("workflowV2") or {}
    specs = workflow_v2.get("behaviorSpecs") or {}
    configured = expand_path(specs.get("template"), skill_root)
    return configured or (skill_root / "v2" / "templates" / "behavior-spec.md")


def render_behavior_spec(template_path: Path, *, ticket: str, profile_name: str | None) -> str:
    template = template_path.read_text(encoding="utf-8")
    values = {
        "ticketKey": ticket,
        "profileName": profile_name or "unselected",
        "generatedAt": now_iso(),
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def upsert_artifact(state: dict[str, Any], record: dict[str, Any]) -> None:
    artifacts = state.setdefault("artifacts", [])
    key = (record.get("key"), record.get("path"))
    for index, existing in enumerate(artifacts):
        if (existing.get("key"), existing.get("path")) == key:
            artifacts[index] = record
            return
    artifacts.append(record)


def build_v2_run_state(
    *,
    existing: dict[str, Any] | None,
    ticket: str,
    profile_name: str | None,
    command: str,
    spec_path: Path,
    spec_digest: str,
) -> dict[str, Any]:
    timestamp = now_iso()
    state = dict(existing or {})
    state.setdefault("schemaVersion", "2.0.0")
    state.setdefault("skillName", "portable-jira-flow-v2")
    state.setdefault("ticketKey", ticket)
    state.setdefault("profile", profile_name)
    state.setdefault("createdAt", timestamp)
    state["updatedAt"] = timestamp
    state["workflowVersion"] = "v2"
    state.setdefault(
        "invocation",
        {
            "rawArgs": [],
            "normalizedArgs": [],
            "primaryCommand": command,
            "legacyAliasesExpanded": [],
        },
    )
    state["invocation"]["primaryCommand"] = command
    state.setdefault("stages", {})
    state.setdefault(
        "policy",
        {
            "publishExplicitlyRequested": False,
            "commitExplicitlyRequested": False,
            "mutationsAllowed": False,
            "blockedGates": [],
        },
    )
    state["behaviorSpec"] = {
        "status": "draft",
        "path": str(spec_path),
        "digestAlgorithm": "sha256",
        "digest": spec_digest,
        "storage": "local-run-artifact",
        "durable": False,
        "selectedAt": timestamp,
        "sourceRevision": None,
        "warnings": [],
    }
    state.setdefault(
        "coverage",
        {
            "requirements": [],
            "scenarios": [],
            "results": [],
            "summary": {
                "planned": 0,
                "implemented": 0,
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "skipped": 0,
                "unknown": 0,
            },
        },
    )
    state.setdefault(
        "provenance",
        {
            "sources": [],
            "assumptions": [],
            "decisions": [],
        },
    )
    state.setdefault(
        "nextAction",
        {
            "command": f"portable-jira-flow-v2 specify {ticket}",
            "reason": "Review and refine the generated behavior contract before implementation.",
            "blocked": False,
        },
    )
    state.setdefault("artifacts", [])
    state.setdefault("artifactRegistrySnapshot", {})
    upsert_artifact(
        state,
        {
            "key": "behaviorSpecDraft",
            "path": str(spec_path),
            "producer": command,
            "privacyLevel": "internal",
            "committable": False,
            "freshness": "current",
            "digest": spec_digest,
            "timestamp": timestamp,
        },
    )
    return state


def write_v2_state(run_dir: Path, state: dict[str, Any]) -> None:
    write_json_atomic(run_dir / "run.json", state)
