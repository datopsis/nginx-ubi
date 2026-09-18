# First-release roadmap

This roadmap is the release gate for the first supported `nginx-ubi9` image.
The immediate objective is a small, usable rootless web and reverse-proxy image
without postponing controls that are difficult to retrofit safely.

A checked item requires reviewable evidence in a pull request, workflow run,
release asset, or qualification record. Automated success is not sufficient
where an item requires human analysis, an external environment, or a support
decision.

## Evidence lifecycle

Evidence has three levels:

1. **Development evidence** comes from a proposed revision or pull request.
2. **Integration evidence** comes from the exact revision merged to `main`.
3. **Release-candidate evidence** is regenerated after the final
   image-affecting change and bound to the candidate commit, image digest,
   architecture, configuration profile, scanner inputs, and platform versions.

Changing the NGINX or UBI inputs, image contents, default configuration,
entrypoint, scanner content, SCAP tailoring, or qualification procedure
invalidates the affected release-candidate evidence. Historical evidence stays
useful for comparison but cannot qualify the changed candidate.

## Working first-release boundary

These are initial positions, not support claims, until qualification closes the
corresponding gates.

| Area | Working first-release position |
| --- | --- |
| Architectures | Support native `linux/amd64` and `linux/arm64`. |
| Primary runtime | Qualify a documented rootless Podman version on an exact Red Hat host baseline. |
| Docker | Retain compatibility evidence without implying the same production-support boundary as Podman. |
| OpenShift | Test restricted-SCC arbitrary-UID operation; call it preview until an exact cluster release is qualified. |
| Core uses | Static web server, HTTP/HTTPS reverse proxy, TLS termination, HTTP load balancing, WebSocket proxy, health endpoints, and rate/connection limiting. |
| Controlled networks | Document connected build, artifact transfer, digest/signature verification, mirrored deployment, local trust, logging, and update procedures. |
| TLS | Support operator-provided certificates, keys, and trust stores mounted read-only; do not generate long-lived production keys in the image. |
| FIPS | Make no FIPS validation claim without a separately defined and evidenced cryptographic boundary. |
| STIG/SCAP | Publish exact tailored image-filesystem results; make no STIG certification claim. |
| Registry | Publish the first release to GHCR. |

Forward proxying, a WAF, ModSecurity, OIDC, embedded certificate automation,
third-party NGINX modules, mail proxying, and broad TCP/UDP stream proxying are
deferred until their dependencies, threat boundaries, and maintenance costs
are separately approved. They must not delay the core first release.

## Immediate first-release sequence

Work proceeds in this dependency order:

1. Close the remaining operational and platform evidence for the minimum
   qualified HTTP and TLS profiles; keep additional profiles explicitly
   preview until their tests close.
2. Establish the requirement tree, its generated trace matrix, the accepted
   decision records, and the profile and architecture diagrams.
3. Complete the repository policy files, support boundary, threat model,
   requirement analysis, control ownership, vulnerability policy, tailored
   SCAP evidence, and deployment cyber package needed for review.
4. Qualify standalone rootless Podman/Quadlet deployment, systemd lifecycle,
   journald collection, controlled-network operation, and rollback on an exact
   supported Linux host.
5. Rehearse the multi-architecture publish, provenance, SBOM, signing, and
   verification workflow from an untagged release candidate.
6. Freeze inputs, regenerate release-candidate evidence, approve findings,
   create the immutable tag, publish by digest, and verify the release.

Step 1 is the immediate engineering critical path. Step 2 precedes step 3
because the control matrix cites requirement identifiers and draws its
verification evidence from the trace matrix, so mapping controls before the
requirements exist produces references that cannot be resolved. Steps 2 and 3
can otherwise proceed in parallel with step 1 only where they do not assume an
unfrozen NGINX package or module set.

## Package 3: supported configurations and TLS

- [ ] Qualify runtime collection, rotation ownership, pipeline failure, and
  retention evidence for the selected logging platform.
- [ ] Qualify lifecycle-alert delivery and exact platform cryptographic-policy
  behavior for the TLS profiles on the selected supported host.

## Package 4: CI and supply-chain controls


## Package 5: security engineering and cyber-review package

The catalogue, baseline, consumer, scope, and representation decisions are
settled and recorded in
[ADR-0009](adr/0009-control-catalogue-and-baseline.md): NIST SP 800-53 Rev 5 at
the **High** baseline as the spine, with DISA SRG, RHEL 9 STIG, and CIS as
cross-references; written for an external assessor to ingest; covering image,
deployment, and host expectations; base controls before enhancements; every
control carrying an explicit origination property and responsible role.

Two consequences of those decisions shape the sequence below.

The **origination property is load-bearing, not decorative**. Host expectations
are in scope and the consumer is an assessor, so a control without a
machine-readable origination value can be read as a satisfied claim. Its check
is listed before the bulk authoring rather than after it.

**Package 8 precedes this package.** The control mapping cites requirement
identifiers from the tree and draws verification evidence from the trace
matrix, so authoring controls first would produce references that cannot be
resolved.

### Foundation

- [ ] Establish the authoritative requirement-source register with publisher,
  title, release, date, retrieval date, URL, SHA-256, status, and license.
  Every catalogue and guidance document is pinned by digest, because a control
  mapping is only meaningful against a known revision.
- [ ] Retrieve and pin the 800-53 Rev 5 OSCAL catalogue and the High baseline
  profile, plus the DISA Container Platform SRG, the web and application-server
  SRGs, the RHEL 9 STIG, and the applicable CIS benchmark.
- [ ] Define the OSCAL component structure before authoring controls: the
  origination values, the responsible roles, how a requirement identifier is
  cited, and how an SRG, STIG, or CIS cross-reference is attached to an 800-53
  control.
- [ ] Add the checks that hold the structure: every control carries an
  origination property and a responsible role, every cited requirement
  identifier exists in the tree, and every catalogue source resolves to its
  pinned digest. These land with the first controls, not after them.

### Control authoring

- [ ] Classify every High-baseline base control as image-owned,
  deployment-configured, host-inherited, organization-inherited, not
  applicable, or research required, with rationale and residual risk. A large
  share will not be image-owned; that is the expected outcome, not a gap.
- [ ] Author the 800-53 High base controls in the component definition, citing
  requirement identifiers from [the requirement tree](L1-REQ.md) and drawing
  verification evidence from [the trace matrix](TRACE-MATRIX.md).
- [ ] Give every image-owned control an examine, test, or interview assessment
  method, owner, defaults, configuration and restart behaviour, dependencies,
  impact, loss-of-function statement, limitations, and evidence pointer.
- [ ] Attach the DISA SRG, RHEL 9 STIG, and CIS cross-references to the
  completed spine, and require independent review of applicability and every
  mapping.
- [ ] Extend the component definition to the High-baseline control
  enhancements. Until this closes, record the deferral where an assessor will
  see it rather than leaving the gap to be discovered.

### Publication

- [ ] Publish the schema-validated OSCAL Component Definition and generate the
  deterministic CSV and human-readable control views from that single source,
  so no view can disagree with another.
- [ ] Publish a control matrix mapping requirements, implementation,
  configuration, validation, evidence, owner, limitations, and residual risk.

### Scanning, threat model, and operational policy

- [ ] Perform discovery with pinned OpenSCAP and ComplianceAsCode content
  against a root-owner-preserving export of each architecture image.
- [ ] Select only image-owned rules, document every inclusion and exclusion,
  publish tailoring, and distinguish failures from not-applicable or
  deployment-owned controls.
- [ ] Keep findings report-only until the selected profile is reviewed and a
  blocking policy is approved; scanner execution errors always block.
- [ ] Publish a threat model covering build inputs, CI, registry, image
  integrity, runtime identity, configuration, ingress/egress, TLS keys and
  trust, logs, denial of service, upstreams, DNS, writable storage, evidence
  integrity, and updates.
- [ ] Define the cryptographic boundary and document why TLS configuration and
  a UBI base do not independently establish FIPS validation.
- [ ] Document vulnerability triage, patch SLAs, exceptions with expiry,
  incident response, backup/restore responsibilities, logging integration,
  monitoring, resource limits, network policy, disconnected deployment, and
  decommissioning.
- [ ] Maintain a qualification ledger keyed by commit, image digest,
  architecture, inputs, runtime/platform versions, configuration, scanner
   versions/databases, result, limitations, evidence level, and artifact.

## Package 6: deployment and platform qualification

- [ ] Publish supported, compatible, preview/unqualified, and unsupported
  definitions plus an exact matrix for architecture, host, Podman/OCI runtime,
  Docker compatibility, OpenShift, configuration profiles, TLS modes,
  controlled-network operation, SCAP, and FIPS claims.
- [ ] Qualify the rootless standalone-host Quadlet on an exact supported RHEL 9
  baseline, including cgroup v2, SELinux enforcing, subordinate IDs, lingering,
  boot, logout, restart throttling, health, reload, graceful stop, update, and
  rollback.
- [ ] Qualify journald persistence, rate and capacity limits, access control,
  restart correlation, authenticated forwarding, forwarding interruption,
  storage pressure, retention, and disposal without sensitive-data leakage.
- [ ] Publish deployment guidance for identity, configuration/content/secrets,
  TLS, ingress/egress/DNS, resource limits, probes, monitoring, incident
  response, update, rollback, controlled transfer, and decommissioning.
- [ ] Test every supported configuration with positive, negative, restricted-
  runtime, load/failure, and logging cases on each claimed platform.
- [ ] Define go-live evidence for the exact image/configuration digest,
  platform, controls, capacity, alerting, contacts, exceptions, and procedures.
- [ ] Decide the OpenShift first-release support boundary from exact restricted-
  SCC qualification; retain preview status if the required cluster evidence is
  unavailable.

## Package 7: signed first release

- [ ] Implement and test the approved
  `v<nginx-version>-ubi<ubi-major>-r<YYYYMMDD>.<daily-sequence>` tag contract,
  NGINX and UBI version matching, UTC date and sequence validation, immutable
  release and commit tags, and OCI metadata.
- [ ] Define the first-release support lifetime and superseded-release policy.
- [ ] Freeze the final upstream versions and digests only after image-affecting
  work is complete.
- [ ] Review all fixed and unfixed scanner findings against authoritative
  vendor advisories; document every time-bounded acceptance.
- [ ] Complete license and third-party notice review.
- [ ] Regenerate native architecture, rootless Podman, TLS, controlled-network,
  standalone Quadlet/systemd/journald, and tailored SCAP release-candidate
  evidence from the exact candidate.
- [ ] Rehearse tag validation and the entire release workflow without granting
  broader permissions than production needs.
- [ ] Publish an AMD64/ARM64 manifest to GHCR with BuildKit provenance and
  SBOM, a complete SPDX release asset, digest-bound Cosign keyless signature
  and attestation, and a GitHub Release.
- [ ] Verify published digests, platforms, labels, signatures, attestations,
  SBOMs, scan artifacts, documentation links, and rollback instructions.

## Package 8: requirements, decisions, and architecture documentation

This package establishes the product's own requirement tree, its decision
record, and the diagrams both depend on. It is distinct from Package 5, which
maps *external* control frameworks onto the product: Package 5 answers "which
published control does this satisfy", and Package 8 answers "what did this
project commit to doing, why, and where is that verified". The two meet in the
trace matrix, which supplies the verification evidence Package 5 cites.

The structure follows the same design as the reference implementation in
`joey-huckabee/mie-decoder`: a three-level SHALL requirement tree with stable
identifiers, a generated trace matrix driven by markers in the tests
themselves, and MADR-style architecture decision records.

**Every item in this package gates the first release.** The requirement tree is
being written against an implementation that already exists, so it is a
reconstruction rather than a specification, and it will expose obligations the
implementation does not yet meet. Those become defects to close or
non-requirements to record, not text to soften, and either outcome is a
release-blocking finding.

- [ ] Reconcile with Package 5 before either is published: the control matrix
  and OSCAL component definition must cite requirement identifiers that exist
  in this tree, and must draw verification evidence from the trace matrix, so
  no control is mapped to a requirement the product never stated.

## Assurance completeness gate

Before release, review this repository against the complete assurance model
below and record any intentionally omitted item with an NGINX-specific
rationale. The review must cover evidence lifecycle,
support semantics, qualification ledger, the requirement tree and its trace
matrix, accepted decision records, architecture and trust-boundary diagrams, rootless runtime and platform qualification, use-case profiles,
TLS and FIPS boundaries, authoritative requirement analysis, control ownership
and OSCAL export, tailored SCAP, vulnerability and exception management,
licensing and notices, supply-chain evidence, controlled-network procedures,
production go-live evidence, release rehearsal, failed-candidate handling,
rollback, incident response, and evidence retention. Database storage,
replication, and backup requirements are included only when an NGINX profile
introduces equivalent durable state.

## After the first release

- [ ] Define support and qualification requirements for stream TCP/UDP proxying.
- [ ] Evaluate WAF/ModSecurity without expanding the trusted computing base
  by default.
- [ ] Evaluate external authentication integrations and OIDC patterns.
- [ ] Add performance, concurrency, connection-exhaustion, and soak baselines.
- [ ] Add exact OpenShift qualification if an appropriate cluster is available.
- [ ] Revisit additional registries only when consumer demand justifies them.
