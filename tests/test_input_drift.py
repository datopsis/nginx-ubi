"""Unit tests for reviewed-input drift reporting.

These run without network access. Live sources are exercised by the scheduled
workflow, not by the test suite: a test whose result depends on what a
publisher happens to be serving reports the internet, not the code.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import unittest
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_input_drift as drift  # noqa: E402

from tests.requirements import requirements  # noqa: E402


class FindingTests(unittest.TestCase):
    def test_equal_values_are_not_drift(self) -> None:
        self.assertFalse(drift.Finding("x", "a", "a", "").drifted)

    def test_different_values_are_drift(self) -> None:
        self.assertTrue(drift.Finding("x", "a", "b", "").drifted)

    @requirements("L2-SUP-005")
    def test_an_unreachable_source_is_not_reported_as_drift(self) -> None:
        # Silence from a publisher is not evidence that nothing changed, and
        # must not be counted as evidence that something did.
        finding = drift.Finding("x", "a", "(unreachable: URLError)", "")
        self.assertFalse(finding.drifted)


class ParsingTests(unittest.TestCase):
    def test_base_reference_is_split_into_its_parts(self) -> None:
        digest = "sha256:" + "a" * 64
        match = drift.BASE_REFERENCE.fullmatch(
            f"registry.access.redhat.com/ubi9/ubi-minimal:9.8@{digest}"
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group("repository"), "ubi9/ubi-minimal")
        self.assertEqual(match.group("tag"), "9.8")
        self.assertEqual(match.group("digest"), digest)

    def test_a_reference_without_a_digest_is_rejected(self) -> None:
        self.assertIsNone(
            drift.BASE_REFERENCE.fullmatch(
                "registry.access.redhat.com/ubi9/ubi-minimal:9.8"
            )
        )

    def test_package_versions_are_read_from_an_index_listing(self) -> None:
        body = (
            '<a href="nginx-1.30.4-1.el9.ngx.x86_64.rpm">x</a>'
            '<a href="nginx-1.30.5-1.el9.ngx.x86_64.rpm">y</a>'
            '<a href="nginx-module-njs-1.30.4-1.el9.ngx.x86_64.rpm">z</a>'
        )
        versions = {m.group("version") for m in drift.NGINX_RPM.finditer(body)}
        # The module package must not be mistaken for the server package.
        self.assertEqual(versions, {"1.30.4", "1.30.5"})


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.findings = [
            drift.Finding("NGINX package (amd64)", "1.30.4", "1.30.5", "newer"),
            drift.Finding("signing key (nginx)", "abc", "abc", "unchanged"),
            drift.Finding("base image (builder)", "sha256:aa", "(unreachable: X)", "n"),
        ]

    def test_markdown_names_the_drift_and_the_unreachable_source(self) -> None:
        report = drift.render(self.findings, "markdown")
        self.assertIn("1 input(s) have moved", report)
        self.assertIn("not evidence of no drift", report)
        self.assertIn("never edits one", report)

    def test_markdown_states_that_a_key_change_is_a_rotation(self) -> None:
        # A signing key that changes is never a routine version bump.
        report = drift.render(self.findings, "markdown")
        self.assertIn("key rotation", report)

    def test_json_counts_drift_and_unreachable_separately(self) -> None:
        report = json.loads(drift.render(self.findings, "json"))
        self.assertEqual(report["drift"], 1)
        self.assertEqual(report["unreachable"], 1)
        self.assertEqual(len(report["findings"]), 3)

    def test_no_drift_is_reported_plainly(self) -> None:
        report = drift.render(
            [drift.Finding("x", "a", "a", "unchanged")], "markdown"
        )
        self.assertIn("No drift detected", report)


class UnreachableSourceTests(unittest.TestCase):
    def test_a_failed_fetch_becomes_a_finding_rather_than_an_exception(self) -> None:
        def explode(*_args, **_kwargs):
            raise urllib.error.URLError("no route")

        original = drift.fetch
        drift.fetch = explode
        try:
            findings = drift.check_nginx(
                {
                    "nginx_version": "1.30.4",
                    "architectures": {"amd64": {"rpm_architecture": "x86_64"}},
                }
            )
        finally:
            drift.fetch = original

        self.assertEqual(len(findings), 1)
        self.assertTrue(findings[0].available.startswith("(unreachable"))
        self.assertFalse(findings[0].drifted)


class RepositoryInputTests(unittest.TestCase):
    def test_the_reviewed_inputs_are_readable_and_complete(self) -> None:
        inputs = json.loads(drift.INPUTS.read_text(encoding="utf-8"))
        self.assertIn("nginx_version", inputs)
        self.assertIn("signing_keys", inputs)
        self.assertEqual(set(inputs["base_images"]), {"builder", "runtime"})
        for reference in inputs["base_images"].values():
            self.assertIsNotNone(drift.BASE_REFERENCE.fullmatch(reference))

    def test_the_closure_report_covers_every_lock(self) -> None:
        findings = drift.check_locked_rpms()
        self.assertEqual(len(findings), len(list(drift.LOCKS.glob("*.json"))))
        for finding in findings:
            # This check never resolves, so it can never report drift.
            self.assertFalse(finding.drifted)
            self.assertIn("reviewed operation", finding.note)


if __name__ == "__main__":
    unittest.main()
