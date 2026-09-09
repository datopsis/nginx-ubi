# Continuous integration

The initial automation protects repository and workflow development before the
container implementation lands. Image build, runtime, SBOM, vulnerability, and
SCAP jobs will be added with the corresponding implementations so a green job
never represents a test that could not actually run.

## Current workflows

| Workflow | Triggers | Current purpose |
| --- | --- | --- |
| `CI` | Pull requests, `main`, weekly, manual | Run pinned pre-commit checks, audit Actions with Zizmor, and scan repository configuration with Trivy. |
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

After the `Containerfile` and smoke suite are implemented, the README will
publish their exercised Podman commands. Native AMD64 and ARM64 CI remains
required before an image receives supported multi-architecture status.

## Planned image assurance

The stable protected check names will be `lint` and `image`. The aggregate
`image` check will require both native architecture jobs after they exist. The
image pipeline will add, in dependency order:

1. Trivy build-configuration scanning.
2. Native architecture builds and restricted-runtime smoke tests.
3. Tailored OpenSCAP evaluation against an ownership-preserving filesystem
   export.
4. Trivy image vulnerability scanning.
5. SPDX inventory generation with Syft.
6. Independent fixed High/Critical vulnerability gating with Grype and a
   retained full finding inventory.
7. Architecture-specific artifacts and non-pull-request SARIF publication.

Branch protection must not require `image` until that aggregate check exists
on the default branch. Once present and proven, both `lint` and `image` become
strict, required, up-to-date checks.
