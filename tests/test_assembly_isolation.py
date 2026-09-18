"""Prove the properties assembly depends on, by reading what it is given.

Four claims are made about release assembly: it cannot pull an image, it cannot
reach a package network, it cannot recalculate the dependency closure, and it
cannot expose acquisition credentials.

The first two are enforced at run time by `--pull=never` and `--network none`,
and the native suites already prove the build fails when a base is absent or a
lock identity is wrong. What those runtime checks cannot show is that the
*inputs* to assembly make the properties reachable at all: a build context that
carries a credential, or a Containerfile that would resolve dependencies given
the chance, is a latent failure that a passing hermetic build does not reveal.

These checks read the build definition and the context rules rather than
running a build, so they hold on every change and cost nothing.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest

from tests.requirements import requirements

REPOSITORY = Path(__file__).resolve().parent.parent
CONTAINERFILE = REPOSITORY / "Containerfile"
BUILD_SCRIPT = REPOSITORY / "scripts" / "build-image.sh"
DOCKERIGNORE = REPOSITORY / ".dockerignore"
GITIGNORE = REPOSITORY / ".gitignore"

# Commands that resolve or fetch software. Any of these in the build definition
# would mean assembly could choose a package set rather than install a
# reviewed one.
RESOLVING_COMMANDS = (
    "dnf",
    "microdnf",
    "yum",
    "rpm -i http",
    "curl",
    "wget",
    "pip",
    "npm",
    "go get",
    "git clone",
)

# Staging directories that hold acquired artifacts and, for an alternate
# source, may sit beside credentials. None may enter a build context.
STAGING_DIRECTORIES = (
    ".artifact-bundle",
    ".artifact-inputs",
    ".artifact-resolver",
)

CREDENTIAL_PATTERN = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|bearer)\b\s*[=:]\s*\S"
)


def instructions(path: Path) -> list[tuple[int, str]]:
    """Return Containerfile instructions with comments removed."""
    lines = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        statement = raw.split("#", 1)[0].strip()
        if statement:
            lines.append((number, statement))
    return lines


class NoResolutionTests(unittest.TestCase):
    @requirements("L2-SUP-005")
    def test_the_build_definition_cannot_resolve_dependencies(self) -> None:
        for number, statement in instructions(CONTAINERFILE):
            lowered = statement.lower()
            for command in RESOLVING_COMMANDS:
                with self.subTest(line=number, command=command):
                    self.assertNotRegex(
                        lowered,
                        rf"(^|[\s;&|]){re.escape(command)}(\s|$)",
                        f"Containerfile:{number} invokes {command!r}. Assembly "
                        f"installs a reviewed set; it does not choose one.",
                    )

    def test_installation_consumes_only_the_supplied_bundle(self) -> None:
        text = CONTAINERFILE.read_text(encoding="utf-8")
        self.assertIn("artifact_bundle", text)
        self.assertIn("install-rpm-bundle", text)

    def test_the_final_stage_keeps_no_package_manager(self) -> None:
        text = CONTAINERFILE.read_text(encoding="utf-8")
        self.assertIn("rm -rf /etc/yum.repos.d", text)


class NoNetworkTests(unittest.TestCase):
    @requirements("L2-SUP-003")
    def test_assembly_disables_the_network_and_forbids_pulling(self) -> None:
        script = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--network none", script)
        self.assertIn("--pull=never", script)

    def test_bases_are_confirmed_present_before_the_build(self) -> None:
        # With pulling forbidden, a missing base must fail as a missing base
        # rather than part-way through a build.
        script = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("image exists", script)

    def test_the_build_verifies_its_bundle_before_using_it(self) -> None:
        script = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("verify-rpm-bundle.sh", script)
        self.assertIn("validate-lock", script)


class CredentialIsolationTests(unittest.TestCase):
    @requirements("L2-SUP-003")
    def test_staging_directories_are_excluded_from_the_build_context(self) -> None:
        ignored = DOCKERIGNORE.read_text(encoding="utf-8").split()
        for directory in STAGING_DIRECTORIES:
            with self.subTest(directory=directory):
                self.assertIn(
                    directory,
                    ignored,
                    f"{directory} may enter the build context, so anything "
                    f"beside an acquired artifact could enter the image.",
                )

    def test_staging_directories_are_excluded_from_version_control(self) -> None:
        ignored = GITIGNORE.read_text(encoding="utf-8").split()
        for directory in STAGING_DIRECTORIES:
            with self.subTest(directory=directory):
                self.assertIn(f"{directory}/", ignored)

    def test_no_build_input_carries_a_credential(self) -> None:
        # A source map, token, or private CA is a protected runner input. None
        # may appear in a file the build or the repository carries.
        for path in (CONTAINERFILE, BUILD_SCRIPT):
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                statement = line.split("#", 1)[0]
                with self.subTest(path=path.name, line=number):
                    self.assertIsNone(
                        CREDENTIAL_PATTERN.search(statement),
                        f"{path.name}:{number} looks like an inline credential.",
                    )

    def test_the_build_takes_no_credential_argument(self) -> None:
        # Acquisition reads a token from the runner environment. Assembly must
        # not, because a build argument is recorded in image history.
        text = CONTAINERFILE.read_text(encoding="utf-8")
        arguments = re.findall(r"^\s*ARG\s+([A-Z_]+)", text, re.M)
        for argument in arguments:
            with self.subTest(argument=argument):
                self.assertNotRegex(
                    argument,
                    r"(?i)(TOKEN|SECRET|PASSWORD|KEY)$",
                    f"ARG {argument} would be recorded in image history.",
                )


if __name__ == "__main__":
    unittest.main()
