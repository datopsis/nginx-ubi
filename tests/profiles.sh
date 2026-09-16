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
pool_a="${prefix}-pool-a"
pool_b="${prefix}-pool-b"
balancer="${prefix}-balancer"
# The WebSocket fixture answers to the same generic `backend` service name the
# reverse-proxy example uses, so it gets its own network rather than competing
# for that alias.
ws_network="${prefix}-ws-network"
ws_backend="${prefix}-ws-backend"
ws_proxy="${prefix}-ws-proxy"
limited="${prefix}-limited"
# The health profile also addresses a generic `backend` service name, so it
# gets its own network rather than competing for that alias.
health_network="${prefix}-health-network"
health_backend="${prefix}-health-backend"
health_proxy="${prefix}-health-proxy"
tmp_root="${PROFILE_TMPDIR:-/tmp}"
static_headers=$(mktemp "${tmp_root}/nginx-static-headers.XXXXXX")
proxy_headers=$(mktemp "${tmp_root}/nginx-proxy-headers.XXXXXX")
proxy_body=$(mktemp "${tmp_root}/nginx-proxy-body.XXXXXX")
balancer_body=$(mktemp "${tmp_root}/nginx-balancer-body.XXXXXX")
ws_body=$(mktemp "${tmp_root}/nginx-ws-body.XXXXXX")
limited_root=$(mktemp -d "${tmp_root}/nginx-limited-root.XXXXXX")
no_new_privileges="no-new-privileges:true"

if grep -qi podman <<< "$("${runtime}" --version 2>&1)"; then
    no_new_privileges="no-new-privileges"
fi

cleanup() {
    "${runtime}" rm --force "${static}" "${proxy}" "${backend}" \
        "${pool_a}" "${pool_b}" "${balancer}" \
        "${ws_backend}" "${ws_proxy}" "${limited}" \
        "${health_backend}" "${health_proxy}" \
        >/dev/null 2>&1 || true
    "${runtime}" network rm "${network}" >/dev/null 2>&1 || true
    "${runtime}" network rm "${ws_network}" >/dev/null 2>&1 || true
    "${runtime}" network rm "${health_network}" >/dev/null 2>&1 || true
    rm -f -- "${static_headers}" "${proxy_headers}" "${proxy_body}" \
        "${balancer_body}" "${ws_body}"
    rm -rf -- "${limited_root}"
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

validate_event() {
    local name="$1"
    shift
    local output=""
    local attempt
    # An access event is written when the request completes, and the runtime
    # surfaces it through `logs` a moment later. Reading the log once turns
    # that delay into an intermittent "found 0 matching events", so wait for
    # the event to appear instead of assuming it already has.
    for attempt in $(seq 1 15); do
        if output=$("${runtime}" logs "${name}" 2>&1 | "${python}" \
            "${script_dir}/validate_profile_logs.py" "$@" 2>&1); then
            printf '%s\n' "${output}"
            return 0
        fi
        sleep 1
    done
    printf '%s\n' "${output}" >&2
    "${runtime}" logs "${name}" >&2
    return 1
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
validate_event "${static}" \
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
validate_event "${proxy}" \
    --profile reverse-proxy \
    --uri /application \
    --request-id proxy.valid-1 \
    --status 200 \
    --forbidden reverse-secret \
    --forbidden do-not-log
validate_event "${proxy}" \
    --profile reverse-proxy \
    --uri /unavailable \
    --request-id proxy.failure-1 \
    --status "${failure_status}"

# ---------------------------------------------------------------------------
# HTTP load balancing
# ---------------------------------------------------------------------------

run_restricted "${pool_a}" 10004 \
    --network "${network}" \
    --network-alias backend-a \
    --hostname pool-member-a \
    --volume "${script_dir}/fixtures/profile-pool/nginx.conf:/etc/nginx/nginx.conf:ro"
run_restricted "${pool_b}" 10005 \
    --network "${network}" \
    --network-alias backend-b \
    --hostname pool-member-b \
    --volume "${script_dir}/fixtures/profile-pool/nginx.conf:/etc/nginx/nginx.conf:ro"
"${runtime}" exec "${pool_a}" nginx -t -q -c /etc/nginx/nginx.conf
"${runtime}" exec "${pool_b}" nginx -t -q -c /etc/nginx/nginx.conf
assert_process_security "${pool_a}"
assert_process_security "${pool_b}"

run_restricted "${balancer}" 10006 \
    --network "${network}" \
    --publish 127.0.0.1::8080 \
    --volume "${examples_dir}/load-balancer/nginx.conf:/etc/nginx/nginx.conf:ro"
balancer_binding=$("${runtime}" port "${balancer}" 8080/tcp)
balancer_port=${balancer_binding##*:}
balancer_url="http://127.0.0.1:${balancer_port}"
wait_for_http "${balancer_url}/healthz" "${balancer}"
assert_process_security "${balancer}"
"${runtime}" exec "${balancer}" nginx -t -q -c /etc/nginx/nginx.conf

# Every healthy member must receive traffic. Round robin alternates per
# request, so a few requests are enough once the pool has settled.
#
# The probe converges instead of sampling once. A member that is still binding
# its listener when the balancer starts collects passive failures, and after
# `max_fails` it is withdrawn for `fail_timeout`, so a single early sample can
# legitimately observe one member. Retrying past `fail_timeout` distinguishes a
# pool that never balances from one that has not finished starting, without
# weakening the assertion that both members serve traffic.
members_seen=""
for round in $(seq 1 20); do
    members_seen=$(for attempt in 1 2 3 4; do
        curl --fail --silent --show-error \
            --header "X-Request-ID: balancer.spread-${round}-${attempt}" \
            "${balancer_url}/application" \
            | "${python}" -c 'import json, sys; print(json.load(sys.stdin)["member"])'
    done | sort -u | tr '\n' ' ')
    if test "${members_seen}" = "pool-member-a pool-member-b "; then
        break
    fi
    sleep 1
done
if test "${members_seen}" != "pool-member-a pool-member-b "; then
    "${runtime}" logs "${balancer}" >&2
    echo "The pool did not distribute across both members: ${members_seen}" >&2
    exit 1
fi

curl --fail --silent --show-error \
    --header 'X-Request-ID: balancer.valid-1' \
    --header 'X-Forwarded-For: 203.0.113.9' \
    --output "${balancer_body}" \
    "${balancer_url}/application?balancer-secret=do-not-log"
"${python}" -c \
    'import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["request_id"] == "balancer.valid-1"
assert payload["xff"] != "203.0.113.9"' \
    "${balancer_body}"

# With one member stopped, every request must still succeed by failing over to
# the surviving member.
#
# Round robin decides which request lands on the stopped member, and the member
# is withdrawn from rotation once it reaches `max_fails`, so no individual
# request is guaranteed to be the one that retries. The contract is therefore
# stated as: no client-visible failure, every response from the surviving
# member, and at least one recorded retry.
"${runtime}" stop --time 10 "${pool_b}" >/dev/null
for attempt in 1 2 3; do
    failover_body=$(curl --fail --silent --show-error \
        --header "X-Request-ID: balancer.failover-${attempt}" \
        "${balancer_url}/application")
    "${python}" -c \
        'import json, sys
payload = json.loads(sys.argv[1])
assert payload["member"] == "pool-member-a", payload' \
        "${failover_body}"
done

balancer_logs=$("${runtime}" logs "${balancer}" 2>&1)
if grep -Fq '/healthz' <<< "${balancer_logs}"; then
    echo "The load-balancer health endpoint unexpectedly wrote an access event" >&2
    exit 1
fi
validate_event "${balancer}" \
    --profile load-balancer \
    --uri /application \
    --request-id balancer.valid-1 \
    --status 200 \
    --upstream-attempts 1 \
    --forbidden balancer-secret \
    --forbidden do-not-log

# Each failover request must be a well-formed event under the profile
# contract, whether or not it was the one that retried. Waiting for all three
# here also guarantees they are present before retries are counted below.
for attempt in 1 2 3; do
    validate_event "${balancer}" \
        --profile load-balancer \
        --uri /application \
        --request-id "balancer.failover-${attempt}" \
        --status 200 >"${null_device}"
done

# At least one failover request must record two upstream attempts. That is
# what distinguishes a real retry from a request that happened to be routed to
# the surviving member, and it proves the dead member was actually tried.
balancer_logs=$("${runtime}" logs "${balancer}" 2>&1)
failover_retries=0
for attempt in 1 2 3; do
    if printf '%s\n' "${balancer_logs}" | "${python}" \
        "${script_dir}/validate_profile_logs.py" \
        --profile load-balancer \
        --uri /application \
        --request-id "balancer.failover-${attempt}" \
        --status 200 \
        --upstream-attempts 2 >"${null_device}" 2>&1; then
        failover_retries=$((failover_retries + 1))
    fi
done
if test "${failover_retries}" -lt 1; then
    printf '%s\n' "${balancer_logs}" >&2
    echo "No failover request recorded a retry to the surviving member" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# WebSocket proxying
#
# The fixture reports what the proxy forwarded rather than implementing the
# WebSocket protocol. That covers the part this profile owns: deriving the
# connection disposition, forwarding the upgrade token, and leaving the plain
# HTTP location unaffected. Frame exchange over an established session is not
# qualified here.
# ---------------------------------------------------------------------------

"${runtime}" network create "${ws_network}" >/dev/null

run_restricted "${ws_backend}" 10007 \
    --network "${ws_network}" \
    --network-alias backend \
    --volume "${script_dir}/fixtures/profile-ws/nginx.conf:/etc/nginx/nginx.conf:ro"
"${runtime}" exec "${ws_backend}" nginx -t -q -c /etc/nginx/nginx.conf
assert_process_security "${ws_backend}"

run_restricted "${ws_proxy}" 10008 \
    --network "${ws_network}" \
    --publish 127.0.0.1::8080 \
    --volume "${examples_dir}/websocket/nginx.conf:/etc/nginx/nginx.conf:ro"
ws_binding=$("${runtime}" port "${ws_proxy}" 8080/tcp)
ws_port=${ws_binding##*:}
ws_url="http://127.0.0.1:${ws_port}"
wait_for_http "${ws_url}/healthz" "${ws_proxy}"
assert_process_security "${ws_proxy}"
"${runtime}" exec "${ws_proxy}" nginx -t -q -c /etc/nginx/nginx.conf

# A request without the upgrade token must reach the application with the
# derived `Connection: close`, never a client-chosen disposition. The client
# deliberately offers a conflicting `Connection` header to prove it is not
# copied through.
curl --fail --silent --show-error \
    --header 'X-Request-ID: websocket.plain-1' \
    --header 'Connection: keep-alive' \
    --output "${ws_body}" \
    "${ws_url}/ws"
"${python}" -c \
    'import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["upgrade"] == "", payload
assert payload["connection"] == "close", payload
assert payload["request_id"] == "websocket.plain-1", payload' \
    "${ws_body}"

# With the upgrade token the application must see the handshake, which it
# answers with 101. Receiving 101 rather than the fixture JSON is what proves
# the Upgrade header survived the proxy.
#
# The proxy tunnels after 101 and neither side sends anything further, so the
# client bounds its own wait. curl reports the status it already received.
upgrade_status=$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    --max-time 5 \
    --header 'X-Request-ID: websocket.upgrade-1' \
    --header 'Connection: Upgrade' \
    --header 'Upgrade: websocket' \
    --header 'Sec-WebSocket-Version: 13' \
    --header 'Sec-WebSocket-Key: ZGF0b3BzaXMtdGVzdC1rZXk=' \
    "${ws_url}/ws" || true)
test "${upgrade_status}" = 101

# The plain HTTP location must keep ordinary proxy behaviour.
curl --fail --silent --show-error \
    --header 'X-Request-ID: websocket.http-1' \
    --output "${ws_body}" \
    "${ws_url}/application"
"${python}" -c \
    'import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["request_id"] == "websocket.http-1", payload' \
    "${ws_body}"

ws_logs=$("${runtime}" logs "${ws_proxy}" 2>&1)
if grep -Fq '/healthz' <<< "${ws_logs}"; then
    echo "The websocket health endpoint unexpectedly wrote an access event" >&2
    exit 1
fi
validate_event "${ws_proxy}" \
    --profile websocket \
    --uri /ws \
    --request-id websocket.plain-1 \
    --status 200 \
    --connection-upgrade close
validate_event "${ws_proxy}" \
    --profile websocket \
    --uri /ws \
    --request-id websocket.upgrade-1 \
    --status 101 \
    --connection-upgrade upgrade

# ---------------------------------------------------------------------------
# Request-rate and connection limiting
# ---------------------------------------------------------------------------

printf 'limited-profile-ok\n' > "${limited_root}/index.html"
# The payload has to exceed `limit_rate_after` so the profile's own bandwidth
# limit paces it. A response that fits in the socket buffer is handed to the
# kernel immediately and the connection is never actually held, so no
# concurrency can build up no matter how slowly the client reads.
head -c 4194304 /dev/zero | tr '\0' 'x' > "${limited_root}/payload.bin"
# mktemp -d creates the directory 0700, which the container identity cannot
# traverse, so the served tree needs an explicit mode rather than the default.
chmod 0755 "${limited_root}"
chmod 0644 "${limited_root}"/*

run_restricted "${limited}" 10009 \
    --publish 127.0.0.1::8080 \
    --volume "${examples_dir}/rate-limited/nginx.conf:/etc/nginx/nginx.conf:ro" \
    --volume "${limited_root}:/srv/www:ro"
limited_binding=$("${runtime}" port "${limited}" 8080/tcp)
limited_port=${limited_binding##*:}
limited_url="http://127.0.0.1:${limited_port}"
wait_for_http "${limited_url}/healthz" "${limited}"
assert_process_security "${limited}"
"${runtime}" exec "${limited}" nginx -t -q -c /etc/nginx/nginx.conf

# A single request well inside the budget must pass both limits.
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    --header 'X-Request-ID: limits.pass-1' \
    "${limited_url}/index.html")" = 200
validate_event "${limited}" \
    --profile rate-limited \
    --uri /index.html \
    --request-id limits.pass-1 \
    --status 200 \
    --require-field limit_req_result=PASSED \
    --require-field limit_conn_result=PASSED

# Concurrency is a separate budget, and it is measured before the rate budget
# is spent. `limit_req` runs first, so once the rate limit is rejecting, the
# connection limit is never evaluated and records NOT_EVALUATED.
#
# The requests arrive together: the rate burst admits 20 of them, and the
# connection limit then rejects everything past its own maximum. Several
# events therefore share this correlation ID with different outcomes, and the
# assertion requires that at least one of them was rejected by the connection
# limit specifically.
conn_urls=()
for _ in $(seq 1 24); do
    conn_urls+=("${limited_url}/payload.bin")
done
conn_codes=$(curl --silent --output "${null_device}" \
    --write-out '%{http_code}\n' \
    --parallel --parallel-immediate --parallel-max 24 \
    --limit-rate 4k --max-time 20 \
    --header 'X-Request-ID: limits.conn-1' \
    "${conn_urls[@]}" || true)
if test "$(grep -c '^429$' <<< "${conn_codes}")" -lt 1; then
    printf '%s\n' "${conn_codes}" >&2
    echo "The connection limit did not reject any concurrent request" >&2
    exit 1
fi
validate_event "${limited}" \
    --profile rate-limited \
    --uri /payload.bin \
    --request-id limits.conn-1 \
    --status 429 \
    --allow-repeated \
    --require-field limit_conn_result=REJECTED

# Exhaust the request-rate budget. One curl invocation reuses the connection,
# so the requests arrive far faster than the configured rate; the burst is
# large enough that a slow runner still exceeds it.
burst_urls=()
for _ in $(seq 1 200); do
    burst_urls+=("${limited_url}/index.html")
done
burst_codes=$(curl --silent --output "${null_device}" \
    --write-out '%{http_code}\n' \
    --header 'X-Request-ID: limits.burst-1' \
    "${burst_urls[@]}")
test "$(grep -c '^200$' <<< "${burst_codes}")" -ge 1
if test "$(grep -c '^429$' <<< "${burst_codes}")" -lt 1; then
    echo "The request-rate limit did not reject any request in the burst" >&2
    exit 1
fi

# The health endpoint stays outside the limit, so it must still answer while
# the client's request budget is exhausted.
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    "${limited_url}/healthz")" = 200

# The burst shares one correlation ID on purpose: a rejected request must be
# recorded as rejected rather than silently dropped.
validate_event "${limited}" \
    --profile rate-limited \
    --uri /index.html \
    --request-id limits.burst-1 \
    --status 429 \
    --allow-repeated \
    --require-field limit_req_result=REJECTED

limited_logs=$("${runtime}" logs "${limited}" 2>&1)
if grep -Fq '/healthz' <<< "${limited_logs}"; then
    echo "The rate-limited health endpoint unexpectedly wrote an access event" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Extended health and readiness endpoints
# ---------------------------------------------------------------------------

"${runtime}" network create "${health_network}" >/dev/null

run_restricted "${health_backend}" 10010 \
    --network "${health_network}" \
    --network-alias backend \
    --volume "${script_dir}/fixtures/profile-backend/nginx.conf:/etc/nginx/nginx.conf:ro"
"${runtime}" exec "${health_backend}" nginx -t -q -c /etc/nginx/nginx.conf
assert_process_security "${health_backend}"

run_restricted "${health_proxy}" 10011 \
    --network "${health_network}" \
    --publish 127.0.0.1::8080 \
    --publish 127.0.0.1::8081 \
    --volume "${examples_dir}/health/nginx.conf:/etc/nginx/nginx.conf:ro"
health_binding=$("${runtime}" port "${health_proxy}" 8080/tcp)
health_port=${health_binding##*:}
health_url="http://127.0.0.1:${health_port}"
status_binding=$("${runtime}" port "${health_proxy}" 8081/tcp)
status_port=${status_binding##*:}
wait_for_http "${health_url}/healthz" "${health_proxy}"
assert_process_security "${health_proxy}"
"${runtime}" exec "${health_proxy}" nginx -t -q -c /etc/nginx/nginx.conf

# With the upstream reachable, the instance is ready.
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    --header 'X-Request-ID: health.ready-1' \
    "${health_url}/readyz")" = 200

# The operator status surface serves nobody by default. Publishing the port is
# not enough to read it, which is the property that keeps an accidentally
# exposed port from becoming an information source.
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    "http://127.0.0.1:${status_port}/status")" = 403
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    "http://127.0.0.1:${status_port}/")" = 404

"${runtime}" stop --time 10 "${health_backend}" >/dev/null

# Liveness must not depend on the upstream. If this returned non-200 with the
# backend down, an orchestrator would restart healthy proxies during a
# dependency outage and remove the capacity needed to recover.
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    "${health_url}/healthz")" = 200

# Readiness must depend on it, so the instance leaves rotation instead.
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    --header 'X-Request-ID: health.unready-1' \
    "${health_url}/readyz")" = 503

validate_event "${health_proxy}" \
    --profile health \
    --uri /readyz \
    --request-id health.unready-1 \
    --status 503

health_logs=$("${runtime}" logs "${health_proxy}" 2>&1)
# A succeeding probe is not an event. Liveness is never logged, and readiness
# is logged only when it fails, so probe traffic cannot bury real requests.
#
# These match structured fields rather than bare substrings. A failed readiness
# probe names the upstream it tried, `http://.../healthz`, in the error stream,
# so a substring search for the liveness path reports an access event that was
# never written.
if grep -Fq '"request_id":"health.ready-1"' <<< "${health_logs}"; then
    echo "A successful readiness probe unexpectedly wrote an access event" >&2
    exit 1
fi
if grep -Fq '"uri":"/healthz"' <<< "${health_logs}"; then
    echo "The liveness endpoint unexpectedly wrote an access event" >&2
    exit 1
fi

"${runtime}" stop --time 10 "${static}" "${proxy}" "${balancer}" "${ws_proxy}" \
    "${limited}" "${health_proxy}" >/dev/null
test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${static}")" = 0
test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${proxy}")" = 0
test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${balancer}")" = 0
test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${ws_proxy}")" = 0
test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${limited}")" = 0
test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${health_proxy}")" = 0

echo "Static, reverse-proxy, load-balancer, websocket, rate-limited, and health profile qualification passed for ${image}"
