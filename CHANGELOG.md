# Changelog

All notable changes to this project are recorded in this file.

The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
but container releases use the upstream-derived format documented in
`docs/VERSION.md` rather than Semantic Versioning.

## [Unreleased]

### Added

- Added the Apache License 2.0 for Datopsis-authored work, third-party notices,
  contribution guidance, and a private vulnerability-reporting policy.
- Defined support classifications, published the current development support
  matrix and ownership boundary, and documented repository governance.
- Added Code Owners, a security-aware pull request template, and structured
  public bug-report and private security-reporting routes.
- Established repository guidance for secure, rootless image development and
  review.
- Defined the forward-looking first-release roadmap and evidence lifecycle.
- Defined independent versioning for container releases and repository-only
  revisions.
- Adopted NGINX-version, UBI-major, and UTC release-date versioning; omitted
  the UBI minor version from release tags; and prohibited mutable convenience
  tags for the first release.
- Added the project overview, intended use cases, security design, rootless
  runtime model, and release status.
- Added pinned local pre-commit checks for repository hygiene, shell code,
  container build files, GitHub Actions, private keys, and attribution trailers.
- Added least-privilege CI, CodeQL Actions, Trivy configuration, Zizmor, and
  OpenSSF Scorecard workflows with immutable third-party Action references.
- Added grouped Dependabot updates for Actions, pre-commit hooks, and the
  hash-locked CI Python environment.
- Documented local checks, GitHub automation, planned image assurance, and the
  evidence boundary of Podman Desktop or a remote Podman machine.
- Added a contributor environment record for the exercised Ubuntu WSL2 and
  rootless Podman development setup.
- Added an initial package-manager-free UBI 9 Micro development image using an
  exact Red Hat NGINX RPM build.
- Added rootless NGINX defaults for unprivileged HTTP, read-only-root operation,
  container log streams, `/tmp` runtime state, health checking, and graceful
  shutdown.
- Added a restricted-runtime smoke suite, static landing page, and hardened
  Compose development service.
- Added native PowerShell smoke testing for Podman Desktop development.
- Standardized local runtime testing on the canonical Bash suite with rootless
  Podman under native Linux or WSL2, removing the duplicated PowerShell suite.
- Preserved the complete restricted-runtime test matrix while allowing the
  Shell harness to enforce `no-new-privileges` using the syntax accepted by
  older rootless Podman development engines.
- Added a preview standalone Linux deployment runbook and rootless Podman
  Quadlet covering systemd lifecycle, journald logging, updates, rollback, and
  exact-host qualification.
- Added a component threat model, security-control ownership model, requirement
  analysis method, and cybersecurity evidence checklist.
- Expanded the first-release roadmap with deployment qualification, systemd and
  logging tests, OSCAL/control engineering, requirement-source review, FIPS
  boundary analysis, go-live evidence, and an assurance-completeness gate.
- Added GitHub topics for NGINX, containers, Podman, OpenShift, UBI 9, and
  supply-chain security.
- Extended CI with native AMD64 and ARM64 builds, restricted-runtime tests,
  Trivy image scanning, Syft SPDX inventories, blocking Grype analysis, full
  finding retention, and an aggregate image result.
- Added an initial use-case catalog covering static serving, reverse proxying,
  load balancing, TLS, WebSockets, ClickHouse, health endpoints, and limiting.
- Added a logging guide for container streams, use-case fields, sensitive-data
  rules, and controlled-network responsibilities.
- Documented the exact Red Hat UBI AppStream source and build path for the
  NGINX RPMs, including trust checks and reproducibility limits.
- Evaluated official NGINX stable RPMs as the proposed first-release package
  source and defined migration and acceptance requirements.
- Approved the official NGINX stable channel, selected
  `nginx-2:1.30.4-1.el9.ngx` for first-release implementation qualification,
  and retired the completed source-selection item from the forward roadmap.
- Added reviewed AMD64 and ARM64 artifact locks for the selected NGINX RPM,
  its complete UBI dependency closure, source RPMs, signing identities, and
  base-image digests, with fail-closed validation and lock-update tooling.
- Added atomic official and protected alternate-source acquisition for locked
  artifact bundles, including exact inventory, digest, RPM signature, signer,
  NEVRA, architecture, and lock-manifest verification without storing source
  credentials or private trust material in the repository or image build.
- Migrated the development image to the selected official NGINX 1.30.4 RPM and
  its exact architecture lock, with local-only RPM installation, installed
  inventory comparison, digest-pinned base preloading, network-disabled
  assembly, and an enforceable no-pull policy in local and native CI builds.
- Added hermetic-build rejection checks for a wrong lock identity and an
  unavailable base, and removed repository configuration from the final
  filesystem.
- Added native real-RPM negative tests for modified, unsigned, signer-mismatched,
  wrong-version, wrong-architecture, missing, and unexpected bundle content;
  bound production lock validation to the reviewed base images, NGINX seed,
  and signing-key inputs; and required filenames to agree with RPM metadata
  and official source URLs.
- Added a lock-bound accountability inventory for all 79 runtime RPMs with
  exact license and source-RPM metadata, publisher and redistribution policy,
  lifecycle boundary, and named update ownership; native CI now checks the
  recorded metadata against every acquired AMD64 and ARM64 RPM.
- Defined reviewed lock refresh, signing-key rotation and revocation, immutable
  artifact mirroring, image rollback, and disconnected-transfer procedures;
  added a schema and fail-closed transfer manifest that binds payload hashes to
  the repository revision, architecture lock, and component inventory.
- Embedded the exact verified 79-RPM manifest in the package-manager-free final
  image; added a reviewed inventory for 22 optional NGINX compile-time modules
  and features; and made native Podman plus Docker compatibility tests reject
  package, module, or NGINX build drift.
- Strengthened rootless failure and lifecycle tests to require precise mounted
  configuration and unwritable-temporary-path diagnostics, worker-replacing
  reloads with PID 1 retained, and complete active-request draining on
  `SIGQUIT` before a clean exit.
- Added qualified preview static-serving and HTTP reverse-proxy configurations
  with bounded request handling, validated correlation IDs, query-free JSON
  access events, safe forwarding-header behavior, explicit upstream failure,
  and native Podman plus Docker compatibility tests under restricted runtime
  controls on AMD64 and ARM64.
- Added qualified preview TLS 1.2/1.3 termination, mandatory mutual-TLS, and
  verified HTTPS-upstream profiles with an ephemeral CA-issued rehearsal for
  protocol bounds, hostname and chain validation, client authentication, leaf
  renewal, untrusted roots, missing keys, restricted runtime, and secret-safe
  structured logging on native Podman and Docker compatibility execution.
- Added 14 focused unit tests for structured profile logs, covering exact
  schemas, JSON escaping, type confusion, numeric bounds, timestamps,
  correlation IDs, query exclusion, TLS results, upstream timing fields,
  secret detection, and unique scenario selection.
- Enforced mounted CRLs for mutual-TLS clients and HTTPS upstreams; extended the
  ephemeral PKI rehearsal to reject revoked certificates and to prove old,
  overlapping, and new-only CA trust states without disabling chain or hostname
  verification.
- Added a public-metadata TLS lifecycle checker with stable JSON output and 12
  boundary-focused unit tests for certificate expiry, CRL freshness, timezone
  handling, exact alert thresholds, malformed output, and fail-closed OpenSSL
  inspection errors.
- Expanded logging guidance with a field-by-field explanation of `$request`,
  a sensitive ClickHouse example, and safer variable choices.
- Defined a source-independent pipeline contract that downloads and verifies
  locked artifacts outside a network-disabled container build.
- Expanded native and local runtime tests to prove non-root processes, zero
  effective capabilities, `no-new-privileges`, arbitrary-UID operation,
  read-only-root behavior, hardened temporary storage, log routing, graceful
  reload and shutdown, and actionable negative startup cases.

### Changed

- Renamed the source repository and planned GHCR image from `nginx-ubi9` to
  `nginx-ubi` so their identities do not prevent future work on other UBI major
  versions; UBI 9-specific service and development identifiers remain
  unchanged.
- Upgraded the reference contributor environment from Ubuntu 22.04.5 and
  Podman 3.4.4 to Ubuntu 24.04.5 and Podman 5.8.2, verified the restricted
  runtime and Quadlet lifecycle after a cold WSL restart, and retired the
  completed upgrade plan from the forward-looking roadmap.
- Retired the completed project-contract package from the forward-looking
  roadmap after its repository files and current support boundary were added.

### Security

- Enabled GitHub vulnerability alerts, Dependabot security updates, secret
  scanning with push protection, and private vulnerability reporting.

### Fixed

- Prevented the Docker smoke suite from failing with SIGPIPE when short-circuit
  log and response assertions run under `pipefail`.
