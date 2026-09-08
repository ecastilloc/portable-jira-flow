#!/usr/bin/env python3
"""Prepare and register local Playwright evidence for portable-jira-flow runs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_NAME = "portable-jira-flow"
PHASES = {"reproduction", "verification"}
MEDIA_EXTENSIONS = {"webm", "mp4", "mov"}
SCREENSHOT_EXTENSIONS = {"png", "jpg", "jpeg"}
SUPPORTING_EXTENSIONS = {"png", "jpg", "jpeg", "zip", "json", "html", "log", "txt"}
REQUIRE_COMPATIBLE_PLAYWRIGHT_CONFIGS = ("playwright.config.cjs", "playwright.config.js")
NON_REQUIRE_PLAYWRIGHT_CONFIGS = ("playwright.config.mjs", "playwright.config.ts")
STATUS_VALUES = {
    "pending",
    "in_progress",
    "complete",
    "blocked",
    "failed",
    "skipped",
    "not_requested",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(skill_root: Path) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for path in [skill_root / "config.example.json", skill_root / "config.json", skill_root / "config.local.json"]:
        if path.exists():
            config = deep_merge(config, read_json(path, {}))

    profiles_dir = skill_root / "profiles.local"
    if profiles_dir.exists():
        for path in sorted(profiles_dir.glob("*.json")):
            config = deep_merge(config, read_json(path, {}))
        for path in sorted(profiles_dir.glob("*/profile.json")):
            config = deep_merge(config, read_json(path, {}))

    profiles = skill_root / "profiles"
    if profiles.exists():
        for path in sorted(profiles.glob("*.local.json")):
            config = deep_merge(config, read_json(path, {}))

    return config


def resolve_profile(config: dict[str, Any], requested: str | None) -> tuple[str | None, dict[str, Any]]:
    profiles = config.get("profiles") or {}
    if requested:
        return requested, profiles.get(requested, {})
    default = config.get("defaultProfile")
    if default:
        return default, profiles.get(default, {})
    if len(profiles) == 1:
        name = next(iter(profiles))
        return name, profiles[name]
    return None, {}


def expand_path(value: str | None, relative_to: Path | None = None) -> Path | None:
    if not value:
        return None
    expanded = Path(os.path.expandvars(os.path.expanduser(value)))
    if not expanded.is_absolute() and relative_to:
        expanded = relative_to / expanded
    return expanded


def resolve_new(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def assert_inside(path: Path, roots: list[Path]) -> Path:
    resolved = resolve_new(path)
    allowed = [resolve_new(root) for root in roots if root]
    if not any(resolved == root or root in resolved.parents for root in allowed):
        raise ValueError("path is outside approved evidence roots")
    return resolved


def render_pattern(pattern: str, values: dict[str, str]) -> str:
    rendered = pattern
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def truthy(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.lower() in {"1", "true", "yes", "y", "on"}


def phase_artifact_key(phase: str) -> str:
    return "reproductionEvidence" if phase == "reproduction" else "verificationEvidence"


def phase_video_key(phase: str) -> str:
    return "reproductionVideo" if phase == "reproduction" else "verificationVideo"


def phase_screenshot_key(phase: str) -> str | None:
    return "verificationScreenshot" if phase == "verification" else None


def phase_markdown_name(phase: str) -> str:
    return "reproduction-evidence.md" if phase == "reproduction" else "verification-evidence.md"


def load_run_state(run_dir: Path, ticket: str, profile_name: str | None) -> dict[str, Any]:
    run_state = read_json(run_dir / "run.json", {})
    timestamp = now_iso()
    run_state.setdefault("schemaVersion", "1.0.0")
    run_state.setdefault("skillName", SKILL_NAME)
    run_state.setdefault("ticketKey", ticket)
    run_state.setdefault("profile", profile_name)
    run_state.setdefault("createdAt", timestamp)
    run_state["updatedAt"] = timestamp
    run_state.setdefault("stages", {})
    run_state.setdefault("policy", {})
    run_state.setdefault("artifacts", [])
    run_state.setdefault("artifactRegistrySnapshot", {})
    run_state.setdefault("classification", {})
    return run_state


def ensure_evidence_state(run_state: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    evidence = run_state.setdefault("evidence", {})
    evidence["policy"] = {
        "enabled": bool(policy.get("enabled", False)),
        "storage": policy.get("storage", "run"),
        "missingPolicy": policy.get("missingPolicy", "warn"),
        "requireReproductionForTicketTypes": policy.get("requireReproductionForTicketTypes", []),
    }
    for phase in PHASES:
        evidence.setdefault(
            phase,
            {
                "required": False,
                "status": "not_requested",
                "artifacts": [],
                "warnings": [],
                "command": None,
                "environment": "local",
                "updatedAt": None,
            },
        )
    return evidence


def get_ticket_type(run_state: dict[str, Any], fallback: str | None) -> str | None:
    classification = run_state.get("classification") or {}
    for key in ["ticketType", "type", "normalizedType", "category"]:
        value = classification.get(key)
        if isinstance(value, str) and value:
            return value
    return fallback


def required_for_phase(
    phase: str,
    requested: str,
    ticket_type: str | None,
    profile: dict[str, Any],
    evidence_policy: dict[str, Any],
) -> bool:
    if requested != "auto":
        return truthy(requested)
    if phase == "verification":
        return bool(profile.get("e2e", {}).get("enabled", False))
    configured = set(evidence_policy.get("requireReproductionForTicketTypes") or [])
    bug_like = set((profile.get("ticketTypes") or {}).get("bugLikeTypes") or [])
    return bool(ticket_type and ticket_type in (configured | bug_like))


def output_dir_for_phase(
    args: argparse.Namespace,
    run_dir: Path,
    ticket: str,
    phase: str,
    environment: str,
    evidence_policy: dict[str, Any],
) -> tuple[Path, list[str]]:
    warnings: list[str] = []
    if args.output_dir:
        return resolve_new(Path(args.output_dir)), warnings

    values = {
        "ticketKey": ticket,
        "environment": environment,
        "evidencePhase": phase,
        "centralEvidenceRoot": str(expand_path(evidence_policy.get("centralEvidenceRoot")) or ""),
    }
    if evidence_policy.get("storage") == "central":
        central_root = expand_path(evidence_policy.get("centralEvidenceRoot"))
        if central_root:
            pattern = (evidence_policy.get("playwright") or {}).get(
                "outputDirPattern", "{centralEvidenceRoot}/{ticketKey}/{evidencePhase}"
            )
            return resolve_new(Path(render_pattern(pattern, values))), warnings
        warnings.append("central evidence storage is enabled but centralEvidenceRoot is not configured")

    return resolve_new(run_dir / "evidence" / phase), warnings


def wrapper_path_for_phase(run_dir: Path, phase: str, evidence_policy: dict[str, Any]) -> Path:
    pattern = (evidence_policy.get("playwright") or {}).get(
        "generatedConfigPattern", "playwright-evidence-{evidencePhase}.config.cjs"
    )
    return resolve_new(run_dir / render_pattern(pattern, {"evidencePhase": phase}))


def command_for_phase(
    profile: dict[str, Any],
    evidence_policy: dict[str, Any],
    phase: str,
    ticket: str,
    environment: str,
    spec_paths: str,
    output_dir: Path,
    wrapper_path: Path,
) -> str | None:
    template = ((evidence_policy.get("phaseCommandTemplates") or {}).get(phase)) or (
        profile.get("e2e", {}).get("runCommandTemplate")
    )
    if not template:
        return None
    values = {
        "ticketKey": ticket,
        "environment": environment,
        "specPaths": spec_paths,
        "evidencePhase": phase,
        "evidenceOutputDir": str(output_dir),
        "playwrightConfigPath": str(wrapper_path),
    }
    return render_pattern(template, values)


def resolve_e2e_workspace(profile: dict[str, Any]) -> Path | None:
    return expand_path((profile.get("e2e") or {}).get("workspacePath"))


def resolve_base_playwright_config(
    profile: dict[str, Any],
    requested: str | None,
) -> tuple[Path | None, list[str]]:
    warnings: list[str] = []
    e2e = profile.get("e2e") or {}
    workspace = resolve_e2e_workspace(profile)

    if requested:
        resolved = expand_path(requested, workspace)
        if resolved and resolved.exists():
            return resolve_new(resolved), warnings
        warnings.append("requested base Playwright config does not exist")
        return None, warnings

    configured = e2e.get("basePlaywrightConfig")
    if configured:
        resolved = expand_path(configured, workspace)
        if resolved and resolved.exists():
            return resolve_new(resolved), warnings
        warnings.append("configured base Playwright config does not exist")
        return None, warnings

    if workspace:
        for name in REQUIRE_COMPATIBLE_PLAYWRIGHT_CONFIGS:
            candidate = workspace / name
            if candidate.exists():
                return resolve_new(candidate), warnings
        for name in NON_REQUIRE_PLAYWRIGHT_CONFIGS:
            if (workspace / name).exists():
                warnings.append(
                    "found a Playwright config that cannot be safely required by the generated CommonJS wrapper"
                )
                break

    return None, warnings


def write_wrapper_config(
    wrapper_path: Path,
    output_dir: Path,
    evidence_policy: dict[str, Any],
    base_config: Path | None,
) -> None:
    settings = evidence_policy.get("playwright") or {}
    video = settings.get("video", "on")
    screenshot = settings.get("screenshot", "only-on-failure")
    trace = settings.get("trace", "retain-on-failure")
    if base_config:
        base_line = f"""const baseConfigPath = {json.dumps(str(base_config))};
const baseDir = path.dirname(baseConfigPath);
const base = require(baseConfigPath);"""
    else:
        base_line = """const baseConfigPath = null;
const baseDir = __dirname;
const base = {};"""
    content = f"""const path = require("path");
{base_line}

const outputDir = {json.dumps(str(output_dir))};

function fromBase(value) {{
  if (!value || path.isAbsolute(value)) {{
    return value;
  }}
  return path.resolve(baseDir, value);
}}

module.exports = {{
  ...base,
  ...(base.testDir ? {{ testDir: fromBase(base.testDir) }} : {{}}),
  ...(base.snapshotDir ? {{ snapshotDir: fromBase(base.snapshotDir) }} : {{}}),
  outputDir,
  reporter: base.reporter || [["list"], ["html", {{ outputFolder: path.join(outputDir, "html-report"), open: "never" }}]],
  use: {{
    ...(base.use || {{}}),
    video: {json.dumps(video)},
    screenshot: {json.dumps(screenshot)},
    trace: {json.dumps(trace)}
  }}
}};
"""
    wrapper_path.parent.mkdir(parents=True, exist_ok=True)
    wrapper_path.write_text(content, encoding="utf-8")


def artifact_record(
    key: str,
    path: Path,
    source_root: Path,
    producer: str,
    privacy: str,
    retention: str,
    phase: str,
    notes: str = "",
    evidence_role: str | None = None,
) -> dict[str, Any]:
    exists = path.exists()
    timestamp = None
    if exists:
        timestamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0)
    try:
        relative = str(path.relative_to(source_root))
    except ValueError:
        relative = None
    record = {
        "key": key,
        "path": str(path),
        "relativePath": relative,
        "sourceRoot": str(source_root),
        "producer": producer,
        "phase": phase,
        "privacyLevel": privacy,
        "retention": retention,
        "exists": exists,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z") if timestamp else None,
        "freshness": "current" if exists else "missing",
        "notes": notes,
    }
    if evidence_role:
        record["evidenceRole"] = evidence_role
    return record


def upsert_artifact(run_state: dict[str, Any], record: dict[str, Any]) -> None:
    artifacts = run_state.setdefault("artifacts", [])
    match_key = (record.get("key"), record.get("path"), record.get("phase"))
    for index, existing in enumerate(artifacts):
        if (existing.get("key"), existing.get("path"), existing.get("phase")) == match_key:
            artifacts[index] = record
            return
    artifacts.append(record)


def upsert_record(records: list[dict[str, Any]], record: dict[str, Any]) -> list[dict[str, Any]]:
    match_key = (record.get("key"), record.get("path"), record.get("phase"))
    updated = list(records)
    for index, existing in enumerate(updated):
        if (existing.get("key"), existing.get("path"), existing.get("phase")) == match_key:
            updated[index] = record
            return updated
    updated.append(record)
    return updated


def media_preference(path: Path, ticket: str, phase: str, kind: str) -> tuple[int, str]:
    normalized = path.name.lower().replace("_", "-")
    ticket_lower = ticket.lower()
    score = 0
    if "canonical" in normalized:
        score += 100
    if "proof" in normalized:
        score += 80
    if f"{phase}-{kind}" in normalized:
        score += 60
    if phase in normalized and kind in normalized:
        score += 40
    if ticket_lower and ticket_lower in normalized:
        score += 20
    return (-score, normalized)


def select_canonical_media(paths: list[Path], ticket: str, phase: str, kind: str) -> Path | None:
    if not paths:
        return None
    return sorted(paths, key=lambda path: media_preference(path, ticket, phase, kind))[0]


def discovered_artifact_keys(phase: str) -> set[str]:
    keys = {phase_video_key(phase), f"{phase}EvidenceArtifact"}
    screenshot_key = phase_screenshot_key(phase)
    if screenshot_key:
        keys.add(screenshot_key)
    return keys


def replace_discovered_artifacts(run_state: dict[str, Any], phase: str, records: list[dict[str, Any]]) -> None:
    discovered_keys = discovered_artifact_keys(phase)
    run_state["artifacts"] = [
        record
        for record in run_state.setdefault("artifacts", [])
        if not (record.get("phase") == phase and record.get("key") in discovered_keys)
    ]
    for record in records:
        upsert_artifact(run_state, record)


def count_records_with_extensions(records: list[dict[str, Any]], extensions: set[str]) -> int:
    count = 0
    for record in records:
        suffix = Path(str(record.get("path") or "")).suffix.lower().lstrip(".")
        if suffix in extensions:
            count += 1
    return count


def discover_output_artifacts(output_dir: Path, phase: str, ticket: str) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    if not output_dir.exists():
        return discovered
    root = resolve_new(output_dir)
    video_paths: list[Path] = []
    screenshot_paths: list[Path] = []
    supporting_paths: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        resolved = resolve_new(path)
        if not (resolved == root or root in resolved.parents):
            continue
        suffix = path.suffix.lower().lstrip(".")
        if suffix not in MEDIA_EXTENSIONS and suffix not in SUPPORTING_EXTENSIONS:
            continue
        if suffix in MEDIA_EXTENSIONS:
            video_paths.append(resolved)
        elif phase == "verification" and suffix in SCREENSHOT_EXTENSIONS:
            screenshot_paths.append(resolved)
        else:
            supporting_paths.append(resolved)

    canonical_video = select_canonical_media(video_paths, ticket, phase, "video") if phase == "verification" else None
    canonical_screenshot = select_canonical_media(screenshot_paths, ticket, phase, "screenshot")
    producer = "start" if phase == "reproduction" else "verify"
    for path in sorted(video_paths + screenshot_paths + supporting_paths):
        suffix = path.suffix.lower().lstrip(".")
        key = f"{phase}EvidenceArtifact"
        notes = "Supporting evidence artifact"
        evidence_role = "supplemental"
        if suffix in MEDIA_EXTENSIONS and phase == "reproduction":
            key = phase_video_key(phase)
            notes = "Playwright video evidence"
            evidence_role = None
        elif path == canonical_video:
            key = phase_video_key(phase)
            notes = "Canonical verification video"
            evidence_role = "canonical"
        elif path == canonical_screenshot:
            key = "verificationScreenshot"
            notes = "Canonical verification screenshot"
            evidence_role = "canonical"
        elif suffix in MEDIA_EXTENSIONS:
            notes = "Supplemental diagnostic video; not primary proof"
        elif suffix in SCREENSHOT_EXTENSIONS:
            notes = "Supplemental diagnostic screenshot; not primary proof"
        discovered.append(
            artifact_record(
                key,
                path,
                root,
                producer,
                "private",
                "manual-cleanup",
                phase,
                notes,
                evidence_role,
            )
        )
    return discovered


def render_markdown(ticket: str, phase: str, state: dict[str, Any], output_dir: Path) -> str:
    title = "Reproduction Evidence" if phase == "reproduction" else "Verification Evidence"
    rows = []
    proof_rows = []
    for artifact in state.get("artifacts") or []:
        if phase == "verification" and artifact.get("key") in {"verificationVideo", "verificationScreenshot"}:
            proof_rows.append(
                "| {key} | {path} | {exists} | {timestamp} | {notes} |".format(
                    key=artifact.get("key", ""),
                    path=artifact.get("path", ""),
                    exists="yes" if artifact.get("exists") else "no",
                    timestamp=artifact.get("timestamp") or "",
                    notes=artifact.get("notes") or "",
                )
            )
        rows.append(
            "| {key} | {path} | {exists} | {timestamp} | {notes} |".format(
                key=artifact.get("key", ""),
                path=artifact.get("path", ""),
                exists="yes" if artifact.get("exists") else "no",
                timestamp=artifact.get("timestamp") or "",
                notes=artifact.get("notes") or "",
            )
        )
    artifact_rows = "\n".join(rows) if rows else "| none |  | no |  | no artifacts registered |"
    proof_section = ""
    if phase == "verification":
        proof_artifact_rows = "\n".join(proof_rows) if proof_rows else "| none |  | no |  | canonical proof artifacts missing |"
        proof_section = f"""
## Canonical Proof
| Artifact | Path | Exists | Timestamp | Notes |
|---|---|---:|---|---|
{proof_artifact_rows}
"""
    warnings = "\n".join(f"- {warning}" for warning in state.get("warnings") or []) or "- none"
    return f"""# {title}

Rendered from: run.json.evidence.{phase}

## Ticket
{ticket}

## Policy
- Required: {"yes" if state.get("required") else "no"}
- Status: {state.get("status", "not_requested")}

## Capture
- Phase: {phase}
- Environment: {state.get("environment") or "local"}
- Command: {state.get("command") or "not configured"}
- Output directory: {output_dir}
- Workdir: {state.get("workspacePath") or "not configured"}
- Base config: {state.get("basePlaywrightConfigPath") or "not configured"}
- Runnable: {"yes" if state.get("runnable") else "no"}
- Updated: {state.get("updatedAt") or ""}
{proof_section}

## Artifacts
| Artifact | Path | Exists | Timestamp | Notes |
|---|---|---:|---|---|
{artifact_rows}

## Warnings
{warnings}
"""


def write_evidence_outputs(
    run_dir: Path,
    ticket: str,
    phase: str,
    output_dir: Path,
    run_state: dict[str, Any],
) -> None:
    phase_state = run_state["evidence"][phase]
    markdown_path = run_dir / phase_markdown_name(phase)
    manifest_path = run_dir / "evidence-manifest.json"
    markdown_path.write_text(render_markdown(ticket, phase, phase_state, output_dir), encoding="utf-8")
    producer = "start" if phase == "reproduction" else "verify"
    upsert_artifact(
        run_state,
        artifact_record(phase_artifact_key(phase), markdown_path, run_dir, producer, "private", "keep", phase),
    )
    manifest = {
        "schemaVersion": "1.0.0",
        "ticketKey": ticket,
        "generatedAt": now_iso(),
        "policy": run_state["evidence"].get("policy", {}),
        "phases": {
            "reproduction": run_state["evidence"].get("reproduction", {}),
            "verification": run_state["evidence"].get("verification", {}),
        },
    }
    write_json(manifest_path, manifest)
    upsert_artifact(
        run_state,
        artifact_record("evidenceManifest", manifest_path, run_dir, producer, "private", "keep", phase),
    )


def prepare(args: argparse.Namespace) -> int:
    skill_root = resolve_new(Path(args.skill_root))
    run_dir = resolve_new(Path(args.run_dir))
    phase = args.phase
    config = load_config(skill_root)
    profile_name, profile = resolve_profile(config, args.profile)
    evidence_policy = profile.get("evidence") or {}
    run_state = load_run_state(run_dir, args.ticket, profile_name)
    evidence = ensure_evidence_state(run_state, evidence_policy)
    ticket_type = get_ticket_type(run_state, args.ticket_type)
    required = required_for_phase(phase, args.required, ticket_type, profile, evidence_policy)
    e2e = profile.get("e2e") or {}
    e2e_enabled = bool(e2e.get("enabled", False))
    workspace_path = resolve_e2e_workspace(profile)
    resolved_workspace_path = resolve_new(workspace_path) if workspace_path else None
    environment = args.environment or e2e.get("defaultEnvironment") or "local"
    output_dir, warnings = output_dir_for_phase(args, run_dir, args.ticket, phase, environment, evidence_policy)
    allowed_roots = [run_dir]
    central_root = expand_path(evidence_policy.get("centralEvidenceRoot"))
    if central_root:
        allowed_roots.append(central_root)
    output_dir = assert_inside(output_dir, allowed_roots)
    output_dir.mkdir(parents=True, exist_ok=True)

    wrapper_path = wrapper_path_for_phase(run_dir, phase, evidence_policy)
    base_config, base_config_warnings = resolve_base_playwright_config(profile, args.base_playwright_config)
    warnings.extend(base_config_warnings)
    if not args.no_wrapper:
        write_wrapper_config(wrapper_path, output_dir, evidence_policy, base_config)
    phase_artifacts = list(evidence[phase].get("artifacts") or [])
    if wrapper_path.exists():
        wrapper_record = artifact_record(
            "playwrightEvidenceConfig",
            wrapper_path,
            run_dir,
            "start" if phase == "reproduction" else "verify",
            "private",
            "keep",
            phase,
            "Generated Playwright evidence wrapper config",
        )
        upsert_artifact(run_state, wrapper_record)
        phase_artifacts = upsert_record(phase_artifacts, wrapper_record)

    command = command_for_phase(
        profile,
        evidence_policy,
        phase,
        args.ticket,
        environment,
        args.spec_paths,
        output_dir,
        wrapper_path,
    )
    runnable = bool(command)
    if e2e_enabled and resolved_workspace_path and not resolved_workspace_path.is_dir():
        runnable = False
        warnings.append("configured E2E workspace does not exist")
    if command and "{specPaths}" in (((evidence_policy.get("phaseCommandTemplates") or {}).get(phase)) or e2e.get("runCommandTemplate") or ""):
        if not args.spec_paths.strip():
            runnable = False
            warnings.append("no ticket-scoped spec paths provided; evidence command was not made runnable")

    if not evidence_policy.get("enabled", False):
        status = "not_requested"
        warnings.append("evidence is disabled for this profile")
    elif not command:
        status = "skipped"
        warnings.append("no evidence command template is configured")
    elif not runnable:
        status = "skipped" if evidence_policy.get("missingPolicy", "warn") == "warn" else "blocked"
    elif required:
        status = "pending"
    else:
        status = "not_requested" if phase == "reproduction" else "pending"

    phase_state = evidence[phase]
    phase_state.update(
        {
            "required": required,
            "status": status,
            "artifacts": phase_artifacts,
            "warnings": sorted(set((phase_state.get("warnings") or []) + warnings)),
            "command": command,
            "environment": environment,
            "updatedAt": now_iso(),
            "outputDir": str(output_dir),
            "playwrightConfigPath": str(wrapper_path),
            "workspacePath": str(resolved_workspace_path) if resolved_workspace_path else None,
            "basePlaywrightConfigPath": str(base_config) if base_config else None,
            "runnable": runnable,
        }
    )
    write_evidence_outputs(run_dir, args.ticket, phase, output_dir, run_state)
    write_json(run_dir / "run.json", run_state)
    print(f"[OK] {phase} evidence prepared status={status} warnings={len(phase_state['warnings'])}")
    return 0


def register(args: argparse.Namespace) -> int:
    skill_root = resolve_new(Path(args.skill_root))
    run_dir = resolve_new(Path(args.run_dir))
    phase = args.phase
    config = load_config(skill_root)
    profile_name, profile = resolve_profile(config, args.profile)
    evidence_policy = profile.get("evidence") or {}
    run_state = load_run_state(run_dir, args.ticket, profile_name)
    evidence = ensure_evidence_state(run_state, evidence_policy)
    environment = args.environment or evidence[phase].get("environment") or profile.get("e2e", {}).get("defaultEnvironment") or "local"
    output_dir = Path(args.output_dir or evidence[phase].get("outputDir") or output_dir_for_phase(args, run_dir, args.ticket, phase, environment, evidence_policy)[0])
    allowed_roots = [run_dir]
    central_root = expand_path(evidence_policy.get("centralEvidenceRoot"))
    if central_root:
        allowed_roots.append(central_root)
    output_dir = assert_inside(output_dir, allowed_roots)

    records = discover_output_artifacts(output_dir, phase, args.ticket)
    replace_discovered_artifacts(run_state, phase, records)

    videos = [record for record in records if record.get("key") == phase_video_key(phase)]
    screenshot_key = phase_screenshot_key(phase)
    screenshots = [record for record in records if screenshot_key and record.get("key") == screenshot_key]
    existing_phase_artifacts = [
        record
        for record in evidence[phase].get("artifacts") or []
        if record.get("key") == "playwrightEvidenceConfig"
    ]
    warnings = list(evidence[phase].get("warnings") or [])
    if phase == "verification" and count_records_with_extensions(records, MEDIA_EXTENSIONS) > 1:
        warnings.append("multiple verification videos found; one canonical verificationVideo was registered and the rest were marked supplemental")
    if phase == "verification" and count_records_with_extensions(records, SCREENSHOT_EXTENSIONS) > 1:
        warnings.append("multiple verification screenshots found; one canonical verificationScreenshot was registered and the rest were marked supplemental")
    if evidence[phase].get("required") and not videos:
        warnings.append(f"missing {phase} Playwright video evidence")
    if phase == "verification" and evidence[phase].get("required") and not screenshots:
        warnings.append("missing canonical verification screenshot")
    status = args.status
    if not status:
        proof_complete = bool(videos) and (phase != "verification" or not evidence[phase].get("required") or bool(screenshots))
        status = "complete" if proof_complete else ("skipped" if not evidence[phase].get("required") else "blocked")
        if evidence_policy.get("missingPolicy", "warn") == "warn" and evidence[phase].get("required") and not proof_complete:
            status = "skipped"

    phase_state = evidence[phase]
    phase_state.update(
        {
            "status": status,
            "artifacts": existing_phase_artifacts + records,
            "warnings": sorted(set(warnings)),
            "environment": environment,
            "updatedAt": now_iso(),
            "outputDir": str(output_dir),
        }
    )
    write_evidence_outputs(run_dir, args.ticket, phase, output_dir, run_state)
    write_json(run_dir / "run.json", run_state)
    print(f"[OK] {phase} evidence registered status={status} artifacts={len(records)} warnings={len(phase_state['warnings'])}")
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--phase", choices=sorted(PHASES), required=True)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--environment", default=None)
    parser.add_argument("--output-dir", default=None)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="Prepare evidence state and Playwright wrapper config.")
    add_common_args(prepare_parser)
    prepare_parser.add_argument("--required", choices=["auto", "true", "false"], default="auto")
    prepare_parser.add_argument("--ticket-type", default=None)
    prepare_parser.add_argument("--spec-paths", default="")
    prepare_parser.add_argument("--base-playwright-config", default=None)
    prepare_parser.add_argument("--no-wrapper", action="store_true")

    register_parser = subparsers.add_parser("register", help="Register discovered evidence files.")
    add_common_args(register_parser)
    register_parser.add_argument("--status", choices=sorted(STATUS_VALUES), default=None)

    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            return prepare(args)
        if args.command == "register":
            return register(args)
    except Exception as exc:
        print(f"[FAIL] evidence helper failed: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
