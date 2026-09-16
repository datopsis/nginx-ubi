#!/usr/bin/env python3
"""Create and verify a lock-bound manifest for disconnected transfers."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import artifacts
import components


MANIFEST_NAME = "transfer-manifest.json"
MANIFEST_FIELDS = {
    "schema_version", "architecture", "repository_revision",
    "artifact_lock_sha256", "component_inventory_sha256", "files",
}
FILE_FIELDS = {"path", "size", "sha256"}
REVISION_RE = re.compile(r"^[a-f0-9]{40}(?:[a-f0-9]{24})?$")


class TransferError(ValueError):
    """A transfer set or its expected identity is invalid."""


def fail(message: str) -> None:
    raise TransferError(message)


def require_keys(value: dict, fields: set[str], label: str) -> None:
    missing = fields - value.keys()
    extra = value.keys() - fields
    if missing:
        fail(f"{label} is missing fields: {', '.join(sorted(missing))}")
    if extra:
        fail(f"{label} has unexpected fields: {', '.join(sorted(extra))}")


def validate_revision(value: str) -> str:
    if not REVISION_RE.fullmatch(value):
        fail("repository revision must be a full lowercase Git object ID")
    return value


def inventory_files(root: Path) -> list[dict]:
    if not root.is_dir():
        fail(f"transfer root is not a directory: {root}")
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            fail(f"transfer set must not contain symbolic links: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            fail(f"transfer set contains a non-regular file: {path}")
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST_NAME:
            continue
        records.append({
            "path": relative,
            "size": path.stat().st_size,
            "sha256": artifacts.sha256_file(path),
        })
    if not records:
        fail("transfer set must contain at least one payload file")
    return records


def create_manifest(
    root: Path,
    architecture: str,
    revision: str,
    lock_sha256: str,
    inventory_sha256: str,
) -> str:
    if architecture not in artifacts.ARCHES:
        fail(f"unsupported architecture: {architecture}")
    validate_revision(revision)
    artifacts.require_sha256(lock_sha256, "artifact lock")
    artifacts.require_sha256(inventory_sha256, "component inventory")
    manifest_path = root / MANIFEST_NAME
    if manifest_path.exists():
        fail(f"refusing to overwrite existing manifest: {manifest_path}")
    manifest = {
        "schema_version": 1,
        "architecture": architecture,
        "repository_revision": revision,
        "artifact_lock_sha256": lock_sha256,
        "component_inventory_sha256": inventory_sha256,
        "files": inventory_files(root),
    }
    encoded = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{MANIFEST_NAME}.", dir=root
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
        os.replace(temporary_name, manifest_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return artifacts.sha256_file(manifest_path)


def read_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read valid transfer manifest: {exc}")
    if not isinstance(value, dict):
        fail("transfer manifest must be one JSON object")
    require_keys(value, MANIFEST_FIELDS, "transfer manifest")
    if value["schema_version"] != 1:
        fail("only transfer manifest schema version 1 is supported")
    if value["architecture"] not in artifacts.ARCHES:
        fail("transfer manifest has an unsupported architecture")
    validate_revision(value["repository_revision"])
    artifacts.require_sha256(value["artifact_lock_sha256"], "artifact lock")
    artifacts.require_sha256(value["component_inventory_sha256"], "component inventory")
    files = value["files"]
    if not isinstance(files, list) or not files:
        fail("transfer manifest files must be a non-empty array")
    paths: set[str] = set()
    for index, record in enumerate(files):
        if not isinstance(record, dict):
            fail(f"transfer file {index} must be an object")
        require_keys(record, FILE_FIELDS, f"transfer file {index}")
        relative = record["path"]
        if not isinstance(relative, str) or not relative:
            fail(f"transfer file {index} path must be a non-empty string")
        parsed = Path(relative)
        if parsed.is_absolute() or ".." in parsed.parts or "\\" in relative:
            fail(f"unsafe transfer path: {relative}")
        if relative == MANIFEST_NAME or relative in paths:
            fail(f"duplicate or reserved transfer path: {relative}")
        if not isinstance(record["size"], int) or record["size"] < 0:
            fail(f"invalid transfer size for {relative}")
        artifacts.require_sha256(record["sha256"], f"transfer file {relative}")
        paths.add(relative)
    if [record["path"] for record in files] != sorted(paths):
        fail("transfer files must be sorted by path")
    return value


def verify_manifest(
    root: Path,
    expected_manifest_sha256: str,
    architecture: str,
    revision: str,
    lock_sha256: str,
    inventory_sha256: str,
) -> dict:
    artifacts.require_sha256(expected_manifest_sha256, "expected transfer manifest")
    manifest_path = root / MANIFEST_NAME
    if artifacts.sha256_file(manifest_path) != expected_manifest_sha256:
        fail("transfer manifest differs from the separately conveyed digest")
    manifest = read_manifest(manifest_path)
    expected_context = {
        "architecture": architecture,
        "repository_revision": validate_revision(revision),
        "artifact_lock_sha256": lock_sha256,
        "component_inventory_sha256": inventory_sha256,
    }
    for field, expected in expected_context.items():
        if manifest[field] != expected:
            fail(f"transfer manifest {field} differs from the expected context")
    actual = inventory_files(root)
    if actual != manifest["files"]:
        fail("transfer payload inventory, size, or SHA-256 differs from the manifest")
    return manifest


def validated_context(args: argparse.Namespace) -> tuple[str, str]:
    repository = args.repository.resolve()
    validate_revision(args.repository_revision)
    head = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD"],
        check=False, capture_output=True, text=True,
    )
    if head.returncode or head.stdout.strip() != args.repository_revision:
        fail("repository HEAD differs from the declared transfer revision")
    status = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v1"],
        check=False, capture_output=True, text=True,
    )
    if status.returncode or status.stdout:
        fail("transfer creation and verification require a clean repository checkout")

    def repository_file(path: Path, label: str) -> Path:
        resolved = path.resolve() if path.is_absolute() else (repository / path).resolve()
        if not resolved.is_relative_to(repository):
            fail(f"{label} must stay within the repository checkout")
        return resolved

    lock_path = repository_file(args.lock, "artifact lock")
    inputs_path = repository_file(args.inputs, "lock inputs")
    inventory_path = repository_file(args.inventory, "component inventory")
    lock = artifacts.validate_lock(lock_path, inputs_path)
    if lock["architecture"] != args.architecture:
        fail("supplied lock architecture differs from the transfer architecture")
    inventory = components.validate_inventory(inventory_path, repository)
    lock_sha256 = artifacts.sha256_file(lock_path)
    inventory_sha256 = artifacts.sha256_file(inventory_path)
    binding = inventory["locks"][args.architecture]
    if binding["sha256"] != lock_sha256:
        fail("supplied lock is not bound by the component inventory")
    return lock_sha256, inventory_sha256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("create", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument("--root", required=True, type=Path)
        child.add_argument("--architecture", required=True, choices=sorted(artifacts.ARCHES))
        child.add_argument("--repository-revision", required=True)
        child.add_argument("--repository", type=Path, default=Path("."))
        child.add_argument("--inputs", type=Path, default=Path("artifacts/lock-inputs.json"))
        child.add_argument("--lock", required=True, type=Path)
        child.add_argument("--inventory", type=Path, default=Path("artifacts/components.json"))
    subparsers.choices["verify"].add_argument(
        "--expected-manifest-sha256", required=True
    )
    args = parser.parse_args()
    try:
        lock_sha256, inventory_sha256 = validated_context(args)
        if args.command == "create":
            digest = create_manifest(
                args.root, args.architecture, args.repository_revision,
                lock_sha256, inventory_sha256,
            )
            print(digest)
        else:
            verify_manifest(
                args.root, args.expected_manifest_sha256, args.architecture,
                args.repository_revision, lock_sha256, inventory_sha256,
            )
            print("disconnected transfer verified")
    except (TransferError, artifacts.LockError, components.InventoryError, OSError) as exc:
        print(f"transfer verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
