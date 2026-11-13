#!/usr/bin/env python3
"""Notify the assigned maintainer when UBI gate state changes, in one issue."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import re

from report_input_drift import api, canonical, fingerprint
from ubi_vulnerability_gate import markdown

TITLE = "UBI vulnerability fix availability"
MARKER = re.compile(r"<!-- ubi-gate:v1 ([A-Za-z0-9_=-]+) -->")


def state_of(reports: list[dict]) -> dict:
    if sorted(r["architecture"] for r in reports) != ["amd64", "arm64"]:
        raise ValueError("Expected exactly one report for each architecture")
    state = {}
    for report in reports:
        arch = report["architecture"]
        if report["errors"]:
            state[f"{arch}:errors"] = sorted(report["errors"])
        for f in report["findings"]:
            if f["decision"] not in {"deferred", "block", "unfixed"}:
                raise ValueError("Unknown gate decision")
            if f["decision"] == "unfixed":
                continue
            key = "/".join([arch, f["scanner"], f["vulnerability"], f["package"], f["installed"]])
            state[key] = [f["decision"], f["severity"], sorted(f["fixes"]), f["reason"]]
    return state


def transition(state: dict, issue: dict | None) -> tuple[str, str | None, str]:
    previous, sequence = None, 0
    body = (issue.get("body") or "") if issue else ""
    match = MARKER.search(body)
    if match:
        saved = json.loads(base64.urlsafe_b64decode(match[1]))
        previous, sequence = saved["state"], saved["sequence"]
        if saved["fingerprint"] != fingerprint(previous):
            raise ValueError("Corrupt UBI gate checkpoint")
    elif "<!-- ubi-gate:" in body:
        raise ValueError("Unknown UBI gate checkpoint")
    opened = issue is not None and issue["state"] == "open"
    action = ("create" if issue is None else "keep" if opened else "reopen") if state else ("close" if opened else "keep")
    changed = previous != state if previous is not None else bool(state) or opened
    comment = None
    if changed:
        sequence += 1
        # Full current report follows in the comment, so transitions to available
        # name the affected package, vendor fix and architecture explicitly.
        comment = ("UBI vulnerability gate state changed.\n\n"
                   + ("A published fix or a verification error blocks CI; deferred findings still require remediation."
                      if state else "No deferred or blocking findings remain; closing this issue.")
                   + f"\n\n<!-- ubi-gate-comment:{sequence}:{fingerprint(state)} -->")
    saved = {"state": state, "sequence": sequence, "fingerprint": fingerprint(state)}
    marker = "<!-- ubi-gate:v1 " + base64.urlsafe_b64encode(canonical(saved)).decode() + " -->"
    return action, comment, marker


def publish(repository: str, assignee: str, reports: list[dict], run_url: str) -> None:
    state = state_of(reports)
    issues = api(repository, "issues?state=all&per_page=100", paginate=True)
    matches = [i for i in issues if "pull_request" not in i and i["title"] == TITLE]
    if len(matches) > 1:
        raise ValueError("Multiple UBI tracking issues; refusing to split notifications")
    issue = matches[0] if matches else None
    action, comment, marker = transition(state, issue)
    if issue is None and action == "keep":
        return
    body = (f"Latest native CI evidence: {run_url}\n\n"
            + "\n".join(markdown(r) for r in reports)
            + "\nUpdated in place by CI. Deferral is not a vulnerability exemption.\n")
    if action == "create":
        issue = api(repository, "issues", "POST", {
            "title": TITLE, "body": body, "assignees": [assignee],
        })
    endpoint = f"issues/{issue['number']}"
    if state and not any(a["login"] == assignee for a in issue.get("assignees", [])):
        assigned = api(repository, endpoint + "/assignees", "POST", {"assignees": [assignee]})
        if not any(a["login"] == assignee for a in assigned.get("assignees", [])):
            raise RuntimeError("GitHub did not assign the UBI tracking issue")
    if action == "reopen":
        api(repository, endpoint, "PATCH", {"state": "open"})
    if comment:
        comments = api(repository, endpoint + "/comments?per_page=100", paginate=True)
        token = comment.splitlines()[-1]
        if not any(token in c["body"] for c in comments):
            api(repository, endpoint + "/comments", "POST", {"body": comment + "\n\n" + body})
    update = {"body": body + "\n" + marker + "\n"}
    if action == "close":
        update.update(state="closed", state_reason="completed")
    # Checkpoint after notification: retries cannot lose or repeat a comment.
    api(repository, endpoint, "PATCH", update)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--assignee", required=True)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    reports = []
    for arch in ("amd64", "arm64"):
        paths = list(args.directory.glob(f"**/{arch}/gate.json"))
        try:
            if len(paths) != 1:
                raise ValueError("Native gate report missing or ambiguous")
            report = json.loads(paths[0].read_text())
            if report["architecture"] != arch or report["schema_version"] != 1:
                raise ValueError("Native gate report identity mismatch")
            # Validate schema before using a report to resolve an issue.
            for field in ("findings", "errors"):
                if not isinstance(report[field], list):
                    raise ValueError("Malformed native gate report")
        except (OSError, ValueError, KeyError) as error:
            report = {"architecture": arch, "errors": [str(error)], "findings": []}
        reports.append(report)
    publish(args.repository, args.assignee, reports, args.run_url)


if __name__ == "__main__":
    main()
