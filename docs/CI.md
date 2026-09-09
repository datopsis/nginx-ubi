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

Podman is the primary local container workflow. Before relying on a result,
record both client and engine details:

```console
podman version
podman info
```

Podman Desktop or a remote Podman machine can run a container process as a
non-root UID while its Linux VM engine itself operates rootfully. That proves
the image's non-root process behavior but does not qualify rootless-host user
namespace behavior. Release evidence will distinguish these cases.

The README contains the exercised Podman build and smoke commands. The local
PowerShell suite is suitable for Podman Desktop on Windows; the Bash suite is
used on Linux CI. Native AMD64 and ARM64 CI remains required before an image
receives supported multi-architecture status.

## Image assurance

The stable protected check names are `lint`, `configuration security`, and
`image`. The aggregate `image` check requires both native architecture jobs.
The implemented image pipeline performs:

1. Trivy build-configuration scanning.
2. Native architecture builds and restricted-runtime smoke tests.
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
