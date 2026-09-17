# nginx-ubi — Level 3 requirements

Implementation obligations derived from [`L2-REQ.md`](L2-REQ.md). Each names
its parent. Status and verifying artifacts are in the generated
[`TRACE-MATRIX.md`](TRACE-MATRIX.md).

Conventions and verification-method definitions are stated in
[`L1-REQ.md`](L1-REQ.md). Rationale lives at L1 and L2; entries here state the
obligation and how it is checked.

---

## Supply chain

### L3-SUP-001
**Parent.** L2-SUP-001 — Lock validation SHALL reject a lock whose schema,
required fields, or reviewed-input binding is malformed. **Verification.** Test.

### L3-SUP-002
**Parent.** L2-SUP-001 — Lock validation SHALL reject a digest, size, or
inventory that differs from the reviewed inputs. **Verification.** Test.

### L3-SUP-003
**Parent.** L2-SUP-002 — Acquisition SHALL publish atomically and SHALL refuse
to replace an existing output directory. **Verification.** Test.

### L3-SUP-004
**Parent.** L2-SUP-002 — An alternate-source map SHALL reject URLs carrying
credentials, query strings, or fragments, and SHALL NOT print a source URL or
token on failure. **Verification.** Test.

### L3-SUP-005
**Parent.** L2-SUP-006 — A transfer manifest SHALL bind its payload to the
repository revision, architecture lock, and component inventory, and SHALL fail
closed when any of them differs. **Verification.** Test.

### L3-SUP-006
**Parent.** L2-SUP-001 — The component inventory SHALL be bound to both
architecture locks by digest, and validation SHALL fail when a lock changes.
**Verification.** Test.

### L3-SUP-007
**Parent.** L2-SUP-002 — Bundle verification SHALL reject byte tampering,
signature removal, signer mismatch, wrong version, wrong architecture, and
missing or additional RPMs. **Verification.** Test.

### L3-SUP-008
**Parent.** L2-SUP-003 — Assembly SHALL fail when the lock identity does not
match, and SHALL fail rather than fetch when a base image is absent.
**Verification.** Test.

## Image and composition

### L3-IMG-001
**Parent.** L2-IMG-003 — The manifest embedded in the image SHALL match the
lock-derived manifest by digest and SHALL NOT be writable at runtime.
**Verification.** Test.

### L3-IMG-002
**Parent.** L2-IMG-002 — The final image SHALL contain no repository
configuration. **Verification.** Test.

### L3-IMG-003
**Parent.** L2-IMG-004 — The dynamic module directory SHALL exist and SHALL be
empty. **Verification.** Test.

### L3-IMG-004
**Parent.** L2-IMG-004 — The NGINX compile-time feature and optional-module set
SHALL match the reviewed inventory. **Verification.** Test.

## Runtime contract

### L3-RUN-001
**Parent.** L2-RUN-001 — The running process SHALL report a non-zero UID and a
zero GID. **Verification.** Test.

### L3-RUN-002
**Parent.** L2-RUN-002 — The running process SHALL report an empty effective
capability set and `NoNewPrivs` enabled. **Verification.** Test.

### L3-RUN-003
**Parent.** L2-RUN-003 — The image SHALL serve with a read-only root filesystem
given only the documented temporary mount. **Verification.** Test.

### L3-RUN-004
**Parent.** L2-RUN-004 — The image SHALL serve under an arbitrary non-root UID
in group zero. **Verification.** Test.

### L3-RUN-005
**Parent.** L2-RUN-005 — A reload SHALL replace every worker process while
process one is retained. **Verification.** Test.

### L3-RUN-006
**Parent.** L2-RUN-006 — A graceful stop SHALL deliver a complete in-flight
response body and SHALL exit zero. **Verification.** Test.

### L3-RUN-007
**Parent.** L2-RUN-007 — An unwritable temporary path SHALL produce a
diagnostic naming that path. **Verification.** Test.

### L3-RUN-008
**Parent.** L2-RUN-007 — An invalid mounted configuration SHALL produce a
diagnostic naming the file and line. **Verification.** Test.

## Proxying

### L3-PRX-001
**Parent.** L2-PRX-001 — A client-supplied forwarding header SHALL be replaced
with the direct peer address. **Verification.** Test.

### L3-PRX-002
**Parent.** L2-PRX-002 — No shipped configuration SHALL enable
`non_idempotent`, and no shipped configuration SHALL use a commercial
directive. **Verification.** Test.

### L3-PRX-003
**Parent.** L2-PRX-004 — A pool SHALL distribute traffic across every healthy
member. **Verification.** Test.

### L3-PRX-004
**Parent.** L2-PRX-004 — Losing a pool member SHALL cause no client-visible
failure, and at least one retry SHALL be recorded. **Verification.** Test.

### L3-PRX-005
**Parent.** L2-PRX-005 — The upstream connection disposition SHALL be derived,
and a conflicting client-supplied value SHALL NOT be forwarded.
**Verification.** Test.

### L3-PRX-006
**Parent.** L2-PRX-004 — The dynamic-upstream profile SHALL recover from an
endpoint replaced at a different address without a reload. **Verification.**
Test.

### L3-PRX-007
**Parent.** L2-PRX-001 — An upstream failure SHALL be represented in the
structured event rather than presented as a proxy failure. **Verification.**
Test.

## Transport security

### L3-TLS-001
**Parent.** L2-TLS-003 — Ingress SHALL accept TLS 1.2 and 1.3 and SHALL reject
TLS 1.1. **Verification.** Test.

### L3-TLS-002
**Parent.** L2-TLS-003 — An untrusted certificate chain SHALL be rejected.
**Verification.** Test.

### L3-TLS-003
**Parent.** L2-TLS-004 — A revoked client certificate SHALL be rejected while a
valid one is accepted. **Verification.** Test.

### L3-TLS-004
**Parent.** L2-TLS-002 — Mounted key material SHALL NOT be writable, and no key
material or client identity SHALL appear in any log stream. **Verification.**
Test.

### L3-TLS-005
**Parent.** L2-TLS-005 — The lifecycle checker SHALL report certificate and
revocation-list deadlines from public metadata, and SHALL fail closed on
malformed or unreadable input. **Verification.** Test.

### L3-TLS-006
**Parent.** L2-TLS-003 — Trust rotation SHALL succeed across old, overlapping,
and new-only trust states without disabling verification. **Verification.**
Test.

## Logging

### L3-LOG-001
**Parent.** L2-LOG-001 — An access event's path SHALL be absolute and SHALL
contain no query arguments. **Verification.** Test.

### L3-LOG-002
**Parent.** L2-LOG-002 — Each profile's access event SHALL carry exactly its
declared field set, with JSON escaping applied. **Verification.** Test.

### L3-LOG-003
**Parent.** L2-LOG-003 — A correlation identifier outside the accepted pattern
SHALL be replaced rather than recorded. **Verification.** Test.

### L3-LOG-004
**Parent.** L2-LOG-001 — Credentials and query text supplied as request
parameters SHALL appear in no output stream. **Verification.** Test.

### L3-LOG-005
**Parent.** L2-LOG-004 — A connection producing no application request SHALL
emit no access event. **Verification.** Test.

## Limiting

### L3-LIM-001
**Parent.** L2-LIM-001 — Exhausting the request-rate budget SHALL produce 429
recorded as rejected by the request limit. **Verification.** Test.

### L3-LIM-002
**Parent.** L2-LIM-001 — Exceeding the connection budget SHALL produce 429
recorded as rejected by the connection limit specifically. **Verification.**
Test.

### L3-LIM-003
**Parent.** L2-LIM-002 — A limit outcome SHALL be one of the recognised
outcomes, including an explicit not-evaluated value. **Verification.** Test.

### L3-LIM-004
**Parent.** L2-LIM-004 — The health endpoint SHALL answer while the client's
request budget is exhausted. **Verification.** Test.

## Health

### L3-HLT-001
**Parent.** L2-HLT-001 — Liveness SHALL answer successfully while the upstream
is stopped. **Verification.** Test.

### L3-HLT-002
**Parent.** L2-HLT-002 — Readiness SHALL report failure while the upstream is
stopped, and SHALL record a structured event. **Verification.** Test.

### L3-HLT-003
**Parent.** L2-HLT-003 — The status surface SHALL refuse an unlisted source
even when its port is published. **Verification.** Test.

### L3-HLT-004
**Parent.** L2-HLT-004 — A succeeding probe SHALL emit no access event.
**Verification.** Test.

## Operations

### L3-OPS-001
**Parent.** L2-OPS-001 — Configuration validation SHALL exit non-zero for an
invalid configuration and zero for a valid one. **Verification.** Test,
Demonstration.
