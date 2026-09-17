from __future__ import annotations

import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import transfer  # noqa: E402
from tests.requirements import requirements


REVISION = "1" * 40
LOCK_SHA256 = "2" * 64
INVENTORY_SHA256 = "3" * 64


class DisconnectedTransferTests(unittest.TestCase):
    def setUp(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        self.temporary = tempfile.TemporaryDirectory(dir=repository)
        self.root = Path(self.temporary.name)
        (self.root / "bundle" / "rpms").mkdir(parents=True)
        (self.root / "bundle" / "rpms" / "example.rpm").write_bytes(b"rpm")
        (self.root / "bases").mkdir()
        (self.root / "bases" / "runtime.oci.tar").write_bytes(b"base")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create(self) -> str:
        return transfer.create_manifest(
            self.root, "amd64", REVISION, LOCK_SHA256, INVENTORY_SHA256
        )

    def verify(self, digest: str) -> None:
        transfer.verify_manifest(
            self.root, digest, "amd64", REVISION, LOCK_SHA256, INVENTORY_SHA256
        )

    @requirements("L3-SUP-005")
    def test_exact_transfer_set_is_accepted(self) -> None:
        digest = self.create()
        self.verify(digest)

    def test_manifest_requires_separately_conveyed_digest(self) -> None:
        self.create()
        with self.assertRaisesRegex(transfer.TransferError, "separately conveyed"):
            self.verify("0" * 64)

    @requirements("L3-SUP-005")
    def test_modified_missing_and_unexpected_payloads_are_rejected(self) -> None:
        for mutation in ("modified", "missing", "unexpected"):
            with self.subTest(mutation=mutation):
                if (self.root / transfer.MANIFEST_NAME).exists():
                    (self.root / transfer.MANIFEST_NAME).unlink()
                rpm = self.root / "bundle" / "rpms" / "example.rpm"
                rpm.write_bytes(b"rpm")
                unexpected = self.root / "unexpected"
                unexpected.unlink(missing_ok=True)
                digest = self.create()
                if mutation == "modified":
                    rpm.write_bytes(b"changed")
                elif mutation == "missing":
                    rpm.unlink()
                else:
                    unexpected.write_bytes(b"extra")
                with self.assertRaisesRegex(transfer.TransferError, "payload inventory"):
                    self.verify(digest)

    def test_rollback_context_mismatch_is_rejected(self) -> None:
        digest = self.create()
        with self.assertRaisesRegex(transfer.TransferError, "artifact_lock_sha256"):
            transfer.verify_manifest(
                self.root, digest, "amd64", REVISION, "4" * 64, INVENTORY_SHA256
            )

    def test_existing_manifest_is_not_overwritten(self) -> None:
        self.create()
        with self.assertRaisesRegex(transfer.TransferError, "refusing to overwrite"):
            self.create()

    @requirements("L3-SUP-005")
    def test_repository_context_binds_the_reviewed_lock_and_inventory(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        arguments = Namespace(
            repository=repository,
            lock=repository / "artifacts" / "locks" / "amd64.json",
            inputs=repository / "artifacts" / "lock-inputs.json",
            inventory=repository / "artifacts" / "components.json",
            architecture="amd64",
            repository_revision="1" * 40,
        )
        git_results = [
            SimpleNamespace(returncode=0, stdout="1" * 40 + "\n"),
            SimpleNamespace(returncode=0, stdout=""),
        ]
        with mock.patch.object(transfer.subprocess, "run", side_effect=git_results):
            lock_sha256, inventory_sha256 = transfer.validated_context(arguments)
        self.assertEqual(len(lock_sha256), 64)
        self.assertEqual(len(inventory_sha256), 64)


if __name__ == "__main__":
    unittest.main()
