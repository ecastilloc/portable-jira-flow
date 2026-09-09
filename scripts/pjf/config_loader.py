"""Shared configuration loading for portable-jira-flow helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigLoadError(Exception):
    """Raised when a configuration file cannot be loaded."""


@dataclass(frozen=True)
class LoadedConfig:
    config: dict[str, Any]
    loaded_paths: tuple[Path, ...]


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigLoadError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigLoadError(f"{path}: expected a JSON object")
    return data


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


def read_jsonc(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(strip_jsonc(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise ConfigLoadError(f"{path}: invalid JSONC: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigLoadError(f"{path}: expected a JSON object")
    return data


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            merged[key] = deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def runtime_config_paths(skill_root: Path) -> list[Path]:
    paths: list[Path] = []
    for name in ("config.defaults.json", "config.json", "config.local.json"):
        path = skill_root / name
        if path.exists():
            paths.append(path)

    profiles_local = skill_root / "profiles.local"
    if profiles_local.exists():
        paths.extend(sorted(profiles_local.glob("*.json")))
        paths.extend(sorted(profiles_local.glob("*/profile.json")))

    profiles = skill_root / "profiles"
    if profiles.exists():
        paths.extend(sorted(profiles.glob("*.local.json")))

    return paths


def load_runtime_config(skill_root: Path) -> LoadedConfig:
    config: dict[str, Any] = {}
    loaded: list[Path] = []
    for path in runtime_config_paths(skill_root):
        config = deep_merge(config, read_json(path))
        loaded.append(path)
    return LoadedConfig(config=config, loaded_paths=tuple(loaded))


def load_example_config(skill_root: Path) -> LoadedConfig:
    path = skill_root / "config.example.json"
    return LoadedConfig(config=read_json(path), loaded_paths=(path,))


def resolve_profile(config: dict[str, Any], requested: str | None) -> tuple[str | None, dict[str, Any]]:
    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        return None, {}
    if requested:
        profile = profiles.get(requested)
        return requested, profile if isinstance(profile, dict) else {}
    default = config.get("defaultProfile")
    if isinstance(default, str) and default:
        profile = profiles.get(default)
        return default, profile if isinstance(profile, dict) else {}
    if len(profiles) == 1:
        name = next(iter(profiles))
        profile = profiles[name]
        return name, profile if isinstance(profile, dict) else {}
    return None, {}
