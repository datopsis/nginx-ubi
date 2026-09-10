# Support definitions and current boundary

No supported container image has been released. Everything currently in this
repository is development material unless an immutable release and its evidence
explicitly state otherwise.

## Definitions

- **Supported** means an exact immutable image digest, architecture,
  configuration profile, host/runtime combination, and support period passed
  the documented release gates and is named by a published support statement.
- **Compatible** means limited tests demonstrated a behavior, but the project
  makes no production-support or security-maintenance commitment for that
  combination.
- **Preview/unqualified** means the material is available for evaluation while
  required tests, operational guidance, or review remain incomplete.
- **Unsupported** means the project does not intend to qualify or maintain the
  behavior within the stated release boundary.

Absence from a matrix means unqualified, not implicitly compatible.

## Current matrix

| Area | Current classification | Evidence or limitation |
| --- | --- | --- |
| Published images | Unsupported | No release has been published. |
| Repository development image | Preview/unqualified | Rootless smoke tests exist; release inputs and evidence are not frozen. |
| Linux AMD64 and ARM64 | Preview/unqualified | Native CI exists; release-candidate evidence is not complete. |
| Ubuntu WSL2 | Compatible for contributor development | The recorded environment passes build, smoke, and Quadlet tests but is not a deployment target. |
| Standalone RHEL/Podman | Preview/unqualified | Exact SELinux-enforcing host qualification remains future work. |
| OpenShift | Preview/unqualified | Restricted-SCC and exact-release qualification remain future work. |
| Docker | Compatible for CI behavior | Docker evidence does not establish rootless Podman equivalence. |

## Ownership boundary

The image project owns verified build inputs, image userspace, the non-root
default, documented ports and writable paths, default NGINX configuration,
tests, SBOM/provenance/signature production, and image vulnerability response.

The host or orchestrator owns the kernel, container runtime, cgroups,
namespaces, seccomp and SELinux/AppArmor enforcement, networking, firewall and
ingress, secrets, certificates and trust, persistent storage, resource policy,
logging retention, monitoring, backup, and incident response. Operators own
their NGINX configuration, upstreams, DNS, exposure, TLS choices, and update
approval. See [Security controls](SECURITY-CONTROLS.md) for the detailed split.

Successful scanning, use of UBI, or a passing tailored SCAP result does not
make this community image Red Hat supported, FIPS validated, STIG certified,
or broadly compliant.
