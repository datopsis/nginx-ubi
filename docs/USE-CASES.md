# Use cases

This catalog defines the intended ways to deploy `nginx-ubi9` and the
configuration, logging, and security concerns that accompany each one. It is
not yet a support matrix. A use case becomes supported only after its example,
negative cases, runtime restrictions, and operational guidance are tested
against the released image.

The current development baseline serves static content and exposes a health
endpoint on unprivileged port `8080`. The other profiles below are design
targets for the first release unless stated otherwise.

## Profile summary

| Use case | Intended purpose | Important logging data | Primary security boundary |
| --- | --- | --- | --- |
| Static web server | Serve HTML, images, downloads, and application assets. | URI path, status, bytes, latency, cache outcome. | Treat mounted content as immutable and prevent path disclosure. |
| Reverse proxy | Route HTTP requests to an application service. | Request ID, total time, upstream address, status, and timing. | Validate forwarded headers, constrain egress, and verify upstream TLS. |
| HTTP load balancer | Distribute requests across an upstream group. | Selected upstream, retries, each upstream status, and timing. | Bound retry behavior and prevent traffic from reaching unapproved backends. |
| TLS termination | Terminate HTTPS using operator-provided keys and certificates. | TLS protocol, cipher, SNI, and handshake or client-certificate result. | Mount private keys read-only and protect identity-bearing TLS fields. |
| WebSocket proxy | Proxy an HTTP Upgrade connection to an application. | Upgrade result, upstream, final status, bytes, and connection duration. | Apply connection limits and explicit idle timeouts. |
| ClickHouse HTTP gateway | Provide a controlled HTTP entry point to ClickHouse. | Safe request ID, status, latency, and upstream result. | Never log queries, credentials, cookies, or sensitive URL parameters. |
| Health and readiness | Give a runtime or orchestrator a low-cost status signal. | Normally none; count externally as a metric when needed. | Keep the endpoint unauthenticated only when its response reveals no state. |
| Request and connection limiting | Protect capacity at an ingress boundary. | Client or policy key, limit outcome, status, and request ID. | Choose trusted client identity and avoid unbounded state zones. |

## Static web server

Mount site content read-only beneath `/usr/share/nginx/html`, or build a
derived image when immutable application content must travel with the image.
The default configuration serves this directory and returns `404` when a path
does not exist.

Access logs help identify missing assets, large responses, abusive clients,
and unexpected methods. Query strings may contain signed-link credentials or
personal data, so a production format should record a normalized path rather
than the complete request target unless a reviewed requirement says otherwise.
Do not enable directory indexes by default.

## Reverse proxy

A reverse-proxy profile will define an explicit upstream and forward only the
headers required by the application. It must distinguish the client-facing
response from the upstream attempts that produced it. At minimum, logs should
carry a generated or validated request ID, total request time, upstream
address, upstream status, connection time, header time, and response time.

Do not trust a client-supplied forwarding chain until a deployment has defined
its trusted proxy hops. Upstream HTTPS must enable certificate-chain and
hostname verification; merely using an `https://` upstream is insufficient.
Network policy should restrict the container to approved upstreams and DNS.

## HTTP load balancer

Load balancing adds retry and failover behavior to the reverse-proxy profile.
Because NGINX variables can contain comma- or colon-separated results for
multiple attempts, collectors must preserve the complete field rather than
assuming one backend per request. Logs should make retry storms, unhealthy
backends, and uneven distribution visible.

Retrying a non-idempotent request can duplicate an operation. Each example
must explicitly define retry conditions, timeouts, failure behavior, and the
supported request methods.

## TLS termination and mutual TLS

Certificates, private keys, and trust stores are deployment inputs, not image
content. Mount them read-only and make them readable by the runtime identity
without starting the container as root. TLS logging should support protocol,
cipher, requested server name, session reuse, and verification result.

Client-certificate subjects, issuers, serial numbers, and fingerprints are
identifiers. Collect only the field needed to meet an authentication or audit
requirement, restrict access to it, and assign a retention period. Never log a
client certificate or private-key material.

## WebSocket proxy

NGINX access logging records the HTTP handshake and the connection's eventual
completion; it does not record individual WebSocket messages. A `101` status
shows a successful protocol switch, while request time and byte counts help
identify long-lived or unexpectedly large sessions.

The profile must test Upgrade header handling, upstream failure, graceful
shutdown, idle timeouts, maximum connections, and behavior when a client
disconnects. Message-level observability belongs in the application or a
purpose-built telemetry component.

## ClickHouse HTTP gateway

ClickHouse accepts queries and authentication data through several HTTP
locations, including request parameters and headers. The current development
log format contains `$request`, which includes the query string, and therefore
must not be treated as a safe ClickHouse production profile.

The qualified profile will log a normalized path without arguments, a safely
validated or generated correlation identifier, response status, latency, and
upstream outcome. It will not log request or response bodies, `Authorization`,
cookies, database credentials, complete query text, or arbitrary client
headers. Prefer a correlation identifier over query content when joining NGINX
events to ClickHouse's own audit and query logs.

## Health and readiness endpoints

The development `/healthz` location returns a fixed `200` response and uses
`access_log off`. This prevents frequent probes from obscuring application
traffic and consuming retention capacity. The container image `HEALTHCHECK`
validates NGINX configuration rather than sending an HTTP request.

A deployment that requires probe evidence should collect probe success from
its orchestrator or use a separate minimal log format. A future readiness
example must define what dependency state it reveals and must not disclose
backend names, credentials, or detailed failure information.

## Request and connection limiting

Rate and connection limits can protect an upstream from bursts, but they are
not a distributed denial-of-service service. The deployment must decide which
trusted identity forms the limit key, how much shared memory is bounded for
the state zone, and whether rejected requests return `429` or another reviewed
status.

Access logs should identify the applied policy and limit outcome without
recording secrets. Error-log severity must be tuned so expected limiting does
not create an alert flood. Limits need load tests because proxy topology,
address translation, and long-lived WebSocket connections change their effect.

## Cross-cutting deployment rules

Every qualified profile must:

- start directly as a non-root user and retain arbitrary-UID compatibility;
- work with a read-only root filesystem and documented writable paths;
- mount configuration, content, keys, certificates, and trust read-only;
- drop all Linux capabilities and set `no-new-privileges`;
- define ingress, egress, DNS, timeout, resource-limit, and failure behavior;
- validate configuration before rollout and document reload and rollback;
- emit only reviewed fields to the container log streams; and
- include positive, negative, and restricted-runtime tests.

See [Logging](LOGGING.md) for collection and field guidance and
[RPM provenance](RPM-PROVENANCE.md) for the image's package source.
