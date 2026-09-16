#!/usr/bin/env python3
"""Check certificate expiry and CRL freshness for TLS lifecycle alerting."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

OPENSSL_TIME = "%b %d %H:%M:%S %Y %Z"


class TLSMaterialError(ValueError):
    """TLS material cannot be evaluated against the lifecycle policy."""


def parse_deadline(output: str, label: str) -> datetime:
    """Parse one OpenSSL name=value deadline as an aware UTC datetime."""
    lines = output.splitlines()
    prefix = f"{label}="
    if len(lines) != 1 or not lines[0].startswith(prefix):
        raise TLSMaterialError(f"expected exactly one {prefix} line")
    value = lines[0][len(prefix):]
    try:
        parsed = datetime.strptime(value, OPENSSL_TIME)
    except ValueError as exc:
        raise TLSMaterialError(f"invalid {label} value: {exc}") from exc
    return parsed.replace(tzinfo=timezone.utc)


def evaluate_deadline(
    deadline: datetime, now: datetime, warning_seconds: int
) -> tuple[str, int]:
    """Classify a certificate or CRL deadline for monitoring."""
    if deadline.tzinfo is None or now.tzinfo is None:
        raise TLSMaterialError("deadline and current time must include time zones")
    if warning_seconds <= 0:
        raise TLSMaterialError("warning window must be positive")
    remaining = int((deadline.astimezone(timezone.utc) - now.astimezone(timezone.utc)).total_seconds())
    if remaining <= 0:
        return "expired", remaining
    if remaining <= warning_seconds:
        return "warning", remaining
    return "healthy", remaining


def inspect_material(
    kind: str,
    path: Path,
    openssl: str,
    now: datetime,
    warning_seconds: int,
) -> dict[str, object]:
    """Ask OpenSSL for a public deadline and return its policy result."""
    if kind == "certificate":
        command = [openssl, "x509", "-in", str(path), "-noout", "-enddate"]
        label = "notAfter"
    elif kind == "crl":
        command = [openssl, "crl", "-in", str(path), "-noout", "-nextupdate"]
        label = "nextUpdate"
    else:
        raise TLSMaterialError(f"unknown TLS material kind: {kind}")
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TLSMaterialError(f"cannot inspect {kind} {path}: {exc}") from exc
    deadline = parse_deadline(result.stdout.strip(), label)
    status, remaining = evaluate_deadline(deadline, now, warning_seconds)
    return {
        "kind": kind,
        "path": str(path),
        "deadline": deadline.isoformat(),
        "seconds_remaining": remaining,
        "status": status,
    }


def parse_now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise TLSMaterialError(f"invalid --now value: {exc}") from exc
    if parsed.tzinfo is None:
        raise TLSMaterialError("--now must include a UTC offset")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", action="append", type=Path, default=[])
    parser.add_argument("--crl", action="append", type=Path, default=[])
    parser.add_argument("--warning-hours", type=int, default=720)
    parser.add_argument("--openssl", default="openssl")
    parser.add_argument("--now", help="ISO 8601 override for reproducible checks")
    args = parser.parse_args()
    if not args.certificate and not args.crl:
        parser.error("at least one --certificate or --crl is required")
    if args.warning_hours <= 0:
        parser.error("--warning-hours must be positive")
    try:
        now = parse_now(args.now)
        results = [
            inspect_material(kind, path, args.openssl, now, args.warning_hours * 3600)
            for kind, paths in (("certificate", args.certificate), ("crl", args.crl))
            for path in paths
        ]
    except TLSMaterialError as exc:
        print(f"TLS material check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"schema_version": 1, "results": results}, sort_keys=True))
    return 0 if all(item["status"] == "healthy" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
