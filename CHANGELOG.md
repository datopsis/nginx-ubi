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
- Adopted NGINX-version plus UTC release-date versioning, removed the UBI minor
  version from release tags, and prohibited mutable convenience tags for the
  first release.
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
- Expanded logging guidance with a field-by-field explanation of `$request`,
  a sensitive ClickHouse example, and safer variable choices.
- Defined a source-independent pipeline contract that downloads and verifies
  locked artifacts outside a network-disabled container build.
- Expanded native and local runtime tests to prove non-root processes, zero
  effective capabilities, `no-new-privileges`, arbitrary-UID operation,
  read-only-root behavior, hardened temporary storage, log routing, graceful
  reload and shutdown, and actionable negative startup cases.

### Changed

- Renamed the source repository from `nginx-ubi9` to `nginx-ubi` so repository
  identity does not prevent future work on other UBI major versions; existing
  image, service, and UBI 9 identifiers remain unchanged.
- Upgraded the reference contributor environment from Ubuntu 22.04.5 and
  Podman 3.4.4 to Ubuntu 24.04.5 and Podman 5.8.2, verified the restricted
  runtime and Quadlet lifecycle after a cold WSL restart, and retired the
  completed upgrade plan from the forward-looking roadmap.
- Retired the completed project-contract package from the forward-looking
  roadmap after its repository files and current support boundary were added.

### Security

- Enabled GitHub vulnerability alerts, Dependabot security updates, secret
  scanning with push protection, and private vulnerability reporting.
