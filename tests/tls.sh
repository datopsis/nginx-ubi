#!/usr/bin/env bash
set -Eeuo pipefail

runtime="${CONTAINER_RUNTIME:-podman}"
image="${IMAGE:-localhost/nginx-ubi9:development}"
python="${PYTHON:-python3}"
openssl="${OPENSSL:-openssl}"
openssl_for_python="${OPENSSL_FOR_PYTHON:-${openssl}}"
script_dir="${SCRIPT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}"
repository="${REPOSITORY:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
examples_dir="${EXAMPLES_DIR:-${repository}/examples/profiles}"
null_device="${NULL_DEVICE:-/dev/null}"
tmp_root="${TLS_TMPDIR:-/tmp}"
evidence=$(mktemp -d "${tmp_root}/nginx-ubi-tls.XXXXXX")
prefix="nginx-ubi9-tls-${RANDOM}-$$"
network="${prefix}-network"
termination="${prefix}-termination"
mtls="${prefix}-mtls"
missing_key="${prefix}-missing-key"
backend="${prefix}-backend"
proxy="${prefix}-proxy"
wrong_trust="${prefix}-wrong-trust"
wrong_host="${prefix}-wrong-host"
revoked_upstream="${prefix}-revoked-upstream"
rotation_overlap="${prefix}-rotation-overlap"
rotation_old_trust="${prefix}-rotation-old-trust"
rotation_new_only="${prefix}-rotation-new-only"
no_new_privileges="no-new-privileges:true"

if grep -qi podman <<< "$("${runtime}" --version 2>&1)"; then
    no_new_privileges="no-new-privileges"
fi
if command -v cygpath >/dev/null 2>&1 && [[ "${openssl_for_python}" = /* ]]; then
    openssl_for_python=$(cygpath -w "${openssl_for_python}")
fi

cleanup() {
    "${runtime}" rm --force \
        "${termination}" "${mtls}" "${missing_key}" "${proxy}" \
        "${wrong_trust}" "${wrong_host}" "${revoked_upstream}" \
        "${rotation_overlap}" "${rotation_old_trust}" \
        "${rotation_new_only}" "${backend}" >/dev/null 2>&1 || true
    "${runtime}" network rm "${network}" >/dev/null 2>&1 || true
    rm -rf -- "${evidence}"
}
trap cleanup EXIT

make_ca() {
    local name="$1"
    local directory="${evidence}/${name}"
    mkdir -p "${directory}"
    "${openssl}" req -x509 -newkey rsa:2048 -nodes -sha256 -days 2 \
        -subj "/CN=${name}" \
        -keyout "${directory}/ca.key" \
        -out "${directory}/ca.crt" >/dev/null 2>&1
    mkdir -p "${directory}/newcerts"
    : > "${directory}/index.txt"
    printf '1000\n' > "${directory}/serial"
    printf '1000\n' > "${directory}/crlnumber"
    # OpenSSL expands the literal $dir references in its configuration.
    # shellcheck disable=SC2016
    printf '%s\n' \
        '[ca]' \
        'default_ca = CA_default' \
        '[CA_default]' \
        "dir = ${directory}" \
        'database = $dir/index.txt' \
        'new_certs_dir = $dir/newcerts' \
        'certificate = $dir/ca.crt' \
        'private_key = $dir/ca.key' \
        'serial = $dir/serial' \
        'crlnumber = $dir/crlnumber' \
        'default_md = sha256' \
        'default_days = 2' \
        'default_crl_days = 1' \
        'unique_subject = no' \
        'policy = policy_any' \
        '[policy_any]' \
        'commonName = supplied' > "${directory}/ca.conf"
}

make_cert() {
    local name="$1"
    local common_name="$2"
    local san="$3"
    local eku="$4"
    local ca_name="$5"
    local directory="${evidence}/${name}"
    local ca_directory="${evidence}/${ca_name}"
    mkdir -p "${directory}"
    printf '[leaf]\nsubjectAltName=%s\nextendedKeyUsage=%s\nkeyUsage=digitalSignature,keyEncipherment\nbasicConstraints=critical,CA:false\n' \
        "${san}" "${eku}" > "${directory}/extensions.conf"
    "${openssl}" req -new -newkey rsa:2048 -nodes -sha256 \
        -subj "/CN=${common_name}" \
        -keyout "${directory}/server.key" \
        -out "${directory}/server.csr" >/dev/null 2>&1
    "${openssl}" ca -batch -notext \
        -config "${ca_directory}/ca.conf" \
        -in "${directory}/server.csr" \
        -extfile "${directory}/extensions.conf" \
        -extensions leaf \
        -out "${directory}/server.crt" >/dev/null 2>&1
}

make_crl() {
    local ca_name="$1"
    local ca_directory="${evidence}/${ca_name}"
    "${openssl}" ca -gencrl -config "${ca_directory}/ca.conf" \
        -out "${ca_directory}/ca.crl" >/dev/null 2>&1
}

revoke_cert() {
    local ca_name="$1"
    local cert_name="$2"
    local ca_directory="${evidence}/${ca_name}"
    "${openssl}" ca -batch -config "${ca_directory}/ca.conf" \
        -revoke "${evidence}/${cert_name}/server.crt" >/dev/null 2>&1
    make_crl "${ca_name}"
}

run_restricted() {
    local name="$1"
    local uid="$2"
    local config="$3"
    local tls_directory="$4"
    shift 4
    "${runtime}" run --detach --name "${name}" \
        --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
        --cap-drop ALL \
        --security-opt "${no_new_privileges}" \
        --user "${uid}:0" \
        --volume "${config}:/etc/nginx/nginx.conf:ro" \
        --volume "${tls_directory}:/etc/nginx/tls:ro" \
        "$@" \
        "${image}" -c /etc/nginx/nginx.conf -g 'daemon off;' \
        >/dev/null
}

wait_for_tls() {
    local url="$1"
    local ca="$2"
    local name="$3"
    shift 3
    local _
    for _ in {1..30}; do
        if curl --fail --silent --output "${null_device}" \
            --cacert "${ca}" "$@" "${url}"; then
            return
        fi
        sleep 1
    done
    "${runtime}" logs "${name}" >&2
    echo "Timed out waiting for TLS endpoint ${name}" >&2
    return 1
}

wait_for_exit() {
    local name="$1"
    local _
    for _ in {1..15}; do
        if test "$("${runtime}" inspect --format '{{.State.Status}}' "${name}")" \
            != running; then
            test "$("${runtime}" inspect --format '{{.State.ExitCode}}' "${name}")" \
                != 0
            return
        fi
        sleep 1
    done
    "${runtime}" logs "${name}" >&2
    return 1
}

# Requirements: L2-TLS-001
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
        test ! -w /etc/nginx/tls/server.key
    '
}

make_ca ingress-ca
make_ca client-ca
make_ca untrusted-ca
make_ca upstream-ca
make_ca upstream-next-ca
make_cert ingress localhost DNS:localhost serverAuth ingress-ca
make_cert ingress-renewed localhost DNS:localhost serverAuth ingress-ca
make_cert client client.test DNS:client.test clientAuth client-ca
make_cert revoked-client revoked.test DNS:revoked.test clientAuth client-ca
make_cert untrusted-client intruder.test DNS:intruder.test clientAuth untrusted-ca
make_cert backend backend.test DNS:backend.test serverAuth upstream-ca
make_cert wrong-host wrong.test DNS:wrong.test serverAuth upstream-ca
make_cert revoked-backend backend.test DNS:backend.test serverAuth upstream-ca
make_cert backend-next backend.test DNS:backend.test serverAuth upstream-next-ca
revoke_cert client-ca revoked-client
revoke_cert upstream-ca revoked-backend
make_crl ingress-ca
make_crl untrusted-ca
make_crl upstream-next-ca

cp "${evidence}/ingress-ca/ca.crt" "${evidence}/ingress/ca.crt"
cp "${evidence}/client-ca/ca.crt" "${evidence}/ingress/client-ca.crt"
cp "${evidence}/client-ca/ca.crl" "${evidence}/ingress/client.crl"
cp "${evidence}/upstream-ca/ca.crt" "${evidence}/backend/upstream-ca.crt"
cp "${evidence}/upstream-ca/ca.crl" "${evidence}/backend/upstream.crl"
cp "${evidence}/upstream-ca/ca.crt" "${evidence}/wrong-host/upstream-ca.crt"
cp "${evidence}/upstream-ca/ca.crl" "${evidence}/wrong-host/upstream.crl"
cp "${evidence}/upstream-ca/ca.crt" \
    "${evidence}/revoked-backend/upstream-ca.crt"
cp "${evidence}/upstream-ca/ca.crl" \
    "${evidence}/revoked-backend/upstream.crl"
cp "${evidence}/upstream-next-ca/ca.crt" \
    "${evidence}/backend-next/upstream-ca.crt"
cp "${evidence}/upstream-next-ca/ca.crl" \
    "${evidence}/backend-next/upstream.crl"
mkdir -p "${evidence}/proxy-trust" "${evidence}/wrong-trust" \
    "${evidence}/overlap-trust" "${evidence}/next-trust" \
    "${evidence}/missing-key"
cp "${evidence}/upstream-ca/ca.crt" "${evidence}/proxy-trust/upstream-ca.crt"
cp "${evidence}/upstream-ca/ca.crl" "${evidence}/proxy-trust/upstream.crl"
cp "${evidence}/untrusted-ca/ca.crt" \
    "${evidence}/wrong-trust/upstream-ca.crt"
cp "${evidence}/untrusted-ca/ca.crl" \
    "${evidence}/wrong-trust/upstream.crl"
cp "${evidence}/upstream-ca/ca.crt" \
    "${evidence}/overlap-trust/upstream-ca.crt"
cp "${evidence}/upstream-next-ca/ca.crt" \
    "${evidence}/overlap-trust/upstream-next-ca.crt"
cat "${evidence}/overlap-trust/upstream-next-ca.crt" >> \
    "${evidence}/overlap-trust/upstream-ca.crt"
cp "${evidence}/upstream-ca/ca.crl" \
    "${evidence}/overlap-trust/upstream.crl"
cat "${evidence}/upstream-next-ca/ca.crl" >> \
    "${evidence}/overlap-trust/upstream.crl"
cp "${evidence}/upstream-next-ca/ca.crt" \
    "${evidence}/next-trust/upstream-ca.crt"
cp "${evidence}/upstream-next-ca/ca.crl" \
    "${evidence}/next-trust/upstream.crl"
cp "${evidence}/ingress/server.crt" "${evidence}/missing-key/server.crt"
chmod 0644 "${evidence}"/*/*.crt
chmod 0644 "${evidence}"/*/*.crl
chmod 0640 "${evidence}"/*/*.key

# Rootless Podman maps the invoking user onto container GID 0, so the runtime
# identity reads these keys through the group bit while they stay unreadable to
# other host users. Rootful Docker preserves host ownership instead, and its
# container GID 0 is host root, so the identical file is unreadable there.
# Setting group 0 on the host would fix Docker and break rootless Podman, so
# the compatibility leg widens the mode on this throwaway rehearsal material
# rather than weakening the primary runtime. These keys are generated per run
# outside the repository and destroyed with the evidence directory.
#
# This is a harness accommodation, not deployment guidance. A deployment makes
# keys readable by the runtime identity through ownership, as described in
# docs/TLS-LIFECYCLE.md, and never by making them readable to every user.
if ! grep -qi podman <<< "$("${runtime}" --version 2>&1)"; then
    chmod 0644 "${evidence}"/*/*.key
fi

"${openssl}" verify -CAfile "${evidence}/ingress-ca/ca.crt" \
    -purpose sslserver -verify_hostname localhost \
    "${evidence}/ingress/server.crt" >/dev/null
"${openssl}" verify -CAfile "${evidence}/client-ca/ca.crt" \
    -purpose sslclient "${evidence}/client/server.crt" >/dev/null
"${openssl}" verify -CAfile "${evidence}/upstream-ca/ca.crt" \
    -purpose sslserver -verify_hostname backend.test \
    "${evidence}/backend/server.crt" >/dev/null
"${python}" "${repository}/scripts/tls_material.py" --warning-hours 1 \
    --openssl "${openssl_for_python}" \
    --certificate "${evidence}/ingress/server.crt" \
    --certificate "${evidence}/client/server.crt" \
    --certificate "${evidence}/backend/server.crt" \
    --crl "${evidence}/client-ca/ca.crl" \
    --crl "${evidence}/upstream-ca/ca.crl" >/dev/null

run_restricted "${termination}" 11001 \
    "${examples_dir}/tls-termination/nginx.conf" "${evidence}/ingress" \
    --publish 127.0.0.1::8443 \
    --volume "${script_dir}/fixtures/profile-site:/srv/www:ro"
termination_binding=$("${runtime}" port "${termination}" 8443/tcp)
termination_port=${termination_binding##*:}
termination_url="https://localhost:${termination_port}"
wait_for_tls "${termination_url}/healthz" "${evidence}/ingress-ca/ca.crt" \
    "${termination}" --resolve "localhost:${termination_port}:127.0.0.1"
assert_process_security "${termination}"

for tls_version in 1.2 1.3; do
    test "$(curl --fail --silent --show-error \
        --tlsv${tls_version} --tls-max "${tls_version}" \
        --cacert "${evidence}/ingress-ca/ca.crt" \
        --resolve "localhost:${termination_port}:127.0.0.1" \
        --header "X-Request-ID: tls.valid-${tls_version}" \
        "${termination_url}/")" = static-profile-ok
done
# Requirements: L3-TLS-001
if curl --silent --show-error --tls-max 1.1 \
    --cacert "${evidence}/ingress-ca/ca.crt" \
    --resolve "localhost:${termination_port}:127.0.0.1" \
    --output "${null_device}" "${termination_url}/" 2>/dev/null; then
    echo "TLS 1.1 unexpectedly succeeded" >&2
    exit 1
fi
# Requirements: L3-TLS-002
if curl --silent --show-error \
    --cacert "${evidence}/untrusted-ca/ca.crt" \
    --resolve "localhost:${termination_port}:127.0.0.1" \
    --output "${null_device}" "${termination_url}/" 2>/dev/null; then
    echo "An untrusted ingress certificate unexpectedly succeeded" >&2
    exit 1
fi
termination_logs=$("${runtime}" logs "${termination}" 2>&1)
printf '%s\n' "${termination_logs}" | "${python}" \
    "${script_dir}/validate_profile_logs.py" \
    --profile tls-termination --uri /index.html \
    --request-id tls.valid-1.3 --status 200
# Requirements: L3-TLS-004
if grep -Eq 'BEGIN .*PRIVATE KEY|client\.test' <<< "${termination_logs}"; then
    echo "TLS termination logs exposed private-key or client identity data" >&2
    exit 1
fi

# Requirements: L3-TLS-006
old_serial=$("${openssl}" x509 -in "${evidence}/ingress/server.crt" \
    -noout -serial)
new_serial=$("${openssl}" x509 -in "${evidence}/ingress-renewed/server.crt" \
    -noout -serial)
test "${old_serial}" != "${new_serial}"
cp "${evidence}/ingress-renewed/server.crt" "${evidence}/ingress/server.crt"
cp "${evidence}/ingress-renewed/server.key" "${evidence}/ingress/server.key"
"${runtime}" exec "${termination}" nginx -t -q -c /etc/nginx/nginx.conf
"${runtime}" kill --signal HUP "${termination}" >/dev/null
sleep 1
observed_serial=$(printf '' | "${openssl}" s_client \
    -connect "127.0.0.1:${termination_port}" -servername localhost \
    -CAfile "${evidence}/ingress-ca/ca.crt" 2>/dev/null \
    | "${openssl}" x509 -noout -serial)
test "${observed_serial}" = "${new_serial}"

run_restricted "${mtls}" 11002 \
    "${examples_dir}/mutual-tls/nginx.conf" "${evidence}/ingress" \
    --publish 127.0.0.1::8443 \
    --volume "${script_dir}/fixtures/profile-site:/srv/www:ro"
mtls_binding=$("${runtime}" port "${mtls}" 8443/tcp)
mtls_port=${mtls_binding##*:}
mtls_url="https://localhost:${mtls_port}"
wait_for_tls "${mtls_url}/healthz" "${evidence}/ingress-ca/ca.crt" "${mtls}" \
    --resolve "localhost:${mtls_port}:127.0.0.1" \
    --cert "${evidence}/client/server.crt" \
    --key "${evidence}/client/server.key"
assert_process_security "${mtls}"
for client_options in \
    "" \
    "--cert ${evidence}/untrusted-client/server.crt --key ${evidence}/untrusted-client/server.key" \
    "--cert ${evidence}/revoked-client/server.crt --key ${evidence}/revoked-client/server.key"; do
    # Requirements: L3-TLS-003
    # Word splitting is intentional for the two fixed curl option strings.
    # shellcheck disable=SC2086
    if curl --fail --silent --show-error \
        --cacert "${evidence}/ingress-ca/ca.crt" \
        --resolve "localhost:${mtls_port}:127.0.0.1" \
        ${client_options} --output "${null_device}" "${mtls_url}/" \
        2>/dev/null; then
        echo "mTLS accepted a missing or untrusted client certificate" >&2
        exit 1
    fi
done
test "$(curl --fail --silent --show-error \
    --cacert "${evidence}/ingress-ca/ca.crt" \
    --resolve "localhost:${mtls_port}:127.0.0.1" \
    --cert "${evidence}/client/server.crt" \
    --key "${evidence}/client/server.key" \
    --header 'X-Request-ID: mtls.valid-1' "${mtls_url}/")" = static-profile-ok
mtls_logs=$("${runtime}" logs "${mtls}" 2>&1)
printf '%s\n' "${mtls_logs}" | "${python}" \
    "${script_dir}/validate_profile_logs.py" \
    --profile mutual-tls --uri /index.html \
    --request-id mtls.valid-1 --status 200
if grep -Eq 'BEGIN .*PRIVATE KEY|client\.test' <<< "${mtls_logs}"; then
    echo "mTLS logs exposed private-key or client identity data" >&2
    exit 1
fi

"${runtime}" run --detach --name "${missing_key}" \
    --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
    --cap-drop ALL --security-opt "${no_new_privileges}" --user 11003:0 \
    --volume "${examples_dir}/tls-termination/nginx.conf:/etc/nginx/nginx.conf:ro" \
    --volume "${evidence}/missing-key:/etc/nginx/tls:ro" \
    "${image}" -c /etc/nginx/nginx.conf -g 'daemon off;' >/dev/null
wait_for_exit "${missing_key}"
grep -Fq '/etc/nginx/tls/server.key' <<< \
    "$("${runtime}" logs "${missing_key}" 2>&1)"

"${runtime}" network create "${network}" >/dev/null
run_restricted "${backend}" 11004 \
    "${script_dir}/fixtures/tls-backend/nginx.conf" "${evidence}/backend" \
    --network "${network}" --network-alias backend
"${runtime}" exec "${backend}" nginx -t -q -c /etc/nginx/nginx.conf
assert_process_security "${backend}"

run_restricted "${proxy}" 11005 \
    "${examples_dir}/tls-upstream/nginx.conf" "${evidence}/proxy-trust" \
    --network "${network}" --publish 127.0.0.1::8080
proxy_binding=$("${runtime}" port "${proxy}" 8080/tcp)
proxy_port=${proxy_binding##*:}
proxy_url="http://127.0.0.1:${proxy_port}"
for _ in {1..30}; do
    if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
        "${proxy_url}/healthz" || true)" = 200; then
        break
    fi
    sleep 1
done
assert_process_security "${proxy}"
proxy_response=$(curl --fail --silent --show-error \
    --header 'X-Request-ID: upstream-tls.valid-1' "${proxy_url}/application")
grep -Fq '"request_id":"upstream-tls.valid-1"' <<< "${proxy_response}"
proxy_logs=$("${runtime}" logs "${proxy}" 2>&1)
printf '%s\n' "${proxy_logs}" | "${python}" \
    "${script_dir}/validate_profile_logs.py" \
    --profile tls-upstream --uri /application \
    --request-id upstream-tls.valid-1 --status 200

run_restricted "${rotation_overlap}" 11011 \
    "${examples_dir}/tls-upstream/nginx.conf" "${evidence}/overlap-trust" \
    --network "${network}" --publish 127.0.0.1::8080
rotation_binding=$("${runtime}" port "${rotation_overlap}" 8080/tcp)
rotation_port=${rotation_binding##*:}
rotation_url="http://127.0.0.1:${rotation_port}"
for _ in {1..30}; do
    if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
        "${rotation_url}/healthz" || true)" = 200; then
        break
    fi
    sleep 1
done
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    "${rotation_url}/old-issuer")" = 200
"${runtime}" rm --force "${rotation_overlap}" >/dev/null

run_restricted "${wrong_trust}" 11006 \
    "${examples_dir}/tls-upstream/nginx.conf" "${evidence}/wrong-trust" \
    --network "${network}" --publish 127.0.0.1::8080
wrong_binding=$("${runtime}" port "${wrong_trust}" 8080/tcp)
wrong_port=${wrong_binding##*:}
wrong_url="http://127.0.0.1:${wrong_port}"
for _ in {1..30}; do
    if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
        "${wrong_url}/healthz" || true)" = 200; then
        break
    fi
    sleep 1
done
wrong_status=$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    --header 'X-Request-ID: upstream-tls.untrusted-1' "${wrong_url}/")
test "${wrong_status}" = 502
grep -Fq 'upstream SSL certificate verify error' <<< \
    "$("${runtime}" logs "${wrong_trust}" 2>&1)"

"${runtime}" rm --force "${backend}" >/dev/null
run_restricted "${backend}" 11007 \
    "${script_dir}/fixtures/tls-backend/nginx.conf" "${evidence}/wrong-host" \
    --network "${network}" --network-alias backend
run_restricted "${wrong_host}" 11008 \
    "${examples_dir}/tls-upstream/nginx.conf" "${evidence}/proxy-trust" \
    --network "${network}" --publish 127.0.0.1::8080
wrong_host_binding=$("${runtime}" port "${wrong_host}" 8080/tcp)
wrong_host_port=${wrong_host_binding##*:}
wrong_host_url="http://127.0.0.1:${wrong_host_port}"
for _ in {1..30}; do
    if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
        "${wrong_host_url}/healthz" || true)" = 200; then
        break
    fi
    sleep 1
done
wrong_host_status=$(curl --silent --output "${null_device}" \
    --write-out '%{http_code}' "${wrong_host_url}/")
test "${wrong_host_status}" = 502
grep -Fq 'upstream SSL certificate does not match "backend.test"' <<< \
    "$("${runtime}" logs "${wrong_host}" 2>&1)"

"${runtime}" rm --force "${backend}" >/dev/null
run_restricted "${backend}" 11009 \
    "${script_dir}/fixtures/tls-backend/nginx.conf" \
    "${evidence}/revoked-backend" \
    --network "${network}" --network-alias backend
run_restricted "${revoked_upstream}" 11010 \
    "${examples_dir}/tls-upstream/nginx.conf" "${evidence}/proxy-trust" \
    --network "${network}" --publish 127.0.0.1::8080
revoked_binding=$("${runtime}" port "${revoked_upstream}" 8080/tcp)
revoked_port=${revoked_binding##*:}
revoked_url="http://127.0.0.1:${revoked_port}"
for _ in {1..30}; do
    if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
        "${revoked_url}/healthz" || true)" = 200; then
        break
    fi
    sleep 1
done
revoked_status=$(curl --silent --output "${null_device}" \
    --write-out '%{http_code}' "${revoked_url}/")
test "${revoked_status}" = 502
grep -Fq 'certificate revoked' <<< \
    "$("${runtime}" logs "${revoked_upstream}" 2>&1)"

"${runtime}" rm --force "${backend}" >/dev/null
run_restricted "${backend}" 11012 \
    "${script_dir}/fixtures/tls-backend/nginx.conf" "${evidence}/backend-next" \
    --network "${network}" --network-alias backend
run_restricted "${rotation_overlap}" 11013 \
    "${examples_dir}/tls-upstream/nginx.conf" "${evidence}/overlap-trust" \
    --network "${network}" --publish 127.0.0.1::8080
rotation_binding=$("${runtime}" port "${rotation_overlap}" 8080/tcp)
rotation_port=${rotation_binding##*:}
rotation_url="http://127.0.0.1:${rotation_port}"
for _ in {1..30}; do
    if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
        "${rotation_url}/healthz" || true)" = 200; then
        break
    fi
    sleep 1
done
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    "${rotation_url}/new-issuer")" = 200

run_restricted "${rotation_old_trust}" 11014 \
    "${examples_dir}/tls-upstream/nginx.conf" "${evidence}/proxy-trust" \
    --network "${network}" --publish 127.0.0.1::8080
old_trust_binding=$("${runtime}" port "${rotation_old_trust}" 8080/tcp)
old_trust_port=${old_trust_binding##*:}
old_trust_url="http://127.0.0.1:${old_trust_port}"
for _ in {1..30}; do
    if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
        "${old_trust_url}/healthz" || true)" = 200; then
        break
    fi
    sleep 1
done
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    "${old_trust_url}/retired-issuer")" = 502

run_restricted "${rotation_new_only}" 11015 \
    "${examples_dir}/tls-upstream/nginx.conf" "${evidence}/next-trust" \
    --network "${network}" --publish 127.0.0.1::8080
new_only_binding=$("${runtime}" port "${rotation_new_only}" 8080/tcp)
new_only_port=${new_only_binding##*:}
new_only_url="http://127.0.0.1:${new_only_port}"
for _ in {1..30}; do
    if test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
        "${new_only_url}/healthz" || true)" = 200; then
        break
    fi
    sleep 1
done
test "$(curl --silent --output "${null_device}" --write-out '%{http_code}' \
    "${new_only_url}/new-only")" = 200

"${runtime}" stop --time 10 \
    "${termination}" "${mtls}" "${proxy}" "${wrong_trust}" \
    "${wrong_host}" "${revoked_upstream}" "${rotation_overlap}" \
    "${rotation_old_trust}" "${rotation_new_only}" "${backend}" >/dev/null

echo "Ingress TLS, mutual TLS, and verified-upstream TLS qualification passed for ${image}"
