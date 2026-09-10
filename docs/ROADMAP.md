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

1. Approve the official NGINX stable channel and select the exact NGINX
   first-release candidate.
2. Implement architecture-specific artifact locks and source-independent
   acquisition driven by protected configuration.
3. Migrate the image to the exact official NGINX RPM and require
   network-disabled, no-pull assembly from a verified local bundle.
4. Close rootless failure diagnostics, graceful lifecycle tests, and
   package/module inventory checks.
5. Qualify the minimum static, reverse-proxy, structured-logging, and TLS
   profiles needed for the first supported image; keep additional profiles
   explicitly preview until their tests close.
6. Complete the repository policy files, support boundary, threat model,
   requirement analysis, control ownership, vulnerability policy, tailored
   SCAP evidence, and deployment cyber package needed for review.
7. Qualify standalone rootless Podman/Quadlet deployment, systemd lifecycle,
   journald collection, controlled-network operation, and rollback on an exact
   supported Linux host.
8. Rehearse the multi-architecture publish, provenance, SBOM, signing, and
   verification workflow from an untagged release candidate.
9. Freeze inputs, regenerate release-candidate evidence, approve findings,
   create the immutable tag, publish by digest, and verify the release.

Steps 1 through 4 are the immediate engineering critical path. Steps 5 and 6
can proceed in parallel only where they do not assume an unfrozen NGINX package
or module set.

## Package 2: rootless minimal image

- [ ] Approve official NGINX stable as the package channel and select an exact
  first-release candidate from authoritative sources.
- [ ] Add reviewed AMD64 and ARM64 artifact locks containing the complete RPM
  closure, checksums, sizes, signatures, source RPMs, and base-image digests.
- [ ] Add official and alternate-source acquisition paths; keep private
  endpoints, repository identifiers, credentials, and private CA material
  outside this public repository and image build.
- [ ] Make ordinary CI and local builds consume verified local bundles with
  build networking and image pulling disabled.
- [ ] Add negative tests for tampered, unsigned, wrong-version,
  wrong-architecture, missing, and unexpected bundle contents.
- [ ] Record source, redistribution, licensing, support lifecycle, and update
  ownership for every runtime component.
- [ ] Define lock refresh, key rotation, artifact mirroring, rollback, and
  disconnected artifact-transfer procedures.

**Fast-release checkpoint:** after Package 2, a development image is usable for
local evaluation but is not yet a supported release.

## Package 3: supported configurations and TLS

- [ ] Provide tested, minimal examples for static content, reverse proxying,
  load balancing, WebSocket proxying, health/readiness endpoints, rate limits,
  connection limits, and ClickHouse HTTP proxying.
- [ ] Establish safe defaults for request limits, timeouts, headers, server
  tokens, method handling, DNS resolution, upstream verification, and failure
  behavior without silently breaking general-purpose use.
- [ ] Document configuration mounting, validation, reload, rollback, logging,
  troubleshooting, and secret redaction.
- [ ] Implement and test structured logging profiles for static content,
  reverse proxying, load balancing, TLS and mTLS, WebSockets, ClickHouse,
  health endpoints, and request and connection limiting.
- [ ] Qualify log escaping, correlation IDs, query-string exclusion, runtime
  collection, rotation ownership, pipeline failure, and retention evidence.
- [ ] Provide TLS 1.2/1.3 examples for ingress termination, upstream TLS with
  hostname and chain verification, client-certificate authentication, trust
  rotation, certificate renewal, revocation limitations, and negative cases.
- [ ] Automate CA-issued TLS rehearsal without committing certificates or
  private keys.

## Package 4: CI and supply-chain controls

- [ ] Add a least-privilege release workflow with strict tag validation,
  native multi-architecture publishing, SBOM and provenance attestations,
  digest-bound signing, and retained verification evidence.
- [ ] Add monitored update proposals for NGINX packages and signing keys, UBI
  image digests, locked RPM dependencies, and assurance tools.
- [ ] Prove that release assembly cannot pull images, reach package networks,
  recalculate dependencies, or expose acquisition credentials.

## Package 5: security engineering and cyber-review package

- [ ] Establish the authoritative requirement-source register with publisher,
  title, release, date, retrieval date, URL, SHA-256, status, and license.
- [ ] Compare applicable NIST SP 800-53/53A, DISA Container Platform and
  web/application-server guidance, RHEL 9 STIG content, and product behavior;
  require independent review of applicability and mappings.
- [ ] Classify each requirement as image-owned, deployment-supported,
  inherited, not applicable, unsupported, or research required, with rationale
  and residual risk.
- [ ] Publish a schema-validated NIST OSCAL Component Definition and generate
  deterministic CSV and human-readable control views from the same source.
- [ ] Give every supported control an examine/test/interview assessment method,
  owner, defaults, configuration and restart behavior, dependencies, impact,
  loss-of-function statement, limitations, and evidence pointer.

- [ ] Perform discovery with pinned OpenSCAP and ComplianceAsCode content
  against a root-owner-preserving export of each architecture image.
- [ ] Select only image-owned rules, document every inclusion and exclusion,
  publish tailoring, and distinguish failures from not-applicable or
  deployment-owned controls.
- [ ] Keep findings report-only until the selected profile is reviewed and a
  blocking policy is approved; scanner execution errors always block.
- [ ] Create architecture, assurance-pipeline, runtime data-flow, TLS trust,
  controlled-network, and control-ownership diagrams.
- [ ] Publish a threat model covering build inputs, CI, registry, image
  integrity, runtime identity, configuration, ingress/egress, TLS keys and
  trust, logs, denial of service, upstreams, DNS, writable storage, evidence
  integrity, and updates.
- [ ] Publish a control matrix mapping requirements, implementation,
   configuration, validation, evidence, owner, limitations, and residual risk.
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

## Assurance completeness gate

Before release, review this repository against the complete assurance model
below and record any intentionally omitted item with an NGINX-specific
rationale. The review must cover evidence lifecycle,
support semantics, qualification ledger, architecture and trust-boundary
diagrams, rootless runtime and platform qualification, use-case profiles,
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
