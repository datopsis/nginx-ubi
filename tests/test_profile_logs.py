"""Unit tests for the deployable profile logging contract."""

from __future__ import annotations

import json
import math
import unittest

from tests import validate_profile_logs as logs


def event(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "timestamp": "2026-09-15T01:02:03+00:00",
        "request_id": "request.valid-1",
        "method": "GET",
        "uri": "/resource",
        "protocol": "HTTP/1.1",
        "status": 200,
        "body_bytes_sent": 12,
        "request_time": 0.125,
    }
    value.update(changes)
    return value


def encoded(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=True)


class ProfileLogTests(unittest.TestCase):
    def test_non_access_output_is_ignored_but_valid_event_is_parsed(self) -> None:
        raw = "notice: worker started\n" + encoded(event())
        self.assertEqual(logs.parse_events(raw, "static"), [event()])

    def test_json_escaped_path_round_trips(self) -> None:
        expected = event(uri='/quote"and\\slash')
        self.assertEqual(logs.parse_events(encoded(expected), "static"), [expected])

    def test_forbidden_value_is_rejected_even_outside_access_event(self) -> None:
        raw = "error detail contains query-secret\n" + encoded(event())
        with self.assertRaisesRegex(logs.ProfileLogError, "forbidden value"):
            logs.parse_events(raw, "static", ["query-secret"])

    def test_malformed_json_event_is_rejected(self) -> None:
        with self.assertRaisesRegex(logs.ProfileLogError, "invalid JSON"):
            logs.parse_events('{"status":', "static")

    def test_missing_and_extra_fields_are_rejected(self) -> None:
        missing = event()
        del missing["request_time"]
        extra = event(unreviewed_header="secret")
        for candidate in (missing, extra):
            with self.subTest(candidate=candidate):
                with self.assertRaisesRegex(logs.ProfileLogError, "fields differ"):
                    logs.parse_events(encoded(candidate), "static")

    def test_boolean_is_not_accepted_as_an_integer_or_number(self) -> None:
        for field in ("status", "body_bytes_sent", "request_time"):
            with self.subTest(field=field):
                with self.assertRaises(logs.ProfileLogError):
                    logs.parse_events(encoded(event(**{field: True})), "static")

    def test_invalid_numeric_ranges_are_rejected(self) -> None:
        candidates = (
            event(status=99),
            event(status=600),
            event(body_bytes_sent=-1),
            event(request_time=-0.1),
            event(request_time=math.inf),
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(logs.ProfileLogError):
                    logs.parse_events(encoded(candidate), "static")

    def test_timestamp_requires_iso_8601_offset(self) -> None:
        for timestamp in ("not-a-date", "2026-09-15T01:02:03"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaisesRegex(logs.ProfileLogError, "timestamp"):
                    logs.parse_events(encoded(event(timestamp=timestamp)), "static")

    def test_request_id_policy_is_enforced(self) -> None:
        invalid = ("/slash", "a b", "-leading", "a" * 65)
        for request_id in invalid:
            with self.subTest(request_id=request_id):
                with self.assertRaisesRegex(logs.ProfileLogError, "request_id"):
                    logs.parse_events(encoded(event(request_id=request_id)), "static")

    def test_uri_must_be_absolute_and_query_free(self) -> None:
        for uri in ("relative", "/path?credential=secret"):
            with self.subTest(uri=uri):
                with self.assertRaisesRegex(logs.ProfileLogError, "uri"):
                    logs.parse_events(encoded(event(uri=uri)), "static")

    def test_upstream_profiles_require_exact_timing_fields(self) -> None:
        upstream = {
            "upstream_addr": "10.0.0.2:8443",
            "upstream_status": "200",
            "upstream_connect_time": "0.001",
            "upstream_header_time": "0.002",
            "upstream_response_time": "0.003",
        }
        expected = event(**upstream)
        self.assertEqual(
            logs.parse_events(encoded(expected), "tls-upstream"), [expected]
        )
        invalid = expected.copy()
        invalid["upstream_status"] = 200
        with self.assertRaisesRegex(logs.ProfileLogError, "upstream_status"):
            logs.parse_events(encoded(invalid), "tls-upstream")

    def test_static_profile_rejects_upstream_fields(self) -> None:
        with self.assertRaisesRegex(logs.ProfileLogError, "fields differ"):
            logs.parse_events(
                encoded(event(upstream_status="200")), "static"
            )

    def test_tls_profiles_require_qualified_protocol_and_verification_result(self) -> None:
        tls = {
            "tls_protocol": "TLSv1.3",
            "tls_cipher": "TLS_AES_256_GCM_SHA384",
            "tls_server_name": "localhost",
            "tls_session_reused": ".",
            "tls_client_verify": "SUCCESS",
        }
        expected = event(**tls)
        self.assertEqual(
            logs.parse_events(encoded(expected), "mutual-tls"), [expected]
        )
        failed = expected | {"tls_client_verify": "FAILED:self-signed certificate"}
        self.assertEqual(
            logs.parse_events(encoded(failed), "mutual-tls"), [failed]
        )
        for changes in (
            {"tls_protocol": "TLSv1.1"},
            {"tls_cipher": ""},
            {"tls_client_verify": "unexpected"},
        ):
            with self.subTest(changes=changes):
                invalid = expected | changes
                with self.assertRaises(logs.ProfileLogError):
                    logs.parse_events(encoded(invalid), "mutual-tls")

    def test_exactly_one_scenario_event_is_required(self) -> None:
        observed = [event(), event(request_id="other")]
        self.assertEqual(
            logs.select_event(observed, "/resource", "request.valid-1", 200),
            observed[0],
        )
        with self.assertRaisesRegex(logs.ProfileLogError, "found 0"):
            logs.select_event(observed, "/missing", "request.valid-1", 200)
        with self.assertRaisesRegex(logs.ProfileLogError, "found 2"):
            logs.select_event([event(), event()], "/resource", "request.valid-1", 200)


if __name__ == "__main__":
    unittest.main()
