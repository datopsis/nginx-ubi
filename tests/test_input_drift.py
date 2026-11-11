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
from unittest.mock import patch
import copy
import tempfile
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_input_drift as drift  # noqa: E402
import report_input_drift as reporter  # noqa: E402

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


def report(*findings):
    return json.loads(drift.render(list(findings), "json"))


def moved(area="base image (runtime)", pinned="a", available="b"):
    return drift.Finding(area, pinned, available, "changed")


def issue_after(decision, state="open"):
    return {"number": 42, "state": state, "body": decision.marker}


class NotificationDecisionTests(unittest.TestCase):
    def setUp(self):
        self.report = report(moved())
        self.first = reporter.decide(self.report, None)
        self.issue = issue_after(self.first)

    def test_first_drift_creates_issue_and_comments(self):
        self.assertEqual(self.first.action, "create")
        self.assertIn("New: base image (runtime)", self.first.comment)
        self.assertIn("baseline", self.first.comment)

    def test_legacy_issue_receives_one_baseline_notification(self):
        decision = reporter.decide(self.report, {"state": "open", "body": "Old report"})
        self.assertEqual(decision.action, "keep")
        self.assertEqual(decision.comment, self.first.comment)
        self.assertIsNone(reporter.decide(self.report, issue_after(decision)).comment)

    def test_unchanged_drift_does_not_comment(self):
        decision = reporter.decide(self.report, self.issue)
        self.assertEqual(decision.action, "keep")
        self.assertIsNone(decision.comment)
        self.assertEqual(decision.marker, self.first.marker)

    def test_changed_drift_summarizes_new_resolved_and_changed_items(self):
        initial = report(moved(), moved("nginx"), moved("signing key"))
        previous = issue_after(reporter.decide(initial, None))
        changed = report(moved(available="c"), moved("nginx", pinned="c", available="d"),
                         moved("builder"), drift.Finding("signing key", "b", "b", "same"))
        decision = reporter.decide(changed, previous)
        self.assertEqual(decision.action, "keep")
        self.assertIn("Changed: base image (runtime): `a` → `b` became `a` → `c`", decision.comment)
        self.assertIn("Changed: nginx: `a` → `b` became `c` → `d`", decision.comment)
        self.assertIn("New: builder", decision.comment)
        self.assertIn("Resolved: signing key", decision.comment)
        self.assertNotEqual(decision.marker, self.first.marker)

    def test_resolved_drift_comments_once_and_closes(self):
        decision = reporter.decide(report(), self.issue)
        self.assertEqual(decision.action, "close")
        self.assertIn("Resolved: base image (runtime)", decision.comment)
        self.assertIn("closing this issue", decision.comment)
        repeated = reporter.decide(report(), issue_after(decision, "closed"))
        self.assertEqual(repeated.action, "keep")
        self.assertIsNone(repeated.comment)

    def test_recurring_drift_reopens_and_comments(self):
        resolved = reporter.decide(report(), self.issue)
        recurring = reporter.decide(self.report, issue_after(resolved, "closed"))
        self.assertEqual(recurring.action, "reopen")
        self.assertIn("New: base image (runtime)", recurring.comment)
        self.assertNotEqual(recurring.comment.splitlines()[-1], self.first.comment.splitlines()[-1])
        self.assertIsNone(reporter.decide(self.report, issue_after(recurring)).comment)

    def test_zero_without_an_issue_does_nothing(self):
        decision = reporter.decide(report(), None)
        self.assertEqual(decision.action, "keep")
        self.assertIsNone(decision.comment)

    def test_zero_closes_legacy_issue_once(self):
        decision = reporter.decide(report(), {"state": "open", "body": "Old report"})
        self.assertEqual(decision.action, "close")
        self.assertIn("All checked inputs are current", decision.comment)
        self.assertIsNone(reporter.decide(report(), issue_after(decision, "closed")).comment)

    def test_order_notes_and_unchanged_inputs_do_not_change_fingerprint(self):
        first = reporter.decide(report(moved("a"), moved("b")), None)
        other = moved("a")
        other.note = "different prose"
        decision = reporter.decide(
            report(moved("b"), drift.Finding("same", "x", "x", ""), other),
            issue_after(first),
        )
        self.assertIsNone(decision.comment)
        self.assertEqual(first.marker, decision.marker)

    def test_incomplete_report_cannot_resolve_previous_drift(self):
        for value in ("(unreachable: URLError)", "(absent)", "(none)", "(unparseable)"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Incomplete"):
                reporter.decide(report(moved(available=value)), self.issue)

    def test_bad_checkpoint_fails_before_reporting(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            reporter.decide(self.report, {"state": "open", "body": "<!-- input-drift:v2 x -->"})

    def test_manually_closed_unchanged_drift_reopens_without_comment(self):
        decision = reporter.decide(self.report, issue_after(self.first, "closed"))
        self.assertEqual(decision.action, "reopen")
        self.assertIsNone(decision.comment)


class PublisherTests(unittest.TestCase):
    """Exercise the real adapter against an in-memory GitHub API, without writes."""

    def setUp(self):
        self.issue = None
        self.comments = []
        self.calls = []
        self.fail_checkpoint = False
        self.api_patch = patch.object(reporter, "api", side_effect=self.api)
        self.api_patch.start()
        self.addCleanup(self.api_patch.stop)

    def api(self, repository, path, method="GET", payload=None, paginate=False):
        self.assertEqual(repository, "datopsis/nginx-ubi")
        self.calls.append((method, path, payload))
        if path.startswith("issues?"):
            return [copy.deepcopy(self.issue)] if self.issue else []
        if path.startswith("labels?"):
            return [{"name": "input-drift"}]
        if path == "issues" and method == "POST":
            self.issue = {"number": 42, "state": "open", **payload}
            return copy.deepcopy(self.issue)
        if path == "issues/42/assignees":
            self.issue["assignees"] = payload["assignees"]
            return copy.deepcopy(self.issue)
        if path.startswith("issues/42/comments?"):
            return copy.deepcopy(self.comments)
        if path == "issues/42/comments" and method == "POST":
            self.assertIn("joey-huckabee", self.issue["assignees"])
            self.comments.append(payload)
            return payload
        if path == "issues/42" and method == "PATCH":
            if "body" in payload and self.fail_checkpoint:
                raise RuntimeError("checkpoint write failed")
            self.issue.update(payload)
            return copy.deepcopy(self.issue)
        self.fail(f"Unexpected API call: {method} {path}")

    def publish(self, current):
        reporter.publish("datopsis/nginx-ubi", "joey-huckabee", current, "Current dashboard")

    def test_full_lifecycle_keeps_one_assigned_issue_and_four_comments(self):
        for current in (report(moved()), report(moved()), report(moved(available="c")),
                        report(), report(), report(moved())):
            self.publish(current)
        self.assertEqual(len(self.comments), 4)
        self.assertEqual(self.issue["state"], "open")
        self.assertEqual(sum(method == "POST" and path == "issues"
                             for method, path, _ in self.calls), 1)
        self.assertTrue(self.issue["body"].startswith("Current dashboard"))
        self.assertTrue(reporter.MARKER.search(self.issue["body"]))
        self.assertNotIn("@", "".join(c["body"] for c in self.comments))

    def test_comment_success_checkpoint_failure_retries_without_duplicate(self):
        self.fail_checkpoint = True
        with self.assertRaisesRegex(RuntimeError, "checkpoint"):
            self.publish(report(moved()))
        self.assertEqual(len(self.comments), 1)
        self.fail_checkpoint = False
        self.publish(report(moved()))
        self.assertEqual(len(self.comments), 1)
        self.assertTrue(reporter.MARKER.search(self.issue["body"]))

    def test_comment_failure_does_not_advance_checkpoint(self):
        self.publish(report(moved()))
        previous_body = self.issue["body"]
        original_api = self.api

        def failing_api(repository, path, method="GET", payload=None, paginate=False):
            if method == "POST" and path.endswith("/comments"):
                raise RuntimeError("comment failed")
            return original_api(repository, path, method, payload, paginate)

        with patch.object(reporter, "api", side_effect=failing_api):
            with self.assertRaisesRegex(RuntimeError, "comment failed"):
                self.publish(report())
        self.assertEqual(self.issue["body"], previous_body)
        self.assertEqual(self.issue["state"], "open")
        self.publish(report())
        self.assertEqual(len(self.comments), 2)
        self.assertEqual(self.issue["state"], "closed")


class SnapshotTests(unittest.TestCase):
    def test_full_base_digests_are_compared_even_when_prefix_matches(self):
        pinned, available = "sha256:" + "a" * 64, "sha256:" + "a" * 63 + "b"
        with patch.object(drift, "fetch", return_value=(200, {"Docker-Content-Digest": available}, b"")):
            findings = drift.check_base_images({"base_images": {
                "runtime": f"registry.access.redhat.com/ubi9/ubi-micro:9.8@{pinned}",
            }})
        self.assertTrue(findings[0].drifted)
        self.assertEqual(findings[0].pinned, pinned)
        self.assertEqual(findings[0].available, available)

    def test_json_and_markdown_share_one_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drift.json"
            with patch.object(sys, "argv", ["check_input_drift.py", "--json-output", str(path)]), \
                    patch.object(drift, "check_nginx", return_value=[moved()]) as nginx, \
                    patch.object(drift, "check_signing_keys", return_value=[]), \
                    patch.object(drift, "check_base_images", return_value=[]), \
                    patch.object(drift, "check_locked_rpms", return_value=[]), \
                    patch("builtins.print") as output:
                self.assertEqual(drift.main(), 0)
            nginx.assert_called_once()
            self.assertEqual(json.loads(path.read_text()), report(moved()))
            self.assertIn("1 input(s) have moved", output.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
