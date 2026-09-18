"""Unit tests for the release tag contract.

A release tag is immutable, so a tag that turns out to be wrong cannot be
corrected — only superseded by another release. Every check here exists to
reject a tag before anything is published under it.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import release_tag  # noqa: E402

from tests.requirements import requirements  # noqa: E402

TODAY = date(2026, 9, 17)


def lock(nginx: str = "1.30.4", major: int = 9) -> Path:
    directory = Path(tempfile.mkdtemp())
    path = directory / "lock.json"
    path.write_text(
        json.dumps(
            {
                "nginx_version": nginx,
                "base_images": {
                    "builder": {
                        "reference": f"registry.access.redhat.com/ubi{major}"
                        f"/ubi-minimal:{major}.8@sha256:aa"
                    },
                    "runtime": {
                        "reference": f"registry.access.redhat.com/ubi{major}"
                        f"/ubi-micro:{major}.8@sha256:bb"
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return path


class ShapeTests(unittest.TestCase):
    @requirements("L2-EVD-001")
    def test_a_conforming_tag_is_accepted(self) -> None:
        parsed = release_tag.validate(
            "v1.30.4-ubi9-r20260917.1", lock(), [], TODAY
        )
        self.assertEqual(parsed.nginx_version, "1.30.4")
        self.assertEqual(parsed.ubi_major, 9)
        self.assertEqual(parsed.sequence, 1)

    def test_malformed_tags_are_rejected(self) -> None:
        for tag in (
            "1.30.4-ubi9-r20260917.1",          # no leading v
            "v1.30-ubi9-r20260917.1",           # version not three parts
            "v1.30.4-ubi0-r20260917.1",         # UBI major zero
            "v1.30.4-r20260917.1",              # no UBI field
            "v1.30.4-ubi9-r2026917.1",          # seven-digit date
            "v1.30.4-ubi9-r20260917.0",         # sequence zero
            "v1.30.4-ubi9-r20260917",           # no sequence
            "v1.30.4-ubi9-r20260917.1-rc1",     # trailing content
            "v1.30.4-ubi9-r20260917.01",        # leading zero in sequence
        ):
            with self.subTest(tag=tag):
                with self.assertRaises(release_tag.ReleaseTagError):
                    release_tag.validate(tag, lock(), [], TODAY)

    def test_a_date_that_does_not_exist_is_rejected(self) -> None:
        # These match the pattern. Only a calendar check rejects them.
        for stamp in ("20260230", "20260931", "20261301", "20260000"):
            with self.subTest(stamp=stamp):
                with self.assertRaisesRegex(
                    release_tag.ReleaseTagError, "real calendar date"
                ):
                    release_tag.validate(
                        f"v1.30.4-ubi9-r{stamp}.1", lock(), [], TODAY
                    )

    def test_a_leap_day_is_accepted_in_a_leap_year(self) -> None:
        release_tag.validate(
            "v1.30.4-ubi9-r20280229.1", lock(), [], date(2028, 3, 1)
        )
        with self.assertRaises(release_tag.ReleaseTagError):
            release_tag.validate(
                "v1.30.4-ubi9-r20260229.1", lock(), [], TODAY
            )


class LockAgreementTests(unittest.TestCase):
    @requirements("L2-EVD-001")
    def test_a_tag_naming_another_nginx_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(release_tag.ReleaseTagError, "the lock builds"):
            release_tag.validate(
                "v1.30.5-ubi9-r20260917.1", lock(nginx="1.30.4"), [], TODAY
            )

    def test_a_tag_naming_another_ubi_major_is_rejected(self) -> None:
        with self.assertRaisesRegex(release_tag.ReleaseTagError, "base images are"):
            release_tag.validate(
                "v1.30.4-ubi10-r20260917.1", lock(major=9), [], TODAY
            )

    def test_disagreeing_base_images_are_rejected(self) -> None:
        path = lock()
        content = json.loads(path.read_text(encoding="utf-8"))
        content["base_images"]["runtime"]["reference"] = (
            "registry.access.redhat.com/ubi10/ubi-micro:10.0@sha256:bb"
        )
        path.write_text(json.dumps(content), encoding="utf-8")
        with self.assertRaisesRegex(release_tag.ReleaseTagError, "disagree"):
            release_tag.validate("v1.30.4-ubi9-r20260917.1", path, [], TODAY)


class CalendarAndSequenceTests(unittest.TestCase):
    def test_a_future_dated_tag_is_rejected(self) -> None:
        with self.assertRaisesRegex(release_tag.ReleaseTagError, "in the future"):
            release_tag.validate(
                "v1.30.4-ubi9-r20260918.1", lock(), [], TODAY
            )

    def test_todays_date_is_accepted(self) -> None:
        release_tag.validate("v1.30.4-ubi9-r20260917.1", lock(), [], TODAY)

    def test_an_existing_tag_is_never_reused(self) -> None:
        existing = ["v1.30.4-ubi9-r20260917.1"]
        with self.assertRaisesRegex(release_tag.ReleaseTagError, "immutable"):
            release_tag.validate(
                "v1.30.4-ubi9-r20260917.1", lock(), existing, TODAY
            )

    def test_the_sequence_continues_from_the_highest_used(self) -> None:
        existing = ["v1.30.4-ubi9-r20260917.1", "v1.30.4-ubi9-r20260917.2"]
        release_tag.validate("v1.30.4-ubi9-r20260917.3", lock(), existing, TODAY)
        with self.assertRaisesRegex(release_tag.ReleaseTagError, "next unused"):
            release_tag.validate(
                "v1.30.4-ubi9-r20260917.4", lock(), existing, TODAY
            )

    @requirements("L2-EVD-001")
    def test_a_gap_is_never_back_filled(self) -> None:
        # Sequence 2 was withdrawn. It stays withdrawn: the next release is 4,
        # because reusing 2 would make two different artifacts share a name.
        existing = ["v1.30.4-ubi9-r20260917.1", "v1.30.4-ubi9-r20260917.3"]
        with self.assertRaisesRegex(release_tag.ReleaseTagError, "next unused"):
            release_tag.validate(
                "v1.30.4-ubi9-r20260917.2", lock(), existing, TODAY
            )
        release_tag.validate("v1.30.4-ubi9-r20260917.4", lock(), existing, TODAY)

    def test_sequences_are_counted_per_date(self) -> None:
        # Yesterday reaching sequence 5 does not advance today's first release.
        existing = [f"v1.30.4-ubi9-r20260916.{n}" for n in range(1, 6)]
        release_tag.validate("v1.30.4-ubi9-r20260917.1", lock(), existing, TODAY)

    def test_unrelated_tags_do_not_affect_the_sequence(self) -> None:
        existing = ["sha-abc1234", "v1.29.0-ubi9-r20260917.7", "not-a-tag", ""]
        # A tag for another NGINX version still occupies a sequence for that
        # date: the sequence is per date, not per version.
        with self.assertRaisesRegex(release_tag.ReleaseTagError, "next unused"):
            release_tag.validate(
                "v1.30.4-ubi9-r20260917.1", lock(), existing, TODAY
            )
        release_tag.validate("v1.30.4-ubi9-r20260917.8", lock(), existing, TODAY)


class RepositoryLockTests(unittest.TestCase):
    def test_the_real_locks_yield_a_consistent_identity(self) -> None:
        root = Path(__file__).resolve().parent.parent
        identities = {
            release_tag.lock_identity(path)
            for path in sorted((root / "artifacts" / "locks").glob("*.json"))
        }
        self.assertEqual(
            len(identities),
            1,
            f"the architecture locks disagree on release identity: {identities}",
        )


if __name__ == "__main__":
    unittest.main()
