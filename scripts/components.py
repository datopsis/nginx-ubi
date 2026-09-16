#!/usr/bin/env python3
"""Validate the reviewed runtime-component accountability inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import artifacts


class InventoryError(ValueError):
    """The component inventory is incomplete or no longer matches its locks."""


POLICY_FIELDS = {
    "id", "publisher", "component_source", "redistribution_terms",
    "license_reference", "support_lifecycle", "update_owner", "rpm_vendor",
}
COMPONENT_FIELDS = {"name", "source_rpm", "license", "policy"}
ROOT_FIELDS = {"schema_version", "locks", "policies", "components"}


def fail(message: str) -> None:
    raise InventoryError(message)


def require_keys(value: dict, expected: set[str], label: str) -> None:
    missing = expected - value.keys()
    extra = value.keys() - expected
    if missing:
        fail(f"{label} is missing fields: {', '.join(sorted(missing))}")
    if extra:
        fail(f"{label} has unexpected fields: {', '.join(sorted(extra))}")


def require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a non-empty string")
    return value


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_inventory(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read valid JSON from {path}: {exc}")
    if not isinstance(value, dict):
        fail("component inventory must be one JSON object")
    return value


def validate_inventory(inventory_path: Path, repository: Path) -> dict:
    value = read_inventory(inventory_path)
    require_keys(value, ROOT_FIELDS, "component inventory")
    if value["schema_version"] != 1:
        fail("only component inventory schema version 1 is supported")

    locks = value["locks"]
    if not isinstance(locks, dict) or set(locks) != set(artifacts.ARCHES):
        fail("inventory must bind exactly the amd64 and arm64 locks")

    lock_packages: dict[str, dict[str, dict]] = {}
    for architecture in artifacts.ARCHES:
        binding = locks[architecture]
        if not isinstance(binding, dict):
            fail(f"{architecture} lock binding must be an object")
        require_keys(binding, {"path", "sha256"}, f"{architecture} lock binding")
        relative = Path(require_text(binding["path"], f"{architecture} lock path"))
        if relative.is_absolute() or ".." in relative.parts:
            fail(f"{architecture} lock path must stay within the repository")
        lock_path = repository / relative
        expected_hash = artifacts.require_sha256(
            binding["sha256"], f"{architecture} lock SHA-256"
        )
        if expected_hash != file_sha256(lock_path):
            fail(f"{architecture} lock SHA-256 no longer matches the inventory")
        lock = artifacts.validate_lock(
            lock_path, repository / "artifacts" / "lock-inputs.json"
        )
        if lock["architecture"] != architecture:
            fail(f"{architecture} binding references the wrong architecture lock")
        lock_packages[architecture] = {item["name"]: item for item in lock["packages"]}

    policies = value["policies"]
    if not isinstance(policies, list) or not policies:
        fail("policies must be a non-empty array")
    policy_ids: set[str] = set()
    policy_vendors: dict[str, str] = {}
    for index, policy in enumerate(policies):
        if not isinstance(policy, dict):
            fail(f"policy {index} must be an object")
        require_keys(policy, POLICY_FIELDS, f"policy {index}")
        for field in POLICY_FIELDS:
            require_text(policy[field], f"policy {index} {field}")
        identifier = policy["id"]
        if identifier in policy_ids:
            fail(f"duplicate policy id: {identifier}")
        policy_ids.add(identifier)
        policy_vendors[identifier] = policy["rpm_vendor"]

    components = value["components"]
    if not isinstance(components, list) or not components:
        fail("components must be a non-empty array")
    records: dict[str, dict] = {}
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            fail(f"component {index} must be an object")
        require_keys(component, COMPONENT_FIELDS, f"component {index}")
        for field in COMPONENT_FIELDS:
            require_text(component[field], f"component {index} {field}")
        name = component["name"]
        if name in records:
            fail(f"duplicate component: {name}")
        if component["policy"] not in policy_ids:
            fail(f"component {name} references an unknown policy")
        records[name] = component

    expected_names = set(lock_packages["amd64"])
    for architecture, packages in lock_packages.items():
        if set(packages) != expected_names:
            fail(f"{architecture} package names differ from the common inventory")
    if set(records) != expected_names:
        missing = expected_names - records.keys()
        extra = records.keys() - expected_names
        fail(
            "component names differ from the locks; "
            f"missing={','.join(sorted(missing)) or '-'}; "
            f"unexpected={','.join(sorted(extra)) or '-'}"
        )

    for name, record in records.items():
        for architecture, packages in lock_packages.items():
            package = packages[name]
            if record["source_rpm"] != package["source_rpm"]:
                fail(f"{name} source RPM differs from the {architecture} lock")
            expected_policy = (
                "nginx-stable" if package["repository"] == "nginx-stable"
                else "redhat-ubi9"
            )
            if record["policy"] != expected_policy:
                fail(f"{name} has the wrong publisher policy for {architecture}")
    value["_policy_vendors"] = policy_vendors
    return value


def verify_rpms(inventory: dict, lock_path: Path, bundle: Path) -> None:
    lock = artifacts.validate_lock(lock_path)
    architecture = lock["architecture"]
    if file_sha256(lock_path) != inventory["locks"][architecture]["sha256"]:
        fail(f"supplied {architecture} lock is not the inventory-bound lock")
    records = {item["name"]: item for item in inventory["components"]}
    policy_vendors = inventory["_policy_vendors"]
    for package in lock["packages"]:
        rpm_path = bundle / "rpms" / package["filename"]
        result = subprocess.run(
            [
                "rpm", "-qp", "--queryformat",
                r"%{NAME}\t%{LICENSE}\t%{SOURCERPM}\t%{VENDOR}", str(rpm_path),
            ],
            check=False, capture_output=True, text=True,
        )
        if result.returncode:
            fail(f"cannot query RPM metadata for {package['filename']}: {result.stderr.strip()}")
        fields = result.stdout.split("\t")
        if len(fields) != 4:
            fail(f"unexpected RPM metadata for {package['filename']}")
        name, license_value, source_rpm, vendor = fields
        record = records.get(name)
        if record is None:
            fail(f"RPM {name} is absent from the component inventory")
        expected = (record["license"], record["source_rpm"], policy_vendors[record["policy"]])
        if (license_value, source_rpm, vendor) != expected:
            fail(f"RPM metadata differs from the component inventory for {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=Path("artifacts/components.json"))
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    try:
        inventory = validate_inventory(args.inventory, args.repository.resolve())
        if (args.lock is None) != (args.bundle is None):
            fail("--lock and --bundle must be supplied together")
        if args.lock is not None:
            verify_rpms(inventory, args.lock, args.bundle)
    except (InventoryError, artifacts.LockError, OSError) as exc:
        print(f"component inventory verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"component inventory verified: {len(inventory['components'])} runtime packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
