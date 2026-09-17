"""Unit tests for the deployable profile logging contract."""

from __future__ import annotations

import json
import math
import unittest

from tests import validate_profile_logs as logs
from tests.requirements import requirements


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

    @requirements("L3-LOG-002")
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

    @requirements("L3-LOG-001")
    def test_uri_must_be_absolute_and_query_free(self) -> None:
        for uri in ("relative", "/path?credential=secret"):
            with self.subTest(uri=uri):
                with self.assertRaisesRegex(logs.ProfileLogError, "uri"):
                    logs.parse_events(encoded(event(uri=uri)), "static")

    @requirements("L3-LOG-002")
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

    def test_load_balancer_requires_the_upstream_fields(self) -> None:
        upstream = {
            "upstream_addr": "10.0.0.1:8080",
            "upstream_status": "200",
            "upstream_connect_time": "0.001",
            "upstream_header_time": "0.002",
            "upstream_response_time": "0.003",
        }
        expected = event(**upstream)
        self.assertEqual(
            logs.parse_events(encoded(expected), "load-balancer"), [expected]
        )
        # The same event without upstream fields belongs to a different profile.
        with self.assertRaises(logs.ProfileLogError):
            logs.parse_events(encoded(event()), "load-balancer")

    def test_single_upstream_attempt_is_counted(self) -> None:
        self.assertEqual(
            logs.upstream_attempts({"upstream_addr": "10.0.0.1:8080"}), 1
        )

    def test_failover_records_one_attempt_per_peer(self) -> None:
        self.assertEqual(
            logs.upstream_attempts(
                {"upstream_addr": "10.0.0.2:8080, 10.0.0.1:8080"}
            ),
            2,
        )

    def test_attempts_within_one_upstream_group_are_counted(self) -> None:
        # NGINX separates attempts made after an internal redirect with " : ",
        # so a reader that only splits on ", " undercounts the retries.
        self.assertEqual(
            logs.upstream_attempts(
                {"upstream_addr": "10.0.0.2:8080 : 10.0.0.1:8080"}
            ),
            2,
        )
        self.assertEqual(
            logs.upstream_attempts(
                {"upstream_addr": "10.0.0.3:8080, 10.0.0.2:8080 : 10.0.0.1:8080"}
            ),
            3,
        )

    def test_websocket_requires_a_derived_connection_disposition(self) -> None:
        upstream = {
            "upstream_addr": "10.0.0.1:8080",
            "upstream_status": "101",
            "upstream_connect_time": "0.001",
            "upstream_header_time": "0.002",
            "upstream_response_time": "0.003",
        }
        expected = event(status=101, connection_upgrade="upgrade", **upstream)
        self.assertEqual(
            logs.parse_events(encoded(expected), "websocket"), [expected]
        )
        self.assertEqual(
            logs.parse_events(
                encoded(event(connection_upgrade="close", **upstream)), "websocket"
            ),
            [event(connection_upgrade="close", **upstream)],
        )

    def test_websocket_rejects_a_client_supplied_disposition(self) -> None:
        # The profile derives this value from a map, so anything other than the
        # two derived tokens means a client-controlled value reached the log.
        upstream = {
            "upstream_addr": "10.0.0.1:8080",
            "upstream_status": "200",
            "upstream_connect_time": "0.001",
            "upstream_header_time": "0.002",
            "upstream_response_time": "0.003",
        }
        for disposition in ("keep-alive", "Upgrade, close", "", "UPGRADE"):
            with self.subTest(disposition=disposition):
                invalid = event(connection_upgrade=disposition, **upstream)
                with self.assertRaises(logs.ProfileLogError):
                    logs.parse_events(encoded(invalid), "websocket")

    @requirements("L3-LIM-003")
    def test_rate_limited_requires_recognised_limit_outcomes(self) -> None:
        limits = {"limit_req_result": "PASSED", "limit_conn_result": "PASSED"}
        expected = event(**limits)
        self.assertEqual(
            logs.parse_events(encoded(expected), "rate-limited"), [expected]
        )
        for outcome in ("REJECTED", "DELAYED", "NOT_EVALUATED"):
            with self.subTest(outcome=outcome):
                valid = event(
                    limit_req_result=outcome, limit_conn_result="PASSED"
                )
                self.assertEqual(
                    logs.parse_events(encoded(valid), "rate-limited"), [valid]
                )

    @requirements("L3-LIM-003")
    def test_rate_limited_rejects_unknown_limit_outcomes(self) -> None:
        for changes in (
            {"limit_req_result": "", "limit_conn_result": "PASSED"},
            {"limit_req_result": "passed", "limit_conn_result": "PASSED"},
            {"limit_req_result": "PASSED", "limit_conn_result": "DELAYED"},
            {"limit_req_result": "PASSED", "limit_conn_result": "unknown"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(logs.ProfileLogError):
                    logs.parse_events(encoded(event(**changes)), "rate-limited")

    def test_repeated_identity_is_rejected_unless_allowed(self) -> None:
        # A scenario that issues identical requests on purpose opts in; every
        # other scenario must still fail when an identity is ambiguous.
        repeated = [event(), event()]
        with self.assertRaisesRegex(logs.ProfileLogError, "found 2"):
            logs.select_events(repeated, "/resource", "request.valid-1", 200)
        self.assertEqual(
            logs.select_events(
                repeated, "/resource", "request.valid-1", 200, allow_repeated=True
            ),
            repeated,
        )

    def test_clickhouse_requires_a_numeric_or_absent_exception_code(self) -> None:
        upstream = {
            "upstream_addr": "10.0.0.1:8123",
            "upstream_status": "200",
            "upstream_connect_time": "0.001",
            "upstream_header_time": "0.002",
            "upstream_response_time": "0.003",
        }
        for code in ("NONE", "241", "0"):
            with self.subTest(code=code):
                valid = event(clickhouse_exception_code=code, **upstream)
                self.assertEqual(
                    logs.parse_events(encoded(valid), "clickhouse"), [valid]
                )

    def test_clickhouse_rejects_an_unvalidated_exception_header(self) -> None:
        # The value comes from an upstream response header, so anything that is
        # neither digits nor the explicit absent token means it reached the log
        # without being checked.
        upstream = {
            "upstream_addr": "10.0.0.1:8123",
            "upstream_status": "200",
            "upstream_connect_time": "0.001",
            "upstream_header_time": "0.002",
            "upstream_response_time": "0.003",
        }
        for code in ("", "none", "241; DROP", "Exception 241"):
            with self.subTest(code=code):
                invalid = event(clickhouse_exception_code=code, **upstream)
                with self.assertRaises(logs.ProfileLogError):
                    logs.parse_events(encoded(invalid), "clickhouse")

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
