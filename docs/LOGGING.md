# Logging

This guide describes the current logging contract and the planned profiles for
the project's different use cases. It also identifies responsibilities that
belong to the container runtime, logging platform, and controlled-network
operator.

## Current development behavior

NGINX writes access events to `/dev/stdout` and error events at `notice` or
higher to `/dev/stderr`. The conventional files under `/var/log/nginx` are
symlinks to those streams. The image does not run a log daemon, write rotating
log files, or require a writable log directory.

The current access record contains:

- remote address and authenticated user, when present;
- local timestamp;
- complete request line;
- final response status and body bytes;
- referrer and user-agent headers; and
- the client-supplied `X-Forwarded-For` header.

### What `$request` means

The variable is singular: `$request`, not `$requests`. NGINX defines it as the
full original HTTP request line. Given this request:

```http
GET /?query=SELECT%20name%20FROM%20system.tables&password=secret HTTP/1.1
Host: clickhouse.example
Authorization: Basic example
```

`$request` produces:

```text
GET /?query=SELECT%20name%20FROM%20system.tables&password=secret HTTP/1.1
```

It includes the method, the original path and query string, and the HTTP
protocol. It does not include request headers or the request body. In this
example, the `Authorization` header is not captured by `$request`, but the SQL
and password in the URL are captured.

The current format surrounds `$request` with quotes, so a complete development
access event would resemble:

```text
10.0.0.8 - - [08/Sep/2026:20:15:31 +0000] "GET /?query=SELECT%20name%20FROM%20system.tables&password=secret HTTP/1.1" 200 87 "-" "curl/8.0" "-"
```

The safer structured profile will assemble reviewed fields instead of logging
the complete request line:

| Variable | Meaning | Query-string behavior |
| --- | --- | --- |
| `$request_method` | Request method such as `GET` or `POST`. | Does not contain it. |
| `$uri` | Current normalized path, which can change during internal processing. | Does not contain it. |
| `$server_protocol` | Protocol such as `HTTP/1.1` or `HTTP/2.0`. | Does not contain it. |
| `$request_uri` | Full original URI. | Contains it; unsafe for sensitive URLs. |
| `$args` or `$query_string` | URL arguments only. | Is the query string; unsafe by default. |
| `$request_id` | NGINX-generated random request identifier. | Does not contain it. |

Using `$uri` instead of `$request_uri` prevents query arguments from entering
the access event, but its normalization and internal-redirect behavior must be
tested for each configuration. The production format will use JSON escaping
and separate fields such as method, normalized path, protocol, status,
duration, bytes, and a correlation identifier.

The forwarded-for value is also untrusted client input unless a deployment
establishes and enforces a trusted proxy chain. These fields must not be used
as authenticated identity, and the current development format is not the
future ClickHouse or sensitive-URL profile.

The `/healthz` location disables access logging. NGINX's error stream still
captures startup, configuration, operational, and shutdown events. Setting
`TZ=UTC` makes the current `$time_local` value use UTC with a numeric offset,
but the planned structured format will prefer `$time_iso8601`.

The relevant source files are [`container/nginx.conf`](../container/nginx.conf)
and [`container/conf.d/default.conf`](../container/conf.d/default.conf).

## Collection by runtime

The runtime captures stdout and stderr. NGINX log rotation is therefore not a
container responsibility; the selected runtime or cluster logging service
must enforce storage, rotation, forwarding, retention, access control, and
disposal.

For local Podman development:

```console
podman logs nginx-ubi9
podman logs --follow --since 10m nginx-ubi9
podman inspect --format '{{.HostConfig.LogConfig.Type}}' nginx-ubi9
```

The effective Podman driver depends on host configuration. A rootless Linux
host, Podman machine, and Podman Desktop can use different storage and journal
paths, so record `podman info` with qualification evidence. Use `podman logs`
or the host journal instead of attempting to tail the stream symlinks inside
the container.

Docker uses the same stream contract:

```console
docker logs --follow --since 10m nginx-ubi9
docker inspect --format '{{.HostConfig.LogConfig.Type}}' nginx-ubi9
```

On Kubernetes or OpenShift, collect the container's stdout and stderr through
the platform logging pipeline. Do not mount a host log directory merely to
make NGINX rotate files. Multi-line error messages and restarts must be tested
with the chosen collector, and platform metadata should supply pod, namespace,
node, container, image digest, and restart identity.

## Use-case logging requirements

| Profile | Add or preserve | Exclude or handle carefully |
| --- | --- | --- |
| Static content | Normalized path, method, protocol, status, bytes, duration. | Query arguments, signed URLs, referrer, and unnecessary client identity. |
| Reverse proxy | Request ID, upstream address/status, connect/header/response time, total time. | Authorization, cookies, untrusted forwarding headers, and internal names exposed to broad audiences. |
| Load balancing | Every attempted upstream and result, retry count or sequence, cache outcome. | Assumptions that one event contains only one upstream attempt. |
| TLS termination | Protocol, cipher, SNI, session reuse, verification result. | Certificate contents; subject, issuer, serial, and fingerprint unless required. |
| WebSocket | Handshake status, upstream, total duration, bytes, termination result. | Message payloads; the access log does not provide message-level auditing. |
| ClickHouse gateway | Safe correlation ID, normalized path, status, duration, upstream result. | Query string, SQL, body, credentials, cookies, and arbitrary headers. |
| Health/readiness | Suppress routine access events or use a dedicated minimal stream. | High-volume probe noise and backend detail. |
| Rate/connection limits | Policy name, trusted limit key or pseudonym, outcome, status. | Raw identifiers when aggregation is enough; repetitive error-log alerts. |

NGINX provides upstream timing variables and TLS variables for these profiles,
but a variable's availability will be verified against the exact Red Hat RPM
build before its configuration is supported. Initial profile examples will use
JSON escaping and stable field names so collectors do not need to parse the
human-oriented development format.

## Sensitive-data rules

Treat request targets, headers, network addresses, user identifiers, TLS
client identity, and backend names according to the deployment's data
classification. In particular:

- do not log `Authorization`, `Proxy-Authorization`, `Cookie`, `Set-Cookie`,
  private keys, certificates, request bodies, or response bodies;
- do not log `$request`, `$request_uri`, or `$args` where URLs may contain
  credentials, queries, tokens, personal data, or signed parameters;
- validate correlation IDs for length and permitted characters before logging
  or forwarding them, or generate a trusted ID at the ingress;
- escape structured values as JSON and test control characters and malformed
  input against the downstream parser;
- restrict log readers and service accounts by least privilege; and
- document the business purpose and retention period for each identity field.

Redaction after collection is a fallback, not permission to collect secrets.
Values excluded at NGINX cannot leak through a later forwarding or storage
stage.

## Error levels and operational signals

The development error threshold is `notice`. A production profile must select
its level with tested examples of startup, reload, upstream failure, TLS
failure, client disconnect, rate limiting, and shutdown. `debug` logging can
expose sensitive request and connection details and must not be a standing
production setting.

Access and error logs are evidence, not a complete monitoring system. Derive
metrics and alerts for at least availability, error ratio, latency, rejected
connections, limiting outcomes, upstream health, TLS failures, log pipeline
failure, and storage exhaustion. Application audit events remain the
application's responsibility.

## Controlled-network control ownership

The image owns NGINX's stream destinations, documented fields, safe defaults,
and tests. The deployment owns:

- the runtime or cluster log driver and collector configuration;
- authenticated and encrypted forwarding to approved destinations;
- trusted time synchronization for the host and logging platform;
- capacity, rotation, retention, legal hold, backup, and secure deletion;
- role-based access, separation of duties, and administrator activity review;
- detection rules, alert routing, incident procedures, and pipeline health;
- protection against modification and evidence that demonstrates it; and
- data classification and approval for deployment-specific added fields.

For release qualification, record the image digest, configuration digest,
runtime and collector versions, log format revision, time source, destination,
retention policy, access-control policy, and tested failure behavior. Container
logs alone do not provide tamper-proof or non-repudiation guarantees.

## Authoritative NGINX references

- [HTTP access logging and JSON escaping](https://nginx.org/en/docs/http/ngx_http_log_module.html)
- [Core error logging](https://nginx.org/en/docs/ngx_core_module.html#error_log)
- [HTTP upstream variables](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#variables)
- [HTTP TLS variables](https://nginx.org/en/docs/http/ngx_http_ssl_module.html#variables)
- [HTTP core variables including `$request` and `$uri`](https://nginx.org/en/docs/http/ngx_http_core_module.html#variables)
- [NGINX syslog output](https://nginx.org/en/docs/syslog.html)
