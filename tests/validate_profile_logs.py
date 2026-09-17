#!/usr/bin/env python3
# Requirements: L3-LOG-005
"""Validate structured access events emitted by tested NGINX profiles."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
import re
import sys
from collections.abc import Iterable

COMMON_FIELDS = {
    "timestamp",
    "request_id",
    "method",
    "uri",
    "protocol",
    "status",
    "body_bytes_sent",
    "request_time",
}
UPSTREAM_FIELDS = {
    "upstream_addr",
    "upstream_status",
    "upstream_connect_time",
    "upstream_header_time",
    "upstream_response_time",
}
WEBSOCKET_FIELDS = {"connection_upgrade"}
CLICKHOUSE_FIELDS = {"clickhouse_exception_code"}
LIMIT_FIELDS = {"limit_req_result", "limit_conn_result"}
# NGINX reports these outcomes; the profile maps the empty value, which means
# the limit was not evaluated for that location, onto an explicit token.
LIMIT_REQ_RESULTS = {
    "PASSED",
    "DELAYED",
    "REJECTED",
    "DELAYED_DRY_RUN",
    "REJECTED_DRY_RUN",
    "NOT_EVALUATED",
}
LIMIT_CONN_RESULTS = {"PASSED", "REJECTED", "REJECTED_DRY_RUN", "NOT_EVALUATED"}
TLS_FIELDS = {
    "tls_protocol",
    "tls_cipher",
    "tls_server_name",
    "tls_session_reused",
    "tls_client_verify",
}
PROFILES = {
    "static",
    "reverse-proxy",
    "load-balancer",
    "websocket",
    "rate-limited",
    "health",
    "clickhouse",
    "dynamic-upstream",
    "tls-termination",
    "mutual-tls",
    "tls-upstream",
}
REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class ProfileLogError(ValueError):
    """An access event differs from the reviewed profile contract."""


def fail(message: str) -> None:
    raise ProfileLogError(message)


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{label} must be a JSON number")
    if not math.isfinite(value) or value < 0:
        fail(f"{label} must be finite and non-negative")
    return float(value)


def _validate_common(event: dict[str, object]) -> None:
    for field in ("timestamp", "request_id", "method", "uri", "protocol"):
        if not isinstance(event[field], str) or not event[field]:
            fail(f"{field} must be a non-empty JSON string")
    try:
        timestamp = datetime.fromisoformat(event["timestamp"])
    except ValueError as exc:
        fail(f"timestamp must be ISO 8601: {exc}")
    if timestamp.tzinfo is None:
        fail("timestamp must contain a UTC offset")
    if not REQUEST_ID.fullmatch(event["request_id"]):
        fail("request_id differs from the correlation-ID policy")
    if not event["method"].isupper() or not event["method"].isalpha():
        fail("method must be an uppercase HTTP token")
    if not event["uri"].startswith("/") or "?" in event["uri"]:
        fail("uri must be an absolute path without query arguments")
    if not event["protocol"].startswith("HTTP/"):
        fail("protocol must identify HTTP")
    status = event["status"]
    if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
        fail("status must be an integer from 100 through 599")
    body_bytes = event["body_bytes_sent"]
    if isinstance(body_bytes, bool) or not isinstance(body_bytes, int) or body_bytes < 0:
        fail("body_bytes_sent must be a non-negative JSON integer")
    _number(event["request_time"], "request_time")


def parse_events(
    raw: str, profile: str, forbidden: Iterable[str] = ()
) -> list[dict[str, object]]:
    """Parse and validate every access event mixed into container logs."""
    if profile not in PROFILES:
        fail(f"unknown profile: {profile}")
    for value in forbidden:
        if value and value in raw:
            fail(f"forbidden value occurred in logs: {value}")
    upstream = profile in {
        "reverse-proxy",
        "load-balancer",
        "websocket",
        "health",
        "clickhouse",
        "dynamic-upstream",
        "tls-upstream",
    }
    websocket = profile == "websocket"
    clickhouse = profile == "clickhouse"
    limited = profile == "rate-limited"
    tls = profile in {"tls-termination", "mutual-tls"}
    fields = (
        COMMON_FIELDS
        | (UPSTREAM_FIELDS if upstream else set())
        | (WEBSOCKET_FIELDS if websocket else set())
        | (CLICKHOUSE_FIELDS if clickhouse else set())
        | (LIMIT_FIELDS if limited else set())
        | (TLS_FIELDS if tls else set())
    )
    events = []
    for line in raw.splitlines():
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"invalid JSON access event: {exc}")
        if not isinstance(event, dict):
            fail("access event must be one JSON object")
        if set(event) != fields:
            fail("access event fields differ from the profile contract")
        _validate_common(event)
        if upstream:
            for field in UPSTREAM_FIELDS:
                if not isinstance(event[field], str) or not event[field]:
                    fail(f"{field} must be a non-empty JSON string")
        if websocket:
            # The value is derived by the profile from a map, so anything
            # outside these two tokens means a client-supplied value reached
            # the log or the map was changed without updating this contract.
            if event["connection_upgrade"] not in {"upgrade", "close"}:
                fail("connection_upgrade must be 'upgrade' or 'close'")
        if clickhouse:
            code = event["clickhouse_exception_code"]
            # Either a numeric ClickHouse exception code or the explicit
            # "no exception" token. Anything else means the upstream header
            # reached the log unvalidated.
            if code != "NONE" and not (isinstance(code, str) and code.isdigit()):
                fail("clickhouse_exception_code must be digits or NONE")
        if limited:
            if event["limit_req_result"] not in LIMIT_REQ_RESULTS:
                fail("limit_req_result is not a recognised limit outcome")
            if event["limit_conn_result"] not in LIMIT_CONN_RESULTS:
                fail("limit_conn_result is not a recognised limit outcome")
        if tls:
            for field in TLS_FIELDS:
                if not isinstance(event[field], str):
                    fail(f"{field} must be a JSON string")
            if event["tls_protocol"] not in {"TLSv1.2", "TLSv1.3"}:
                fail("tls_protocol is outside the qualified versions")
            if not event["tls_cipher"]:
                fail("tls_cipher must be a non-empty JSON string")
            client_verify = event["tls_client_verify"]
            if client_verify not in {"NONE", "SUCCESS"} and not client_verify.startswith(
                "FAILED:"
            ):
                fail("tls_client_verify has an unexpected result")
        events.append(event)
    return events


def upstream_attempts(event: dict[str, object]) -> int:
    """Count upstream attempts recorded for one client request.

    NGINX writes one entry per attempt, separated by ", ". A ":" separates
    attempts made within a single upstream group after an internal redirect,
    so both separators count toward the total.
    """
    addresses = str(event["upstream_addr"])
    return sum(len(part.split(" : ")) for part in addresses.split(", "))


def select_events(
    events: Iterable[dict[str, object]],
    uri: str,
    request_id: str,
    status: int,
    allow_repeated: bool = False,
) -> list[dict[str, object]]:
    """Return the events matching the scenario identity.

    A scenario that deliberately issues many identical requests, such as
    exhausting a limit, cannot give each one its own correlation ID. Those
    scenarios set `allow_repeated`, and the caller then requires that at least
    one of the matches satisfies the remaining assertions.
    """
    matches = [
        event
        for event in events
        if event["uri"] == uri
        and event["request_id"] == request_id
        and event["status"] == status
    ]
    if not matches:
        fail("expected exactly one matching event; found 0")
    if len(matches) != 1 and not allow_repeated:
        fail(f"expected exactly one matching event; found {len(matches)}")
    return matches


def select_event(
    events: Iterable[dict[str, object]], uri: str, request_id: str, status: int
) -> dict[str, object]:
    """Require exactly one event matching the scenario identity."""
    return select_events(events, uri, request_id, status)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", choices=sorted(PROFILES), required=True
    )
    parser.add_argument("--uri", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--status", required=True, type=int)
    parser.add_argument("--forbidden", action="append", default=[])
    parser.add_argument(
        "--method",
        default="GET",
        help=(
            "request method the matching event must carry; a scenario that "
            "sends a body states it explicitly"
        ),
    )
    parser.add_argument(
        "--connection-upgrade",
        choices=("upgrade", "close"),
        help="require this derived connection disposition on the matching event",
    )
    parser.add_argument(
        "--require-field",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="require the matching event to carry this exact field value",
    )
    parser.add_argument(
        "--allow-repeated",
        action="store_true",
        help=(
            "permit several events to share the scenario identity, for a "
            "scenario that issues identical requests on purpose"
        ),
    )
    parser.add_argument(
        "--upstream-attempts",
        type=int,
        help=(
            "require exactly this many upstream attempts for the matching "
            "event, proving that failover did or did not occur"
        ),
    )
    args = parser.parse_args()

    requirements = []
    for requirement in args.require_field:
        name, separator, expected = requirement.partition("=")
        if not separator:
            parser.error("--require-field expects NAME=VALUE")
        requirements.append((name, expected))

    try:
        events = parse_events(sys.stdin.read(), args.profile, args.forbidden)
        matches = select_events(
            events, args.uri, args.request_id, args.status, args.allow_repeated
        )
    except ProfileLogError as exc:
        parser.error(str(exc))

    def unmet(event: dict[str, object]) -> str | None:
        """Return why this event fails the assertions, or None if it passes."""
        if event["method"] != args.method:
            return f"expected method {args.method}; observed {event['method']}"
        if args.connection_upgrade is not None:
            if "connection_upgrade" not in event:
                return "profile does not record a connection disposition"
            if event["connection_upgrade"] != args.connection_upgrade:
                return (
                    f"expected connection_upgrade {args.connection_upgrade}; "
                    f"observed {event['connection_upgrade']}"
                )
        for name, expected in requirements:
            if name not in event:
                return f"matching event has no field {name}"
            if str(event[name]) != expected:
                return f"expected {name} {expected}; observed {event[name]}"
        if args.upstream_attempts is not None:
            if "upstream_addr" not in event:
                return "profile does not record upstream attempts"
            observed = upstream_attempts(event)
            if observed != args.upstream_attempts:
                return (
                    f"expected {args.upstream_attempts} upstream attempts; "
                    f"observed {observed}"
                )
        return None

    # When several events share the scenario identity on purpose, the
    # assertions describe the outcome under test rather than every request that
    # happened to carry the same correlation ID, so one satisfying event is the
    # contract. Reporting the first reason keeps the failure readable.
    reasons = [unmet(event) for event in matches]
    if all(reason is not None for reason in reasons):
        parser.error(reasons[0])

    print(f"validated {args.profile} structured access event")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
