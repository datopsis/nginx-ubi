#!/usr/bin/env bash
# Native rootless Podman rehearsal. No fixture packages enter the image.
set -Eeuo pipefail
runtime=${CONTAINER_RUNTIME:-podman}
image=${IMAGE:-localhost/nginx-ubi9:development}
repository=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
evidence=$(mktemp -d /tmp/nginx-tls-proxies.XXXXXX)
prefix="nginx-tls-proxies-${RANDOM}-$$"
network="${prefix}-network"
proxy="${prefix}-proxy"
backend="${prefix}-backend"
client="${prefix}-client"
cleanup() {
    "${runtime}" rm --force "${client}" "${backend}" "${proxy}" >/dev/null 2>&1 || true
    "${runtime}" network rm "${network}" >/dev/null 2>&1 || true
    rm -rf -- "${evidence}"
}
trap cleanup EXIT
trap '"${runtime}" logs "${proxy}" >&2; "${runtime}" logs "${backend}" >&2' ERR

test "$(id -u)" -ne 0
"${runtime}" info --format '{{.Host.Security.Rootless}}' | grep -qx true
go version
mkdir "${evidence}/bin"
GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off CGO_ENABLED=0 \
    go build -p 2 -trimpath -o "${evidence}/bin/fixture" \
    "${repository}/tests/fixtures/tls-proxy/main.go"
"${evidence}/bin/fixture" pki "${evidence}/pki"
chmod 755 "${evidence}"
# Rootless Podman maps the runner's group to container GID 0. Keys stay 0640.
restricted=(--read-only --cap-drop ALL --security-opt no-new-privileges
    --tmpfs "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777" --user 999:0
    --volume "${evidence}/bin:/fixture:ro")
"${runtime}" network create "${network}" >/dev/null

run_client() {
    "${runtime}" run --rm --name "${client}" "${restricted[@]}" \
        --network "${network}" \
        --volume "${evidence}/pki/public:/trust:ro" \
        --entrypoint /fixture/fixture "${image}" "$@"
}
check() {
    run_client check "${profile}" "https://${host}:${port}" /trust/ca.crt "$@"
}
start_pair() {
    local kind=$1
    "${runtime}" run --detach --name "${proxy}" "${restricted[@]}" \
        --user 10001:0 --network "${network}" \
        --network-alias "${host}" --network-alias wrong.test \
        --volume "${repository}/examples/profiles/${profile}:/etc/nginx/profile:ro" \
        --volume "${evidence}/pki/${host}/${kind}:/etc/nginx/tls:ro" \
        "${image}" -c /etc/nginx/profile/nginx.conf -g 'daemon off;' >/dev/null
    "${runtime}" run --detach --name "${backend}" "${restricted[@]}" \
        --network "container:${proxy}" \
        --entrypoint /fixture/fixture "${image}" serve "${profile}" >/dev/null
    # Only readiness retries. The actual positive/negative assertions never retry.
    for attempt in {1..30}; do
        if "${runtime}" exec "${backend}" /fixture/fixture probe "127.0.0.1:${backend_port}" open >/dev/null 2>&1 \
            && run_client probe "${host}:${port}" open >/dev/null 2>&1; then
            return
        fi
        if test "${attempt}" = 30; then return 1; fi
        sleep 1
    done
}
stop_pair() {
    "${runtime}" logs "${proxy}" > "${evidence}/proxy.log" 2>&1
    # No request bodies, query secrets or private PEM material in either log stream.
    if grep -E 'query-private|body-private|BEGIN .*PRIVATE KEY' "${evidence}/proxy.log"; then
        return 1
    fi
    "${runtime}" rm --force "${backend}" "${proxy}" >/dev/null
}

for profile in lakekeeper sail; do
    if test "${profile}" = lakekeeper; then
        host=catalog; port=8181; backend_port=8182
    else
        host=sail; port=50051; backend_port=50052
    fi
    start_pair valid
    "${runtime}" exec "${proxy}" /fixture/fixture security
    "${runtime}" exec "${backend}" /fixture/fixture security
    # Sharing networking must not share the proxy's secret mount.
    "${runtime}" exec "${backend}" sh -c 'test ! -e /etc/nginx/tls/server.key'
    test "$("${runtime}" exec "${proxy}" readlink /proc/self/ns/net)" = \
        "$("${runtime}" exec "${backend}" readlink /proc/self/ns/net)"
    echo "PASS ${profile} shared network namespace and separate key mounts"
    check ok tls12
    check ok tls13
    run_client plaintext "${host}:${port}"
    # IPv6 listener is TLS-only too, even though the test bridge is IPv4.
    "${runtime}" exec "${backend}" /fixture/fixture plaintext "[::1]:${port}"
    check ok short
    run_client check "${profile}" "https://${host}:${port}" /trust/wrong-ca.crt ca short
    check ok short
    run_client check "${profile}" "https://wrong.test:${port}" /trust/ca.crt hostname short
    check ok short
    # A positive control from the same peer rules out an isolated/dead network.
    run_client probe "${host}:${port}" open
    run_client probe "${host}:${backend_port}" closed
    for closed_port in 8080 8443 9000; do
        run_client probe "${host}:${closed_port}" closed
    done
    "${runtime}" exec "${backend}" /fixture/fixture probe "[::1]:${backend_port}" closed
    check ok short
    if test "${profile}" = sail; then
        check ok long
        check ok status
    fi
    stop_pair
    # Recreate both sides together: never strand a backend in an old namespace.
    for mutation in expired wrong-san wrong-issuer; do
        case "${mutation}" in
            expired) expected=expired ;;
            wrong-san) expected=hostname ;;
            wrong-issuer) expected=ca ;;
        esac
        start_pair "${mutation}"
        check "${expected}" short
        stop_pair
        start_pair valid
        check ok short
        stop_pair
    done
    echo "PASS ${profile} TLS proxy rehearsal"
done
