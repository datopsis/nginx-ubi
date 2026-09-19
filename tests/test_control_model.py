"""Hold the structure of the control deliverable before the controls exist.

Host expectations are in scope and the reader is an external assessor
(ADR-0009), so a control without a machine-readable origination value can be
read as a claim that something is satisfied. These checks make that shape a
property of the document rather than a convention.

They are written before the 188 base controls, deliberately. A rule introduced
after the bulk authoring has to be retrofitted across every entry, and a
property that is merely conventional is the first thing dropped under a
deadline — which is exactly when the overclaim it prevents matters most.
"""

from __future__ import annotations

from pathlib import Path
import json
import re
import unittest

from tests.requirements import requirements

REPOSITORY = Path(__file__).resolve().parent.parent
REGISTER = REPOSITORY / "artifacts" / "requirement-sources.json"
COMPONENT = REPOSITORY / "artifacts" / "oscal" / "component-definition.json"
NS = "https://datopsis.example/ns/oscal"

ORIGINATIONS = {
    "image-owned",
    "deployment-configured",
    "host-inherited",
    "organization-inherited",
    "not-applicable",
    "research-required",
}
ROLE_FOR = {
    "image-owned": "image-project",
    "deployment-configured": "deployment-profile",
    "host-inherited": "host-orchestrator",
    "organization-inherited": "organization",
}
ASSESSMENT_METHODS = {"examine", "test", "interview"}
REQUIREMENT_ID = re.compile(r"^L[123]-[A-Z]{3}-\d{3}$")
SOURCE_STATUSES = {"pinned", "unresolved", "unavailable"}


def register() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def component() -> dict:
    return json.loads(COMPONENT.read_text(encoding="utf-8"))


def implemented() -> list[dict]:
    found = []
    for comp in component()["component-definition"]["components"]:
        for implementation in comp.get("control-implementations", []):
            found.extend(implementation.get("implemented-requirements", []))
    return found


def props(entry: dict, name: str) -> list[str]:
    return [
        p["value"]
        for p in entry.get("props", [])
        if p.get("name") == name and p.get("ns") == NS
    ]


def requirement_ids() -> set[str]:
    found = set()
    for level in (1, 2, 3):
        text = (REPOSITORY / "docs" / f"L{level}-REQ.md").read_text(encoding="utf-8")
        found.update(re.findall(r"^###\s+(L[123]-[A-Z]{3}-\d{3})\s*$", text, re.M))
    return found


class SourceRegisterTests(unittest.TestCase):
    @requirements("L2-SUP-005")
    def test_every_source_records_the_fields_a_mapping_needs(self) -> None:
        for source in register()["sources"]:
            with self.subTest(source=source["id"]):
                for field in (
                    "publisher", "title", "release", "retrieved_on", "url",
                    "sha256", "status", "role", "license", "redistributable",
                ):
                    self.assertIn(field, source)
                self.assertIn(source["status"], SOURCE_STATUSES)

    def test_a_pinned_source_carries_a_digest_and_an_unpinned_one_does_not(self) -> None:
        # A half-pinned entry is the dangerous shape: it looks authoritative
        # and identifies nothing.
        for source in register()["sources"]:
            with self.subTest(source=source["id"]):
                if source["status"] == "pinned":
                    self.assertRegex(source["sha256"] or "", r"^[0-9a-f]{64}$")
                    self.assertTrue((source["url"] or "").startswith("https://"))
                    self.assertIsNotNone(source["release"])
                else:
                    self.assertIsNone(source["sha256"])
                    self.assertTrue(
                        (source.get("notes") or "").strip(),
                        "an unpinned source must record why it is unpinned",
                    )

    def test_the_spine_and_baseline_are_pinned(self) -> None:
        # Cross-references may lag. The spine may not: without it there is no
        # catalogue to map against at all.
        by_role = {s["role"]: s for s in register()["sources"]}
        for role in ("spine", "baseline"):
            self.assertEqual(by_role[role]["status"], "pinned")

    def test_a_source_ruled_not_applicable_records_the_basis(self) -> None:
        # Deciding an SRG does not apply is a claim in its own right. Without a
        # stated basis it is indistinguishable from having forgotten it.
        for source in register()["sources"]:
            if source["role"] != "not-applicable":
                continue
            with self.subTest(source=source["id"]):
                self.assertTrue(
                    (source.get("notes") or "").strip(),
                    "a source ruled not applicable must record why",
                )

    def test_a_non_redistributable_source_is_marked_as_such(self) -> None:
        for source in register()["sources"]:
            with self.subTest(source=source["id"]):
                self.assertIsInstance(source["redistributable"], bool)


class OriginationTests(unittest.TestCase):
    @requirements("L2-EVD-001")
    def test_every_control_declares_exactly_one_origination(self) -> None:
        entries = implemented()
        self.assertGreater(len(entries), 0, "no controls found to check")
        for entry in entries:
            with self.subTest(control=entry["control-id"]):
                values = props(entry, "origination")
                self.assertEqual(
                    len(values),
                    1,
                    f"{entry['control-id']} must carry exactly one origination",
                )
                self.assertIn(values[0], ORIGINATIONS)

    @requirements("L2-EVD-001")
    def test_the_responsible_role_matches_the_origination(self) -> None:
        for entry in implemented():
            origination = props(entry, "origination")[0]
            roles = [r["role-id"] for r in entry.get("responsible-roles", [])]
            with self.subTest(control=entry["control-id"]):
                self.assertTrue(roles, "a control must name a responsible role")
                expected = ROLE_FOR.get(origination)
                if expected:
                    self.assertIn(
                        expected,
                        roles,
                        f"{entry['control-id']} is {origination} but does not "
                        f"name {expected} as responsible",
                    )

    def test_every_named_role_is_defined(self) -> None:
        defined = {
            r["id"]
            for r in component()["component-definition"]["metadata"].get("roles", [])
        }
        for entry in implemented():
            for role in entry.get("responsible-roles", []):
                with self.subTest(control=entry["control-id"]):
                    self.assertIn(role["role-id"], defined)


class VerificationPointerTests(unittest.TestCase):
    @requirements("L2-EVD-001")
    def test_an_image_owned_control_cites_a_requirement(self) -> None:
        # This is what stops a control asserting something the product never
        # stated it would do.
        for entry in implemented():
            if props(entry, "origination")[0] != "image-owned":
                continue
            with self.subTest(control=entry["control-id"]):
                self.assertTrue(
                    props(entry, "requirement"),
                    f"{entry['control-id']} claims image-owned without citing "
                    f"a requirement to verify it",
                )

    def test_every_cited_requirement_exists_in_the_tree(self) -> None:
        known = requirement_ids()
        self.assertGreater(len(known), 50, "requirement tree did not parse")
        for entry in implemented():
            for identifier in props(entry, "requirement"):
                with self.subTest(control=entry["control-id"], requirement=identifier):
                    self.assertRegex(identifier, REQUIREMENT_ID)
                    self.assertIn(
                        identifier,
                        known,
                        f"{entry['control-id']} cites {identifier}, which is "
                        f"not a requirement this product states",
                    )

    def test_a_control_that_is_not_image_owned_claims_no_assessment(self) -> None:
        # Supplying an assessment method for a host control would describe an
        # assessment this project cannot perform.
        for entry in implemented():
            if props(entry, "origination")[0] == "image-owned":
                continue
            with self.subTest(control=entry["control-id"]):
                self.assertEqual(props(entry, "assessment-method"), [])

    def test_an_image_owned_control_declares_an_assessment_method(self) -> None:
        for entry in implemented():
            if props(entry, "origination")[0] != "image-owned":
                continue
            methods = props(entry, "assessment-method")
            with self.subTest(control=entry["control-id"]):
                self.assertTrue(methods)
                for method in methods:
                    self.assertIn(method, ASSESSMENT_METHODS)


class CrossReferenceTests(unittest.TestCase):
    def test_every_cross_reference_names_a_registered_source(self) -> None:
        known = {s["id"] for s in register()["sources"]}
        for entry in implemented():
            for value in props(entry, "cross-reference"):
                with self.subTest(control=entry["control-id"], reference=value):
                    self.assertIn(":", value, "expected <source-id>:<identifier>")
                    source_id = value.split(":", 1)[0]
                    self.assertIn(
                        source_id,
                        known,
                        f"{entry['control-id']} cites source {source_id!r}, "
                        f"which is not in the requirement-source register",
                    )

    def test_the_implementation_names_its_catalogue_source(self) -> None:
        pinned = {
            s["url"] for s in register()["sources"] if s["status"] == "pinned"
        }
        for comp in component()["component-definition"]["components"]:
            for implementation in comp.get("control-implementations", []):
                with self.subTest(component=comp["title"]):
                    self.assertIn(implementation["source"], pinned)


class ScopeHonestyTests(unittest.TestCase):
    def test_the_document_does_not_yet_claim_baseline_coverage(self) -> None:
        # 188 base controls are an open item. Until they exist, the metadata
        # must say so rather than let a reader infer coverage from four.
        remarks = component()["component-definition"]["metadata"].get("remarks", "")
        self.assertIn("Foundation", remarks)
        self.assertLess(
            len(implemented()),
            188,
            "if the baseline is complete, update this check and the remarks",
        )

    @requirements("L2-EVD-002")
    def test_a_hand_off_control_says_what_the_other_party_must_do(self) -> None:
        for entry in implemented():
            if props(entry, "origination")[0] == "image-owned":
                continue
            with self.subTest(control=entry["control-id"]):
                self.assertTrue(
                    (entry.get("remarks") or "").strip(),
                    f"{entry['control-id']} hands off without saying what the "
                    f"responsible party has to do",
                )


if __name__ == "__main__":
    unittest.main()
