#!/usr/bin/env python3
"""Inventory, copy, and verify legacy Jira workflow run artifacts.

This helper copies immediate ticket directories from old run roots into:

    {targetRoot}/legacy-runs/{sourceSlug}/{ticketKey}/

It never rewrites source artifacts and never inspects file contents beyond
size and SHA-256 checksums.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
CHUNK_SIZE = 1024 * 1024


class MigrationError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-._").lower()
    return slug or "source"


def default_source_label(source_root: Path) -> str:
    parts = source_root.parts
    if len(parts) >= 3 and parts[-1] == "runs" and parts[-2].startswith("."):
        return slugify(f"{parts[-3]}-{parts[-2].lstrip('.')}")
    if len(parts) >= 2 and parts[-1] == "runs":
        return slugify(f"{parts[-2]}-runs")
    return slugify(source_root.name)


def parse_sources(args: argparse.Namespace) -> list[dict[str, Any]]:
    roots = [resolve_path(value) for value in args.source_root]
    labels = args.source_label or []
    if labels and len(labels) != len(roots):
        raise MigrationError("--source-label must be supplied once per --source-root when used")

    sources: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for index, root in enumerate(roots):
        label = slugify(labels[index]) if labels else default_source_label(root)
        if label in seen_labels:
            raise MigrationError(f"duplicate source label after normalization: {label}")
        seen_labels.add(label)
        sources.append({"label": label, "sourceRoot": root})
    return sources


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def file_record(path: Path, ticket_dir: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "relativePath": path.relative_to(ticket_dir).as_posix(),
        "bytes": stat.st_size,
        "sha256": sha256_file(path),
        "modifiedAt": mtime_iso(path),
    }


def scan_ticket(ticket_dir: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    byte_count = 0

    for path in sorted(ticket_dir.rglob("*")):
        relative_path = path.relative_to(ticket_dir).as_posix()
        if path.is_symlink():
            skipped.append({"relativePath": relative_path, "reason": "symlink"})
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            skipped.append({"relativePath": relative_path, "reason": "not-a-regular-file"})
            continue
        record = file_record(path, ticket_dir)
        byte_count += int(record["bytes"])
        files.append(record)

    return {
        "ticketKey": ticket_dir.name,
        "sourcePath": str(ticket_dir),
        "fileCount": len(files),
        "byteCount": byte_count,
        "skipped": skipped,
        "files": files,
    }


def scan_source(source: dict[str, Any]) -> dict[str, Any]:
    source_root: Path = source["sourceRoot"]
    if not source_root.exists():
        raise MigrationError(f"source root does not exist: {source_root}")
    if not source_root.is_dir():
        raise MigrationError(f"source root is not a directory: {source_root}")

    tickets: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for child in sorted(source_root.iterdir()):
        if child.is_symlink():
            skipped.append({"relativePath": child.name, "reason": "symlink"})
            continue
        if child.is_dir():
            tickets.append(scan_ticket(child))
            continue
        skipped.append({"relativePath": child.name, "reason": "not-a-ticket-directory"})

    return {
        "label": source["label"],
        "sourceRoot": str(source_root),
        "ticketCount": len(tickets),
        "fileCount": sum(ticket["fileCount"] for ticket in tickets),
        "byteCount": sum(ticket["byteCount"] for ticket in tickets),
        "skipped": skipped,
        "tickets": tickets,
    }


def build_manifest(command: str, sources: list[dict[str, Any]], target_root: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    source_records = [scan_source(source) for source in sources]
    skipped_count = sum(len(source["skipped"]) for source in source_records)
    skipped_count += sum(len(ticket["skipped"]) for source in source_records for ticket in source["tickets"])
    manifest: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "tool": "portable-jira-flow legacy artifact migration",
        "command": command,
        "generatedAt": now_iso(),
        "dryRun": dry_run,
        "sources": source_records,
        "summary": {
            "sourceCount": len(source_records),
            "ticketCount": sum(source["ticketCount"] for source in source_records),
            "fileCount": sum(source["fileCount"] for source in source_records),
            "byteCount": sum(source["byteCount"] for source in source_records),
            "skippedCount": skipped_count,
        },
    }
    if target_root is not None:
        manifest["targetRoot"] = str(target_root)
        manifest["legacyArchiveRoot"] = str(target_root / "legacy-runs")
        manifest["migrationManifestRoot"] = str(target_root / "migration-manifests")
    return manifest


def summarize(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    return (
        f"sources={summary['sourceCount']} tickets={summary['ticketCount']} "
        f"files={summary['fileCount']} bytes={summary['byteCount']} skipped={summary['skippedCount']}"
    )


def copy_artifacts(manifest: dict[str, Any], target_root: Path) -> dict[str, Any]:
    archive_root = target_root / "legacy-runs"
    copied = 0
    unchanged = 0
    conflicts: list[dict[str, str]] = []

    for source in manifest["sources"]:
        source_label = source["label"]
        for ticket in source["tickets"]:
            source_ticket_dir = Path(ticket["sourcePath"])
            target_ticket_dir = archive_root / source_label / ticket["ticketKey"]
            ticket["targetPath"] = str(target_ticket_dir)
            for record in ticket["files"]:
                relative_path = Path(record["relativePath"])
                source_file = source_ticket_dir / relative_path
                target_file = target_ticket_dir / relative_path

                if target_file.exists():
                    if not target_file.is_file():
                        conflicts.append({
                            "targetPath": str(target_file),
                            "reason": "target-exists-not-file",
                        })
                        continue
                    if sha256_file(target_file) == record["sha256"]:
                        unchanged += 1
                        continue
                    conflicts.append({
                        "targetPath": str(target_file),
                        "reason": "target-exists-different-checksum",
                    })
                    continue

                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)
                if sha256_file(target_file) != record["sha256"]:
                    conflicts.append({
                        "targetPath": str(target_file),
                        "reason": "copied-checksum-mismatch",
                    })
                    continue
                copied += 1

    return {
        "copied": copied,
        "unchanged": unchanged,
        "conflictCount": len(conflicts),
        "conflicts": conflicts,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def relative_display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def write_legacy_index(target_root: Path) -> Path:
    archive_root = target_root / "legacy-runs"
    manifest_root = target_root / "migration-manifests"
    rows: list[dict[str, Any]] = []
    total_files = 0
    total_bytes = 0

    if archive_root.exists():
        for source_dir in sorted(path for path in archive_root.iterdir() if path.is_dir()):
            for ticket_dir in sorted(path for path in source_dir.iterdir() if path.is_dir()):
                file_count = 0
                byte_count = 0
                for path in ticket_dir.rglob("*"):
                    if path.is_symlink() or not path.is_file():
                        continue
                    file_count += 1
                    byte_count += path.stat().st_size
                total_files += file_count
                total_bytes += byte_count
                rows.append({
                    "source": source_dir.name,
                    "ticket": ticket_dir.name,
                    "files": file_count,
                    "bytes": byte_count,
                    "path": relative_display(ticket_dir, target_root),
                })

    manifest_files = sorted(manifest_root.glob("migration-manifest-*.json")) if manifest_root.exists() else []

    lines = [
        "# Legacy Artifact Index",
        "",
        f"Generated: {now_iso()}",
        "",
        "Imported legacy runs are immutable audit archives. Active workflow state remains under `runs/{ticketKey}/`.",
        "",
        "## Totals",
        "",
        f"- Sources: {len({row['source'] for row in rows})}",
        f"- Tickets: {len(rows)}",
        f"- Files: {total_files}",
        f"- Bytes: {total_bytes}",
        "",
        "## Imported Runs",
        "",
    ]
    if rows:
        lines.extend([
            "| Source | Ticket | Files | Bytes | Path |",
            "|---|---|---:|---:|---|",
        ])
        for row in rows:
            lines.append(f"| {row['source']} | {row['ticket']} | {row['files']} | {row['bytes']} | `{row['path']}` |")
    else:
        lines.append("_No legacy artifacts imported._")

    lines.extend([
        "",
        "## Migration Manifests",
        "",
    ])
    if manifest_files:
        for path in manifest_files:
            lines.append(f"- `{relative_display(path, target_root)}`")
    else:
        lines.append("_No migration manifests found._")

    index_path = target_root / "legacy-artifact-index.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index_path


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MigrationError(f"invalid JSON manifest {path}: {exc}") from exc


def verify_manifest(manifest_path: Path) -> int:
    manifest = read_json(manifest_path)
    archive_root = Path(manifest.get("legacyArchiveRoot", ""))
    verified = 0
    missing: list[str] = []
    mismatched: list[str] = []

    for source in manifest.get("sources", []):
        for ticket in source.get("tickets", []):
            target_ticket_dir = Path(ticket.get("targetPath") or archive_root / source["label"] / ticket["ticketKey"])
            for record in ticket.get("files", []):
                path = target_ticket_dir / Path(record["relativePath"])
                if not path.exists():
                    missing.append(str(path))
                    continue
                if not path.is_file():
                    mismatched.append(str(path))
                    continue
                if sha256_file(path) != record["sha256"]:
                    mismatched.append(str(path))
                    continue
                verified += 1

    if missing or mismatched:
        print(
            f"[FAIL] verified={verified} missing={len(missing)} mismatched={len(mismatched)} "
            f"manifest={manifest_path}",
            file=sys.stderr,
        )
        for path in (missing + mismatched)[:10]:
            print(f"  {path}", file=sys.stderr)
        return 1

    print(f"[OK] verified={verified} manifest={manifest_path}")
    return 0


def command_inventory(args: argparse.Namespace) -> int:
    manifest = build_manifest("inventory", parse_sources(args))
    print(f"[OK] inventoried legacy artifacts {summarize(manifest)}")
    return 0


def command_copy(args: argparse.Namespace) -> int:
    target_root = resolve_path(args.target_root)
    manifest = build_manifest("copy", parse_sources(args), target_root=target_root, dry_run=args.dry_run)

    if args.dry_run:
        print(f"[OK] dry-run legacy artifact copy {summarize(manifest)} targetRoot={target_root}")
        return 0

    copy_result = copy_artifacts(manifest, target_root)
    manifest["copy"] = copy_result
    manifest["summary"].update({
        "copied": copy_result["copied"],
        "unchanged": copy_result["unchanged"],
        "conflictCount": copy_result["conflictCount"],
    })

    manifest_path = target_root / "migration-manifests" / f"migration-manifest-{now_stamp()}.json"
    write_json(manifest_path, manifest)
    index_path = write_legacy_index(target_root)

    if copy_result["conflictCount"]:
        print(
            f"[FAIL] copied with conflicts {summarize(manifest)} "
            f"copied={copy_result['copied']} unchanged={copy_result['unchanged']} "
            f"conflicts={copy_result['conflictCount']} manifest={manifest_path}",
            file=sys.stderr,
        )
        return 2

    print(
        f"[OK] copied legacy artifacts {summarize(manifest)} copied={copy_result['copied']} "
        f"unchanged={copy_result['unchanged']} manifest={manifest_path} index={index_path}"
    )
    return 0


def command_verify(args: argparse.Namespace) -> int:
    return verify_manifest(resolve_path(args.manifest))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_source_args(command: argparse.ArgumentParser) -> None:
        command.add_argument("--source-root", action="append", required=True, help="Legacy run root containing ticket directories.")
        command.add_argument("--source-label", action="append", default=None, help="Stable label for the matching source root.")

    inventory = subparsers.add_parser("inventory", help="Checksum and count legacy artifacts without writing files.")
    add_source_args(inventory)
    inventory.set_defaults(func=command_inventory)

    copy = subparsers.add_parser("copy", help="Copy legacy artifacts into a central archive and write a manifest.")
    add_source_args(copy)
    copy.add_argument("--target-root", required=True, help="Portable Jira Flow state root, not the runs subdirectory.")
    copy.add_argument("--dry-run", action="store_true", help="Report what would be copied without writing files.")
    copy.set_defaults(func=command_copy)

    verify = subparsers.add_parser("verify", help="Verify a migration manifest against copied archive files.")
    verify.add_argument("--manifest", required=True, help="Migration manifest path.")
    verify.set_defaults(func=command_verify)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except MigrationError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
