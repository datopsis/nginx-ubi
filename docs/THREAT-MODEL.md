# Threat model

This component threat model covers the `nginx-ubi9` source, build and release
pipeline, OCI image, configuration interface, and representative deployment.
Each system owner must extend it for the actual application, data, network,
identity, availability objectives, platform, and authorization boundary.

## Security objectives and assets

The objectives are to preserve the integrity and provenance of the image;
serve or proxy only approved traffic; protect TLS keys, credentials, content,
configuration, upstream trust, and logs; limit the effect of compromise; keep
the service available within its stated capacity; and produce trustworthy,
reviewable evidence.

Assets include source and workflows, artifact locks and signing identities,
base images and RPMs, the published image and attestations, NGINX configuration,
site content, TLS private keys and trust stores, request and upstream data,
DNS and routing decisions, logs, vulnerability data, and qualification records.

## Actors and trust boundaries

Relevant actors are maintainers and reviewers, CI and registry identities,
artifact publishers, deployment administrators, clients, upstream services,
log operators, host/platform administrators, and an attacker controlling a
client, network path, upstream, dependency source, contributor account, or
compromised workload.

Trust boundaries exist between:

1. upstream publishers and the acquisition/verification job;
2. repository changes, protected CI, and release identities;
3. the registry or transfer process and the deployment host;
4. host kernel/runtime controls and the container user namespace;
5. client ingress and NGINX;
6. NGINX, DNS, and upstream services;
7. mounted configuration/content/secrets and the immutable image;
8. stdout/stderr, the runtime log driver, journald or cluster collection, and
   the central security platform; and
9. image evidence and the larger system authorization decision.

Rootless execution reduces host privilege available to a compromised NGINX
process. It does not protect against malicious configuration, authorized host
root, kernel/runtime flaws, data disclosed by proxy policy, denial of service
within allowed resources, or a trusted upstream returning hostile content.

## Threat and treatment register

| ID | Threat and consequence | Primary treatment | Owner and residual risk |
| --- | --- | --- | --- |
| TM-01 | A substituted base image, RPM, key, or dependency enters the build. | Protected lock updates; authoritative source; digest/checksum, RPM signature, fingerprint, NEVRA, architecture, and closure verification before a network-disabled build. | Project/CI. Publisher or signing-key compromise remains; use review, key-rotation procedure, provenance, and incident response. |
| TM-02 | A malicious or compromised workflow exfiltrates credentials or publishes an unreviewed image. | Pull-request review, immutable action references, least-privilege tokens, isolated jobs, protected environments/tags, OIDC, and digest-bound signing. | Repository administrators. Platform and maintainer-account compromise remain. |
| TM-03 | A deployment uses the wrong, mutable, unsigned, or failed candidate. | Promote and deploy by digest; verify signature, provenance, SBOM, platforms, and release status; quarantine failed candidates; prohibit first-release mutable tags. | Release and deployment owners. Verification-policy misconfiguration remains. |
| TM-04 | NGINX gains host privilege after request-processing compromise. | Dedicated rootless account, non-root container UID, all capabilities dropped, `no-new-privileges`, default seccomp, enforcing SELinux, read-only root, narrow mounts, no engine socket or host namespaces. | Image, host, and deployment. Host kernel/runtime vulnerabilities and host administrator access remain. |
| TM-05 | Configuration or mounted content is altered to expose files, redirect traffic, weaken TLS, or execute an unintended module. | Read-only dedicated mounts; root-owned immutable image programs; configuration review, digesting, `nginx -t`, change control, module inventory, reload tests, and rollback. | Deployment and project examples. An approved but unsafe NGINX directive remains possible. |
| TM-06 | Credentials, SQL, tokens, personal data, or internal details leak through logs. | Structured allow-listed fields, query-string exclusion, no bodies or credential headers, JSON escaping, restricted readers, retention policy, and adversarial logging tests. | Image configuration and logging operators. NGINX errors and deployment-added fields require separate review. |
| TM-07 | Spoofed forwarding or correlation headers create false identity or poisoned logs. | Define trusted proxy hops; overwrite or validate identifiers; bound length/characters; escape fields; never treat a client header as authenticated identity without a trust rule. | Deployment. Rootless network forwarding may change source addresses and must be qualified. |
| TM-08 | Ingress TLS is downgraded or keys are disclosed. | TLS 1.2/1.3 profile, reviewed ciphers, read-only operator-managed secrets, least-readable permissions, renewal/rotation rehearsal, expiry alerts, and negative protocol/certificate tests. | Deployment. FIPS is a separate boundary; revocation availability and CA compromise remain. |
| TM-09 | Upstream TLS accepts an attacker or DNS routes traffic to an unapproved service. | Certificate-chain and hostname verification, explicit trust store, stable approved names, resolver/timeouts, egress allow-list, DNS protection, and negative trust/name tests. | Deployment/network. Approved DNS, CA, or upstream compromise remains. |
| TM-10 | Proxy behavior enables request smuggling, header confusion, cache poisoning, open proxying, or unintended methods/routes. | Minimal explicit routes and headers, no forward-proxy default, safe timeout/body/header limits, server-token suppression, configuration-specific positive and negative tests, and upstream application validation. | Project examples and application owner. Protocol parser differences require continuing advisory review. |
| TM-11 | Request, connection, WebSocket, upstream, log, or temporary-storage exhaustion denies service or host capacity. | Cgroup memory/PID/CPU limits, bounded tmpfs, file-descriptor and NGINX connection limits, rate limits based on trusted identity, timeouts, body limits, log capacity/rate controls, load and failure testing, and upstream protection. | Deployment/host. A single instance has no inherent high availability and volumetric attacks require external capacity controls. |
| TM-12 | Writable paths or special files enable persistence or execution. | Package-manager-free final image, read-only root, only documented bounded tmpfs, `noexec,nosuid,nodev`, no unnecessary devices, and runtime mount/invariant tests. | Image/deployment. Memory-resident compromise persists until process replacement. |
| TM-13 | Logs or evidence are changed, dropped, flooded, expired, or incorrectly associated with a digest. | Off-host authenticated forwarding, time synchronization, access separation, capacity/retention monitoring, immutable or protected storage where required, failure tests, and evidence records bound to commit/digest/config/tool databases. | Host, logging, and assurance owners. Local journald alone is not non-repudiation. |
| TM-14 | A vulnerability remains unpatched or an update breaks security/availability. | Scheduled scans and advisory review, time-bounded exceptions, update SLAs, SBOM delta review, native tests, canary/staging validation, immutable previous digest, and rehearsed rollback. | Project and deployment owners. Unfixed or unknown vulnerabilities remain subject to risk acceptance. |
| TM-15 | Controlled-network transfer or stale offline data invalidates trust claims. | Hash/signature verification at both boundaries, recorded digest mapping, approved media/transfer station, mirrored trust and scanner data with age recorded, and a fully disconnected rehearsal. | Environment owner. Offline evidence is point-in-time and cannot claim current public intelligence. |
| TM-16 | Health checks show configuration validity while the proxied application is unavailable. | Distinguish startup, liveness, readiness, and external transaction monitoring; keep probes low-cost and non-sensitive; test upstream failure. | Deployment/application. The image health check intentionally does not prove end-to-end service health. |

## Abuse cases that must be tested

Configuration profiles should test oversized and malformed request lines and
headers, encoded paths, unsupported methods, untrusted forwarding headers,
control characters in logged values, sensitive query strings, slow clients,
connection floods, WebSocket idle behavior, upstream retry behavior, DNS and
TLS failures, full tmpfs, failed log forwarding, reload under traffic, and
termination with active connections.

Build and release tests should reject tampered, unsigned, wrong-version,
wrong-architecture, missing, and unexpected artifacts; mutable or malformed
release tags; absent attestations; scanner operational errors; and mismatched
native architecture evidence.

## Review and maintenance

Review this model whenever NGINX or UBI inputs, compiled modules, acquisition,
workflows, registry, runtime, network mode, supported configuration, log schema,
TLS boundary, or scanner content changes. Each accepted risk needs an owner,
compensating control, expiry or review date, and evidence. A clean scanner
result does not close threats that require design review or behavioral tests.
