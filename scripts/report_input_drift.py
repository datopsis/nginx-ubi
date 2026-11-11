#!/usr/bin/env python3
"""Keep one assigned drift issue and notify only on state transitions.

The pure decision function is independent of GitHub. The adapter uses gh and
JSON stdin; report values are never evaluated as shell commands.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess

MARKER = re.compile(r"<!-- input-drift:v1 ([A-Za-z0-9_=-]+) -->")
LABEL = "input-drift"
TITLE = "Reviewed input drift"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def fingerprint(state: dict) -> str:
    return hashlib.sha256(canonical(state)).hexdigest()


@dataclass(frozen=True)
class Decision:
    action: str
    comment: str | None
    marker: str


def decide(report: dict, issue: dict | None) -> Decision:
    """Plan create/reopen/close/keep, a change summary, and the new checkpoint.

    Only moved area/pinned/available tuples define drift; notes and ordering do
    not. An incomplete observation cannot prove resolution: fail before writing
    anything, retaining the last complete checkpoint for the next successful run.
    """
    if any(f["available"].startswith("(") for f in report["findings"]):
        raise ValueError("Incomplete input report; retaining the previous drift state")
    state = {
        f["area"]: [f["pinned"], f["available"]]
        for f in report["findings"] if f["drifted"]
    }
    previous, sequence = None, 0
    match = MARKER.search(issue.get("body", "") or "") if issue else None
    if match:
        checkpoint = json.loads(base64.urlsafe_b64decode(match[1]))
        previous, sequence = checkpoint["state"], checkpoint["sequence"]
        if checkpoint["fingerprint"] != fingerprint(previous):
            raise ValueError("Invalid input-drift checkpoint fingerprint")
    elif issue and "<!-- input-drift:" in (issue.get("body") or ""):
        raise ValueError("Unrecognized input-drift checkpoint")

    is_open = issue is not None and issue["state"].lower() == "open"
    action = "keep"
    if state:
        action = "create" if issue is None else "keep" if is_open else "reopen"
    elif is_open:
        action = "close"
    changed = (fingerprint(previous) != fingerprint(state) if previous is not None
               else bool(state) or is_open)
    comment = None
    if changed:
        lines = [f"Reviewed input drift changed: {len(state)} input(s) moved.", ""]
        if previous is None:
            lines += ["First notification; establishing the drift baseline.", ""]
        for area in sorted(set(previous or {}) | set(state)):
            old, new = (previous or {}).get(area), state.get(area)
            if old == new:
                continue
            if new is None:
                lines.append(f"- Resolved: {area} (was `{old[0]}` → `{old[1]}`).")
            elif old is None:
                lines.append(f"- New: {area}: `{new[0]}` → `{new[1]}`.")
            else:
                lines.append(
                    f"- Changed: {area}: `{old[0]}` → `{old[1]}` became "
                    f"`{new[0]}` → `{new[1]}`."
                )
        if not state:
            lines += ["", "All checked inputs are current; closing this issue."]
        else:
            lines += ["", "Review the current issue body and `docs/ARTIFACT-LIFECYCLE.md`."]
        sequence += 1
        # Sequence distinguishes repeated A -> B transitions after recurrence.
        lines += ["", f"<!-- input-drift-comment:{sequence}:{fingerprint(state)} -->"]
        comment = "\n".join(lines)
    checkpoint = {"state": state, "fingerprint": fingerprint(state), "sequence": sequence}
    encoded = base64.urlsafe_b64encode(canonical(checkpoint)).decode()
    return Decision(action, comment, f"<!-- input-drift:v1 {encoded} -->")


def api(repository: str, path: str, method: str = "GET", payload: dict | None = None,
        paginate: bool = False):
    command = ["gh", "api", f"repos/{repository}/{path}", "--method", method]
    if paginate:
        command += ["--paginate", "--slurp"]
    if payload is not None:
        command += ["--input", "-"]
    result = subprocess.run(
        command, input=json.dumps(payload) if payload is not None else None,
        text=True, capture_output=True, check=True,
    )
    value = json.loads(result.stdout)
    return [item for page in value for item in page] if paginate else value


def publish(repository: str, assignee: str, report: dict, markdown: str) -> None:
    issues = api(repository, f"issues?state=all&labels={LABEL}&per_page=100", paginate=True)
    issues = [issue for issue in issues if "pull_request" not in issue]
    issue = max(issues, key=lambda i: (i["state"] == "open", i["number"]), default=None)
    decision = decide(report, issue)
    print(f"Drift issue: {decision.action}; comment: {decision.comment is not None}")
    if issue is None and decision.action == "keep":
        return
    body = (markdown.rstrip() + "\n\nGenerated by the input-drift workflow.\n"
            "This issue is updated in place; it is not a proposal to merge.\n")
    if decision.action == "create":
        labels = api(repository, "labels?per_page=100", paginate=True)
        if not any(label["name"] == LABEL for label in labels):
            api(repository, "labels", "POST", {
                "name": LABEL, "color": "FBCA04",
                "description": "Reviewed build inputs have moved upstream",
            })
        # Do not checkpoint until the notification has succeeded.
        issue = api(repository, "issues", "POST", {
            "title": TITLE, "body": body, "labels": [LABEL], "assignees": [assignee],
        })
    endpoint = f"issues/{issue['number']}"
    if decision.action != "close" and report["drift"]:
        if not any(person["login"] == assignee for person in issue.get("assignees", [])):
            issue = api(repository, f"{endpoint}/assignees", "POST", {"assignees": [assignee]})
        if not any(person["login"] == assignee for person in issue.get("assignees", [])):
            raise RuntimeError(f"GitHub did not assign the drift issue to {assignee}")
    if decision.action == "reopen":
        api(repository, endpoint, "PATCH", {"state": "open"})
    if decision.comment:
        comments = api(repository, f"{endpoint}/comments?per_page=100", paginate=True)
        token = decision.comment.splitlines()[-1]
        # If comment succeeded but checkpoint write failed, retry only the write.
        if not any(token in comment["body"] for comment in comments):
            api(repository, f"{endpoint}/comments", "POST", {"body": decision.comment})
    update = {"body": body + "\n" + decision.marker + "\n"}
    if decision.action == "close":
        update.update(state="closed", state_reason="completed")
    api(repository, endpoint, "PATCH", update)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--assignee", required=True)
    parser.add_argument("--report", type=Path, default=Path("drift.json"))
    parser.add_argument("--markdown", type=Path, default=Path("drift.md"))
    args = parser.parse_args()
    publish(args.repository, args.assignee,
            json.loads(args.report.read_text(encoding="utf-8")),
            args.markdown.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
