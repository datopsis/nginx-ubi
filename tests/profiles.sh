#!/usr/bin/env bash
set -Eeuo pipefail

runtime="${CONTAINER_RUNTIME:-podman}"
image="${IMAGE:-localhost/nginx-ubi9:development}"
python="${PYTHON:-python3}"
script_dir="${SCRIPT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}"
repository="${REPOSITORY:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
examples_dir="${EXAMPLES_DIR:-${repository}/examples/profiles}"
null_device="${NULL_DEVICE:-/dev/null}"
prefix="nginx-ubi9-profile-${RANDOM}-$$"
network="${prefix}-network"
static="${prefix}-static"
backend="${prefix}-backend"
proxy="${prefix}-proxy"
tmp_root="${PROFILE_TMPDIR:-/tmp}"
static_headers=$(mktemp "${tmp_root}/nginx-static-headers.XXXXXX")
proxy_headers=$(mktemp "${tmp_root}/nginx-proxy-headers.XXXXXX")
proxy_body=$(mktemp "${tmp_root}/nginx-proxy-body.XXXXXX")
no_new_privileges="no-new-privileges:true"

if grep -qi podman <<< "$("${runtime}" --version 2>&1)"; then
    no_new_privileges="no-new-privileges"
fi

cleanup() {
    "${runtime}" rm --force "${static}" "${proxy}" "${backend}" \
        >/dev/null 2>&1 || true
    "${runtime}" network rm "${network}" >/dev/null 2>&1 || true
    rm -f -- "${static_headers}" "${proxy_headers}" "${proxy_body}"
}
trap cleanup EXIT

run_restricted() {
    local name="$1"
    local uid="$2"
    shift 2
    "${runtime}" run --detach --name "${name}" \
        --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
        --cap-drop ALL \
        --security-opt "${no_new_privileges}" \
        --user "${uid}:0" \
        "$@" \
        "${image}" -c /etc/nginx/nginx.conf -g 'daemon off;' \
        >/dev/null
}

wait_for_http() {
    local url="$1"
    local name="$2"
    local _
    for _ in {1..30}; do
        if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
            "${url}" || true)" = 200; then
            return
        fi
        sleep 1
    done
    "${runtime}" logs "${name}" >&2
    echo "Timed out waiting for ${name}" >&2
    return 1
}

assert_process_security() {
    local name="$1"
    # Values expand inside the container, not in this test process.
    # shellcheck disable=SC2016
    "${runtime}" exec "${name}" sh -eu -c '
        test "$(id -u)" -ne 0
        test "$(id -g)" -eq 0
        while IFS=: read -r key value; do
            case "${key}" in
                CapEff) set -- ${value}; test "$1" = 0000000000000000 ;;
                NoNewPrivs) set -- ${value}; test "$1" = 1 ;;
            esac
        done < /proc/1/status
    '
}

header_value() {
    local header="$1"
    local file="$2"
    sed -n "s/^${header}:[[:space:]]*//Ip" "${file}" | tr -d '\r' | head -n 1
}

"${runtime}" image inspect "${image}" >/dev/null
"${runtime}" network create "${network}" >/dev/null

run_restricted "${static}" 10001 \
    --publish 127.0.0.1::8080 \
    --volume "${examples_dir}/static/nginx.conf:/etc/nginx/nginx.conf:ro" \
    --volume "${script_dir}/fixtures/profile-site:/srv/www:ro"
static_binding=$("${runtime}" port "${static}" 8080/tcp)
static_port=${static_binding##*:}
static_url="http://127.0.0.1:${static_port}"
wait_for_http "${static_url}/healthz" "${static}"
assert_process_security "${static}"
"${runtime}" exec "${static}" nginx -t -q -c /etc/nginx/nginx.conf

test "$(curl --fail --silent --show-error "${static_url}/")" = \
    "static-profile-ok"
curl --silent --show-error \
    --header 'X-Request-ID: static.valid-1' \
    --dump-header "${static_headers}" \
    --output "${null_device}" \
    "${static_url}/missing?profile-secret=do-not-log"
test "$(header_value X-Request-ID "${static_headers}")" = "static.valid-1"

curl --silent --show-error \
    --header 'X-Request-ID: invalid/request/id' \
    --dump-header "${static_headers}" \
    --output "${null_device}" \
    "${static_url}/"
generated_request_id=$(header_value X-Request-ID "${static_headers}")
[[ "${generated_request_id}" =~ ^[0-9a-f]{32}$ ]]

test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    --request POST "${static_url}/")" = 403
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    "${static_url}/.hidden")" = 403
static_logs=$("${runtime}" logs "${static}" 2>&1)
if grep -Fq '/healthz' <<< "${static_logs}"; then
    echo "The static health endpoint unexpectedly wrote an access event" >&2
    exit 1
fi
printf '%s\n' "${static_logs}" | "${python}" \
    "${script_dir}/validate_profile_logs.py" \
    --profile static \
    --uri /missing \
    --request-id static.valid-1 \
    --status 404 \
    --forbidden profile-secret \
    --forbidden do-not-log

run_restricted "${backend}" 10002 \
    --network "${network}" \
    --network-alias backend \
    --volume "${script_dir}/fixtures/profile-backend/nginx.conf:/etc/nginx/nginx.conf:ro"
"${runtime}" exec "${backend}" nginx -t -q -c /etc/nginx/nginx.conf
assert_process_security "${backend}"

run_restricted "${proxy}" 10003 \
    --network "${network}" \
    --publish 127.0.0.1::8080 \
    --volume "${examples_dir}/reverse-proxy/nginx.conf:/etc/nginx/nginx.conf:ro"
proxy_binding=$("${runtime}" port "${proxy}" 8080/tcp)
proxy_port=${proxy_binding##*:}
proxy_url="http://127.0.0.1:${proxy_port}"
wait_for_http "${proxy_url}/healthz" "${proxy}"
assert_process_security "${proxy}"
"${runtime}" exec "${proxy}" nginx -t -q -c /etc/nginx/nginx.conf

curl --fail --silent --show-error \
    --header 'X-Request-ID: proxy.valid-1' \
    --header 'X-Forwarded-For: 203.0.113.9' \
    --dump-header "${proxy_headers}" \
    --output "${proxy_body}" \
    "${proxy_url}/application?reverse-secret=do-not-log"
test "$(header_value X-Request-ID "${proxy_headers}")" = "proxy.valid-1"
"${python}" -c \
    'import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["xff"] != "203.0.113.9"
assert payload["proto"] == "http"
assert payload["request_id"] == "proxy.valid-1"' \
    "${proxy_body}"

"${runtime}" stop --time 10 "${backend}" >/dev/null
failure_status=$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    --header 'X-Request-ID: proxy.failure-1' \
    "${proxy_url}/unavailable")
[[ "${failure_status}" =~ ^50[24]$ ]]
proxy_logs=$("${runtime}" logs "${proxy}" 2>&1)
if grep -Fq '/healthz' <<< "${proxy_logs}"; then
    echo "The reverse-proxy health endpoint unexpectedly wrote an access event" >&2
    exit 1
fi
printf '%s\n' "${proxy_logs}" | "${python}" \
    "${script_dir}/validate_profile_logs.py" \
    --profile reverse-proxy \
    --uri /application \
    --request-id proxy.valid-1 \
    --status 200 \
    --forbidden reverse-secret \
    --forbidden do-not-log
printf '%s\n' "${proxy_logs}" | "${python}" \
    "${script_dir}/validate_profile_logs.py" \
    --profile reverse-proxy \
    --uri /unavailable \
    --request-id proxy.failure-1 \
    --status "${failure_status}"

"${runtime}" stop --time 10 "${static}" "${proxy}" >/dev/null
test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${static}")" = 0
test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${proxy}")" = 0

echo "Static and reverse-proxy profile qualification passed for ${image}"
