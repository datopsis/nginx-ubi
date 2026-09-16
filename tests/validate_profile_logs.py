#!/usr/bin/env python3
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
    upstream = profile in {"reverse-proxy", "load-balancer", "tls-upstream"}
    tls = profile in {"tls-termination", "mutual-tls"}
    fields = (
        COMMON_FIELDS
        | (UPSTREAM_FIELDS if upstream else set())
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


def select_event(
    events: Iterable[dict[str, object]], uri: str, request_id: str, status: int
) -> dict[str, object]:
    """Require exactly one event matching the scenario identity."""
    matches = [
        event
        for event in events
        if event["uri"] == uri
        and event["request_id"] == request_id
        and event["status"] == status
    ]
    if len(matches) != 1:
        fail(f"expected exactly one matching event; found {len(matches)}")
    return matches[0]


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
        "--upstream-attempts",
        type=int,
        help=(
            "require exactly this many upstream attempts for the matching "
            "event, proving that failover did or did not occur"
        ),
    )
    args = parser.parse_args()

    try:
        events = parse_events(sys.stdin.read(), args.profile, args.forbidden)
        event = select_event(events, args.uri, args.request_id, args.status)
    except ProfileLogError as exc:
        parser.error(str(exc))
    if event["method"] != "GET":
        parser.error("matching event has an unexpected request method")
    if args.upstream_attempts is not None:
        if "upstream_addr" not in event:
            parser.error("profile does not record upstream attempts")
        observed = upstream_attempts(event)
        if observed != args.upstream_attempts:
            parser.error(
                f"expected {args.upstream_attempts} upstream attempts; "
                f"observed {observed}"
            )

    print(f"validated {args.profile} structured access event")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
