#!/usr/bin/env python3
"""Validate a release tag against the version contract and the artifact lock.

The contract is stated in `docs/VERSION.md`:

    v<nginx-version>-ubi<ubi-major>-r<YYYYMMDD>.<daily-sequence>

Pattern matching is only the first check. A tag that matches the pattern can
still be wrong: it can name an NGINX version the lock does not build, a UBI
major the base images do not come from, a date that does not exist, a future
date, or a sequence that reuses or back-fills one already published.

This runs before anything is built or pushed, so a malformed tag fails while
nothing has been published under it. Release tags are immutable, so a tag
discovered to be wrong afterwards cannot be corrected — only superseded.

Usage:
    python scripts/release_tag.py v1.30.4-ubi9-r20260917.1 \\
        --lock artifacts/locks/amd64.json \\
        --existing-tags-from -
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

TAG = re.compile(
    r"^v(?P<nginx>[0-9]+\.[0-9]+\.[0-9]+)"
    r"-ubi(?P<ubi>[1-9][0-9]*)"
    r"-r(?P<date>[0-9]{8})"
    r"\.(?P<sequence>[1-9][0-9]*)$"
)
BASE_MAJOR = re.compile(r"/ubi(?P<major>[0-9]+)/")


class ReleaseTagError(ValueError):
    """The tag does not satisfy the version contract."""


class ReleaseTag:
    def __init__(self, tag: str, nginx: str, ubi_major: int, day: date, sequence: int):
        self.tag = tag
        self.nginx_version = nginx
        self.ubi_major = ubi_major
        self.date = day
        self.sequence = sequence

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return f"ReleaseTag({self.tag!r})"


def parse(tag: str) -> ReleaseTag:
    """Parse the tag's shape and the calendar validity of its date."""
    match = TAG.fullmatch(tag)
    if not match:
        raise ReleaseTagError(
            f"{tag!r} does not match "
            f"v<nginx-version>-ubi<ubi-major>-r<YYYYMMDD>.<daily-sequence>"
        )
    stamp = match.group("date")
    try:
        day = datetime.strptime(stamp, "%Y%m%d").date()
    except ValueError:
        # 20260230 matches the pattern and is not a date.
        raise ReleaseTagError(f"{stamp} is not a real calendar date") from None
    return ReleaseTag(
        tag=tag,
        nginx=match.group("nginx"),
        ubi_major=int(match.group("ubi")),
        day=day,
        sequence=int(match.group("sequence")),
    )


def lock_identity(lock_path: Path) -> tuple[str, int]:
    """Return the NGINX version and UBI major the lock actually builds."""
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    nginx = lock["nginx_version"]

    majors = set()
    for role in ("builder", "runtime"):
        reference = lock["base_images"][role]["reference"]
        found = BASE_MAJOR.search(reference)
        if not found:
            raise ReleaseTagError(
                f"cannot determine the UBI major version from {reference!r}"
            )
        majors.add(int(found.group("major")))
    if len(majors) != 1:
        raise ReleaseTagError(
            f"the base images disagree on the UBI major version: {sorted(majors)}"
        )
    return nginx, majors.pop()


def next_sequence(day: date, existing: list[str]) -> int:
    """The next sequence for a date.

    A gap is never filled and a sequence is never reused, including one from a
    failed or withdrawn release, so this is one past the highest seen rather
    than the lowest free number.
    """
    stamp = day.strftime("%Y%m%d")
    used = []
    for tag in existing:
        match = TAG.fullmatch(tag.strip())
        if match and match.group("date") == stamp:
            used.append(int(match.group("sequence")))
    return max(used) + 1 if used else 1


def validate(
    tag: str,
    lock_path: Path,
    existing: list[str] | None = None,
    today: date | None = None,
) -> ReleaseTag:
    """Validate a tag against the lock, the calendar, and published tags."""
    parsed = parse(tag)
    existing = existing or []
    today = today or datetime.now(timezone.utc).date()

    nginx, ubi_major = lock_identity(lock_path)
    if parsed.nginx_version != nginx:
        raise ReleaseTagError(
            f"tag names NGINX {parsed.nginx_version}; the lock builds {nginx}"
        )
    if parsed.ubi_major != ubi_major:
        raise ReleaseTagError(
            f"tag names UBI {parsed.ubi_major}; the base images are UBI {ubi_major}"
        )
    if parsed.date > today:
        raise ReleaseTagError(
            f"tag is dated {parsed.date.isoformat()}, which is in the future "
            f"relative to {today.isoformat()} UTC"
        )
    if tag in {candidate.strip() for candidate in existing}:
        raise ReleaseTagError(
            f"{tag} already exists; release tags are immutable and are never reused"
        )

    expected = next_sequence(parsed.date, existing)
    if parsed.sequence != expected:
        raise ReleaseTagError(
            f"tag uses daily sequence {parsed.sequence}; the next unused "
            f"sequence for {parsed.date.isoformat()} is {expected}. A gap is "
            f"never back-filled and a withdrawn sequence is never reused."
        )
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument(
        "--existing-tags-from",
        type=argparse.FileType("r", encoding="utf-8"),
        help="file of existing release tags, one per line; - reads standard input",
    )
    parser.add_argument(
        "--today",
        help="UTC date as YYYY-MM-DD, for testing the future-date rule",
    )
    arguments = parser.parse_args()

    existing = (
        arguments.existing_tags_from.read().splitlines()
        if arguments.existing_tags_from
        else []
    )
    today = date.fromisoformat(arguments.today) if arguments.today else None

    try:
        parsed = validate(arguments.tag, arguments.lock, existing, today)
    except (ReleaseTagError, KeyError, OSError) as error:
        print(f"release tag rejected: {error}", file=sys.stderr)
        return 1

    print(
        f"release tag accepted: {parsed.tag} "
        f"(NGINX {parsed.nginx_version}, UBI {parsed.ubi_major}, "
        f"{parsed.date.isoformat()}, sequence {parsed.sequence})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
