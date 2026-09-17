# nginx-ubi — Level 2 requirements

Architectural obligations derived from [`L1-REQ.md`](L1-REQ.md). Each names its
parent. Implementation-level obligations are in [`L3-REQ.md`](L3-REQ.md), and
status is tracked in the generated [`TRACE-MATRIX.md`](TRACE-MATRIX.md).

Conventions, identifier rules, and verification-method definitions are stated
once in [`L1-REQ.md`](L1-REQ.md) and are not repeated here.

---

## Image and composition

### L2-IMG-001

**Parent.** L1-IMG-001

**Statement.** The builder and runtime base images SHALL be referenced by
manifest-list digest, and the digest recorded in the artifact lock SHALL match
the one the build uses.

**Rationale.** Two places record the base. If they can disagree, the lock
describes something other than what was built.

**Verification.** Test, Inspection.

### L2-IMG-002

**Parent.** L1-IMG-002

**Statement.** The final image SHALL contain no package-management binary and
no repository configuration.

**Rationale.** Repository configuration left behind is an instruction for where
to fetch software, even with no tool present to act on it.

**Verification.** Test.

### L2-IMG-003

**Parent.** L1-IMG-003

**Statement.** The image SHALL embed a manifest of installed packages that
matches the architecture lock exactly.

**Rationale.** An inventory derived from the image at inspection time can be
wrong. One written at install time from the verified transaction cannot drift
from it unnoticed.

**Verification.** Test.

### L2-IMG-004

**Parent.** L1-IMG-003

**Statement.** The NGINX build's compile-time feature and module set SHALL
match a reviewed inventory, and no separately packaged dynamic module SHALL be
present.

**Rationale.** A changed module set changes the attack surface and the set of
directives that load, which a package-version comparison alone does not show.

**Verification.** Test.

## Supply chain

### L2-SUP-001

**Parent.** L1-SUP-001

**Statement.** The architecture lock SHALL record, for every artifact, its
filename, size, SHA-256, signer fingerprint, NEVRA, source RPM, and origin URL.

**Rationale.** Verification is only possible against recorded expectations.

**Verification.** Test, Inspection.

### L2-SUP-002

**Parent.** L1-SUP-001

**Statement.** Every acquired RPM SHALL be verified against its recorded digest
and signed by an approved fingerprint before assembly begins.

**Rationale.** A digest proves the bytes; a signature proves the publisher.
Neither substitutes for the other.

**Verification.** Test.

### L2-SUP-003

**Parent.** L1-SUP-002

**Statement.** Assembly SHALL run with networking disabled and image pulling
forbidden, with base images preloaded and confirmed present beforehand.

**Rationale.** Disabling the network only proves hermeticity if the inputs were
already staged and checked.

**Verification.** Test.

### L2-SUP-004

**Parent.** L1-SUP-003

**Statement.** Installation SHALL compare the resulting package inventory
against the lock and fail on any difference.

**Rationale.** Comparing intent to outcome is what turns a pin into a check.

**Verification.** Test.

### L2-SUP-005

**Parent.** L1-SUP-004

**Statement.** Dependency resolution SHALL occur only in an explicitly invoked
command, never during an ordinary or release build.

**Rationale.** A build that resolves can change its own inputs, and then
describes something it chose rather than something that was reviewed.

**Verification.** Inspection, Analysis.

### L2-SUP-006

**Parent.** L1-SUP-001

**Statement.** A payload transferred into a disconnected environment SHALL be
bound to its repository revision, architecture lock, and component inventory.

**Rationale.** A payload that cannot prove which review it came from has to be
reviewed again on arrival.

**Verification.** Test.

## Runtime contract

### L2-RUN-001

**Parent.** L1-RUN-001

**Statement.** The image SHALL declare a non-root runtime user, and the running
process SHALL NOT be UID zero.

**Rationale.** A declared identity that the runtime overrides is not evidence
about the running process.

**Verification.** Test.

### L2-RUN-002

**Parent.** L1-RUN-002

**Statement.** The running process SHALL report an empty effective capability
set and `NoNewPrivs` enabled.

**Rationale.** The process's own view is the authoritative one; the runtime
flags describe intent.

**Verification.** Test.

### L2-RUN-003

**Parent.** L1-RUN-003

**Statement.** All runtime writes SHALL be confined to a single mounted
temporary filesystem, and every NGINX temporary path SHALL resolve within it.

**Rationale.** A path outside the writable mount fails at the first request
that needs it, not at startup.

**Verification.** Test.

### L2-RUN-004

**Parent.** L1-RUN-004

**Statement.** Files the runtime must read SHALL be readable through group
zero, and the image SHALL NOT require a specific UID.

**Rationale.** Group zero is the only identity an arbitrary-UID platform
guarantees.

**Verification.** Test.

### L2-RUN-005

**Parent.** L1-RUN-005

**Statement.** A reload SHALL replace worker processes while retaining process
one.

**Rationale.** A reload that replaces process one is a restart, and the
container runtime treats it as one.

**Verification.** Test.

### L2-RUN-006

**Parent.** L1-RUN-005

**Statement.** A graceful stop SHALL complete in-flight responses before the
process exits, and SHALL exit zero.

**Rationale.** A non-zero exit on an intentional stop is indistinguishable from
a crash to anything watching.

**Verification.** Test.

### L2-RUN-007

**Parent.** L1-RUN-006

**Statement.** A configuration or filesystem startup failure SHALL name the
offending path, and where applicable the line.

**Rationale.** "Failed to start" is not a diagnostic.

**Verification.** Test.

## Proxying

### L2-PRX-001

**Parent.** L1-PRX-001

**Statement.** Proxying profiles SHALL replace any client-supplied forwarding
header with the direct peer address.

**Rationale.** Extending a chain the proxy cannot authenticate preserves
attacker-chosen content.

**Verification.** Test.

### L2-PRX-002

**Parent.** L1-PRX-002

**Statement.** No profile SHALL enable retries for non-idempotent methods, and
profiles with no alternative peer SHALL disable retries entirely.

**Rationale.** See ADR-0005.

**Verification.** Test, Inspection.

### L2-PRX-003

**Parent.** L1-PRX-003

**Statement.** Profiles that retry SHALL bound both the number of attempts and
the total time spent on them.

**Rationale.** Either bound alone permits amplification.

**Verification.** Inspection.

### L2-PRX-004

**Parent.** L1-PRX-003

**Statement.** A pool SHALL distribute across healthy members and SHALL survive
the loss of one without client-visible failure.

**Rationale.** A pool that does not distribute is a single upstream with extra
configuration.

**Verification.** Test.

### L2-PRX-005

**Parent.** L1-PRX-001

**Statement.** An upgraded-protocol profile SHALL derive the upstream
connection disposition rather than copying it from the client.

**Rationale.** A client that chooses how its connection is framed upstream
controls proxy behaviour it should not.

**Verification.** Test.

## Transport security

### L2-TLS-001

**Parent.** L1-TLS-001

**Statement.** Certificates, keys, and trust stores SHALL be consumed from
read-only mounts and SHALL NOT be writable by the runtime identity.

**Rationale.** Nothing in this image has cause to modify trust material.

**Verification.** Test.

### L2-TLS-002

**Parent.** L1-TLS-002

**Statement.** No private key SHALL exist in the image, and no key material
SHALL appear in any log stream.

**Rationale.** Both are permanent disclosures once they occur.

**Verification.** Test.

### L2-TLS-003

**Parent.** L1-TLS-003

**Statement.** HTTPS upstream profiles SHALL verify the chain and the hostname
against a mounted trust store, and SHALL reject an untrusted chain.

**Rationale.** Verification that can be satisfied by any certificate is not
verification.

**Verification.** Test.

### L2-TLS-004

**Parent.** L1-TLS-003

**Statement.** Client-certificate and upstream profiles SHALL enforce a mounted
revocation list.

**Rationale.** A certificate is valid until it is revoked, and revocation only
takes effect where it is checked.

**Verification.** Test.

### L2-TLS-005

**Parent.** L1-TLS-001

**Statement.** Certificate and revocation-list expiry SHALL be observable from
public metadata alone.

**Rationale.** A lifecycle check that needs the private key cannot run where
monitoring runs.

**Verification.** Test.

## Logging

### L2-LOG-001

**Parent.** L1-LOG-001

**Statement.** Access events SHALL record the normalised path and SHALL NOT
record the request line, request target, or query arguments.

**Rationale.** See ADR-0004.

**Verification.** Test.

### L2-LOG-002

**Parent.** L1-LOG-002

**Statement.** Each access event SHALL be one JSON object with a fixed field
set per profile and JSON escaping enabled.

**Rationale.** A varying field set forces a collector to guess.

**Verification.** Test.

### L2-LOG-003

**Parent.** L1-LOG-003

**Statement.** An inbound correlation identifier SHALL be accepted only when it
matches a bounded character and length pattern, and SHALL otherwise be
replaced by a generated one.

**Rationale.** An unbounded identifier is an injection vector into every system
that stores it.

**Verification.** Test.

### L2-LOG-004

**Parent.** L1-LOG-002

**Statement.** A connection that produces no application request SHALL NOT emit
an access event.

**Rationale.** An event whose required fields are empty cannot be validated,
and a schema that tolerates empties validates nothing.

**Verification.** Test.

## Limiting

### L2-LIM-001

**Parent.** L1-LIM-001

**Statement.** A request rejected by a limit SHALL receive status 429.

**Rationale.** See ADR-0006.

**Verification.** Test.

### L2-LIM-002

**Parent.** L1-LIM-001

**Statement.** Each access event SHALL record the outcome of every limit
evaluated, including that a limit was not reached.

**Rationale.** "Not evaluated" and "passed" mean different things, and
conflating them hides which control acted.

**Verification.** Test.

### L2-LIM-003

**Parent.** L1-LIM-002

**Statement.** The limit key SHALL NOT appear in any access event.

**Rationale.** The outcome is operational data; the key is a client
identifier.

**Verification.** Test, Inspection.

### L2-LIM-004

**Parent.** L1-LIM-001

**Statement.** Health endpoints SHALL be excluded from every limit.

**Rationale.** A limited health check converts a traffic spike into a restart.

**Verification.** Test.

## Health

### L2-HLT-001

**Parent.** L1-HLT-001

**Statement.** The liveness endpoint SHALL answer successfully while every
upstream is unreachable.

**Rationale.** This is the property, stated as the condition under which it
must hold.

**Verification.** Test.

### L2-HLT-002

**Parent.** L1-HLT-001

**Statement.** The readiness endpoint SHALL report failure when its upstream is
unreachable, and SHALL NOT cause the process to be replaced.

**Rationale.** Removal from rotation is reversible; replacement is not.

**Verification.** Test.

### L2-HLT-003

**Parent.** L1-HLT-002

**Statement.** The operator status surface SHALL be served on a separate
listener and SHALL deny all sources by default.

**Rationale.** A separate listener is what allows network policy to treat it
differently.

**Verification.** Test.

### L2-HLT-004

**Parent.** L1-LOG-002

**Statement.** A succeeding probe SHALL NOT emit an access event.

**Rationale.** Continuous probes otherwise dominate the access stream and bury
real traffic.

**Verification.** Test.

## Operations

### L2-OPS-001

**Parent.** L1-OPS-001

**Statement.** Configuration validation SHALL be runnable against the image
without starting a service, and SHALL exit non-zero on an invalid
configuration.

**Rationale.** A check that cannot fail cannot gate anything.

**Verification.** Test, Demonstration.

### L2-OPS-002

**Parent.** L1-OPS-002

**Statement.** Configuration SHALL be mounted such that an atomic replacement
is visible to a subsequent reload.

**Rationale.** A single-file bind mount pins an inode, so a rename-based
deployment reloads the previous content while reporting success.

**Verification.** Demonstration, Inspection.

## Evidence

### L2-EVD-001

**Parent.** L1-EVD-002

**Statement.** Every support-matrix entry SHALL state its qualification level
and the evidence that supports it.

**Rationale.** A matrix row without evidence is an assertion.

**Verification.** Inspection.

### L2-EVD-002

**Parent.** L1-EVD-001

**Statement.** Behaviour that has been tested but not qualified SHALL be
labelled preview, and the untested aspects SHALL be named.

**Rationale.** "Tested" is routinely read as "supported". Naming what was not
covered is what prevents that.

**Verification.** Inspection.
