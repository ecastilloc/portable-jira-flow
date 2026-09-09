"""Executable contracts shared by portable-jira-flow validators and helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


CONFIG_SCHEMA_VERSION = "1.0.0"
RUN_STATE_V1 = "1.0.0"
RUN_STATE_V2 = "2.0.0"

PRIMARY_COMMANDS = {
    "help",
    "doctor",
    "inspect",
    "start",
    "implement",
    "verify",
    "ready",
    "accept",
    "publish",
    "report",
    "status",
    "cleanup",
}
STATUS_VALUES = {
    "pending",
    "in_progress",
    "complete",
    "blocked",
    "failed",
    "skipped",
    "not_requested",
}
PRIVACY_LEVELS = {"public", "internal", "private", "secret-redacted"}
RETENTION_VALUES = {"keep", "keep-latest", "expire", "manual-cleanup"}
MUTABILITY_VALUES = {
    "read-only",
    "local-disposable-mutation",
    "environment-mutation",
    "destructive",
}
WORKFLOW_V2_DRAFT_MODES = {"local-run-artifact"}
WORKFLOW_V2_DURABLE_STORAGE = {"explicit-policy-only", "configured-durable-path"}


class ContractError(Exception):
    """Raised when a config or run-state contract is invalid."""


def _kind(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    return type(value).__name__


def _require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{path}: expected object, got {_kind(value)}")
    return value


def _require_array(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{path}: expected array, got {_kind(value)}")
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{path}: expected string, got {_kind(value)}")
    return value


def _require_boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{path}: expected boolean, got {_kind(value)}")
    return value


def _require_string_array(value: Any, path: str) -> list[str]:
    values = _require_array(value, path)
    for index, item in enumerate(values):
        _require_string(item, f"{path}[{index}]")
    return values


def _optional_mapping(parent: dict[str, Any], key: str, path: str) -> dict[str, Any]:
    value = parent.get(key, {})
    if value is None:
        return {}
    return _require_mapping(value, f"{path}.{key}")


def _require_enum(value: Any, path: str, allowed: set[str]) -> str:
    string = _require_string(value, path)
    if string not in allowed:
        raise ContractError(f"{path}: expected one of {sorted(allowed)}, got {string!r}")
    return string


def validate_config_contract(
    config: dict[str, Any],
    *,
    root: Path | None = None,
    public_package: bool = False,
) -> None:
    _require_mapping(config, "config")
    required = [
        "schemaVersion",
        "defaultProfile",
        "invocation",
        "stageRegistry",
        "artifactRegistry",
        "policy",
        "profiles",
    ]
    for key in required:
        if key not in config:
            raise ContractError(f"config.{key}: missing required key")
    if config.get("schemaVersion") != CONFIG_SCHEMA_VERSION:
        raise ContractError("config.schemaVersion: must be 1.0.0")
    if config.get("defaultProfile") is not None and not isinstance(config.get("defaultProfile"), str):
        raise ContractError("config.defaultProfile: expected string or null")

    invocation = _require_mapping(config["invocation"], "config.invocation")
    stage_registry = _require_mapping(config["stageRegistry"], "config.stageRegistry")
    artifact_registry = _require_mapping(config["artifactRegistry"], "config.artifactRegistry")
    _require_mapping(config["policy"], "config.policy")
    profiles = _require_mapping(config["profiles"], "config.profiles")

    _validate_invocation(invocation, stage_registry)
    _validate_stage_registry(stage_registry, invocation, artifact_registry)
    _validate_artifact_registry(artifact_registry, stage_registry, invocation, public_package)
    _validate_profiles(profiles, stage_registry, artifact_registry, public_package)
    if root:
        _validate_template_references(config, root)


def validate_runtime_config_contract(config: dict[str, Any], *, root: Path | None = None) -> None:
    if not config:
        return
    validate_config_contract(config, root=root, public_package=False)


def _validate_invocation(invocation: dict[str, Any], stage_registry: dict[str, Any]) -> None:
    primary = _require_mapping(invocation.get("primaryCommands"), "config.invocation.primaryCommands")
    missing = PRIMARY_COMMANDS - set(primary)
    if missing:
        raise ContractError(f"config.invocation.primaryCommands: missing commands {sorted(missing)}")
    for command, stages in primary.items():
        _require_string_array(stages, f"config.invocation.primaryCommands.{command}")
        for index, stage_name in enumerate(stages):
            if stage_name not in stage_registry:
                raise ContractError(
                    f"config.invocation.primaryCommands.{command}[{index}]: unknown stage {stage_name!r}"
                )

    aliases = _require_mapping(invocation.get("legacyAliases"), "config.invocation.legacyAliases")
    for alias, command in aliases.items():
        _require_string(command, f"config.invocation.legacyAliases.{alias}")
        if command not in primary:
            raise ContractError(f"config.invocation.legacyAliases.{alias}: unknown command {command!r}")

    explicit_flags = _require_mapping(invocation.get("explicitFlags"), "config.invocation.explicitFlags")
    for key, value in explicit_flags.items():
        if isinstance(value, str):
            continue
        _require_string_array(value, f"config.invocation.explicitFlags.{key}")


def _validate_stage_registry(
    stage_registry: dict[str, Any],
    invocation: dict[str, Any],
    artifact_registry: dict[str, Any],
) -> None:
    commands = set(invocation.get("primaryCommands") or {})
    artifacts = set(artifact_registry)
    for stage_name, raw_stage in stage_registry.items():
        stage = _require_mapping(raw_stage, f"config.stageRegistry.{stage_name}")
        for key in [
            "command",
            "legacyAliases",
            "readOnly",
            "mayEditCode",
            "mayMutateEnvironment",
            "requiresExplicitUserIntent",
            "writesArtifacts",
        ]:
            if key not in stage:
                raise ContractError(f"config.stageRegistry.{stage_name}.{key}: missing required key")
        command = _require_string(stage["command"], f"config.stageRegistry.{stage_name}.command")
        if command not in commands:
            raise ContractError(f"config.stageRegistry.{stage_name}.command: unknown command {command!r}")
        _require_string_array(stage["legacyAliases"], f"config.stageRegistry.{stage_name}.legacyAliases")
        _require_boolean(stage["readOnly"], f"config.stageRegistry.{stage_name}.readOnly")
        _require_boolean(stage["mayEditCode"], f"config.stageRegistry.{stage_name}.mayEditCode")
        _require_boolean(stage["mayMutateEnvironment"], f"config.stageRegistry.{stage_name}.mayMutateEnvironment")
        _require_boolean(
            stage["requiresExplicitUserIntent"],
            f"config.stageRegistry.{stage_name}.requiresExplicitUserIntent",
        )
        for artifact in _require_string_array(stage["writesArtifacts"], f"config.stageRegistry.{stage_name}.writesArtifacts"):
            if artifact not in artifacts:
                raise ContractError(
                    f"config.stageRegistry.{stage_name}.writesArtifacts: unknown artifact {artifact!r}"
                )


def _validate_artifact_registry(
    artifact_registry: dict[str, Any],
    stage_registry: dict[str, Any],
    invocation: dict[str, Any],
    public_package: bool,
) -> None:
    commands = set(invocation.get("primaryCommands") or {})
    stages = set(stage_registry)
    allowed_refs = commands | stages | {"all", "migration"}
    for artifact_name, raw_artifact in artifact_registry.items():
        artifact = _require_mapping(raw_artifact, f"config.artifactRegistry.{artifact_name}")
        for key in [
            "path",
            "producer",
            "consumers",
            "sourceOfTruth",
            "derived",
            "userFacing",
            "privacyLevel",
            "committable",
            "retention",
        ]:
            if key not in artifact:
                raise ContractError(f"config.artifactRegistry.{artifact_name}.{key}: missing required key")
        _require_string(artifact["path"], f"config.artifactRegistry.{artifact_name}.path")
        producer = _require_string(artifact["producer"], f"config.artifactRegistry.{artifact_name}.producer")
        if producer not in allowed_refs:
            raise ContractError(f"config.artifactRegistry.{artifact_name}.producer: unknown producer {producer!r}")
        for consumer in _require_string_array(
            artifact["consumers"], f"config.artifactRegistry.{artifact_name}.consumers"
        ):
            if consumer not in allowed_refs:
                raise ContractError(
                    f"config.artifactRegistry.{artifact_name}.consumers: unknown consumer {consumer!r}"
                )
        _require_boolean(artifact["sourceOfTruth"], f"config.artifactRegistry.{artifact_name}.sourceOfTruth")
        _require_boolean(artifact["derived"], f"config.artifactRegistry.{artifact_name}.derived")
        _require_boolean(artifact["userFacing"], f"config.artifactRegistry.{artifact_name}.userFacing")
        _require_enum(artifact["privacyLevel"], f"config.artifactRegistry.{artifact_name}.privacyLevel", PRIVACY_LEVELS)
        committable = _require_boolean(artifact["committable"], f"config.artifactRegistry.{artifact_name}.committable")
        if public_package and committable:
            raise ContractError(f"config.artifactRegistry.{artifact_name}.committable: public default must be false")
        _require_enum(artifact["retention"], f"config.artifactRegistry.{artifact_name}.retention", RETENTION_VALUES)


def _validate_profiles(
    profiles: dict[str, Any],
    stage_registry: dict[str, Any],
    artifact_registry: dict[str, Any],
    public_package: bool,
) -> None:
    for profile_name, raw_profile in profiles.items():
        profile = _require_mapping(raw_profile, f"config.profiles.{profile_name}")
        for key in ["displayName", "ticketPrefixes", "jira", "repositories", "workspaces"]:
            if key not in profile:
                raise ContractError(f"config.profiles.{profile_name}.{key}: missing required key")
        _require_string(profile["displayName"], f"config.profiles.{profile_name}.displayName")
        _require_string_array(profile["ticketPrefixes"], f"config.profiles.{profile_name}.ticketPrefixes")
        _require_mapping(profile["jira"], f"config.profiles.{profile_name}.jira")
        repositories = _require_array(profile["repositories"], f"config.profiles.{profile_name}.repositories")
        for index, repository in enumerate(repositories):
            _require_mapping(repository, f"config.profiles.{profile_name}.repositories[{index}]")
        _require_mapping(profile["workspaces"], f"config.profiles.{profile_name}.workspaces")

        artifacts = _optional_mapping(profile, "artifacts", f"config.profiles.{profile_name}")
        if artifacts:
            if "nonCommittable" in artifacts:
                _require_boolean(artifacts["nonCommittable"], f"config.profiles.{profile_name}.artifacts.nonCommittable")

        evidence = _optional_mapping(profile, "evidence", f"config.profiles.{profile_name}")
        if evidence:
            if "enabled" in evidence:
                _require_boolean(evidence["enabled"], f"config.profiles.{profile_name}.evidence.enabled")
            if "storage" in evidence:
                _require_enum(
                    evidence["storage"],
                    f"config.profiles.{profile_name}.evidence.storage",
                    {"central", "run", "custom"},
                )

        for index, command in enumerate(profile.get("commands") or []):
            command_obj = _require_mapping(command, f"config.profiles.{profile_name}.commands[{index}]")
            stage = _require_string(command_obj.get("stage"), f"config.profiles.{profile_name}.commands[{index}].stage")
            if stage not in stage_registry:
                raise ContractError(f"config.profiles.{profile_name}.commands[{index}].stage: unknown stage {stage!r}")
            if "mutability" in command_obj:
                _require_enum(
                    command_obj["mutability"],
                    f"config.profiles.{profile_name}.commands[{index}].mutability",
                    MUTABILITY_VALUES,
                )
            for key in ["artifacts", "nonCommittableArtifacts"]:
                if key in command_obj:
                    _require_string_array(command_obj[key], f"config.profiles.{profile_name}.commands[{index}].{key}")
            for key in ["requiredForPublish", "backupBeforeRun", "compareOnFailure"]:
                if key in command_obj:
                    _require_boolean(command_obj[key], f"config.profiles.{profile_name}.commands[{index}].{key}")

        _validate_workflow_v2(profile_name, profile)
        if public_package and profile_name == "example":
            _validate_example_profile(profile, artifact_registry)


def _validate_example_profile(profile: dict[str, Any], artifact_registry: dict[str, Any]) -> None:
    artifacts = _require_mapping(profile.get("artifacts"), "config.profiles.example.artifacts")
    if not artifacts.get("runsRoot"):
        raise ContractError("config.profiles.example.artifacts.runsRoot: missing configured run root")
    if artifacts.get("runLayout") != "ticket":
        raise ContractError("config.profiles.example.artifacts.runLayout: must default to ticket")
    if artifacts.get("nonCommittable") is not True:
        raise ContractError("config.profiles.example.artifacts.nonCommittable: must be true")
    evidence = _require_mapping(profile.get("evidence"), "config.profiles.example.evidence")
    if evidence.get("enabled") is not True:
        raise ContractError("config.profiles.example.evidence.enabled: must be true")
    if evidence.get("storage") != "central":
        raise ContractError("config.profiles.example.evidence.storage: must default to central")
    if evidence.get("missingPolicy") != "warn":
        raise ContractError("config.profiles.example.evidence.missingPolicy: must default to warn")
    relationships = _require_mapping(profile.get("relationships"), "config.profiles.example.relationships")
    if relationships.get("enabled") is not True:
        raise ContractError("config.profiles.example.relationships.enabled: must be true")
    if relationships.get("defaultRelationshipType") != "standalone":
        raise ContractError("config.profiles.example.relationships.defaultRelationshipType: must default to standalone")
    if "defect" not in relationships.get("relationshipTypes", []):
        raise ContractError("config.profiles.example.relationships.relationshipTypes: must include defect")
    if "defect" not in relationships.get("reuseParentBranchForTypes", []):
        raise ContractError("config.profiles.example.relationships.reuseParentBranchForTypes: must include defect")
    base_refresh = _require_mapping(relationships.get("baseRefresh"), "config.profiles.example.relationships.baseRefresh")
    if base_refresh.get("strategy") != "merge":
        raise ContractError("config.profiles.example.relationships.baseRefresh.strategy: must default to merge")
    for artifact_name in ["runState", "behaviorSpecDraft", "behaviorCoverage"]:
        if artifact_name not in artifact_registry:
            raise ContractError(f"config.artifactRegistry.{artifact_name}: missing v2 MVP artifact")


def _validate_workflow_v2(profile_name: str, profile: dict[str, Any]) -> None:
    workflow = profile.get("workflowV2")
    if workflow is None:
        return
    workflow = _require_mapping(workflow, f"config.profiles.{profile_name}.workflowV2")
    if "enabled" in workflow:
        _require_boolean(workflow["enabled"], f"config.profiles.{profile_name}.workflowV2.enabled")
    specs = _optional_mapping(workflow, "behaviorSpecs", f"config.profiles.{profile_name}.workflowV2")
    if specs:
        if "draftMode" in specs:
            _require_enum(
                specs["draftMode"],
                f"config.profiles.{profile_name}.workflowV2.behaviorSpecs.draftMode",
                WORKFLOW_V2_DRAFT_MODES,
            )
        if "durableStorage" in specs:
            _require_enum(
                specs["durableStorage"],
                f"config.profiles.{profile_name}.workflowV2.behaviorSpecs.durableStorage",
                WORKFLOW_V2_DURABLE_STORAGE,
            )
        if "template" in specs:
            _require_string(specs["template"], f"config.profiles.{profile_name}.workflowV2.behaviorSpecs.template")


def _validate_template_references(config: dict[str, Any], root: Path) -> None:
    config_text = (root / "config.example.json").read_text(encoding="utf-8")
    for placeholder in [
        "{ticketKey}",
        "{environment}",
        "{specPaths}",
        "{evidencePhase}",
        "{evidenceOutputDir}",
        "{playwrightConfigPath}",
    ]:
        if placeholder not in config_text:
            raise ContractError(f"config.example.json: missing E2E/evidence placeholder {placeholder}")

    for profile_name, profile in (config.get("profiles") or {}).items():
        publishing = profile.get("publishing") or {}
        refs = []
        if "descriptionTemplate" in publishing:
            refs.append((profile_name, "descriptionTemplate", publishing["descriptionTemplate"]))
        for ticket_type, template_ref in (publishing.get("descriptionTemplateByTicketType") or {}).items():
            refs.append((profile_name, f"descriptionTemplateByTicketType.{ticket_type}", template_ref))
        if "descriptionTemplateFallback" in publishing:
            refs.append((profile_name, "descriptionTemplateFallback", publishing["descriptionTemplateFallback"]))
        workflow_v2 = profile.get("workflowV2") or {}
        specs = workflow_v2.get("behaviorSpecs") or {}
        if "template" in specs:
            refs.append((profile_name, "workflowV2.behaviorSpecs.template", specs["template"]))
        for profile, field, template_ref in refs:
            path_text, _, fragment = _require_string(template_ref, f"config.profiles.{profile}.{field}").partition("#")
            path = root / path_text
            if not path.exists():
                raise ContractError(f"config.profiles.{profile}.{field}: missing template file {path_text}")
            if fragment and fragment not in path.read_text(encoding="utf-8"):
                raise ContractError(f"config.profiles.{profile}.{field}: missing template fragment {fragment}")


def validate_run_state(state: dict[str, Any], *, v2: bool = False) -> None:
    _require_mapping(state, "runState")
    expected_version = RUN_STATE_V2 if v2 else RUN_STATE_V1
    if state.get("schemaVersion") != expected_version:
        raise ContractError(f"runState.schemaVersion: expected {expected_version}")
    expected_skill = "portable-jira-flow-v2" if v2 else "portable-jira-flow"
    if state.get("skillName") != expected_skill:
        raise ContractError(f"runState.skillName: expected {expected_skill}")
    for key in ["ticketKey", "createdAt", "updatedAt"]:
        _require_string(state.get(key), f"runState.{key}")
    if state.get("profile") is not None:
        _require_string(state.get("profile"), "runState.profile")
    _require_mapping(state.get("invocation"), "runState.invocation")
    _require_mapping(state.get("stages"), "runState.stages")
    _require_mapping(state.get("policy"), "runState.policy")
    _require_array(state.get("artifacts"), "runState.artifacts")
    if v2:
        _require_mapping(state.get("behaviorSpec"), "runState.behaviorSpec")
        _require_mapping(state.get("coverage"), "runState.coverage")
        _require_mapping(state.get("provenance"), "runState.provenance")
