"""Hold the configuration decisions that nothing else enforces.

Two accepted decisions were recorded with no automated enforcement:

* ADR-0002 packages open source NGINX only, so no commercial directive may
  appear in a shipped configuration.
* ADR-0005 never retries a non-idempotent request, so no profile may enable
  ``non_idempotent`` on ``proxy_next_upstream``.

Both are invisible in review: a commercial directive looks like ordinary
configuration to anyone who does not know which edition ships it, and
``non_idempotent`` reads as an obvious availability improvement. These checks
make either one fail before it is merged.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest

REPOSITORY = Path(__file__).resolve().parent.parent
CONFIGURATION_ROOTS = (REPOSITORY / "examples", REPOSITORY / "container")

# Directives that exist only in NGINX Plus. Each would load on a Plus build and
# fail on this image, so a configuration carrying one is either untested or
# quietly assumes a licence this project has not bought.
COMMERCIAL_DIRECTIVES = (
    "health_check",
    "sticky",
    "keyval",
    "keyval_zone",
    "zone_sync",
    "zone_sync_server",
    "status_zone",
    "js_import",
    "js_content",
    "mp4_limit_rate",
    "api",
)


def configuration_files() -> list[Path]:
    files: list[Path] = []
    for root in CONFIGURATION_ROOTS:
        if root.is_dir():
            files.extend(sorted(root.rglob("*.conf")))
    return files


def directive_lines(path: Path) -> list[tuple[int, str]]:
    """Return the configuration lines with comments removed.

    A comment explaining why a directive is absent must not be mistaken for the
    directive itself, which is the whole difficulty with checking for something
    that is deliberately missing.
    """
    lines = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        statement = raw.split("#", 1)[0].strip()
        if statement:
            lines.append((number, statement))
    return lines


class ProfilePolicyTests(unittest.TestCase):
    def test_configuration_files_are_discovered(self) -> None:
        # A scan that silently matches nothing proves nothing, so the checks
        # below are only meaningful while this holds.
        self.assertGreaterEqual(len(configuration_files()), 10)

    def test_no_commercial_directive_is_used(self) -> None:
        for path in configuration_files():
            for number, statement in directive_lines(path):
                directive = re.split(r"[\s;{]", statement, 1)[0]
                with self.subTest(path=path.name, line=number):
                    self.assertNotIn(
                        directive,
                        COMMERCIAL_DIRECTIVES,
                        f"{path.relative_to(REPOSITORY)}:{number} uses the NGINX "
                        f"Plus directive '{directive}'. See ADR-0002: this "
                        f"project packages open source NGINX only.",
                    )

    def test_no_profile_enables_non_idempotent_retries(self) -> None:
        for path in configuration_files():
            for number, statement in directive_lines(path):
                with self.subTest(path=path.name, line=number):
                    self.assertNotIn(
                        "non_idempotent",
                        statement,
                        f"{path.relative_to(REPOSITORY)}:{number} enables "
                        f"non-idempotent retries. See ADR-0005: replaying a "
                        f"request the application may already have applied is a "
                        f"correctness risk, not an availability improvement.",
                    )

    def test_the_comment_explaining_the_absence_is_not_mistaken_for_the_directive(
        self,
    ) -> None:
        # The load-balancer profile documents why non_idempotent is absent. A
        # naive substring scan would fail on that comment, so this asserts the
        # comment exists and that the check above still passes with it present.
        load_balancer = REPOSITORY / "examples/profiles/load-balancer/nginx.conf"
        self.assertIn("non_idempotent", load_balancer.read_text(encoding="utf-8"))
        self.assertNotIn(
            "non_idempotent",
            " ".join(statement for _, statement in directive_lines(load_balancer)),
        )


if __name__ == "__main__":
    unittest.main()
