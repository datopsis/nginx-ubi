#!/usr/bin/env bash
set -euo pipefail

architecture=${1:?usage: hermetic-build-negative.sh ARCHITECTURE}
runtime=${CONTAINER_RUNTIME:-podman}
python=${PYTHON:-python3}
bundle=${ARTIFACT_BUNDLE:-.artifact-bundle/${architecture}}
lock=artifacts/locks/${architecture}.json
builder=$("${python}" scripts/artifacts.py base-reference "${lock}" builder)
runtime_base=$("${python}" scripts/artifacts.py base-reference "${lock}" runtime)

expect_build_failure() {
    local label=$1
    shift
    if "$@" >/dev/null 2>&1; then
        echo "Hermetic build unexpectedly accepted ${label}" >&2
        return 1
    fi
}

common_args=(
    build
    --file Containerfile
    --format docker
    --network none
    --pull=never
    --build-context "artifact_bundle=${bundle}"
    --build-arg "UBI_MICRO_IMAGE=${runtime_base}"
)

expect_build_failure "the wrong lock identity" \
    "${runtime}" "${common_args[@]}" \
    --build-arg "UBI_MINIMAL_IMAGE=${builder}" \
    --build-arg "ARTIFACT_LOCK_SHA256=$(printf '0%.0s' {1..64})" \
    .

expect_build_failure "an unavailable base while pulling is forbidden" \
    "${runtime}" "${common_args[@]}" \
    --build-arg "UBI_MINIMAL_IMAGE=localhost/nginx-ubi-missing-base:never" \
    --build-arg "ARTIFACT_LOCK_SHA256=$(sha256sum "${lock}" | cut -d' ' -f1)" \
    .
