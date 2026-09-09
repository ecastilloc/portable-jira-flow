#!/usr/bin/env python3
"""Validate portable-jira-flow public package files."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from pjf.config_loader import ConfigLoadError, load_example_config, read_jsonc
from pjf.contracts import ContractError, validate_config_contract


SKILL_NAME = "portable-jira-flow"
REQUIRED_REFERENCES = [
    "commands.md",
    "safety.md",
    "configuration.md",
    "artifacts.md",
    "relationships.md",
    "evidence.md",
    "performance.md",
    "templates.md",
    "publishing.md",
]
REQUIRED_COMMANDS = {
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
REQUIRED_ARTIFACTS = {
    "runState",
    "artifactIndex",
    "legacyArtifactIndex",
    "legacyMigrationManifest",
    "jira",
    "context",
    "relationshipMap",
    "baseRefresh",
    "implementationPlan",
    "implementationSummary",
    "validationResults",
    "manualValidation",
    "reproductionEvidence",
    "verificationEvidence",
    "evidenceManifest",
    "optimizationPlan",
    "performanceBaseline",
    "performanceComparison",
    "reproductionVideo",
    "verificationVideo",
    "verificationScreenshot",
    "environmentReadiness",
    "environmentAcceptance",
    "prePublishValidation",
    "finalSummary",
    "sourcePack",
    "behaviorFacts",
    "behaviorSpecData",
    "behaviorSpecDraft",
    "behaviorCoverage",
    "behaviorImplementationPlanData",
    "behaviorImplementationPlanDraft",
}
PRIVATE_TERMS = [
    "/Users/" + "W" + "490" + "623",
    "W" + "490" + "623",
    "W" + "EX",
    "Payzer" + "ware",
    "Al" + "berto",
    "ecastillo" + "c",
    "Jerome" + "W" + "EX" + "Payzer",
    "ic" + "csafe",
    "wex" + "fsm",
]
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(password|secret|bearer|api[_-]?token)\s*[=:]\s*['\"][A-Za-z0-9_./+=-]{12,}['\"]"
)


class ValidationError(Exception):
    pass


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path}: invalid JSON: {exc}") from exc


def strip_jsonc(text: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    i = 0
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            i += 1
            continue
        if char == "/" and nxt == "/":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        output.append(char)
        i += 1
    return "".join(output)



def _matches_json_type(value: object, expected: object) -> bool:
    if isinstance(expected, list):
        return any(_matches_json_type(value, item) for item in expected)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate_schema_value(value: object, schema: dict, path: str) -> None:
    if "const" in schema and value != schema["const"]:
        raise ValidationError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValidationError(f"{path}: expected one of {schema['enum']!r}")
    if "type" in schema and not _matches_json_type(value, schema["type"]):
        raise ValidationError(f"{path}: expected JSON type {schema['type']!r}")

    schema_type = schema.get("type")
    if schema_type == "object" or (isinstance(schema_type, list) and "object" in schema_type):
        if not isinstance(value, dict):
            return
        for key in schema.get("required", []):
            if key not in value:
                raise ValidationError(f"{path}.{key}: missing required key")
        properties = schema.get("properties") or {}
        for key, child_schema in properties.items():
            if key in value and isinstance(child_schema, dict):
                validate_schema_value(value[key], child_schema, f"{path}.{key}")
    if schema_type == "array" or (isinstance(schema_type, list) and "array" in schema_type):
        if not isinstance(value, list):
            return
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_schema_value(item, item_schema, f"{path}[{index}]")


def validate_json_artifact(root: Path, schema_name: str, artifact_path: Path) -> None:
    schema = read_json(root / "schemas" / schema_name)
    document = read_json(artifact_path)
    validate_schema_value(document, schema, artifact_path.name)


def validate_v2_fixture_artifacts(root: Path) -> None:
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        run_dir = tmp / "v2" / "ABC-900"
        base = ["python3", str(root / "scripts" / "v2_contract.py"), "--skill-root", str(root)]
        commands = [
            base + [
                "specify",
                "ABC-900",
                "--run-dir",
                str(run_dir),
                "--source",
                str(root / "evals" / "fixtures" / "v2" / "feature-ticket.json"),
                "--force",
            ],
            base + ["plan", "ABC-900", "--run-dir", str(run_dir)],
        ]
        for command in commands:
            result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
            if result.returncode != 0:
                raise ValidationError(result.stderr.strip() or result.stdout.strip())
        for schema_name, artifact_name in [
            ("source-pack.v1.schema.json", "source-pack.json"),
            ("behavior-facts.v1.schema.json", "behavior-facts.json"),
            ("behavior-spec.v1.schema.json", "behavior-spec.json"),
            ("implementation-plan.v1.schema.json", "implementation-plan.json"),
            ("run-state.v2.schema.json", "run.json"),
        ]:
            validate_json_artifact(root, schema_name, run_dir / artifact_name)


def validate_frontmatter(path: Path, expected_name: str = SKILL_NAME) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValidationError(f"{path}: missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValidationError(f"{path}: unclosed YAML frontmatter")
    frontmatter = text[4:end]
    if f"name: {expected_name}" not in frontmatter:
        raise ValidationError(f"{path}: expected name {expected_name}")
    if "description:" not in frontmatter:
        raise ValidationError(f"{path}: missing description")
    if "[TODO" in text or "TODO:" in text:
        raise ValidationError(f"{path}: contains placeholder TODO text")


def iter_public_files(root: Path) -> list[Path]:
    skip_dirs = {
        ".git",
        "__pycache__",
        "node_modules",
        "profiles.local",
        ".portable-jira-flow",
        "runs",
        "coverage",
        "playwright-report",
        "test-results",
    }
    skip_files = {"config.local.json"}
    result: list[Path] = []
    for path in root.rglob("*"):
        rel_parts = set(path.relative_to(root).parts)
        if rel_parts & skip_dirs:
            continue
        if path.name in skip_files:
            continue
        if path.is_file():
            result.append(path)
    return sorted(result)


def validate_public_scan(root: Path) -> None:
    for path in iter_public_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for term in PRIVATE_TERMS:
            if term in text:
                raise ValidationError(f"{path}: contains private/local term {term!r}")
        if SECRET_ASSIGNMENT.search(text):
            raise ValidationError(f"{path}: contains a secret-looking assignment")


def validate_config(root: Path) -> None:
    defaults = read_json(root / "config.defaults.json")
    config = load_example_config(root).config
    schema = read_json(root / "config.schema.json")
    if schema.get("title") != "Portable Jira Flow Config":
        raise ValidationError("config.schema.json: unexpected title")
    try:
        validate_config_contract(defaults, root=root, public_package=True)
    except ContractError as exc:
        raise ValidationError(f"config.defaults.json: {exc}") from exc
    if defaults.get("defaultProfile") is not None:
        raise ValidationError("config.defaults.json: defaultProfile must be null")
    if defaults.get("profiles") != {}:
        raise ValidationError("config.defaults.json: must not contain executable profiles")

    try:
        validate_config_contract(config, root=root, public_package=True)
    except ContractError as exc:
        raise ValidationError(f"config.example.json: {exc}") from exc

    primary = set(config["invocation"]["primaryCommands"])
    missing_commands = REQUIRED_COMMANDS - primary
    if missing_commands:
        raise ValidationError(f"config.example.json: missing primary commands {sorted(missing_commands)}")

    aliases = config["invocation"]["legacyAliases"]
    for alias in ["analyze", "branch", "check", "complete"]:
        if alias not in aliases:
            raise ValidationError(f"config.example.json: missing legacy alias {alias}")

    missing_artifacts = REQUIRED_ARTIFACTS - set(config["artifactRegistry"])
    if missing_artifacts:
        raise ValidationError(f"config.example.json: missing artifacts {sorted(missing_artifacts)}")

    try:
        read_jsonc(root / "config.local.example.jsonc")
    except ConfigLoadError as exc:
        raise ValidationError(str(exc)) from exc


def validate_adapters(root: Path) -> None:
    templates = root / "adapters" / "templates"
    for target in ["codex", "claude", "cursor"]:
        path = templates / f"{target}.SKILL.md.tmpl"
        if not path.exists():
            raise ValidationError(f"missing adapter template: {path}")
        text = path.read_text(encoding="utf-8")
        if "{{SKILL_ROOT}}" not in text:
            raise ValidationError(f"{path}: missing {{SKILL_ROOT}} placeholder")
        validate_frontmatter(path)
        v2_path = templates / f"{target}-v2.SKILL.md.tmpl"
        if not v2_path.exists():
            raise ValidationError(f"missing v2 adapter template: {v2_path}")
        v2_text = v2_path.read_text(encoding="utf-8")
        if "{{SKILL_ROOT}}" not in v2_text:
            raise ValidationError(f"{v2_path}: missing {{SKILL_ROOT}} placeholder")
        validate_frontmatter(v2_path, "portable-jira-flow-v2")


def validate_references(root: Path) -> None:
    for name in REQUIRED_REFERENCES:
        path = root / "references" / name
        if not path.exists():
            raise ValidationError(f"missing reference: {path}")
        if path.stat().st_size == 0:
            raise ValidationError(f"empty reference: {path}")


def validate_scripts(root: Path) -> None:
    for name in ["evidence.py", "migrate_legacy_artifacts.py", "v2_contract.py", "test_v2_contract.py"]:
        path = root / "scripts" / name
        if not path.exists():
            raise ValidationError(f"missing script: {path}")
        if path.stat().st_size == 0:
            raise ValidationError(f"empty script: {path}")
    for name in ["config_loader.py", "contracts.py", "state_writer.py", "v2_contracts.py", "v2_plan.py", "v2_specify.py"]:
        path = root / "scripts" / "pjf" / name
        if not path.exists():
            raise ValidationError(f"missing shared helper: {path}")
        if path.stat().st_size == 0:
            raise ValidationError(f"empty shared helper: {path}")


def validate_v2(root: Path) -> None:
    validate_frontmatter(root / "v2" / "SKILL.md", "portable-jira-flow-v2")
    for name in ["commands.md", "behavior-contract.md", "run-state.md", "publishing.md"]:
        path = root / "v2" / "references" / name
        if not path.exists():
            raise ValidationError(f"missing v2 reference: {path}")
        if path.stat().st_size == 0:
            raise ValidationError(f"empty v2 reference: {path}")
    for name in ["behavior-spec.md"]:
        path = root / "v2" / "templates" / name
        if not path.exists():
            raise ValidationError(f"missing v2 template: {path}")
        if path.stat().st_size == 0:
            raise ValidationError(f"empty v2 template: {path}")
    for name in [
        "run-state.v1.schema.json",
        "run-state.v2.schema.json",
        "source-pack.v1.schema.json",
        "behavior-facts.v1.schema.json",
        "behavior-spec.v1.schema.json",
        "implementation-plan.v1.schema.json",
    ]:
        path = root / "schemas" / name
        if not path.exists():
            raise ValidationError(f"missing schema: {path}")
        read_json(path)
    for name in [
        "feature-ticket.json",
        "bug-ticket.json",
        "performance-ticket.json",
        "contradictory-source.md",
        "attachment-instructions.txt",
    ]:
        path = root / "evals" / "fixtures" / "v2" / name
        if not path.exists():
            raise ValidationError(f"missing v2 fixture: {path}")
        if path.stat().st_size == 0:
            raise ValidationError(f"empty v2 fixture: {path}")
    validate_v2_fixture_artifacts(root)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None, help="Skill root. Defaults to this script's parent skill.")
    parser.add_argument("--public", action="store_true", help="Run public-shareability checks.")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parents[1]
    try:
        validate_frontmatter(root / "SKILL.md")
        validate_references(root)
        validate_scripts(root)
        validate_adapters(root)
        validate_config(root)
        validate_v2(root)
        if args.public:
            validate_public_scan(root)
    except ValidationError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] {SKILL_NAME} validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
