"""Hold the properties hand-authored diagrams must have.

Diagrams are committed as SVG with no rendering step (ADR-0008), so the
published file is the source. That removes source-versus-render drift, and
replaces it with a different obligation: nothing checks the file before a
reader sees it, so the checks that matter have to run here.

A diagram that reaches for a remote font or image renders differently for
different readers, and one carrying script is not a diagram.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree
import re
import unittest

from tests.requirements import requirements

REPOSITORY = Path(__file__).resolve().parent.parent
ARCHITECTURE = REPOSITORY / "docs" / "architecture"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"

# Anything that would make the rendered result depend on a network fetch.
EXTERNAL_REFERENCE = re.compile(
    r"""(?:href|src)\s*=\s*["']\s*(?:https?:)?//""", re.I
)


def diagrams() -> list[Path]:
    if not ARCHITECTURE.is_dir():
        return []
    return sorted(ARCHITECTURE.rglob("*.svg"))


class DiagramTests(unittest.TestCase):
    def test_diagrams_are_present(self) -> None:
        # A suite that silently checks nothing would pass forever.
        self.assertGreater(len(diagrams()), 0, "no diagrams found to check")

    def test_each_diagram_parses_as_xml(self) -> None:
        for path in diagrams():
            with self.subTest(diagram=path.name):
                try:
                    ElementTree.parse(path)
                except ElementTree.ParseError as error:
                    self.fail(f"{path.name} is not well-formed XML: {error}")

    def test_each_diagram_scales(self) -> None:
        for path in diagrams():
            with self.subTest(diagram=path.name):
                root = ElementTree.parse(path).getroot()
                self.assertEqual(root.tag, f"{{{SVG_NAMESPACE}}}svg")
                self.assertIsNotNone(
                    root.get("viewBox"),
                    f"{path.name} has no viewBox, so it cannot scale with the "
                    f"page it is embedded in.",
                )

    def test_no_diagram_carries_script(self) -> None:
        for path in diagrams():
            with self.subTest(diagram=path.name):
                root = ElementTree.parse(path).getroot()
                scripts = root.iter(f"{{{SVG_NAMESPACE}}}script")
                self.assertEqual(
                    list(scripts),
                    [],
                    f"{path.name} contains a script element. See ADR-0008.",
                )

    def test_no_diagram_references_an_external_resource(self) -> None:
        for path in diagrams():
            with self.subTest(diagram=path.name):
                match = EXTERNAL_REFERENCE.search(path.read_text(encoding="utf-8"))
                self.assertIsNone(
                    match,
                    f"{path.name} references an external resource, so it would "
                    f"render differently for different readers. See ADR-0008.",
                )

    @requirements("L2-EVD-002")
    def test_each_diagram_is_described_for_a_reader_who_cannot_see_it(self) -> None:
        # A diagram in a review package that carries no text alternative is
        # evidence only to people who can see it.
        for path in diagrams():
            with self.subTest(diagram=path.name):
                root = ElementTree.parse(path).getroot()
                title = root.find(f"{{{SVG_NAMESPACE}}}title")
                description = root.find(f"{{{SVG_NAMESPACE}}}desc")
                self.assertIsNotNone(title, f"{path.name} has no <title>")
                self.assertIsNotNone(description, f"{path.name} has no <desc>")
                self.assertGreater(
                    len((description.text or "").strip()),
                    40,
                    f"{path.name} has a <desc> too short to describe it",
                )


class DiagramReferenceTests(unittest.TestCase):
    def test_every_diagram_is_referenced_from_a_document(self) -> None:
        # An unreferenced diagram is one nobody maintains.
        markdown = list((REPOSITORY / "docs").rglob("*.md"))
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in markdown)
        for path in diagrams():
            with self.subTest(diagram=path.name):
                self.assertIn(
                    path.name,
                    corpus,
                    f"{path.name} is referenced by no document.",
                )


if __name__ == "__main__":
    unittest.main()
