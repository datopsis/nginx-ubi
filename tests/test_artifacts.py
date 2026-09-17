from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import artifacts  # noqa: E402
from tests.requirements import requirements


FINGERPRINT = "8540A6F18833A80E9C1653A42FD21310B49F6B46"
SHA = "0" * 64


def valid_lock() -> dict:
    digest = f"sha256:{'1' * 64}"
    rpm_architecture = "x86_64"
    package = {
        "name": "nginx",
        "epoch": 2,
        "version": "1.30.4",
        "release": "1.el9.ngx",
        "architecture": rpm_architecture,
        "nevra": "nginx-2:1.30.4-1.el9.ngx.x86_64",
        "filename": "nginx-1.30.4-1.el9.ngx.x86_64.rpm",
        "url": "https://nginx.org/packages/rhel/9/x86_64/RPMS/nginx-1.30.4-1.el9.ngx.x86_64.rpm",
        "repository": "nginx-stable",
        "size": 1,
        "sha256": SHA,
        "signing_key_fingerprint": FINGERPRINT,
        "source_rpm": "nginx-1.30.4-1.el9.ngx.src.rpm",
    }
    return {
        "schema_version": 1,
        "bundle_version": 1,
        "architecture": "amd64",
        "rpm_architecture": rpm_architecture,
        "generated_at": "2026-09-12T00:00:00Z",
        "nginx_version": "1.30.4",
        "nginx_rpm_version": "1.30.4-1.el9.ngx",
        "base_images": {
            role: {
                "reference": f"registry.access.redhat.com/ubi9/{image}:9.8@{digest}",
                "digest": digest,
                "platform": "linux/amd64",
            }
            for role, image in (("builder", "ubi-minimal"), ("runtime", "ubi-micro"))
        },
        "signing_keys": [{
            "id": "nginx-signing",
            "filename": "nginx_signing.key",
            "url": "https://nginx.org/keys/nginx_signing.key",
            "sha256": SHA,
            "fingerprint": FINGERPRINT,
        }],
        "packages": [package],
        "source_packages": [{
            "filename": "nginx-1.30.4-1.el9.ngx.src.rpm",
            "url": "https://nginx.org/packages/rhel/9/SRPMS/nginx-1.30.4-1.el9.ngx.src.rpm",
            "repository": "nginx-stable-source",
            "size": 1,
            "sha256": SHA,
        }],
    }


class ArtifactLockTests(unittest.TestCase):
    def setUp(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        self.temporary = tempfile.TemporaryDirectory(dir=repository)
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_lock(self, value: dict) -> Path:
        path = self.root / "lock.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def assert_rejected(self, value: dict) -> None:
        with self.assertRaises(artifacts.LockError):
            artifacts.validate_lock(self.write_lock(value))

    def write_bundle(self, lock_path: Path, value: dict, include_sources: bool = False) -> Path:
        bundle = self.root / "bundle"
        key_bytes = b"k"
        rpm_bytes = b"r"
        source_bytes = b"s"
        value["signing_keys"][0]["sha256"] = artifacts.hashlib.sha256(key_bytes).hexdigest()
        value["packages"][0]["sha256"] = artifacts.hashlib.sha256(rpm_bytes).hexdigest()
        value["source_packages"][0]["sha256"] = artifacts.hashlib.sha256(source_bytes).hexdigest()
        lock_path.write_text(json.dumps(value), encoding="utf-8")
        (bundle / "keys").mkdir(parents=True)
        (bundle / "rpms").mkdir()
        (bundle / "keys" / value["signing_keys"][0]["filename"]).write_bytes(key_bytes)
        (bundle / "rpms" / value["packages"][0]["filename"]).write_bytes(rpm_bytes)
        if include_sources:
            (bundle / "srpms").mkdir()
            (bundle / "srpms" / value["source_packages"][0]["filename"]).write_bytes(source_bytes)
        manifests = artifacts.manifest_contents(
            value, artifacts.sha256_file(lock_path), include_sources
        )
        for filename, contents in manifests.items():
            (bundle / filename).write_text(contents, encoding="utf-8", newline="\n")
        return bundle

    def test_valid_lock_is_accepted(self) -> None:
        artifacts.validate_lock(self.write_lock(valid_lock()))

    def test_runtime_manifest_is_derived_from_the_validated_lock(self) -> None:
        lock = artifacts.validate_lock(self.write_lock(valid_lock()))
        manifest = artifacts.rpm_manifest(lock)
        self.assertEqual(
            manifest.splitlines(),
            [
                "filename\tname\tepoch\tversion\trelease\tarchitecture\t"
                "source_rpm\tfingerprint\tsha256",
                "nginx-1.30.4-1.el9.ngx.x86_64.rpm\tnginx\t2\t1.30.4\t"
                f"1.el9.ngx\tx86_64\tnginx-1.30.4-1.el9.ngx.src.rpm\t{FINGERPRINT}\t{SHA}",
            ],
        )

    @requirements("L3-SUP-001")
    def test_repository_inputs_and_generated_locks_are_valid(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        inputs = artifacts.validate_inputs(repository / "artifacts" / "lock-inputs.json")
        for architecture in artifacts.ARCHES:
            lock = artifacts.validate_lock(repository / "artifacts" / "locks" / f"{architecture}.json")
            self.assertEqual(lock["nginx_version"], inputs["nginx_version"])
            self.assertEqual(lock["nginx_rpm_version"], inputs["nginx_rpm_version"])
            for role, reference in inputs["base_images"].items():
                self.assertEqual(lock["base_images"][role]["reference"], reference)
            selected = inputs["architectures"][architecture]["nginx_rpm"]
            nginx = next(item for item in lock["packages"] if item["name"] == "nginx")
            self.assertEqual(nginx["url"], selected["url"])
            self.assertEqual(nginx["sha256"], selected["sha256"])
            expected_keys = {
                (item["id"], item["url"], item["sha256"], item["fingerprint"])
                for item in inputs["signing_keys"]
            }
            actual_keys = {
                (item["id"], item["url"], item["sha256"], item["fingerprint"])
                for item in lock["signing_keys"]
            }
            self.assertEqual(actual_keys, expected_keys)

    @requirements("L3-SUP-001")
    def test_malformed_and_unexpected_fields_fail_closed(self) -> None:
        path = self.root / "bad.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaises(artifacts.LockError):
            artifacts.validate_lock(path)
        value = valid_lock()
        value["unexpected"] = True
        self.assert_rejected(value)

    @requirements("L3-SUP-002")
    def test_wrong_arch_version_nevra_source_and_base_are_rejected(self) -> None:
        mutations = []
        value = valid_lock()
        value["packages"][0]["architecture"] = "aarch64"
        mutations.append(value)
        value = valid_lock()
        value["packages"][0]["version"] = "1.30.3"
        mutations.append(value)
        value = valid_lock()
        value["packages"][0]["nevra"] = "wrong"
        mutations.append(value)
        value = valid_lock()
        value["packages"][0]["source_rpm"] = "missing.src.rpm"
        mutations.append(value)
        value = valid_lock()
        value["base_images"]["runtime"]["platform"] = "linux/arm64"
        mutations.append(value)
        value = valid_lock()
        value["base_images"]["runtime"]["digest"] = f"sha256:{'2' * 64}"
        mutations.append(value)
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_rejected(mutation)

    @requirements("L3-SUP-002")
    def test_base_digest_drift_from_reviewed_inputs_is_rejected(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        lock = json.loads(
            (repository / "artifacts" / "locks" / "amd64.json").read_text(encoding="utf-8")
        )
        changed_digest = f"sha256:{'2' * 64}"
        lock["base_images"]["runtime"]["digest"] = changed_digest
        prefix = lock["base_images"]["runtime"]["reference"].rsplit("@", 1)[0]
        lock["base_images"]["runtime"]["reference"] = f"{prefix}@{changed_digest}"
        lock_path = self.write_lock(lock)
        with self.assertRaises(artifacts.LockError):
            artifacts.validate_lock(lock_path, repository / "artifacts" / "lock-inputs.json")

    @requirements("L3-SUP-002")
    def test_duplicate_and_unapproved_signer_or_url_are_rejected(self) -> None:
        value = valid_lock()
        value["packages"].append(copy.deepcopy(value["packages"][0]))
        self.assert_rejected(value)
        value = valid_lock()
        value["packages"][0]["signing_key_fingerprint"] = "A" * 40
        self.assert_rejected(value)
        value = valid_lock()
        value["packages"][0]["url"] = "https://example.invalid/package.rpm"
        self.assert_rejected(value)

    def test_exact_bundle_is_accepted_with_or_without_sources(self) -> None:
        for include_sources in (False, True):
            with self.subTest(include_sources=include_sources):
                lock_path = self.root / f"lock-{include_sources}.json"
                bundle = self.write_bundle(lock_path, valid_lock(), include_sources)
                artifacts.verify_bundle(lock_path, bundle, include_sources)
                if bundle.exists():
                    for path in sorted(bundle.rglob("*"), reverse=True):
                        if path.is_file():
                            path.unlink()
                        else:
                            path.rmdir()
                    bundle.rmdir()

    @requirements("L3-SUP-007")
    def test_tampered_missing_unexpected_and_wrong_lock_bundles_fail_closed(self) -> None:
        cases = ("tampered", "missing", "unexpected", "wrong-lock")
        for case in cases:
            with self.subTest(case=case):
                lock_path = self.root / f"{case}.json"
                value = valid_lock()
                bundle = self.write_bundle(lock_path, value)
                rpm = bundle / "rpms" / value["packages"][0]["filename"]
                if case == "tampered":
                    rpm.write_bytes(b"x")
                elif case == "missing":
                    rpm.unlink()
                elif case == "unexpected":
                    (bundle / "unexpected").write_text("x", encoding="utf-8")
                else:
                    lock_path.write_text(json.dumps({**value, "generated_at": "2026-09-13T00:00:00Z"}), encoding="utf-8")
                with self.assertRaises(artifacts.LockError):
                    artifacts.verify_bundle(lock_path, bundle)
                for path in sorted(bundle.rglob("*"), reverse=True):
                    if path.is_file():
                        path.unlink()
                    else:
                        path.rmdir()
                bundle.rmdir()

    @requirements("L3-SUP-004")
    def test_alternate_source_map_requires_an_exact_safe_mapping(self) -> None:
        value = valid_lock()
        expected = set(artifacts.bundle_artifacts(value))
        mapping = {
            "schema_version": 1,
            "artifacts": {path: f"https://mirror.example.test/{path}" for path in expected},
        }
        path = self.root / "source-map.json"
        path.write_text(json.dumps(mapping), encoding="utf-8")
        urls, hosts = artifacts.read_source_map(path, expected)
        self.assertEqual(set(urls), expected)
        self.assertEqual(hosts, {"mirror.example.test"})

        invalid = copy.deepcopy(mapping)
        invalid["artifacts"].pop(next(iter(expected)))
        path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(artifacts.LockError):
            artifacts.read_source_map(path, expected)

        invalid = copy.deepcopy(mapping)
        invalid["artifacts"]["unexpected"] = "https://mirror.example.test/unexpected"
        path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(artifacts.LockError):
            artifacts.read_source_map(path, expected)

        invalid = copy.deepcopy(mapping)
        logical_path = next(iter(expected))
        invalid["artifacts"][logical_path] = "https://user:secret@mirror.example.test/file"
        path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(artifacts.LockError):
            artifacts.read_source_map(path, expected)

    @requirements("L3-SUP-003")
    def test_acquisition_publishes_only_a_complete_verified_bundle(self) -> None:
        value = valid_lock()
        value["signing_keys"][0]["sha256"] = artifacts.hashlib.sha256(b"k").hexdigest()
        value["packages"][0]["sha256"] = artifacts.hashlib.sha256(b"r").hexdigest()
        lock_path = self.write_lock(value)
        output = self.root / "acquired"

        def fake_download(url, destination, hosts, context, token):
            del url, hosts, context, token
            destination.write_bytes(b"k" if destination.parent.name == "keys" else b"r")

        with mock.patch.object(artifacts, "download", side_effect=fake_download):
            artifacts.acquire_bundle(lock_path, output)
        artifacts.verify_bundle(lock_path, output)
        self.assertEqual(list(self.root.glob(".acquired.*")), [])

        with self.assertRaises(artifacts.LockError):
            artifacts.acquire_bundle(lock_path, output)

        failed_output = self.root / "failed"
        with mock.patch.object(artifacts, "download", side_effect=artifacts.LockError("failed")):
            with self.assertRaises(artifacts.LockError):
                artifacts.acquire_bundle(lock_path, failed_output)
        self.assertFalse(failed_output.exists())
        self.assertEqual(list(self.root.glob(".failed.*")), [])


if __name__ == "__main__":
    unittest.main()
