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
