#!/usr/bin/env python3
"""Validate the selected NGINX RPM's compiled feature inventory."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

import artifacts


ROOT_FIELDS = {
    "schema_version", "nginx_version", "nginx_rpm_version",
    "compiled_features", "compiled_optional_modules", "dynamic_module_files",
    "compiled_but_unsupported_subsystems",
}
FEATURES = {"--with-compat", "--with-file-aio", "--with-threads"}


class FeatureError(ValueError):
    """The observed NGINX build differs from the reviewed feature inventory."""


def fail(message: str) -> None:
    raise FeatureError(message)


def string_array(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        fail(f"{label} must be an array of non-empty strings")
    if value != sorted(set(value)):
        fail(f"{label} must be sorted and unique")
    return value


def validate_inventory(path: Path, inputs_path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read valid feature inventory: {exc}")
    if not isinstance(value, dict):
        fail("feature inventory must be one JSON object")
    artifacts.require_keys(value, ROOT_FIELDS, "NGINX feature inventory")
    if value["schema_version"] != 1:
        fail("only NGINX feature inventory schema version 1 is supported")
    inputs = artifacts.validate_inputs(inputs_path)
    for field in ("nginx_version", "nginx_rpm_version"):
        if value[field] != inputs[field]:
            fail(f"feature inventory {field} differs from reviewed inputs")
    features = string_array(value["compiled_features"], "compiled_features")
    if set(features) != FEATURES:
        fail("compiled feature flags differ from the reviewed feature set")
    modules = string_array(
        value["compiled_optional_modules"], "compiled_optional_modules"
    )
    for module in modules:
        if not module.startswith("--with-") or not (
            module.endswith("_module") or module in {"--with-mail", "--with-stream"}
        ):
            fail(f"invalid optional module argument: {module}")
    if string_array(value["dynamic_module_files"], "dynamic_module_files"):
        fail("the first-release package must not install dynamic module files")
    unsupported = string_array(
        value["compiled_but_unsupported_subsystems"],
        "compiled_but_unsupported_subsystems",
    )
    if unsupported != ["mail", "stream"]:
        fail("compiled but unsupported subsystems must be exactly mail and stream")
    if not {"--with-mail", "--with-stream"}.issubset(modules):
        fail("unsupported compiled subsystems are absent from the module inventory")
    return value


def validate_nginx_v(output: str, inventory: dict) -> None:
    expected_version = f"nginx version: nginx/{inventory['nginx_version']}"
    if expected_version not in output.splitlines():
        fail("nginx -V version differs from the reviewed inventory")
    marker = "configure arguments:"
    matching = [line for line in output.splitlines() if line.startswith(marker)]
    if len(matching) != 1:
        fail("nginx -V must contain exactly one configure-arguments line")
    try:
        arguments = shlex.split(matching[0][len(marker):].strip())
    except ValueError as exc:
        fail(f"cannot parse nginx configure arguments: {exc}")
    if any(item.startswith(("--add-module=", "--add-dynamic-module=")) for item in arguments):
        fail("nginx was built with an unreviewed external module path")
    actual_features = sorted(item for item in arguments if item in FEATURES)
    actual_modules = sorted(
        item for item in arguments
        if item.startswith("--with-")
        and (item.endswith("_module") or item in {"--with-mail", "--with-stream"})
    )
    if actual_features != inventory["compiled_features"]:
        fail("nginx compiled feature flags differ from the reviewed inventory")
    if actual_modules != inventory["compiled_optional_modules"]:
        fail("nginx optional modules differ from the reviewed inventory")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=Path("artifacts/nginx-features.json"))
    parser.add_argument("--inputs", type=Path, default=Path("artifacts/lock-inputs.json"))
    parser.add_argument("--nginx-v-output", type=Path, help="read output from a file instead of stdin")
    args = parser.parse_args()
    try:
        inventory = validate_inventory(args.inventory, args.inputs)
        output = (
            args.nginx_v_output.read_text(encoding="utf-8")
            if args.nginx_v_output else sys.stdin.read()
        )
        validate_nginx_v(output, inventory)
    except (FeatureError, artifacts.LockError, OSError) as exc:
        print(f"NGINX feature verification failed: {exc}", file=sys.stderr)
        return 1
    print(
        "NGINX feature inventory verified: "
        f"{len(inventory['compiled_optional_modules'])} optional modules"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
