# Qualified HTTP and TLS configuration profiles

The repository provides minimal static-serving and HTTP reverse-proxy
configurations under `examples/profiles`. Static serving, HTTP reverse proxy,
TLS termination, mutual TLS, and verified HTTPS upstream profiles are exercised
on native AMD64 and ARM64 runners with rootless Podman and then with Docker
compatibility execution. They remain **preview/unqualified** until an immutable
image release and its platform evidence explicitly name them as supported.

## Common contract

Both profiles:

- listen on unprivileged port `8080` and expose a fixed, unlogged `/healthz`;
- run under the image default identity or an arbitrary non-root UID in group
  `0` with all capabilities dropped and `no-new-privileges` enabled;
- use only `/tmp` for PID and temporary state, allowing a read-only root;
- set `server_tokens off`, a `1m` request-body limit, bounded request and
  keepalive timeouts, and `X-Content-Type-Options: nosniff`;
- accept `X-Request-ID` only when it contains 1--64 ASCII letters, digits,
  periods, underscores, or hyphens and starts with a letter or digit;
- generate an NGINX request ID when the inbound value fails validation; and
- emit one JSON access event per application request to stdout while sending
  operational messages at `notice` or higher to stderr.

A connection that never produces a request has no method: a rejected TLS
handshake, a malformed request line, or a client that disconnects before its
request is read. Those are not application requests, so the profiles suppress
their access events rather than emit a structured record whose method, URI, and
protocol are empty. They remain visible in the error stream, which is where a
failed handshake belongs. Deployments that need connection-level accounting
should collect the error stream or the platform's network telemetry rather than
relax this rule, because an access schema that admits empty required fields
cannot be validated.

The access event records `$uri`, never `$request`, `$request_uri`, `$args`,
headers, or bodies. Query strings, credentials, cookies, referrers, user-agent
values, and client-provided forwarding chains are therefore absent. JSON
escaping is enabled for every string field. Runtime or platform logging owns
collection, access control, capacity, rotation, retention, and disposal.

## Static content

[`examples/profiles/static/nginx.conf`](../examples/profiles/static/nginx.conf)
serves a read-only tree mounted at `/srv/www`. It permits `GET` and implicitly
`HEAD`, rejects other methods, disables directory indexes, denies dot-prefixed
path components, and returns `404` for absent content.

Its access-event schema is:

| Field | JSON type | Meaning |
| --- | --- | --- |
| `timestamp` | string | ISO 8601 event time. |
| `request_id` | string | Validated inbound or generated correlation ID. |
| `method` | string | Request method. |
| `uri` | string | Normalized path without query arguments. |
| `protocol` | string | Client HTTP protocol. |
| `status` | integer | Final client-facing response status. |
| `body_bytes_sent` | integer | Response-body bytes sent. |
| `request_time` | number | Total request duration in seconds. |

## HTTP reverse proxy

[`examples/profiles/reverse-proxy/nginx.conf`](../examples/profiles/reverse-proxy/nginx.conf)
proxies to `backend:8080`. Copy the example and replace that endpoint with the
deployment's approved service name. NGINX must be able to resolve it when the
configuration loads.

The profile deliberately overwrites `X-Forwarded-For` with the direct peer
address rather than extending a client-supplied chain. It also sets
`X-Forwarded-Proto`, forwards the validated or generated request ID, uses
HTTP/1.1 upstream keepalive, bounds connect/send/read timeouts, and disables
automatic retry. A failed or timed-out connection therefore produces a
client-facing `502` or `504` without silently attempting another backend.
HTTPS upstreams are outside this profile; use the forthcoming verified-
upstream TLS profile instead of merely changing the scheme.

In addition to the static fields, access events contain string-valued
`upstream_addr`, `upstream_status`, `upstream_connect_time`,
`upstream_header_time`, and `upstream_response_time`. NGINX can use `-` when an
upstream phase has no measurement. Treat backend addresses as operationally
sensitive when choosing log-reader access.

## TLS termination

[`examples/profiles/tls-termination/nginx.conf`](../examples/profiles/tls-termination/nginx.conf)
serves the static profile over port `8443`. Mount the ordered server certificate
chain as `/etc/nginx/tls/server.crt` and its matching private key as
`/etc/nginx/tls/server.key`. The profile permits TLS 1.2 and 1.3, restricts TLS
1.2 to ECDHE-RSA AEAD suites, disables session tickets, and adds HSTS without
claiming control over subdomains. TLS 1.3 cipher selection belongs to the
linked OpenSSL implementation and exact platform cryptographic policy.

TLS access events add `tls_protocol`, `tls_cipher`, `tls_server_name`,
`tls_session_reused`, and `tls_client_verify`. They deliberately exclude
certificate subjects, issuers, serials, fingerprints, and certificate content.

## Mutual TLS

[`examples/profiles/mutual-tls/nginx.conf`](../examples/profiles/mutual-tls/nginx.conf)
adds mandatory client-certificate authentication. Mount the issuing trust
bundle as `/etc/nginx/tls/client-ca.crt` and its current CRLs as
`/etc/nginx/tls/client.crl`. The profile verifies the chain and revocation state
to a maximum depth of two and records only `NONE`, `SUCCESS`, or NGINX's escaped
`FAILED:` result. It does not authorize a client identity: mapping a validated
certificate to application permissions remains a deployment-specific control.

## Verified HTTPS upstream

[`examples/profiles/tls-upstream/nginx.conf`](../examples/profiles/tls-upstream/nginx.conf)
extends the reverse proxy with TLS 1.2/1.3, chain verification, hostname
verification, SNI, and a bounded verification depth. Its example identity is
`backend.test`; copy the file and change `server`, `proxy_set_header Host`, and
`proxy_ssl_name` together to the reviewed service identity. Mount only the
narrow upstream trust bundle at `/etc/nginx/tls/upstream-ca.crt`. Do not reuse a
host-wide trust store merely to make validation succeed.

Mount current issuer CRLs at `/etc/nginx/tls/upstream.crl`; revoked backend
certificates fail closed as gateway errors.

The automated rehearsal generates short-lived private CAs, server and client
certificates outside the repository. It proves both TLS protocol versions,
trusted ingress, rejection of legacy TLS and untrusted chains, required and
untrusted client-certificate behavior, certificate/key readability by an
arbitrary UID, leaf-certificate renewal through validated reload, upstream
chain and hostname verification, absence of private material and client names
from logs, and useful missing-key diagnostics. The generated authorities are
test fixtures, never production trust anchors.

The extended lifecycle rehearsal also rejects revoked client and backend
certificates and proves old-only, old-plus-new overlap, and new-only upstream
trust states. See [TLS lifecycle](TLS-LIFECYCLE.md) for monitoring, renewal,
rotation, rollback, and the residual cryptographic-policy boundary.

## Mount, validate, and operate

Pin an immutable image digest in real deployments. This example shows the
static profile; also mount the content with an SELinux relabel option required
by the exact host policy when applicable:

```console
podman run --rm \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
  --cap-drop ALL --security-opt no-new-privileges \
  --volume ./examples/profiles/static/nginx.conf:/etc/nginx/nginx.conf:ro \
  --volume ./site:/srv/www:ro \
  ghcr.io/datopsis/nginx-ubi@sha256:<digest> -t -q
```

After validation, remove `--rm`, publish `8080`, and replace `-t -q` with
`-g 'daemon off;'`. Apply ingress, egress, DNS, CPU, memory, process, and
connection limits outside the container. The reverse-proxy profile needs an
explicit network path only to approved DNS and backend destinations.

Prefer replacing the container with a validated configuration digest. If an
in-place reload is required, run `nginx -t -q` inside the container before
sending `HUP`, then verify worker replacement, health, error logs, and sample
traffic. Roll back by restoring the last reviewed configuration and replacing
the container; do not edit the mounted configuration inside a running
container.

Use `bash tests/profiles.sh` and `bash tests/tls.sh` against the development
image to reproduce the
positive, negative, forwarding-header, correlation-ID, query-exclusion,
upstream-failure, certificate, structured-log, and restricted-runtime checks.
These harnesses do not qualify a deployment's CA operations, DNS, network
policy, collector, retention, capacity, or host security controls.
