#!/usr/bin/env python3
"""Regenerate docs/TRACE-MATRIX.md from the requirement documents and markers.

The matrix is the single source of truth for requirement status. The
requirement documents carry specification content only, so status cannot drift
between them: it is derived every time.

Sources:

1. ``docs/L1-REQ.md`` for L1 identifiers and declared verification methods, and
   for the ``NR-`` non-requirements.
2. ``docs/L2-REQ.md`` and ``docs/L3-REQ.md`` for L2 and L3 identifiers and
   their ``Parent`` links.
3. ``tests/*.py`` for every identifier in a ``@requirements(...)`` marker,
   collected by parsing the source rather than importing it.
4. ``tests/*.sh`` and the standalone negative suites for every identifier in a
   ``# Requirements:`` comment.

A requirement is **covered** when it has at least one verifying artifact, or
when every child beneath it is covered. A requirement whose declared
verification method is not Test is reported as such rather than counted as a
gap, because no marker can exist for it.

Usage:
    python scripts/build-trace-matrix.py            # regenerate in place
    python scripts/build-trace-matrix.py --check    # fail if the file drifted
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TESTS = ROOT / "tests"
TRACE_DOC = DOCS / "TRACE-MATRIX.md"

REQUIREMENT_ID = re.compile(r"\bL([123])-([A-Z]{3})-(\d{3})\b")
HEADING_ID = re.compile(r"^#{3,4}\s+(L[123]-[A-Z]{3}-\d{3})\s*$", re.M)
INLINE_ID = re.compile(r"^###\s+(L[123]-[A-Z]{3}-\d{3})\s*$", re.M)
PARENT = re.compile(r"\*\*Parent\.\*\*\s+(L[12]-[A-Z]{3}-\d{3})")
METHODS = re.compile(r"\*\*Verification\.\*\*\s+([^\n]+)")
NON_REQUIREMENT = re.compile(r"^\|\s*`(NR-\d{3})`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.M)
# Markers inside a block are indented, so leading whitespace is allowed. A
# marker that only counted at column zero would silently miss them.
BASH_MARKER = re.compile(r"^[ 	]*#\s*Requirements:\s*(.+)$", re.M)

METHOD_LETTERS = {"Test": "T", "Analysis": "A", "Inspection": "I", "Demonstration": "D"}


class Requirement:
    def __init__(self, identifier: str, level: int) -> None:
        self.identifier = identifier
        self.level = level
        self.parent: str | None = None
        self.methods: list[str] = []
        self.artifacts: list[str] = []
        self.children: list[str] = []

    @property
    def is_test_verified(self) -> bool:
        return "Test" in self.methods


def parse_requirement_document(path: Path, level: int) -> dict[str, Requirement]:
    """Read one requirement document into identifier records."""
    text = path.read_text(encoding="utf-8")
    found: dict[str, Requirement] = {}

    # Sections are delimited by the next heading at the same depth, so a
    # requirement's metadata cannot be attributed to its neighbour.
    matches = list(INLINE_ID.finditer(text)) or list(HEADING_ID.finditer(text))
    for index, match in enumerate(matches):
        identifier = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]

        requirement = Requirement(identifier, level)
        parent = PARENT.search(body)
        if parent:
            requirement.parent = parent.group(1)
        methods = METHODS.search(body)
        if methods:
            requirement.methods = [
                name
                for name in METHOD_LETTERS
                if re.search(rf"\b{name}\b", methods.group(1))
            ]
        found[identifier] = requirement

    return found


def collect_python_markers() -> dict[str, list[str]]:
    """Read @requirements markers by parsing, never by importing."""
    artifacts: dict[str, list[str]] = defaultdict(list)
    for path in sorted(TESTS.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                name = decorator.func
                name = name.id if isinstance(name, ast.Name) else getattr(name, "attr", "")
                if name != "requirements":
                    continue
                for argument in decorator.args:
                    if isinstance(argument, ast.Constant) and isinstance(
                        argument.value, str
                    ):
                        module = f"tests.{path.stem}"
                        artifacts[argument.value].append(f"{module}.{node.name}")
    return artifacts


def collect_comment_markers() -> dict[str, list[str]]:
    """Read `# Requirements:` comments from the scenario suites."""
    artifacts: dict[str, list[str]] = defaultdict(list)
    candidates = sorted(TESTS.glob("*.sh")) + sorted(TESTS.glob("*.py"))
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        for match in BASH_MARKER.finditer(text):
            line = text[: match.start()].count("\n") + 1
            for identifier in REQUIREMENT_ID.finditer(match.group(1)):
                relative = path.relative_to(ROOT).as_posix()
                artifacts[identifier.group(0)].append(f"{relative}:{line}")
    return artifacts


def compute_status(requirement: Requirement, index: dict[str, Requirement]) -> str:
    """Covered when verified directly, or when every child is covered."""
    if requirement.artifacts:
        return "covered"
    if requirement.children:
        statuses = {compute_status(index[c], index) for c in requirement.children}
        if statuses == {"covered"}:
            return "covered"
        if "covered" in statuses:
            return "partial"
        return "uncovered"
    if not requirement.is_test_verified:
        # Analysis, Inspection, and Demonstration produce no marker. Reporting
        # them as gaps would bury the real ones.
        return "not-test-verified"
    return "uncovered"


STATUS_LABEL = {
    "covered": "covered",
    "partial": "partial",
    "uncovered": "**uncovered**",
    "not-test-verified": "not test-verified",
}


def build() -> str:
    documents = {
        1: parse_requirement_document(DOCS / "L1-REQ.md", 1),
        2: parse_requirement_document(DOCS / "L2-REQ.md", 2),
        3: parse_requirement_document(DOCS / "L3-REQ.md", 3),
    }
    index: dict[str, Requirement] = {}
    for level in (1, 2, 3):
        index.update(documents[level])

    unknown_parents = []
    for requirement in index.values():
        if requirement.parent:
            if requirement.parent in index:
                index[requirement.parent].children.append(requirement.identifier)
            else:
                unknown_parents.append((requirement.identifier, requirement.parent))

    markers: dict[str, list[str]] = defaultdict(list)
    for source in (collect_python_markers(), collect_comment_markers()):
        for identifier, artifacts in source.items():
            markers[identifier].extend(artifacts)

    orphan_markers = sorted(set(markers) - set(index))
    for identifier, artifacts in markers.items():
        if identifier in index:
            index[identifier].artifacts = sorted(set(artifacts))

    lines: list[str] = []
    add = lines.append

    add("# nginx-ubi — requirement trace matrix")
    add("")
    add("**This file is generated. Do not edit it.**")
    add("")
    add("Regenerate with `python scripts/build-trace-matrix.py`; CI runs")
    add("`--check` and fails when the committed file has drifted from its")
    add("sources.")
    add("")
    add("Status is derived here rather than recorded in the requirement")
    add("documents, so the two cannot disagree. A requirement is *covered* when")
    add("it has a verifying artifact or when every child beneath it is covered.")
    add("A requirement whose declared verification method is not Test is")
    add("reported as *not test-verified*, because no marker can exist for it,")
    add("and counting it as a gap would bury the real gaps.")
    add("")

    counted = [
        r
        for r in index.values()
        if r.level in (2, 3) or (r.level == 1 and not r.children)
    ]
    covered = [r for r in counted if compute_status(r, index) == "covered"]
    not_tested = [r for r in counted if compute_status(r, index) == "not-test-verified"]
    gaps = [r for r in counted if compute_status(r, index) == "uncovered"]

    add("## Coverage")
    add("")
    add("| Measure | Count |")
    add("| --- | --- |")
    add(f"| L1 requirements | {len(documents[1])} |")
    add(f"| L2 requirements | {len(documents[2])} |")
    add(f"| L3 requirements | {len(documents[3])} |")
    add(f"| Counted for coverage | {len(counted)} |")
    add(f"| Covered | {len(covered)} |")
    add(f"| Not test-verified | {len(not_tested)} |")
    add(f"| **Uncovered** | **{len(gaps)}** |")
    add("")
    add(
        "Composite L1 requirements are excluded from the count: they are "
        "verified through their children, which are counted, so counting both "
        "would double-count."
    )
    add("")

    if gaps:
        add("### Uncovered requirements")
        add("")
        for requirement in sorted(gaps, key=lambda r: r.identifier):
            add(f"- `{requirement.identifier}` — declared Test, no marker found")
        add("")

    if unknown_parents:
        add("### Unresolved parents")
        add("")
        for identifier, parent in sorted(unknown_parents):
            add(f"- `{identifier}` names `{parent}`, which does not exist")
        add("")

    if orphan_markers:
        add("### Markers with no requirement")
        add("")
        for identifier in orphan_markers:
            add(f"- `{identifier}` is marked in a test but defined nowhere")
        add("")

    for level in (1, 2, 3):
        add(f"## L{level} requirements")
        add("")
        add("| Requirement | Methods | Parent | Children | Verifying artifacts | Status |")
        add("| --- | --- | --- | --- | --- | --- |")
        for identifier in sorted(documents[level]):
            requirement = index[identifier]
            methods = (
                "".join(METHOD_LETTERS[m] for m in requirement.methods) or "—"
            )
            parent = f"`{requirement.parent}`" if requirement.parent else "—"
            children = (
                ", ".join(f"`{c}`" for c in sorted(requirement.children)) or "—"
            )
            artifacts = (
                "<br>".join(f"`{a}`" for a in requirement.artifacts) or "—"
            )
            status = STATUS_LABEL[compute_status(requirement, index)]
            add(
                f"| `{identifier}` | {methods} | {parent} | {children} | "
                f"{artifacts} | {status} |"
            )
        add("")

    non_requirements = NON_REQUIREMENT.findall(
        (DOCS / "L1-REQ.md").read_text(encoding="utf-8")
    )
    if non_requirements:
        add("## Non-requirements")
        add("")
        add("| ID | Non-requirement | Reason |")
        add("| --- | --- | --- |")
        for identifier, statement, reason in non_requirements:
            add(f"| `{identifier}` | {statement} | {reason} |")
        add("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the committed matrix differs from its sources",
    )
    arguments = parser.parse_args()

    generated = build()
    if arguments.check:
        if not TRACE_DOC.exists():
            print(f"{TRACE_DOC.relative_to(ROOT)} does not exist", file=sys.stderr)
            return 1
        current = TRACE_DOC.read_text(encoding="utf-8")
        if current != generated:
            print(
                f"{TRACE_DOC.relative_to(ROOT)} is out of date; regenerate it "
                f"with python scripts/build-trace-matrix.py",
                file=sys.stderr,
            )
            return 1
        print(f"{TRACE_DOC.relative_to(ROOT)} is up to date")
        return 0

    TRACE_DOC.write_text(generated, encoding="utf-8", newline="\n")
    print(f"wrote {TRACE_DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
