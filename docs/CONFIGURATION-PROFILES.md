# Qualified HTTP and TLS configuration profiles

The repository provides minimal static-serving, HTTP reverse-proxy, HTTP
load-balancing, WebSocket-proxying, request-limiting, health-endpoint, and
ClickHouse-proxying configurations under `examples/profiles`. Static serving,
HTTP reverse proxy, HTTP load balancing, WebSocket proxying, request and
connection limiting, health and readiness endpoints, ClickHouse HTTP proxying,
TLS termination, mutual TLS, and verified HTTPS upstream profiles are exercised
on native AMD64 and ARM64 runners with rootless Podman and then with Docker
compatibility execution. They remain **preview/unqualified** until an immutable
image release and its platform evidence explicitly name them as supported.

[The profile map](architecture/README.md#configuration-profiles) shows how the
profiles relate and what each adds to this baseline, and
[the profile pages](architecture/profiles/README.md) give each one its own
request path and qualification boundary.

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

## ClickHouse HTTP proxying

[`examples/profiles/clickhouse/nginx.conf`](../examples/profiles/clickhouse/nginx.conf)
proxies the ClickHouse HTTP interface.

### This proxy is not an authorization boundary

NGINX parses HTTP, not SQL. It cannot make a session read-only, restrict which
statements run, bound how many rows a query returns, or tell a `SELECT` from a
`DROP`.

Anything that depends on the content of a query belongs to ClickHouse:
`readonly` user settings, quotas, row policies, and per-user grants. Treating
this file as the control that stops clients modifying data is a misreading of
what it does. The profile restricts methods and body size, which bounds the
shape of a request, not its meaning.

### Credentials and query text in the request target

This is the profile where the repository-wide logging rule earns its keep.

The ClickHouse HTTP interface accepts `?query=...`, and many deployments accept
`?user=...&password=...`. The request target therefore routinely carries both
credentials and customer data. Every profile here logs `$uri` and never
`$request`, `$request_uri`, or `$args`, so passwords and query text are
structurally absent from the access stream rather than filtered out of it.

The test asserts this directly: it issues a request carrying a password and a
column name as parameters, then requires that neither string appears anywhere
in the container's output.

An operator should confirm the same property for anything downstream. A log
collector, an error tracker, or a reverse proxy in front that records full
request lines reintroduces exactly what this profile removes.

### Failures are reported by code, not by statement

`X-ClickHouse-Exception-Code` is recorded as a structured field, which gives
the failure class without putting any part of the query into the log. A request
the proxy refuses never reaches the database, so its upstream fields record
`NONE`, keeping "the database rejected this" distinguishable from "the database
never saw it".

### Temporary storage

`proxy_max_temp_file_size 0` with buffering off is deliberate. A result set
larger than the proxy buffers would otherwise spill to `proxy_temp_path`, which
is on the container's `/tmp` tmpfs. One large result could consume the tmpfs
and take the container down, so the response is streamed instead.

### Timeouts and capacity

Analytical queries run far longer than web requests, so the read timeout is
large and scoped to the query location. Each waiting query holds a worker
connection, so size `worker_connections` for the expected concurrent query
count rather than for request rate. Retries are disabled: re-running a
statement is unsafe for anything that writes and wasteful for anything else.

### Qualified behaviour

The tests run against a stand-in for the ClickHouse HTTP interface built from
this image. It reports what the proxy forwarded and can answer with an
exception code; it executes nothing and implements no part of the ClickHouse
protocol.

They prove that a POST body reaches the upstream, that credentials and query
text in the request target never reach the log, that an exception code is
recorded, that methods outside the interface are refused, and that an oversized
body is refused before reaching the database.

They do **not** qualify interoperation with a real ClickHouse server, protocol
or version behaviour, query semantics, compression negotiation, or performance
against real result sets. A deployment must qualify those against its own
server.

## Extended health and readiness endpoints

[`examples/profiles/health/nginx.conf`](../examples/profiles/health/nginx.conf)
separates three surfaces that are often collapsed into one: liveness,
readiness, and an operator status endpoint.

### Liveness must not depend on an upstream

`/healthz` answers for this process alone and never consults the backend.

This is the most consequential decision in the profile. A liveness probe that
fails because a dependency is down makes the orchestrator kill and restart
healthy proxies, converting a backend outage into a restart storm that removes
the capacity needed to recover. The tests assert that `/healthz` still answers
`200` while the upstream is stopped.

### Readiness must depend on it

`/readyz` proxies to the upstream's own health endpoint and reports `503` when
that fails. A failing readiness probe removes the instance from rotation
without restarting it, which is the correct response to a dependency being
unavailable.

Its timeouts are deliberately shorter than a typical probe interval. A
readiness check that outlives its own probe period stacks concurrent probes
against an already struggling upstream.

Open source NGINX has no active upstream health checking, so readiness is
expressed as a real request to the upstream rather than as a background probe.
That is a deliberate consequence of the open source constraint described in
[the package-source decision](PACKAGE-SOURCE.md), not an oversight.

### Probe logging

Liveness is never logged. Readiness is logged only when it fails. Probes run
continuously, so a successful check is not an event worth recording, while a
failing one is exactly what an operator needs to see. This keeps probe traffic
from burying real requests in the access stream.

### The status surface serves nobody by default

`stub_status` is exposed on a second listener, port `8081`, and denies every
source out of the box. The counters are not secrets, but they describe load and
capacity, so a deployment that scrapes them must make a reviewed change naming
the collector's source range and must keep the port off any public ingress.

Binding it to a separate port rather than a path under the application server
is what allows network policy to separate the two. The tests assert that
publishing the port is not by itself enough to read it.

### Qualified behaviour

The tests prove that readiness succeeds while the upstream is reachable, that
liveness keeps answering when it is not, that readiness then reports `503` and
records a structured event, that a successful probe writes no event, and that
the status surface refuses an unlisted source.

They do **not** qualify probe interval and threshold tuning for any
orchestrator, startup-probe behaviour, or the status surface under an approved
allow-list.

## Request-rate and connection limiting

[`examples/profiles/rate-limited/nginx.conf`](../examples/profiles/rate-limited/nginx.conf)
applies three separate budgets to a served tree: request rate, concurrent
connections, and per-connection bandwidth. They are independent, and a
deployment that sets only one leaves the others unbounded.

### The limit key decides whether the limit exists

The key is `$binary_remote_addr`, the direct peer address.

Behind a load balancer or ingress controller that address is the *proxy*, so
every client shares one bucket and a per-client limit silently becomes a global
cap. A deployment in that position needs a key derived from a forwarded address
it actually trusts, through `realip` with a trusted-proxy list or an equivalent
reviewed mechanism.

Never key a limit on a header the client controls. A client that chooses its
own key gets a fresh bucket for every request, and the limit stops existing
while continuing to look configured.

The zones are shared across workers and are sized in advance. An exhausted zone
fails closed and rejects new clients, so size for the expected distinct-client
count rather than for steady-state traffic.

### Status code

Both limits answer `429`. The NGINX default is `503`, which is
indistinguishable from an outage and invites clients to retry harder against a
server that is already shedding load.

### Evaluation order matters when reading logs

`limit_req` is evaluated before `limit_conn`. Once the rate limit is rejecting,
the connection limit is never reached, and its field records `NOT_EVALUATED`
rather than `PASSED`. A reader who treats `NOT_EVALUATED` as "allowed" will
conclude the connection limit is inactive when it is simply downstream of a
limit that is already firing.

### The health endpoint is outside both limits

A limited health endpoint turns a traffic spike into a failed liveness probe
and a restart, which removes capacity exactly when it is needed.

### Access-event schema

The profile emits the common fields plus:

| Field | JSON type | Meaning |
| --- | --- | --- |
| `limit_req_result` | string | `PASSED`, `DELAYED`, `REJECTED`, a dry-run variant, or `NOT_EVALUATED`. |
| `limit_conn_result` | string | `PASSED`, `REJECTED`, a dry-run variant, or `NOT_EVALUATED`. |

The limit *key* is deliberately not logged. Recording the outcome supports
capacity and abuse analysis; recording the raw client identifier for every
request adds a personal identifier to an access stream that is otherwise free
of them.

### Qualified behaviour

The tests prove that a request inside both budgets passes, that exhausting the
request rate produces `429` recorded as `REJECTED`, that concurrent requests
beyond the connection maximum are rejected by the connection limit
specifically, and that the health endpoint keeps answering while the client's
request budget is exhausted.

They do **not** qualify tuning for any particular workload, zone sizing under
real client populations, behaviour once a zone is exhausted, or the interaction
between these limits and an upstream rate limiter.

## Upstream resolution: static by default, dynamic by choice

Every proxying profile in this repository resolves its upstream **once, when
the configuration loads**. That is the default, and it is the right default.

It is also a real constraint: if the endpoint behind the name is replaced on a
new address, those profiles keep sending traffic to the old one. Verified
against this image — after replacing a backend container with another on a
different address under the same name, requests fail until the proxy is
reloaded, and `SIGHUP` recovers them because a reload re-resolves.

For a deployment whose endpoint addresses are stable, or which can reload when
membership changes, that is the whole story and the static profiles are the
right choice.

### When a reload is not available

[`examples/profiles/dynamic-upstream/nginx.conf`](../examples/profiles/dynamic-upstream/nginx.conf)
re-resolves per request instead. Verified the same way: after the same
replacement, it recovers on its own, with no reload, bounded by the resolver
validity.

This is a **different file to mount**, not a setting to toggle. The two modes
need structurally different directives, so one configuration cannot offer both.

### What the dynamic profile gives up

Holding the endpoint in a variable is what makes NGINX resolve it per request.
It is also what removes the `upstream` block, and everything that lives in one:

| Capability | Static profiles | Dynamic profile |
| --- | --- | --- |
| Balancing method across peers | configurable | none |
| Passive failure tracking (`max_fails`, `fail_timeout`) | yes | none |
| Failover to another peer | `proxy_next_upstream` | nothing to fail over to |
| Connection reuse (`keepalive`) | yes | none; `keepalive` is an `upstream` directive |
| Picks up a replaced endpoint | on reload | on its own, within the resolver validity |

A dead endpoint keeps receiving requests until DNS stops returning it, because
nothing is tracking failures. The load-balancing profile is not a substitute
either: its members are resolved at load time like every other static profile.

### The resolver is supplied by the deployment

NGINX does not read `/etc/resolv.conf` for this, so there is no usable default
and a wrong value fails every request. The profile therefore includes a file
the deployment mounts:

```console
--volume /path/to/resolver.conf:/etc/nginx/resolver.conf:ro
```

containing one directive, for example:

```text
resolver 10.96.0.10 valid=30s ipv6=off;
```

`valid` bounds how long a resolved address is reused, and therefore how long
traffic can keep reaching a replaced endpoint. Setting it below the record's
own TTL does not make failover faster than the zone allows.

**DNS becomes part of the trust boundary.** A resolver returning an
attacker-controlled address redirects traffic for the life of the cache entry,
and unlike the static profiles there is no reload or review step in between.
Use a resolver the deployment controls.

### A note on `proxy_pass` and the request URI

`proxy_pass` with a variable and no URI part passes the request URI through
unchanged. The URI-substitution rule that catches people applies when
`proxy_pass` carries a URI part of its own.

Appending `$request_uri` is therefore redundant rather than safer here. Path,
query string, and normalisation of a traversal segment were compared both ways
against this image and behave identically, matching the static profiles.

### Upstream verification applies to HTTPS upstreams only

The proxying profiles other than
[`tls-upstream`](../examples/profiles/tls-upstream/nginx.conf) reach their
upstream over plain HTTP, where there is no certificate to verify. That is a
deployment boundary decision, not an omission: those profiles assume the
segment between proxy and upstream is already trusted, and a deployment where
it is not should use the verified-HTTPS pattern, which qualifies chain and
hostname verification and CRL enforcement.

Adding `https://` to an upstream without that pattern is worse than plain HTTP,
because it looks verified and is not.

### Qualified behaviour

The tests prove the dynamic profile serves a request with its path intact,
and that after the endpoint is replaced on a different address under the same
name it recovers without a reload.

They do **not** qualify resolver failure modes, behaviour when DNS returns
several addresses, cache behaviour under load, or recovery time against any
particular zone's TTL.

## WebSocket proxying

[`examples/profiles/websocket/nginx.conf`](../examples/profiles/websocket/nginx.conf)
proxies upgrade-capable traffic under `/ws` and ordinary HTTP everywhere else,
to the same application.

The connection disposition sent upstream is derived from a map rather than
copied from the client: a request carrying an upgrade token is forwarded with
`Connection: upgrade`, and every other request with `Connection: close`. A
client therefore cannot choose how the proxied connection is framed.

### Timeouts and capacity

An idle WebSocket sends nothing for long periods, so `proxy_read_timeout` must
exceed the application's own idle or ping interval or NGINX closes healthy
sessions. That long timeout is scoped to the upgrade location: the plain HTTP
location keeps the short timeout, so a stuck HTTP upstream cannot hold a worker
connection for an hour.

Every idle session still occupies a worker connection on both sides. Size
`worker_connections` and any per-client connection limit for the expected
concurrent *session* count rather than for request rate. This is the main
capacity difference between this profile and the plain proxy, and it is not
qualified by the tests.

Upgrades are never retried against another member. The handshake is not
idempotent, and once the client has begun speaking the upgraded protocol there
is nothing to replay.

### Origin validation is not performed

NGINX does not validate `Origin`, and this profile does not add that check.
Browsers do not apply the same-origin policy to WebSocket handshakes, so an
application that authenticates with cookies alone is exposed to cross-site
WebSocket hijacking. Origin or token validation belongs to the application or
an authenticating layer. This is a deployment responsibility, and mounting this
profile does not discharge it.

### Access-event schema

The profile emits the common fields, the upstream fields, and:

| Field | JSON type | Meaning |
| --- | --- | --- |
| `connection_upgrade` | string | Derived disposition, `upgrade` or `close`. |

The value is derived, never client-supplied, so the tests reject any event
carrying another token.

### Qualified behaviour

The tests prove that a request without the upgrade token reaches the
application with the derived `close` disposition even when the client offers a
conflicting `Connection` header, that a request carrying the token reaches the
application as a handshake and its `101` response is relayed, that the plain
HTTP location is unaffected, and that both events match the schema.

They do **not** qualify frame exchange over an established session, session
duration, idle-timeout behaviour under real traffic, or concurrent session
capacity. The fixture reports what the proxy forwarded; it does not implement
the WebSocket protocol.

## HTTP load balancing

[`examples/profiles/load-balancer/nginx.conf`](../examples/profiles/load-balancer/nginx.conf)
distributes requests across a pool of HTTP members. Copy the example and
replace the member endpoints with the deployment's approved service names.

The pool uses weighted round robin, the NGINX default. It needs no shared state
between workers and distributes predictably. `least_conn` suits long-lived or
uneven requests and a hash method suits affinity; change the method only with a
stated reason, because it changes failure behaviour under load.

Member endpoints are resolved once when the configuration loads. A pool whose
membership changes at runtime needs a reviewed resolver configuration, which is
not part of this profile.

### Failure handling

`max_fails` and `fail_timeout` are *passive* checks. NGINX open source performs
no active upstream probing, so a member is withdrawn only after real requests
fail, and it is returned to rotation when `fail_timeout` expires rather than
after any proof that it recovered. Sizing these too aggressively removes
capacity during a transient blip; too loosely keeps sending traffic to a dead
member. A deployment that needs health-driven membership owns that outside this
image.

Retries are restricted to `error` and `timeout`, which are failures that occur
before the application observed the request. `non_idempotent` is deliberately
absent: replaying a `POST`, `PATCH`, or `DELETE` that may already have been
applied is a correctness and duplicate-side-effect risk, not an availability
improvement. `proxy_next_upstream_tries` and `proxy_next_upstream_timeout` are
both set so a failing pool cannot multiply one client request into an unbounded
amount of upstream work.

### Access-event schema

The profile emits the common fields plus the upstream fields shared with the
reverse proxy:

| Field | JSON type | Meaning |
| --- | --- | --- |
| `upstream_addr` | string | Member address, one entry per attempt. |
| `upstream_status` | string | Upstream status, one entry per attempt. |
| `upstream_connect_time` | string | Connect duration, one entry per attempt. |
| `upstream_header_time` | string | Header duration, one entry per attempt. |
| `upstream_response_time` | string | Response duration, one entry per attempt. |

These stay strings rather than numbers because on failover NGINX records one
entry per attempt. A reader splits on `", "`, and treats `" : "` as an attempt
boundary within a single upstream group. Counting attempts is how the tests
distinguish a real retry from a request that was simply routed to a healthy
member.

### Qualified behaviour

The tests require that every healthy member receives traffic, that stopping a
member produces no client-visible failure, and that at least one retry is
recorded in the structured events. They do not qualify capacity, latency under
load, connection draining during a rolling member restart, or session affinity.

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
