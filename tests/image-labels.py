"""Compare built image provenance labels to the actual checkout and arch lock."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

architecture, image = sys.argv[1:]
if architecture not in ("amd64", "arm64"):
    raise SystemExit("unsupported architecture")
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
lock_hash = hashlib.sha256(Path(f"artifacts/locks/{architecture}.json").read_bytes()).hexdigest()
metadata = json.loads(subprocess.check_output(
    [os.environ.get("CONTAINER_RUNTIME", "podman"), "image", "inspect", image], text=True
))[0]
expected = {
    "org.opencontainers.image.revision": revision,
    "io.datopsis.artifact-lock.sha256": lock_hash,
}
if metadata["Architecture"] != architecture:
    raise SystemExit("image architecture differs from selected lock")
for label, value in expected.items():
    if metadata["Config"]["Labels"].get(label) != value:
        raise SystemExit(f"image label {label} does not match checkout")
    print(f"PASS {architecture} {label}={value}")
