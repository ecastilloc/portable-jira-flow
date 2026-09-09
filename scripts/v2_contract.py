#!/usr/bin/env python3
"""Prepare and inspect portable-jira-flow v2 behavior-contract state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pjf.config_loader import load_runtime_config, resolve_profile
from pjf.contracts import ContractError, validate_run_state, validate_runtime_config_contract
from pjf.v2_inspect import status_freshness, write_inspect_artifacts
from pjf.v2_contracts import (
    behavior_template_path,
    build_v2_run_state,
    default_v2_run_dir,
    digest_text,
    render_behavior_spec,
    write_v2_state,
)


def read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_run_dir(args: argparse.Namespace, skill_root: Path, profile: dict) -> Path:
    if args.run_dir:
        return Path(args.run_dir).expanduser().resolve()
    return default_v2_run_dir(skill_root, profile, args.ticket).expanduser().resolve()


def ticket_arg(args: argparse.Namespace) -> str:
    ticket = getattr(args, "ticket_arg", None) or getattr(args, "ticket", None)
    if not ticket:
        raise ContractError("ticket: required")
    return ticket


def doctor(args: argparse.Namespace) -> int:
    skill_root = Path(args.skill_root).expanduser().resolve()
    loaded = load_runtime_config(skill_root)
    validate_runtime_config_contract(loaded.config, root=skill_root)
    profile_count = len(loaded.config.get("profiles") or {})
    print(f"[OK] v2 doctor passed loaded_files={len(loaded.loaded_paths)} profiles={profile_count}")
    return 0


def init(args: argparse.Namespace) -> int:
    skill_root = Path(args.skill_root).expanduser().resolve()
    loaded = load_runtime_config(skill_root)
    validate_runtime_config_contract(loaded.config, root=skill_root)
    profile_name, profile = resolve_profile(loaded.config, args.profile)
    run_dir = resolve_run_dir(args, skill_root, profile)
    run_dir.mkdir(parents=True, exist_ok=True)

    spec_path = run_dir / "behavior-spec.md"
    template_path = behavior_template_path(skill_root, profile)
    if args.force or not spec_path.exists():
        spec_text = render_behavior_spec(template_path, ticket=args.ticket, profile_name=profile_name)
        spec_path.write_text(spec_text, encoding="utf-8")
    else:
        spec_text = spec_path.read_text(encoding="utf-8")
    spec_digest = digest_text(spec_text)

    existing = read_json(run_dir / "run.json", {})
    state = build_v2_run_state(
        existing=existing,
        ticket=args.ticket,
        profile_name=profile_name,
        command="inspect",
        spec_path=spec_path,
        spec_digest=spec_digest,
    )
    validate_run_state(state, v2=True)
    write_v2_state(run_dir, state)
    print(f"[OK] v2 behavior contract initialized ticket={args.ticket} digest={spec_digest[:12]}")
    return 0


def inspect(args: argparse.Namespace) -> int:
    skill_root = Path(args.skill_root).expanduser().resolve()
    loaded = load_runtime_config(skill_root)
    validate_runtime_config_contract(loaded.config, root=skill_root)
    ticket = ticket_arg(args)
    args.ticket = ticket
    profile_name, profile = resolve_profile(loaded.config, args.profile)
    run_dir = resolve_run_dir(args, skill_root, profile)
    existing = {} if args.force else read_json(run_dir / "run.json", {})
    state = write_inspect_artifacts(
        run_dir=run_dir,
        ticket=ticket,
        profile_name=profile_name,
        profile=profile,
        source_paths=args.source or [],
        source_notes=args.source_note or [],
        existing_state=existing,
    )
    validate_run_state(state, v2=True)
    write_v2_state(run_dir, state)
    coverage = state.get("coverage", {}).get("summary", {})
    spec = state.get("behaviorSpec") or {}
    print(
        "[OK] v2 inspect "
        f"ticket={ticket} "
        f"sources={len(state.get('provenance', {}).get('sources') or [])} "
        f"scenarios={len(state.get('coverage', {}).get('scenarios') or [])} "
        f"planned={coverage.get('planned', 0)} "
        f"unknown={coverage.get('unknown', 0)} "
        f"open_decisions={spec.get('openDecisionCount', 0)} "
        f"digest={str(spec.get('digest') or '')[:12]}"
    )
    return 0


def status(args: argparse.Namespace) -> int:
    if args.run_dir:
        run_dir = Path(args.run_dir).expanduser().resolve()
    else:
        skill_root = Path(args.skill_root).expanduser().resolve()
        loaded = load_runtime_config(skill_root)
        validate_runtime_config_contract(loaded.config, root=skill_root)
        ticket = ticket_arg(args)
        args.ticket = ticket
        _, profile = resolve_profile(loaded.config, args.profile)
        run_dir = resolve_run_dir(args, skill_root, profile)
    state = read_json(run_dir / "run.json", {})
    validate_run_state(state, v2=True)
    spec = state.get("behaviorSpec") or {}
    coverage = (state.get("coverage") or {}).get("summary") or {}
    freshness = status_freshness(state)
    print(
        "[OK] v2 status "
        f"ticket={state.get('ticketKey')} "
        f"spec_status={spec.get('status')} "
        f"digest={str(spec.get('digest') or '')[:12]} "
        f"scenarios={len((state.get('coverage') or {}).get('scenarios') or [])} "
        f"planned={coverage.get('planned', 0)} "
        f"passed={coverage.get('passed', 0)} "
        f"unknown={coverage.get('unknown', 0)} "
        f"open_decisions={spec.get('openDecisionCount', 0)} "
        f"stale_sources={len(freshness['staleSources'])} "
        f"spec_stale={'yes' if freshness['specMarkdownStale'] or freshness['specContractStale'] else 'no'}"
    )
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Validate shared runtime config for v2 use.")
    doctor_parser.set_defaults(func=doctor)

    inspect_parser = subparsers.add_parser("inspect", help="Ingest sources and draft a v2 behavior contract.")
    inspect_parser.add_argument("ticket_arg", nargs="?")
    inspect_parser.add_argument("--ticket", default=None)
    inspect_parser.add_argument("--profile", default=None)
    inspect_parser.add_argument("--run-dir", default=None)
    inspect_parser.add_argument("--source", action="append", default=[])
    inspect_parser.add_argument("--source-note", action="append", default=[])
    inspect_parser.add_argument("--force", action="store_true")
    inspect_parser.set_defaults(func=inspect)

    init_parser = subparsers.add_parser("init", help="Create or refresh local v2 behavior-contract state.")
    init_parser.add_argument("--ticket", required=True)
    init_parser.add_argument("--profile", default=None)
    init_parser.add_argument("--run-dir", default=None)
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(func=init)

    status_parser = subparsers.add_parser("status", help="Summarize a v2 run state.")
    status_parser.add_argument("ticket_arg", nargs="?")
    status_parser.add_argument("--ticket", default=None)
    status_parser.add_argument("--profile", default=None)
    status_parser.add_argument("--run-dir", default=None)
    status_parser.set_defaults(func=status)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ContractError as exc:
        print(f"[FAIL] v2 contract failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[FAIL] v2 helper failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
