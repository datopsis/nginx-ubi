# Continuous integration

The automation protects repository, workflow, and container development. A
green job represents only checks that have an implemented target and an
inspectable result; planned controls are not represented as passing jobs.

## Current workflows

| Workflow | Triggers | Current purpose |
| --- | --- | --- |
| `CI` | Pull requests, `main`, weekly, manual | Run pinned repository checks, audit Actions, scan configuration, and build, test, inventory, and scan native AMD64 and ARM64 images. |
| `CodeQL` | Workflow changes, `main`, weekly, manual | Analyze GitHub Actions with the security-extended query suite. |
| `OpenSSF Scorecard` | `main`, branch-protection changes, weekly, manual | Publish repository supply-chain findings and SARIF. |

Workflow permissions default to read-only. A job receives a write scope only
when it must publish code-scanning results. The Scorecard job also receives an
OIDC token for authenticated result publication. Third-party Actions are pinned
to full commit SHAs and are tracked by Dependabot.

## Local repository checks

Install the hash-locked pre-commit environment with Python 3.13 or a compatible
Python version:

```console
python -m pip install --require-hashes --only-binary=:all: \
  --requirement .github/requirements/pre-commit.txt
pre-commit install --install-hooks
pre-commit run --all-files --show-diff-on-failure
```

The configured hooks check text normalization, YAML and JSON syntax, merge
markers, unsafe or broken symlinks, oversized files, private keys, shell code,
container build files, GitHub Actions, and prohibited co-author trailers.
The lint job also runs
`python -m unittest tests.test_artifacts tests.test_components
tests.test_nginx_features tests.test_transfer -v` to validate the reviewed
lock inputs, both architecture locks, the lock-bound 79-package component
accountability inventory, the NGINX compile-feature inventory,
disconnected-transfer integrity, and fail-closed negative cases without
downloading artifacts.

The `commit-msg` hook applies only after `pre-commit install` installs the
configured hook types. CI separately evaluates repository files but cannot
retroactively validate a local commit message that was never pushed.

## Local Podman development

Rootless Podman under native Linux or WSL2 is the primary local container
workflow. Before relying on a result, record both client and engine details:

```console
podman version
podman info
```

Podman Desktop or a remote Podman machine can run a container process as a
non-root UID while its Linux VM engine itself operates rootfully. That proves
the image's non-root process behavior but does not qualify rootless-host user
namespace behavior. Release evidence will distinguish these cases.

Use Podman inside WSL2 or on native Linux for local rootless-host evidence.
The Bash harness retains compatibility with older development engines where
safe, but compatibility does not make an engine part of the production support
boundary. Quadlet deployment requires Podman 4.6 or newer, and first-release
qualification will record a newer exact vendor-supported baseline.

The README contains the exercised Podman build and smoke commands. Bash is the
single canonical smoke implementation for local Podman and Linux CI, avoiding
behavioral drift between platform-specific suites. Native AMD64 and ARM64 CI
remains required before an image receives supported multi-architecture status.

## External acquisition

Reviewed AMD64 and ARM64 locks, explicit update tooling, and official and
alternate-source acquisition paths are in the repository. The acquisition and
verification tools check exact inventory, size, SHA-256, lock identity, RPM
signatures, approved signing fingerprints, NEVRA, architecture, and source-RPM
identity before a bundle is exposed to assembly. Unit tests cover atomic
publication and fail-closed inventory and source-map behavior without
downloading artifacts.

Native image jobs acquire and verify their matching bundle, preload the exact
digest-pinned UBI bases, and build with Podman using `--network none` and
`--pull=never`. They also prove that the build rejects a wrong lock identity
and cannot fetch an unavailable base. Before assembly, isolated copies of the
real bundle prove rejection of tampering, signature removal, signer mismatch,
wrong version, wrong architecture, missing RPMs, and additional RPMs. The
jobs also compare every RPM's publisher-supplied license tag, source RPM, and
vendor header with `artifacts/components.json`. The completed image is
transferred by local archive into Docker solely for the existing compatibility
smoke and scanner steps; that transfer performs no image build or registry
pull.

The official public source is the default. An alternate approved source can be
selected through protected CI configuration, but private endpoints,
credentials, and private CA configuration must not enter this repository or
the container build. Verification remains identical after either source
downloads the artifacts. See
[External artifact acquisition](ARTIFACT-ACQUISITION.md).

## Image assurance

The stable protected check names are `lint`, `configuration security`, and
`image`. The aggregate `image` check requires both native architecture jobs.
The implemented image pipeline performs:

1. Trivy build-configuration scanning.
2. Verified, network-disabled, no-pull native architecture builds followed by
   native Podman and Docker-compatibility restricted-runtime tests. They cover
   the exact 79-RPM manifest, NGINX compile-feature and empty dynamic-module
   inventories, declared and arbitrary runtime identities, process privileges,
   a read-only root, hardened temporary storage, static content, health and log
   behavior, worker-replacing reload, active-request graceful shutdown, and
   actionable startup failures.
3. Trivy image vulnerability scanning.
4. SPDX inventory generation with Syft.
5. Independent fixed High/Critical vulnerability gating with Grype and a
   retained full finding inventory.
6. Architecture-specific artifacts and non-pull-request SARIF publication.

Tailored OpenSCAP evaluation against an ownership-preserving filesystem export
will be inserted after the runtime tests when its profile and result semantics
are reviewed. Branch protection must not require `image` until its aggregate
check exists on the default branch. Once present and proven, `image` becomes a
strict, required, up-to-date check alongside the current repository checks.
