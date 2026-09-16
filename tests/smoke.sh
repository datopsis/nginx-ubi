#!/usr/bin/env bash
set -Eeuo pipefail

runtime="${CONTAINER_RUNTIME:-podman}"
image="${IMAGE:-localhost/nginx-ubi9:development}"
python="${PYTHON:-python3}"
script_dir="${SCRIPT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}"
repository="${REPOSITORY:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
null_device="${NULL_DEVICE:-/dev/null}"
prefix="nginx-ubi9-smoke-${RANDOM}-$$"
primary="${prefix}-primary"
arbitrary="${prefix}-arbitrary"
missing_tmp="${prefix}-missing-tmp"
invalid_config="${prefix}-invalid-config"
graceful="${prefix}-graceful"
graceful_output=$(mktemp "${SMOKE_TMPDIR:-/tmp}/nginx-ubi-smoke.XXXXXX")
missing_tmp_runtime_args=()
no_new_privileges="no-new-privileges:true"

if grep -qi podman <<< "$("${runtime}" --version 2>&1)"; then
    # Podman otherwise creates writable tmpfs mounts for read-only containers.
    missing_tmp_runtime_args+=(--read-only-tmpfs=false)
    # Older supported-for-development Podman releases reject Docker's :true
    # spelling but enforce the same security option with the bare name.
    no_new_privileges="no-new-privileges"
fi

cleanup() {
    "${runtime}" rm --force \
        "${primary}" "${arbitrary}" "${missing_tmp}" "${invalid_config}" \
        "${graceful}" \
        >/dev/null 2>&1 || true
    rm -f -- "${graceful_output}"
}
trap cleanup EXIT

run_restricted() {
    local name="$1"
    shift
    "${runtime}" run --detach --name "${name}" \
        --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
        --cap-drop ALL \
        --security-opt "${no_new_privileges}" \
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

worker_pids() {
    local name="$1"
    # NGINX workers are the non-PID-1 nginx processes in this single-service image.
    #
    # This function is called while workers are being replaced, so a process
    # can exit between the glob and the read. Reading /proc/PID/comm through a
    # command substitution lets a vanished process be skipped; redirecting from
    # the file instead would abort the whole listing under `sh -e`.
    #
    # The variables expand in the inner container shell, not this script.
    # shellcheck disable=SC2016
    "${runtime}" exec "${name}" sh -eu -c '
        for comm in /proc/[0-9]*/comm; do
            command_name=$(cat "${comm}" 2>/dev/null) || continue
            test "${command_name}" = nginx || continue
            pid=${comm#/proc/}
            pid=${pid%/comm}
            test "${pid}" != 1 || continue
            printf "%s\n" "${pid}"
        done
    ' | sort -n
}

assert_reload_replaced_workers() {
    local name="$1"
    local old_workers
    local new_workers
    local old_pid
    local replaced
    local _
    old_workers=$(worker_pids "${name}")
    test -n "${old_workers}"
    "${runtime}" exec "${name}" nginx -s reload
    for _ in {1..30}; do
        new_workers=$(worker_pids "${name}")
        replaced=1
        test -n "${new_workers}" || replaced=""
        test "${new_workers}" != "${old_workers}" || replaced=""
        while IFS= read -r old_pid; do
            test -n "${old_pid}" || continue
            if "${runtime}" exec "${name}" test -e "/proc/${old_pid}"; then
                replaced=""
            fi
        done <<< "${old_workers}"
        if test -n "${replaced}"; then
            test "$("${runtime}" exec "${name}" sh -c 'cat /tmp/nginx.pid')" = "1"
            return
        fi
        sleep 1
    done
    "${runtime}" logs "${name}" >&2
    echo "NGINX reload did not replace its worker processes" >&2
    return 1
}

assert_active_request_drains_on_stop() {
    local binding
    local host_port
    local curl_pid
    local size
    local started=""
    local _
    "${runtime}" run --detach --name "${graceful}" \
        --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
        --cap-drop ALL \
        --security-opt "${no_new_privileges}" \
        --publish 127.0.0.1::8080 \
        --volume "${script_dir}/fixtures/graceful-nginx.conf:/tmp/graceful-nginx.conf:ro" \
        --entrypoint sh \
        "${image}" -eu -c \
        'dd if=/dev/zero of=/tmp/slow.bin bs=1024 count=256 2>/dev/null; exec nginx -c /tmp/graceful-nginx.conf -g "daemon off;"' \
        >/dev/null
    binding=$("${runtime}" port "${graceful}" 8080/tcp)
    host_port=${binding##*:}
    started=""
    for _ in {1..30}; do
        if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
            "http://127.0.0.1:${host_port}/healthz" || true)" = 200; then
            started=1
            break
        fi
        sleep 1
    done
    if test -z "${started}"; then
        "${runtime}" logs "${graceful}" >&2
        echo "Timed out waiting for the graceful-stop test server" >&2
        return 1
    fi
    started=""
    curl --fail --silent --show-error \
        "http://127.0.0.1:${host_port}/slow" --output "${graceful_output}" &
    curl_pid=$!
    for _ in {1..50}; do
        size=$(wc -c < "${graceful_output}")
        if test "${size}" -gt 0 && test "${size}" -lt 262144; then
            started=1
            break
        fi
        sleep 0.1
    done
    test -n "${started}"
    "${runtime}" stop --time 20 "${graceful}" >/dev/null
    wait "${curl_pid}"
    test "$(wc -c < "${graceful_output}")" -eq 262144
    test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${graceful}")" = "0"
    grep -Fq 'gracefully shutting down' <<< \
        "$("${runtime}" logs "${graceful}" 2>&1)"
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

wait_for_log() {
    local name="$1"
    local expected="$2"
    local logs
    local _
    for _ in {1..15}; do
        logs="$("${runtime}" logs "${name}" 2>&1)"
        if grep -Fq "${expected}" <<< "${logs}"; then
            return
        fi
        sleep 1
    done
    "${runtime}" logs "${name}" >&2
    echo "Timed out waiting for ${name} to log: ${expected}" >&2
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
nginx_build=$("${runtime}" exec "${primary}" nginx -V 2>&1)
printf '%s\n' "${nginx_build}" | "${python}" \
    "${repository}/scripts/nginx_features.py"
architecture=$("${runtime}" image inspect --format '{{.Architecture}}' "${image}")
expected_rpm_manifest_sha256=$(
    "${python}" "${repository}/scripts/artifacts.py" rpm-manifest \
        "${repository}/artifacts/locks/${architecture}.json" \
        | tr -d '\r' | sha256sum | cut -d' ' -f1
)
actual_rpm_manifest_sha256=$(
    "${runtime}" exec "${primary}" cat /usr/share/nginx-ubi/rpm-manifest.tsv \
        | sha256sum | cut -d' ' -f1
)
test "${actual_rpm_manifest_sha256}" = "${expected_rpm_manifest_sha256}"
test "$("${runtime}" exec "${primary}" \
    sh -c 'wc -l < /usr/share/nginx-ubi/rpm-manifest.tsv')" -eq 80
"${runtime}" exec "${primary}" test ! -w /usr/share/nginx-ubi/rpm-manifest.tsv
"${runtime}" exec "${primary}" test -d /usr/lib64/nginx/modules
test -z "$("${runtime}" exec "${primary}" \
    find /usr/lib64/nginx/modules -mindepth 1 -maxdepth 1 -print)"
"${runtime}" exec "${primary}" test ! -w /etc/nginx/nginx.conf
"${runtime}" exec "${primary}" sh -c \
    '! command -v dnf && ! command -v microdnf && ! command -v rpm && ! command -v yum'
"${runtime}" exec "${primary}" sh -c \
    '! (printf probe > /root-filesystem-probe) >/dev/null 2>&1'
"${runtime}" exec "${primary}" test ! -e /etc/yum.repos.d
# The variable expands in the inner container shell, not this script.
# shellcheck disable=SC2016
"${runtime}" exec "${primary}" sh -c 'read -r pid < /tmp/nginx.pid; test "${pid}" = "1"'

binding="$("${runtime}" port "${primary}" 8080/tcp)"
host_port="${binding##*:}"
test "$(curl --fail --silent --show-error "http://127.0.0.1:${host_port}/healthz")" = "ok"
grep -Fq 'NGINX on UBI 9' <<< \
    "$(curl --fail --silent --show-error "http://127.0.0.1:${host_port}/")"
test "$(curl --silent --show-error --output "${null_device}" --write-out '%{http_code}' \
    "http://127.0.0.1:${host_port}/missing?smoke-probe=value")" = "404"
grep -Eiq '^server: nginx[[:space:]]*$' <<< \
    "$(curl --fail --silent --show-error --dump-header - --output "${null_device}" \
        "http://127.0.0.1:${host_port}/healthz")"
primary_logs="$("${runtime}" logs "${primary}" 2>&1)"
grep -Fq '/missing?smoke-probe=value' <<< "${primary_logs}"
if grep -Fq 'GET /healthz' <<< "${primary_logs}"; then
    echo "The health endpoint unexpectedly wrote an access event" >&2
    exit 1
fi

assert_reload_replaced_workers "${primary}"
test "$(curl --fail --silent --show-error "http://127.0.0.1:${host_port}/healthz")" = "ok"
wait_for_log "${primary}" 'reconfiguring'

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
    --security-opt "${no_new_privileges}" \
    "${image}" >/dev/null
wait_for_exit "${missing_tmp}"
missing_tmp_logs=$("${runtime}" logs "${missing_tmp}" 2>&1)
grep -Fq '/tmp/nginx-client-body' <<< "${missing_tmp_logs}"
grep -Eiq 'read-only file system|permission denied' <<< "${missing_tmp_logs}"

"${runtime}" run --detach --name "${invalid_config}" \
    --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
    --cap-drop ALL \
    --security-opt "${no_new_privileges}" \
    --volume "${script_dir}/fixtures/invalid-nginx.conf:/etc/nginx/nginx.conf:ro" \
    "${image}" \
    >/dev/null
wait_for_exit "${invalid_config}"
invalid_logs=$("${runtime}" logs "${invalid_config}" 2>&1)
grep -Eiq 'unknown directive.*invalid_directive' <<< "${invalid_logs}"
grep -Fq '/etc/nginx/nginx.conf:1' <<< "${invalid_logs}"

assert_active_request_drains_on_stop

assert_clean_exit "${arbitrary}"
assert_clean_exit "${primary}"

echo "Rootless restricted-runtime scenario tests passed for ${image}"
