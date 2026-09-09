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

## Planned external acquisition

The current development build resolves RPMs from inside the builder stage. It
does not yet meet the first-release artifact-acquisition contract.

The replacement pipeline will separate a reviewed lock update from ordinary
CI. Normal jobs will download only the exact architecture-specific files in
the merged lock, verify their checksums, RPM signatures, signing fingerprints,
NEVRA, architecture, and bundle completeness, and preload digest-verified base
images. The image will then assemble from that local bundle with networking and
pulling disabled.

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
2. Native architecture builds and restricted-runtime scenario tests covering
   the declared and arbitrary runtime identities, process privileges, a
   read-only root, hardened temporary storage, static content, health behavior,
   log streams, reload and shutdown, and actionable startup failures.
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
