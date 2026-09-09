#!/usr/bin/env bash
set -Eeuo pipefail

runtime="${CONTAINER_RUNTIME:-podman}"
image="${IMAGE:-localhost/nginx-ubi9:development}"
prefix="nginx-ubi9-smoke-${RANDOM}-$$"
primary="${prefix}-primary"
arbitrary="${prefix}-arbitrary"
missing_tmp="${prefix}-missing-tmp"
invalid_config="${prefix}-invalid-config"
missing_tmp_runtime_args=()

if "${runtime}" --version 2>&1 | grep -qi podman; then
    # Podman otherwise creates writable tmpfs mounts for read-only containers.
    missing_tmp_runtime_args+=(--read-only-tmpfs=false)
fi

cleanup() {
    "${runtime}" rm --force \
        "${primary}" "${arbitrary}" "${missing_tmp}" "${invalid_config}" \
        >/dev/null 2>&1 || true
}
trap cleanup EXIT

run_restricted() {
    local name="$1"
    shift
    "${runtime}" run --detach --name "${name}" \
        --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
        --cap-drop ALL \
        --security-opt no-new-privileges:true \
        "$@" \
        "${image}" >/dev/null
}

assert_process_security() {
    local name="$1"
    # The variables expand in the inner container shell, not this script.
    # shellcheck disable=SC2016
    "${runtime}" exec "${name}" sh -eu -c '
        for status in /proc/[0-9]*/status; do
            uid=""
            cap_eff=""
            no_new_privs=""
            while IFS=: read -r key value; do
                case "${key}" in
                    Uid)
                        set -- ${value}
                        uid="$1"
                        ;;
                    CapEff)
                        set -- ${value}
                        cap_eff="$1"
                        ;;
                    NoNewPrivs)
                        set -- ${value}
                        no_new_privs="$1"
                        ;;
                esac
            done < "${status}"
            test -n "${uid}"
            test "${uid}" -ne 0
            test "${cap_eff}" = "0000000000000000"
            test "${no_new_privs}" = "1"
        done
    '
}

assert_tmpfs_security() {
    local name="$1"
    # The variables expand in the inner container shell, not this script.
    # shellcheck disable=SC2016
    "${runtime}" exec "${name}" sh -eu -c '
        found=""
        while read -r _ mount_point _ options _; do
            if test "${mount_point}" = "/tmp"; then
                found=1
                case ",${options}," in *,rw,*) : ;; *) exit 1 ;; esac
                case ",${options}," in *,noexec,*) : ;; *) exit 1 ;; esac
                case ",${options}," in *,nosuid,*) : ;; *) exit 1 ;; esac
                case ",${options}," in *,nodev,*) : ;; *) exit 1 ;; esac
            fi
        done < /proc/mounts
        test "${found}" = "1"
        printf "#!/bin/sh\nexit 0\n" > /tmp/noexec-probe
        chmod 0700 /tmp/noexec-probe
        ! /tmp/noexec-probe >/dev/null 2>&1
        rm -f /tmp/noexec-probe
    '
}

assert_clean_exit() {
    local name="$1"
    "${runtime}" stop --time 10 "${name}" >/dev/null
    test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${name}")" = "0"
}

wait_for_exit() {
    local name="$1"
    local state
    local exit_code
    local _
    for _ in {1..15}; do
        state="$("${runtime}" inspect --format '{{.State.Status}}' "${name}")"
        if test "${state}" != "running"; then
            exit_code="$("${runtime}" inspect --format '{{.State.ExitCode}}' "${name}")"
            test "${exit_code}" != "0"
            return
        fi
        sleep 1
    done
    "${runtime}" logs "${name}" >&2
    echo "Expected ${name} to exit with a failure" >&2
    return 1
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
assert_process_security "${primary}"
assert_tmpfs_security "${primary}"
"${runtime}" exec "${primary}" nginx -t -q
"${runtime}" exec "${primary}" test ! -w /etc/nginx/nginx.conf
"${runtime}" exec "${primary}" sh -c \
    '! command -v dnf && ! command -v microdnf && ! command -v rpm && ! command -v yum'
"${runtime}" exec "${primary}" sh -c \
    '! (printf probe > /root-filesystem-probe) >/dev/null 2>&1'
# The variable expands in the inner container shell, not this script.
# shellcheck disable=SC2016
"${runtime}" exec "${primary}" sh -c 'read -r pid < /tmp/nginx.pid; test "${pid}" = "1"'

binding="$("${runtime}" port "${primary}" 8080/tcp)"
host_port="${binding##*:}"
test "$(curl --fail --silent --show-error "http://127.0.0.1:${host_port}/healthz")" = "ok"
curl --fail --silent --show-error "http://127.0.0.1:${host_port}/" | grep -Fq 'NGINX on UBI 9'
test "$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    "http://127.0.0.1:${host_port}/missing?smoke-probe=value")" = "404"
curl --fail --silent --show-error --dump-header - --output /dev/null \
    "http://127.0.0.1:${host_port}/healthz" | \
    grep -Eiq '^server: nginx[[:space:]]*$'
"${runtime}" logs "${primary}" 2>&1 | grep -Fq '/missing?smoke-probe=value'
if "${runtime}" logs "${primary}" 2>&1 | grep -Fq 'GET /healthz'; then
    echo "The health endpoint unexpectedly wrote an access event" >&2
    exit 1
fi

"${runtime}" exec "${primary}" nginx -s reload
test "$(curl --fail --silent --show-error "http://127.0.0.1:${host_port}/healthz")" = "ok"
"${runtime}" logs "${primary}" 2>&1 | grep -Fq 'reconfiguring'

run_restricted "${arbitrary}" --user 10001:0
wait_for_nginx "${arbitrary}"
test "$("${runtime}" exec "${arbitrary}" id -u)" = "10001"
test "$("${runtime}" exec "${arbitrary}" id -g)" = "0"
assert_process_security "${arbitrary}"
assert_tmpfs_security "${arbitrary}"
"${runtime}" exec "${arbitrary}" nginx -t -q

"${runtime}" run --detach --name "${missing_tmp}" \
    --read-only \
    "${missing_tmp_runtime_args[@]}" \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    "${image}" >/dev/null
wait_for_exit "${missing_tmp}"
"${runtime}" logs "${missing_tmp}" 2>&1 | grep -Eiq \
    'read-only file system|/tmp/nginx.pid'

"${runtime}" run --detach --name "${invalid_config}" \
    --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    --entrypoint sh \
    "${image}" -eu -c \
    'printf "invalid_directive;\n" > /tmp/invalid.conf; exec nginx -t -c /tmp/invalid.conf' \
    >/dev/null
wait_for_exit "${invalid_config}"
"${runtime}" logs "${invalid_config}" 2>&1 | grep -Eiq \
    'unknown directive.*invalid_directive|emerg'

assert_clean_exit "${arbitrary}"
assert_clean_exit "${primary}"

echo "Rootless restricted-runtime scenario tests passed for ${image}"
