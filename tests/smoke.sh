#!/usr/bin/env bash
set -Eeuo pipefail

runtime="${CONTAINER_RUNTIME:-podman}"
image="${IMAGE:-localhost/nginx-ubi9:development}"
prefix="nginx-ubi9-smoke-${RANDOM}-$$"
primary="${prefix}-primary"
arbitrary="${prefix}-arbitrary"

cleanup() {
    "${runtime}" rm --force "${primary}" "${arbitrary}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

run_restricted() {
    local name="$1"
    shift
    "${runtime}" run --detach --name "${name}" \
        --read-only \
        --tmpfs /tmp:size=64m,mode=1777 \
        --cap-drop ALL \
        --security-opt no-new-privileges:true \
        "$@" \
        "${image}" >/dev/null
}

wait_for_nginx() {
    local name="$1"
    local _
    for _ in {1..30}; do
        if "${runtime}" exec "${name}" nginx -t -q >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    "${runtime}" logs "${name}" >&2
    return 1
}

test "$("${runtime}" image inspect --format '{{.Config.User}}' "${image}")" = "999:0"

run_restricted "${primary}" --publish 127.0.0.1::8080
wait_for_nginx "${primary}"
test "$("${runtime}" exec "${primary}" id -u)" = "999"
test "$("${runtime}" exec "${primary}" id -g)" = "0"
"${runtime}" exec "${primary}" nginx -t -q
"${runtime}" exec "${primary}" test ! -w /etc/nginx/nginx.conf
"${runtime}" exec "${primary}" sh -c '! command -v dnf && ! command -v microdnf && ! command -v yum'

binding="$("${runtime}" port "${primary}" 8080/tcp)"
host_port="${binding##*:}"
test "$(curl --fail --silent --show-error "http://127.0.0.1:${host_port}/healthz")" = "ok"
curl --fail --silent --show-error "http://127.0.0.1:${host_port}/" | grep -Fq 'NGINX on UBI 9'

run_restricted "${arbitrary}" --user 10001:0
wait_for_nginx "${arbitrary}"
test "$("${runtime}" exec "${arbitrary}" id -u)" = "10001"
test "$("${runtime}" exec "${arbitrary}" id -g)" = "0"

echo "Rootless restricted-runtime smoke tests passed for ${image}"
