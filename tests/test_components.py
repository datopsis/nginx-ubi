from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import components  # noqa: E402


class ComponentInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = Path(__file__).resolve().parents[1]
        cls.inventory_path = cls.repository / "artifacts" / "components.json"
        cls.inventory = components.read_inventory(cls.inventory_path)

    def write_inventory(self, value: dict) -> Path:
        temporary = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", dir=self.repository, delete=False, encoding="utf-8"
        )
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        with temporary:
            json.dump(value, temporary)
        return Path(temporary.name)

    def test_repository_inventory_covers_both_reviewed_locks(self) -> None:
        result = components.validate_inventory(self.inventory_path, self.repository)
        self.assertEqual(len(result["components"]), 79)

    def test_missing_component_is_rejected(self) -> None:
        value = copy.deepcopy(self.inventory)
        value["components"].pop()
        with self.assertRaisesRegex(components.InventoryError, "component names differ"):
            components.validate_inventory(self.write_inventory(value), self.repository)

    def test_lock_hash_drift_is_rejected(self) -> None:
        value = copy.deepcopy(self.inventory)
        value["locks"]["amd64"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(components.InventoryError, "no longer matches"):
            components.validate_inventory(self.write_inventory(value), self.repository)

    def test_wrong_publisher_policy_is_rejected(self) -> None:
        value = copy.deepcopy(self.inventory)
        nginx = next(item for item in value["components"] if item["name"] == "nginx")
        nginx["policy"] = "redhat-ubi9"
        with self.assertRaisesRegex(components.InventoryError, "wrong publisher policy"):
            components.validate_inventory(self.write_inventory(value), self.repository)

    def test_rpm_headers_must_match_the_reviewed_metadata(self) -> None:
        inventory = components.validate_inventory(self.inventory_path, self.repository)
        records = {item["name"]: item for item in inventory["components"]}
        rpm_metadata = copy.deepcopy(records)
        lock_path = self.repository / "artifacts" / "locks" / "amd64.json"
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        filenames = {item["filename"]: item["name"] for item in lock["packages"]}

        def rpm_query(command: list[str], **_kwargs: object) -> SimpleNamespace:
            name = filenames[Path(command[-1]).name]
            record = rpm_metadata[name]
            vendor = inventory["_policy_vendors"][record["policy"]]
            output = "\t".join((name, record["license"], record["source_rpm"], vendor))
            return SimpleNamespace(returncode=0, stdout=output, stderr="")

        with mock.patch.object(components.subprocess, "run", side_effect=rpm_query):
            components.verify_rpms(inventory, lock_path, Path("unused-bundle"))
            records["nginx"]["license"] = "wrong license"
            with self.assertRaisesRegex(components.InventoryError, "metadata differs"):
                components.verify_rpms(inventory, lock_path, Path("unused-bundle"))


if __name__ == "__main__":
    unittest.main()
