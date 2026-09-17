"""Unit tests for TLS lifecycle deadline monitoring."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from scripts import tls_material
from tests.requirements import requirements


NOW = datetime(2026, 9, 15, 1, 2, 3, tzinfo=timezone.utc)


class TLSMaterialTests(unittest.TestCase):
    def test_parse_certificate_deadline(self) -> None:
        observed = tls_material.parse_deadline(
            "notAfter=Sep 16 01:02:03 2026 GMT", "notAfter"
        )
        self.assertEqual(observed, NOW + timedelta(days=1))

    def test_parse_crl_deadline_accepts_single_digit_day_spacing(self) -> None:
        observed = tls_material.parse_deadline(
            "nextUpdate=Sep  5 01:02:03 2026 GMT", "nextUpdate"
        )
        self.assertEqual(observed.day, 5)

    def test_deadline_rejects_wrong_label_extra_lines_and_bad_time(self) -> None:
        values = (
            "notBefore=Sep 16 01:02:03 2026 GMT",
            "notAfter=Sep 16 01:02:03 2026 GMT\nextra",
            "notAfter=not-a-time",
        )
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(tls_material.TLSMaterialError):
                    tls_material.parse_deadline(value, "notAfter")

    def test_healthy_deadline_is_outside_warning_window(self) -> None:
        self.assertEqual(
            tls_material.evaluate_deadline(
                NOW + timedelta(seconds=101), NOW, 100
            ),
            ("healthy", 101),
        )

    def test_exact_warning_boundary_is_actionable(self) -> None:
        self.assertEqual(
            tls_material.evaluate_deadline(
                NOW + timedelta(seconds=100), NOW, 100
            ),
            ("warning", 100),
        )

    def test_exact_expiry_and_past_deadlines_are_expired(self) -> None:
        self.assertEqual(
            tls_material.evaluate_deadline(NOW, NOW, 100), ("expired", 0)
        )
        self.assertEqual(
            tls_material.evaluate_deadline(
                NOW - timedelta(seconds=5), NOW, 100
            ),
            ("expired", -5),
        )

    def test_naive_times_and_nonpositive_warning_are_rejected(self) -> None:
        naive = NOW.replace(tzinfo=None)
        with self.assertRaises(tls_material.TLSMaterialError):
            tls_material.evaluate_deadline(naive, NOW, 100)
        with self.assertRaises(tls_material.TLSMaterialError):
            tls_material.evaluate_deadline(NOW, NOW, 0)

    def test_parse_now_requires_an_offset(self) -> None:
        self.assertEqual(tls_material.parse_now(NOW.isoformat()), NOW)
        with self.assertRaises(tls_material.TLSMaterialError):
            tls_material.parse_now("2026-09-15T01:02:03")

    @mock.patch("scripts.tls_material.subprocess.run")
    @requirements("L3-TLS-005")
    def test_certificate_inspection_uses_public_metadata_only(self, run: mock.Mock) -> None:
        run.return_value = subprocess.CompletedProcess(
            [], 0, stdout="notAfter=Sep 16 01:02:03 2026 GMT\n", stderr=""
        )
        result = tls_material.inspect_material(
            "certificate", Path("server.crt"), "openssl", NOW, 3600
        )
        self.assertEqual(result["status"], "healthy")
        run.assert_called_once_with(
            ["openssl", "x509", "-in", "server.crt", "-noout", "-enddate"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    @mock.patch("scripts.tls_material.subprocess.run")
    @requirements("L3-TLS-005")
    def test_crl_inspection_reports_warning(self, run: mock.Mock) -> None:
        run.return_value = subprocess.CompletedProcess(
            [], 0, stdout="nextUpdate=Sep 15 02:02:03 2026 GMT\n", stderr=""
        )
        result = tls_material.inspect_material(
            "crl", Path("client.crl"), "openssl", NOW, 7200
        )
        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["seconds_remaining"], 3600)

    @mock.patch("scripts.tls_material.subprocess.run")
    @requirements("L3-TLS-005")
    def test_openssl_failure_is_fail_closed_without_stderr_leak(self, run: mock.Mock) -> None:
        run.side_effect = subprocess.CalledProcessError(
            1, ["openssl"], stderr="sensitive diagnostic"
        )
        with self.assertRaisesRegex(
            tls_material.TLSMaterialError, "cannot inspect certificate"
        ) as raised:
            tls_material.inspect_material(
                "certificate", Path("server.crt"), "openssl", NOW, 3600
            )
        self.assertNotIn("sensitive diagnostic", str(raised.exception))

    def test_unknown_material_kind_is_rejected(self) -> None:
        with self.assertRaisesRegex(tls_material.TLSMaterialError, "unknown"):
            tls_material.inspect_material(
                "private-key", Path("server.key"), "openssl", NOW, 3600
            )


if __name__ == "__main__":
    unittest.main()
