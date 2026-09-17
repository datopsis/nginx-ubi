# nginx-ubi — Level 1 requirements

## Purpose

This document states the Level 1 (L1) SHALL requirements for `nginx-ubi`: a
security-oriented, rootless NGINX container image built on Red Hat UBI 9, with
tested configuration profiles and reviewable assurance evidence.

L1 states **what** the product must do at the highest level of abstraction.
[`L2-REQ.md`](L2-REQ.md) decomposes each L1 into architectural obligations, and
[`L3-REQ.md`](L3-REQ.md) decomposes each L2 into implementation obligations.
All three are traced through [`TRACE-MATRIX.md`](TRACE-MATRIX.md).

## Scope

This document covers the container image, the configuration profiles under
`examples/profiles`, the artifact acquisition and assembly tooling, and the
evidence the project publishes about them.

It is written against an implementation that already exists. It reconstructs
obligations rather than specifying them in advance, which means it can expose
behaviour the implementation does not meet. Where that happens the outcome is a
defect to close or a non-requirement to record, not a requirement to soften.

Deferred work is recorded in [`ROADMAP.md`](ROADMAP.md) rather than here.
Explicit exclusions are recorded as non-requirements below.

## Conventions

### Identifier format

Each requirement has a stable identifier `L<n>-<CATEGORY>-<NNN>`, where
`<CATEGORY>` is drawn from the table below and `<NNN>` is a zero-padded
sequence number within that category.

**Identifiers are permanent.** A retired requirement takes its identifier with
it, and the number is never reused.

| Category | Covers |
| --- | --- |
| `IMG` | Image composition and published metadata |
| `SUP` | Supply chain: artifact acquisition, locks, assembly |
| `RUN` | Runtime contract: identity, privileges, filesystem, lifecycle |
| `PRX` | Proxying behaviour and upstream handling |
| `TLS` | Transport security and trust material |
| `LOG` | Structured logging and its exclusions |
| `LIM` | Request, connection, and bandwidth limiting |
| `HLT` | Health and readiness surfaces |
| `OPS` | Operational procedures |
| `EVD` | Assurance evidence and support statements |

Non-requirements use `NR-<NNN>`.

### SHALL language

Every L1 requirement uses SHALL to express a mandatory obligation. SHOULD and
MAY are reserved for L2 and L3 derivations, where they carry their conventional
meanings.

### Verification methods

Drawn from the DO-178 vocabulary:

- **Test (T)** — executable verification. A `unittest` case carrying a
  `@requirements(...)` marker, or a Bash scenario carrying a
  `# Requirements:` comment.
- **Analysis (A)** — logical evaluation, including static analysis and review
  of generated inventories.
- **Inspection (I)** — examination of code, configuration, or documents.
- **Demonstration (D)** — operational observation on a target platform.

Status is tracked in [`TRACE-MATRIX.md`](TRACE-MATRIX.md), which is generated.
This document carries specification content only.

### Marker conventions

`unittest` cases use the decorator in `tests/requirements.py`:

```python
@requirements("L3-LOG-001")
def test_query_strings_are_absent(self) -> None:
```

Bash scenario suites use a comment immediately preceding the scenario:

```bash
# Requirements: L3-PRX-004 L3-PRX-005
```

A Python marker can also be used to *run* the tests verifying one requirement
(`python -m tests.requirements L3-LOG-001`). A Bash marker cannot: the suites
are linear scripts rather than individually addressable cases, so the marker
provides traceability only. This is recorded as `NR-007` rather than treated as
satisfied.

---

## Image and composition

### L1-IMG-001

**Statement.** The final image SHALL be built on a digest-pinned Red Hat UBI 9
base.

**Rationale.** A tag moves; a digest does not. Release evidence describes a
filesystem, and that filesystem must be identifiable.

**Verification.** Test, Inspection.

### L1-IMG-002

**Statement.** The final image SHALL contain no package manager.

**Rationale.** A package manager in a runtime image is an installation
capability available to anything that achieves execution, and it invalidates
the claim that the image's contents are exactly the reviewed set.

**Verification.** Test.

### L1-IMG-003

**Statement.** The image SHALL record the exact set of packages it contains.

**Rationale.** Vulnerability triage, licensing review, and provenance all
require knowing what is installed without inferring it.

**Verification.** Test, Analysis.

## Supply chain

### L1-SUP-001

**Statement.** Every external build input SHALL be pinned and verified before
use.

**Rationale.** An unverified input is trusted implicitly. Pinning without
verification records an intention that nothing checks.

**Verification.** Test, Analysis.

### L1-SUP-002

**Statement.** Image assembly SHALL NOT access the network or pull images.

**Rationale.** Assembly that can reach the network can install something not in
the reviewed set, and cannot run in a disconnected environment.

**Verification.** Test.

### L1-SUP-003

**Statement.** A change in an external input SHALL cause a build failure rather
than a silent substitution.

**Rationale.** This project has already experienced the alternative: a cached
layer masked a package set the repositories no longer offered, and every build
reported success. See ADR-0001.

**Verification.** Test.

### L1-SUP-004

**Statement.** Refreshing a pinned input SHALL be an explicit, reviewable
operation distinct from an ordinary build.

**Rationale.** A build that can update its own inputs cannot produce evidence
about them.

**Verification.** Inspection, Analysis.

## Runtime contract

### L1-RUN-001

**Statement.** The image SHALL run as a non-root user with no privilege
transition at startup.

**Rationale.** An entrypoint that starts as root and drops privileges has a
root-privileged window, and requires trusting the transition.

**Verification.** Test.

### L1-RUN-002

**Statement.** The image SHALL operate with all Linux capabilities dropped and
`no-new-privileges` enabled.

**Rationale.** Capabilities retained are capabilities available to an attacker
who achieves execution.

**Verification.** Test.

### L1-RUN-003

**Statement.** The image SHALL operate with a read-only root filesystem, given
documented writable mounts.

**Rationale.** A writable root turns code execution into persistence.

**Verification.** Test.

### L1-RUN-004

**Statement.** The image SHALL operate under an arbitrary non-root UID in group
zero.

**Rationale.** OpenShift and equivalent platforms assign a UID the image cannot
predict. An image that works only as its declared user does not run there.

**Verification.** Test.

### L1-RUN-005

**Statement.** The runtime SHALL reload configuration and stop gracefully
without dropping accepted requests.

**Rationale.** A reload that drops connections makes routine configuration
changes an outage, and operators respond by not making them.

**Verification.** Test.

### L1-RUN-006

**Statement.** A startup failure SHALL produce a diagnostic naming the cause.

**Rationale.** A container that exits without explanation converts a
configuration error into an investigation.

**Verification.** Test.

## Proxying

### L1-PRX-001

**Statement.** Proxying profiles SHALL NOT forward a client-supplied
forwarding chain as though it were trusted.

**Rationale.** A client that can set its own forwarding header can attribute
its traffic to another address, defeating anything downstream that trusts it.

**Verification.** Test.

### L1-PRX-002

**Statement.** Proxying profiles SHALL NOT retry a request the upstream may
already have applied.

**Rationale.** A duplicated write is harder to detect and more expensive to
repair than a failed one. See ADR-0005.

**Verification.** Test, Inspection.

### L1-PRX-003

**Statement.** Proxying profiles SHALL bound the upstream work that one client
request can cause.

**Rationale.** Unbounded retries turn a failing upstream into an amplifier.

**Verification.** Inspection.

## Transport security

### L1-TLS-001

**Statement.** TLS profiles SHALL support operator-provided certificates, keys,
and trust stores mounted read-only.

**Rationale.** Key material belongs to the deployment. An image that generates
or contains its own production keys makes every instance share them.

**Verification.** Test.

### L1-TLS-002

**Statement.** The image SHALL NOT contain, generate, or log private key
material.

**Rationale.** A key in an image is published to everyone who can pull it.

**Verification.** Test, Inspection.

### L1-TLS-003

**Statement.** Upstream TLS SHALL verify the certificate chain and hostname.

**Rationale.** An unverified TLS upstream provides encryption without
authentication, which is worse than plain HTTP because it appears verified.

**Verification.** Test.

## Logging

### L1-LOG-001

**Statement.** Access events SHALL NOT contain query strings, request bodies,
headers, or credentials.

**Rationale.** Access logs propagate to collectors, retention, and backups.
Exclusion is structural; redaction is a runtime behaviour that can fail. See
ADR-0004.

**Verification.** Test.

### L1-LOG-002

**Statement.** Access events SHALL be machine-parseable and schema-stable.

**Rationale.** A collector that has to parse a human-oriented format breaks
whenever the format is adjusted.

**Verification.** Test.

### L1-LOG-003

**Statement.** Every access event SHALL carry a correlation identifier that is
either validated or generated.

**Rationale.** An unvalidated client-supplied identifier is an injection point
into every downstream system that indexes it.

**Verification.** Test.

## Limiting

### L1-LIM-001

**Statement.** A rejected request SHALL be distinguishable from a service
failure.

**Rationale.** A limit answering like an outage invites harder retries and
records a working control as an incident. See ADR-0006.

**Verification.** Test.

### L1-LIM-002

**Statement.** Limiting SHALL NOT record the limit key in access events.

**Rationale.** The outcome supports capacity analysis; the raw client
identifier adds a personal identifier to an otherwise identifier-free stream.

**Verification.** Test, Inspection.

## Health

### L1-HLT-001

**Statement.** Liveness SHALL NOT depend on the health of any upstream.

**Rationale.** A liveness probe that fails during a dependency outage makes the
orchestrator restart healthy instances, removing the capacity needed to
recover. See ADR-0007.

**Verification.** Test.

### L1-HLT-002

**Statement.** An operator status surface SHALL NOT be readable by default.

**Rationale.** Connection and capacity counters are not secrets, but they are
not public either, and a published port should not by itself grant access.

**Verification.** Test.

## Operations

### L1-OPS-001

**Statement.** A candidate configuration SHALL be verifiable before it reaches
a running container.

**Rationale.** Validation after deployment is discovery, not verification.

**Verification.** Test, Demonstration.

### L1-OPS-002

**Statement.** Documented procedures SHALL have been executed against the image
they describe.

**Rationale.** An untested procedure is a hypothesis. This project has already
published a reload procedure whose failure mode was only found by running it.

**Verification.** Demonstration, Inspection.

## Evidence

### L1-EVD-001

**Statement.** The project SHALL NOT claim a qualification it has not
performed.

**Rationale.** The value of the evidence depends entirely on the claims being
exact.

**Verification.** Inspection.

### L1-EVD-002

**Statement.** Every support statement SHALL name the runtime, architecture,
and configuration it applies to.

**Rationale.** An unqualified support claim is inherited by environments that
were never tested.

**Verification.** Inspection.

---

## Non-requirements

Explicit exclusions. Each is a decision, not an oversight.

| ID | Non-requirement | Reason |
| --- | --- | --- |
| `NR-001` | NGINX Plus capability | Open source only; see ADR-0002 |
| `NR-002` | FIPS validation | No cryptographic boundary has been defined or evidenced |
| `NR-003` | STIG certification | Tailored SCAP results describe selected rules only |
| `NR-004` | Enforcing query semantics at the proxy | NGINX parses HTTP, not SQL; belongs to the database |
| `NR-005` | Active upstream health checking | Commercial feature; passive checks used instead |
| `NR-006` | Session persistence | Commercial feature; hash-based affinity is the open source option |
| `NR-007` | Selecting a Bash scenario by requirement | Suites are linear scripts; markers give traceability only |
| `NR-008` | Forward proxying, WAF, mail proxying, stream proxying | Deferred; see the roadmap |
| `NR-009` | Interoperation with a real ClickHouse server | Tested against a stand-in; a deployment qualifies its own server |
