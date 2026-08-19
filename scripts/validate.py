#!/usr/bin/env python3
"""Validate portable-jira-flow public package files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SKILL_NAME = "portable-jira-flow"
REQUIRED_REFERENCES = [
    "commands.md",
    "safety.md",
    "configuration.md",
    "artifacts.md",
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
    "jira",
    "context",
    "implementationPlan",
    "validationResults",
    "manualValidation",
    "environmentReadiness",
    "environmentAcceptance",
    "prePublishValidation",
    "finalSummary",
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
    config = read_json(root / "config.example.json")
    schema = read_json(root / "config.schema.json")
    if schema.get("title") != "Portable Jira Flow Config":
        raise ValidationError("config.schema.json: unexpected title")
    if config.get("schemaVersion") != "1.0.0":
        raise ValidationError("config.example.json: schemaVersion must be 1.0.0")

    primary = set(config.get("invocation", {}).get("primaryCommands", {}))
    missing_commands = REQUIRED_COMMANDS - primary
    if missing_commands:
        raise ValidationError(f"config.example.json: missing primary commands {sorted(missing_commands)}")

    aliases = config.get("invocation", {}).get("legacyAliases", {})
    for alias in ["analyze", "branch", "check", "complete"]:
        if alias not in aliases:
            raise ValidationError(f"config.example.json: missing legacy alias {alias}")

    stages = config.get("stageRegistry", {})
    for stage_name, stage in stages.items():
        for key in ["command", "legacyAliases", "readOnly", "mayEditCode", "mayMutateEnvironment", "requiresExplicitUserIntent", "writesArtifacts"]:
            if key not in stage:
                raise ValidationError(f"stageRegistry.{stage_name}: missing {key}")

    artifacts = config.get("artifactRegistry", {})
    missing_artifacts = REQUIRED_ARTIFACTS - set(artifacts)
    if missing_artifacts:
        raise ValidationError(f"config.example.json: missing artifacts {sorted(missing_artifacts)}")
    if not artifacts["runState"].get("sourceOfTruth"):
        raise ValidationError("artifactRegistry.runState: must be sourceOfTruth")
    for name, artifact in artifacts.items():
        if artifact.get("committable") is not False:
            raise ValidationError(f"artifactRegistry.{name}: public run artifacts must be non-committable by default")

    publishing = config["profiles"]["example"]["publishing"]
    template_path, _, fragment = publishing["descriptionTemplate"].partition("#")
    if not (root / template_path).exists():
        raise ValidationError(f"config.example.json: missing description template file {template_path}")
    if fragment and fragment not in (root / template_path).read_text(encoding="utf-8"):
        raise ValidationError(f"config.example.json: missing description template fragment {fragment}")

    json.loads(strip_jsonc((root / "config.local.example.jsonc").read_text(encoding="utf-8")))


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


def validate_references(root: Path) -> None:
    for name in REQUIRED_REFERENCES:
        path = root / "references" / name
        if not path.exists():
            raise ValidationError(f"missing reference: {path}")
        if path.stat().st_size == 0:
            raise ValidationError(f"empty reference: {path}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None, help="Skill root. Defaults to this script's parent skill.")
    parser.add_argument("--public", action="store_true", help="Run public-shareability checks.")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parents[1]
    try:
        validate_frontmatter(root / "SKILL.md")
        validate_references(root)
        validate_adapters(root)
        validate_config(root)
        if args.public:
            validate_public_scan(root)
    except ValidationError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] {SKILL_NAME} validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
