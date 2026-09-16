from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import nginx_features  # noqa: E402


class NginxFeatureInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repository = Path(__file__).resolve().parents[1]
        cls.inventory = nginx_features.validate_inventory(
            repository / "artifacts" / "nginx-features.json",
            repository / "artifacts" / "lock-inputs.json",
        )

    def output(self, arguments: list[str] | None = None) -> str:
        selected = arguments or (
            self.inventory["compiled_features"]
            + self.inventory["compiled_optional_modules"]
        )
        return (
            f"nginx version: nginx/{self.inventory['nginx_version']}\n"
            f"configure arguments: {' '.join(selected)}\n"
        )

    def test_reviewed_feature_inventory_is_accepted(self) -> None:
        nginx_features.validate_nginx_v(self.output(), self.inventory)

    def test_missing_or_unexpected_module_is_rejected(self) -> None:
        arguments = (
            self.inventory["compiled_features"]
            + self.inventory["compiled_optional_modules"]
        )
        with self.assertRaisesRegex(nginx_features.FeatureError, "optional modules"):
            nginx_features.validate_nginx_v(self.output(arguments[:-1]), self.inventory)
        with self.assertRaisesRegex(nginx_features.FeatureError, "external module"):
            nginx_features.validate_nginx_v(
                self.output(arguments + ["--add-module=/unreviewed"]), self.inventory
            )

    def test_version_and_reviewed_input_drift_are_rejected(self) -> None:
        with self.assertRaisesRegex(nginx_features.FeatureError, "version differs"):
            nginx_features.validate_nginx_v(
                self.output().replace("nginx/1.30.4", "nginx/1.30.3"), self.inventory
            )
        changed = copy.deepcopy(self.inventory)
        changed["compiled_features"].pop()
        with self.assertRaisesRegex(nginx_features.FeatureError, "feature flags"):
            nginx_features.validate_nginx_v(self.output(), changed)


if __name__ == "__main__":
    unittest.main()
