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

## Package 1: project contract and minimal skeleton

- [ ] Add `README.md`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`,
  `CHANGELOG.md`, notices, editor settings, and ignore rules.
- [ ] Define supported, compatible, preview/unqualified, and unsupported.
- [ ] Publish the initial support matrix and explicit control ownership split.
- [ ] Add Code Owners, pull-request and issue templates, and dependency update
  configuration.
- [ ] Document required GitHub rulesets, least-privilege Actions defaults,
  secret scanning, push protection, private vulnerability reporting, and tag
  protection.

## Package 2: rootless minimal image

- [ ] Select supported NGINX and UBI 9 inputs from authoritative sources and
  pin every base image and downloaded artifact by digest or checksum.
- [ ] Record source, redistribution, licensing, support lifecycle, and update
  ownership for every runtime component.
- [ ] Build a package-manager-free UBI 9 Micro final stage.
- [ ] Run NGINX directly as a fixed non-root identity compatible with an
  arbitrary UID in group `0`; do not include a root entrypoint phase.
- [ ] Listen on `8080` and `8443`; make PID, cache, temporary, and state paths
  explicit and compatible with a read-only root filesystem.
- [ ] Send access and error logs to stdout/stderr without symlink mutation at
  startup.
- [ ] Add a health check that does not require a shell when practical.
- [ ] Add smoke tests for image identity, process identity, static serving,
  reverse proxying, graceful shutdown, read-only root, dropped capabilities,
  `no-new-privileges`, arbitrary UID, writable-path failures, and absence of a
  package manager.

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
- [ ] Provide TLS 1.2/1.3 examples for ingress termination, upstream TLS with
  hostname and chain verification, client-certificate authentication, trust
  rotation, certificate renewal, revocation limitations, and negative cases.
- [ ] Automate CA-issued TLS rehearsal without committing certificates or
  private keys.

## Package 4: CI and supply-chain controls

- [ ] Add pre-commit checks, ShellCheck, Hadolint, Actionlint, Zizmor, YAML and
  JSON validation, private-key detection, unsafe-symlink detection, and release
  tag tests.
- [ ] Build and smoke-test on native AMD64 and ARM64 GitHub-hosted runners.
- [ ] Run Trivy configuration and image scanning with fixed High/Critical
  findings blocking.
- [ ] Generate architecture-specific SPDX SBOMs with Syft and scan them with
  Grype as an independent fixed High/Critical gate; retain the complete
  non-blocking finding inventory for review.
- [ ] Run CodeQL for GitHub Actions and OpenSSF Scorecard with SARIF published
  under minimum required permissions.
- [ ] Pin GitHub Actions to full commit SHAs and automate reviewable updates.
- [ ] Retain evidence even when a blocking scan fails, without leaking secrets
  into artifacts.

## Package 5: SCAP and cyber-review package

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
- [ ] Document vulnerability triage, patch SLAs, exceptions with expiry,
  incident response, backup/restore responsibilities, logging integration,
  monitoring, resource limits, network policy, disconnected deployment, and
  decommissioning.
- [ ] Maintain a qualification ledger keyed by commit, image digest,
  architecture, inputs, runtime/platform versions, configuration, scanner
  versions/databases, result, limitations, evidence level, and artifact.

## Package 6: signed first release

- [ ] Freeze the final upstream versions and digests only after image-affecting
  work is complete.
- [ ] Review all fixed and unfixed scanner findings against authoritative
  vendor advisories; document every time-bounded acceptance.
- [ ] Complete license and third-party notice review.
- [ ] Regenerate native architecture, rootless Podman, TLS, controlled-network,
  and tailored SCAP release-candidate evidence from the exact candidate.
- [ ] Rehearse tag validation and the entire release workflow without granting
  broader permissions than production needs.
- [ ] Publish an AMD64/ARM64 manifest to GHCR with BuildKit provenance and
  SBOM, a complete SPDX release asset, digest-bound Cosign keyless signature
  and attestation, and a GitHub Release.
- [ ] Verify published digests, platforms, labels, signatures, attestations,
  SBOMs, scan artifacts, documentation links, and rollback instructions.

## After the first release

- [ ] Define support and qualification requirements for stream TCP/UDP proxying.
- [ ] Evaluate WAF/ModSecurity without expanding the trusted computing base
  by default.
- [ ] Evaluate external authentication integrations and OIDC patterns.
- [ ] Add performance, concurrency, connection-exhaustion, and soak baselines.
- [ ] Add exact OpenShift qualification if an appropriate cluster is available.
- [ ] Revisit additional registries only when consumer demand justifies them.
