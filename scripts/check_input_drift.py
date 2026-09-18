#!/usr/bin/env python3
"""Report drift between the reviewed inputs and what the publishers now offer.

Dependabot already proposes updates for GitHub Actions, pre-commit hooks, and
the pinned Python assurance tools. The inputs it cannot see are the ones this
project pins itself: the NGINX package, the NGINX signing key, the UBI base
image digests, and the locked RPM closure.

This tool **reports**. It never edits a lock, and it is deliberately incapable
of doing so. A lock refresh is a reviewed operation with its own procedure, and
a monitor that could perform one would be a way to change build inputs without
review — exactly what the lock exists to prevent.

Exit status is 0 when the report was produced, whether or not drift was found.
Drift is a finding to route to a human, not a failure of this tool. Use
`--fail-on-drift` where a non-zero status is wanted instead.

Usage:
    python scripts/check_input_drift.py --format markdown
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "artifacts" / "lock-inputs.json"
LOCKS = ROOT / "artifacts" / "locks"

NGINX_INDEX = "https://nginx.org/packages/rhel/9/{arch}/RPMS/"
NGINX_RPM = re.compile(r'href="(nginx-(?P<version>\d+\.\d+\.\d+)-\d+\.el9\.ngx\.[a-z0-9_]+\.rpm)"')
REGISTRY_MANIFEST = "https://registry.access.redhat.com/v2/{repository}/manifests/{tag}"
BASE_REFERENCE = re.compile(
    r"^(?P<registry>[^/]+)/(?P<repository>.+):(?P<tag>[^@]+)@(?P<digest>sha256:[0-9a-f]{64})$"
)
ACCEPT = (
    "application/vnd.oci.image.index.v1+json, "
    "application/vnd.docker.distribution.manifest.list.v2+json"
)


class Finding:
    def __init__(self, area: str, pinned: str, available: str, note: str) -> None:
        self.area = area
        self.pinned = pinned
        self.available = available
        self.note = note

    @property
    def drifted(self) -> bool:
        return self.pinned != self.available and not self.available.startswith("(")


def fetch(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict, bytes]:
    context = ssl.create_default_context()
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30, context=context) as response:
        return response.status, dict(response.headers), response.read()


def check_nginx(inputs: dict) -> list[Finding]:
    """Compare the pinned NGINX version with the newest the channel offers."""
    findings = []
    pinned = inputs["nginx_version"]
    for architecture, spec in inputs["architectures"].items():
        arch = spec["rpm_architecture"]
        try:
            _, _, body = fetch(NGINX_INDEX.format(arch=arch))
        except (urllib.error.URLError, OSError) as error:
            findings.append(
                Finding(
                    f"NGINX package ({architecture})",
                    pinned,
                    f"(unreachable: {type(error).__name__})",
                    "the channel could not be read; this is not evidence of no drift",
                )
            )
            continue
        versions = sorted(
            {
                tuple(int(part) for part in match.group("version").split("."))
                for match in NGINX_RPM.finditer(body.decode("utf-8", "replace"))
            }
        )
        newest = ".".join(str(part) for part in versions[-1]) if versions else "(none)"
        findings.append(
            Finding(
                f"NGINX package ({architecture})",
                pinned,
                newest,
                "a newer stable package is published"
                if newest != pinned
                else "pinned version is the newest published",
            )
        )
    return findings


def check_signing_keys(inputs: dict) -> list[Finding]:
    """Compare each reviewed signing key with what its URL serves now."""
    import hashlib

    findings = []
    for key in inputs["signing_keys"]:
        try:
            _, _, body = fetch(key["url"])
        except (urllib.error.URLError, OSError) as error:
            findings.append(
                Finding(
                    f"signing key ({key['id']})",
                    key["sha256"][:16],
                    f"(unreachable: {type(error).__name__})",
                    "the key could not be read; this is not evidence of no drift",
                )
            )
            continue
        digest = hashlib.sha256(body).hexdigest()
        findings.append(
            Finding(
                f"signing key ({key['id']})",
                key["sha256"][:16],
                digest[:16],
                "the published key bundle changed — treat as a key rotation, "
                "never as a routine update"
                if digest != key["sha256"]
                else "unchanged",
            )
        )
    return findings


def check_base_images(inputs: dict) -> list[Finding]:
    """Compare each pinned base digest with what the tag resolves to now."""
    findings = []
    for role, reference in inputs["base_images"].items():
        match = BASE_REFERENCE.fullmatch(reference)
        if not match:
            findings.append(
                Finding(f"base image ({role})", reference, "(unparseable)", "")
            )
            continue
        url = REGISTRY_MANIFEST.format(
            repository=match.group("repository"), tag=match.group("tag")
        )
        try:
            _, headers, _ = fetch(url, {"Accept": ACCEPT})
        except (urllib.error.URLError, OSError) as error:
            findings.append(
                Finding(
                    f"base image ({role})",
                    match.group("digest")[:23],
                    f"(unreachable: {type(error).__name__})",
                    "the registry could not be read; this is not evidence of no drift",
                )
            )
            continue
        current = headers.get("Docker-Content-Digest", "(absent)")
        findings.append(
            Finding(
                f"base image ({role})",
                match.group("digest")[:23],
                current[:23],
                "the tag now resolves to different content; a refresh also moves "
                "the locked RPM closure"
                if current != match.group("digest")
                else "unchanged",
            )
        )
    return findings


def check_locked_rpms() -> list[Finding]:
    """Report what a refresh would have to re-resolve.

    The locked closure cannot be compared package by package without running a
    dependency resolution, which is the reviewed operation this tool must not
    perform. What it can state is the size of what a refresh would move.
    """
    findings = []
    for path in sorted(LOCKS.glob("*.json")):
        lock = json.loads(path.read_text(encoding="utf-8"))
        findings.append(
            Finding(
                f"locked RPM closure ({lock['architecture']})",
                f"{len(lock['packages'])} packages",
                f"{len(lock['packages'])} packages",
                "resolution is a reviewed operation and is not performed here; "
                "a base image or NGINX change above implies this closure moves too",
            )
        )
    return findings


def render(findings: list[Finding], style: str) -> str:
    drifted = [finding for finding in findings if finding.drifted]
    unreachable = [
        finding for finding in findings if finding.available.startswith("(unreachable")
    ]

    if style == "json":
        return json.dumps(
            {
                "drift": len(drifted),
                "unreachable": len(unreachable),
                "findings": [
                    {
                        "area": f.area,
                        "pinned": f.pinned,
                        "available": f.available,
                        "drifted": f.drifted,
                        "note": f.note,
                    }
                    for f in findings
                ],
            },
            indent=2,
        )

    lines = ["## Reviewed input drift", ""]
    if drifted:
        lines.append(
            f"**{len(drifted)} input(s) have moved.** Each needs a reviewed "
            f"decision, not an automatic update."
        )
    else:
        lines.append("No drift detected in the inputs this tool can read.")
    if unreachable:
        lines.append("")
        lines.append(
            f"{len(unreachable)} source(s) could not be read. That is not "
            f"evidence of no drift."
        )
    lines += ["", "| Input | Pinned | Available | Note |", "| --- | --- | --- | --- |"]
    for finding in findings:
        marker = "**moved**" if finding.drifted else "same"
        lines.append(
            f"| {finding.area} | `{finding.pinned}` | `{finding.available}` | "
            f"{marker} - {finding.note} |"
        )
    lines += [
        "",
        "Refreshing a lock is a reviewed operation with its own procedure in",
        "`docs/ARTIFACT-LIFECYCLE.md`. This report never edits one.",
        "",
        "A changed signing key is a **key rotation**, not an update: confirm the",
        "new fingerprint through independent publisher-controlled references",
        "before it is trusted.",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="exit non-zero when an input has moved",
    )
    arguments = parser.parse_args()

    inputs = json.loads(INPUTS.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    findings += check_nginx(inputs)
    findings += check_signing_keys(inputs)
    findings += check_base_images(inputs)
    findings += check_locked_rpms()

    print(render(findings, arguments.format))

    if arguments.fail_on_drift and any(f.drifted for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
