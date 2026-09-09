# CLAUDE.md

This file provides guidance to coding agents working in this repository.

## Project overview

This repository builds a security-oriented, rootless NGINX container on Red
Hat UBI 9. The intended uses include static web serving, TLS termination,
reverse proxying, HTTP load balancing, WebSocket proxying, rate limiting, and
controlled-network deployments.

Preserve these non-negotiable properties:

- the final image is based on a digest-pinned Red Hat UBI 9 image;
- the final runtime has no package manager;
- NGINX starts and remains non-root, with no entrypoint privilege transition;
- the default listeners use unprivileged ports;
- the image supports a read-only root filesystem with explicit writable
  `tmpfs` or volume mounts;
- the runtime needs no Linux capabilities and enables `no-new-privileges` in
  documented deployments;
- configuration, certificates, private keys, and trust stores can be mounted
  read-only;
- third-party downloads and build inputs are pinned and verified;
- CI produces reviewable vulnerability, SBOM, and tailored SCAP evidence;
- release images are multi-architecture, immutable, attested, and signed;
- documentation does not claim FIPS validation, STIG certification, or broad
  platform support without matching qualification evidence.

The first release boundary and ordered work packages are defined in
`docs/ROADMAP.md`. Version rules are defined in `docs/VERSION.md`.

## Development and verification

Use Podman for the primary local workflow where it is available. Docker
compatibility is tested independently and is not evidence of identical Podman
or OpenShift behavior.

The canonical build, smoke-test, lint, scan, and release commands will be
added to `README.md` as their implementations land. Do not document an
untested command as supported.

For image-affecting work, verification must cover at least:

- the configured runtime identity is non-root;
- the running processes remain non-root;
- startup succeeds with a read-only root filesystem and only the documented
  writable paths;
- startup succeeds with all capabilities dropped and
  `no-new-privileges` enabled;
- static serving and reverse proxying work;
- invalid or unwritable configuration fails with a useful diagnostic;
- TLS keys are not copied into the image or exposed in logs;
- both supported architectures receive native-runtime evidence before a
  supported release.

Generated SBOM, SARIF, SCAP result, certificate, private-key, and scanner-cache
files must not be committed. Retain release evidence in CI, the OCI registry,
or GitHub Releases as defined by the roadmap.

## Security and documentation conventions

Treat examples as deployable security guidance. Examples must not contain
default passwords, embedded private keys, permissive catch-all trust, disabled
certificate verification, world-writable application directories, or a root
runtime.

Keep product behavior separate from deployment responsibility. Clearly state
which controls belong to the image, the container runtime, the orchestrator,
the host, the network boundary, and the operator.

SCAP results describe only the selected rules, content version, scanner
version, target filesystem, architecture, and configuration that were
evaluated. Never translate a passing tailored scan into a claim that the image
or deployment is STIG certified.

When adding a use case, add or update its automated test, example
configuration, operational guidance, security considerations, and support
classification together.

## Git conventions

Keep changes small and reviewable. Prefer one dependency-ordered roadmap
increment per pull request. Start work from current `main`, require protected
checks before merge, and do not force-push or move release tags.

Use concise Conventional Commit subjects such as `feat:`, `fix:`, `docs:`,
`test:`, `ci:`, `build:`, `refactor:`, and `chore:`.

Do not add `Co-Authored-By`, AI, assistant, or tool-attribution trailers to
commit messages. Commits are the human-reviewed record of intent; tool
attribution belongs in tool logs.

Container release tags and repository revisions are intentionally distinct.
Do not create a source-only release or tag for documentation, test, policy,
development-tool, or analysis-workflow changes. Follow `docs/VERSION.md`.
