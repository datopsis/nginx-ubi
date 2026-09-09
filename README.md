# NGINX on Red Hat UBI 9

`nginx-ubi9` builds a security-oriented, rootless NGINX container for static
web serving, TLS termination, reverse proxying, and HTTP load balancing. The
project is designed for Podman, Docker-compatible runtimes, OpenShift-style
arbitrary user IDs, and controlled networks that require inspectable security
evidence.

> [!IMPORTANT]
> The project is under initial development. No supported container image has
> been released. Commands, tags, and security claims will be published only
> after their implementations are tested and the applicable roadmap gates are
> complete.

## Intended uses

The first release is being designed for:

- serving static websites and application assets;
- reverse proxying HTTP and HTTPS applications;
- terminating ingress TLS with operator-managed keys and certificates;
- verifying TLS connections to upstream services;
- balancing traffic across HTTP upstreams;
- proxying WebSocket connections;
- exposing health and readiness endpoints;
- applying request-rate and connection limits; and
- providing a hardened HTTP gateway to ClickHouse and similar services.

Forward proxying, a web application firewall, ModSecurity, OIDC, third-party
NGINX modules, mail proxying, and broad TCP/UDP stream proxying are not in the
first-release boundary. They may be evaluated later without expanding the
default image's trusted computing base.

## Security design

The planned image contract requires:

- a digest-pinned Red Hat UBI 9 base and verified build inputs;
- a package-manager-free UBI 9 Micro final image;
- a non-root NGINX process with no privileged entrypoint phase;
- unprivileged listeners on ports `8080` and `8443`;
- compatibility with an arbitrary non-root UID in group `0`;
- operation with a read-only root filesystem and explicit writable mounts;
- all Linux capabilities dropped and `no-new-privileges` enabled;
- configuration, private keys, certificates, and trust stores mounted
  read-only;
- access and error logs written to the container log streams;
- native AMD64 and ARM64 runtime testing;
- vulnerability scanning with Trivy and Grype;
- SPDX software bills of materials generated with Syft;
- tailored OpenSCAP evidence with documented rule selection and exclusions;
- BuildKit provenance and SBOM attestations; and
- digest-bound, keyless Cosign signatures for releases.

These properties do not make the image, host, orchestrator, network, or
application automatically secure. Deployment controls, secrets, network
policy, resource limits, monitoring, patching, and risk acceptance remain
shared responsibilities and will be identified explicitly in the security
documentation.

The project will not claim FIPS validation, STIG certification, OpenShift
support, or compliance with an entire control framework without evidence that
matches the exact claim and assessed boundary.

## Rootless runtime model

NGINX will start directly as a non-root identity and will not attempt to repair
volume ownership with `chown`. Operators must provision writable runtime paths
for the selected container identity or platform-assigned arbitrary UID.

The image will use high ports and place PID, cache, and temporary files only in
documented writable locations. Supported run examples will use a read-only
root filesystem, explicit `tmpfs` mounts, dropped capabilities, and
`no-new-privileges` after those combinations are exercised by automated tests.

## Project documentation

- [First-release roadmap](docs/ROADMAP.md) defines outstanding work and release
  gates. It is forward-looking; completed work belongs in the changelog and
  Git history.
- [Versioning and releases](docs/VERSION.md) separates container artifact
  versions from repository-only revisions.
- [Changelog](CHANGELOG.md) records notable completed changes.
- [Agent guidance](CLAUDE.md) defines repository implementation and security
  conventions.
- [Continuous integration](docs/CI.md) documents current automation, local
  pre-commit checks, and the planned image assurance pipeline.

Operational, TLS, configuration, architecture, threat-model, control-matrix,
SCAP, vulnerability-management, support, and disconnected-network guides will
be added as their associated implementations and evidence are developed.

## Images and releases

The planned image location is:

```text
ghcr.io/datopsis/nginx-ubi9
```

Container releases will use annotated tags in this form:

```text
v<nginx-version>-ubi<ubi-version>-<packaging-revision>
```

Image releases and repository revisions are deliberately separate. Production
deployments should pin an immutable OCI digest. Repository-only changes are
identified by their full Git commit SHA and do not receive source-only release
tags.

## Development status

The current work is governed by the dependency-ordered roadmap. Build and test
commands will be added here only when they exist and have been exercised.
Repository checks can be run now with:

```console
python -m pip install --require-hashes --only-binary=:all: \
  --requirement .github/requirements/pre-commit.txt
pre-commit run --all-files --show-diff-on-failure
```

See the [continuous integration guide](docs/CI.md) for hook installation and
Podman evidence boundaries. Until the first signed release is published, this
repository should be treated as development material rather than a supported
production image.

Security concerns should not be disclosed in a public issue. A private
reporting process and supported-version policy will be published in
`SECURITY.md` during the project-contract work package.
