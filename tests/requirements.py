"""Requirement markers for the `unittest` suites, and a selector for them.

A requirement's evidence has to be selectable by the runner rather than
asserted in prose, or the trace matrix records an intention instead of a fact.
`unittest` has no marker mechanism of its own, so this module supplies one:

    from tests.requirements import requirements

    class ExampleTests(unittest.TestCase):
        @requirements("L3-LOG-001")
        def test_query_strings_are_absent(self) -> None:
            ...

`scripts/build-trace-matrix.py` reads these markers by parsing the source, so
it never imports or runs the suites. The same markers can be used to run only
the tests verifying one requirement:

    python -m tests.requirements L3-LOG-001

Bash scenario suites use a comment convention instead, described in
`docs/L1-REQ.md`. Those markers are read by the generator but cannot be used to
select a scenario, because the suites are linear scripts rather than
individually addressable cases. That limitation is recorded rather than
papered over.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import re
import sys
import unittest
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TypeVar

REQUIREMENT_ID = re.compile(r"^L[123]-[A-Z]{3}-\d{3}$")

F = TypeVar("F", bound=Callable[..., object])


def requirements(*identifiers: str) -> Callable[[F], F]:
    """Record the requirements a test verifies.

    Identifiers are validated here rather than only by the generator, so a
    malformed identifier fails when the suite is imported instead of silently
    contributing nothing to the matrix.
    """
    if not identifiers:
        raise ValueError("at least one requirement identifier is required")
    for identifier in identifiers:
        if not REQUIREMENT_ID.fullmatch(identifier):
            raise ValueError(
                f"{identifier!r} is not a requirement identifier of the form "
                f"L<level>-<CATEGORY>-<NNN>"
            )

    def decorate(function: F) -> F:
        existing = getattr(function, "__requirements__", ())
        function.__requirements__ = tuple(dict.fromkeys(existing + identifiers))
        return function

    return decorate


def _cases(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _cases(item)
        else:
            yield item


def _suite_modules() -> Iterator[str]:
    """Name every `tests.test_*` module.

    `unittest` discovery is not used here. `tests` is a namespace package, so
    the loader will neither accept it as a start directory nor recurse into it
    from the repository root, while importing `tests.<module>` works normally.
    Naming the modules explicitly avoids depending on that behaviour.
    """
    for module in pkgutil.iter_modules([str(Path(__file__).resolve().parent)]):
        if module.name.startswith("test_"):
            yield f"tests.{module.name}"


def select(identifier: str) -> unittest.TestSuite:
    """Return the tests marked as verifying one requirement."""
    loader = unittest.defaultTestLoader
    selected = unittest.TestSuite()
    for name in sorted(_suite_modules()):
        loaded = loader.loadTestsFromModule(importlib.import_module(name))
        for case in _cases(loaded):
            method = getattr(case, case._testMethodName, None)
            if identifier in getattr(method, "__requirements__", ()):
                selected.addTest(case)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirement", help="requirement identifier to verify")
    parser.add_argument("-v", "--verbose", action="count", default=1)
    arguments = parser.parse_args()

    if not REQUIREMENT_ID.fullmatch(arguments.requirement):
        parser.error(f"{arguments.requirement!r} is not a requirement identifier")

    suite = select(arguments.requirement)
    if suite.countTestCases() == 0:
        # Silence here would look like success, and a requirement with no
        # evidence is the thing the matrix exists to surface.
        print(
            f"no test is marked as verifying {arguments.requirement}",
            file=sys.stderr,
        )
        return 1

    result = unittest.TextTestRunner(verbosity=arguments.verbose).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
