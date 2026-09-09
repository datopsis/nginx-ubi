# Changelog

All notable changes to this project are recorded in this file.

The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
but container releases use the upstream-derived format documented in
`docs/VERSION.md` rather than Semantic Versioning.

## [Unreleased]

### Added

- Established repository guidance for secure, rootless image development and
  review.
- Defined the forward-looking first-release roadmap and evidence lifecycle.
- Defined independent versioning for container releases and repository-only
  revisions.
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
- Added an initial package-manager-free UBI 9 Micro development image using an
  exact Red Hat NGINX RPM build.
- Added rootless NGINX defaults for unprivileged HTTP, read-only-root operation,
  container log streams, `/tmp` runtime state, health checking, and graceful
  shutdown.
- Added a restricted-runtime smoke suite, static landing page, and hardened
  Compose development service.
- Added native PowerShell smoke testing for Podman Desktop development.
- Extended CI with native AMD64 and ARM64 builds, restricted-runtime tests,
  Trivy image scanning, Syft SPDX inventories, blocking Grype analysis, full
  finding retention, and an aggregate image result.
- Added an initial use-case catalog covering static serving, reverse proxying,
  load balancing, TLS, WebSockets, ClickHouse, health endpoints, and limiting.
- Added a logging guide for container streams, use-case fields, sensitive-data
  rules, and controlled-network responsibilities.
- Documented the exact Red Hat UBI AppStream source and build path for the
  NGINX RPMs, including trust checks and reproducibility limits.
