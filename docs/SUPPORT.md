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
| Static HTTP profile | Preview/unqualified | Native AMD64/ARM64 Podman and Docker compatibility tests exist; exact host and release evidence remain incomplete. |
| HTTP reverse-proxy profile | Preview/unqualified | Restricted-runtime, safe-header, logging, and upstream-failure tests exist; HTTPS upstreams and platform controls are outside this profile. |
| HTTP load-balancing profile | Preview/unqualified | Distribution, passive failure handling, bounded retries, and failover logging are tested on native AMD64/ARM64 Podman and Docker compatibility; capacity, latency, draining, and affinity are not qualified. |
| WebSocket proxying profile | Preview/unqualified | Upgrade forwarding, derived connection disposition, `101` relay, and unaffected plain HTTP are tested; frame exchange, session duration, and concurrent session capacity are not. |
| Request and connection limiting profile | Preview/unqualified | Rate rejection, connection rejection, bandwidth pacing, and unlimited health checks are tested; workload tuning, zone sizing, and exhausted-zone behaviour are not. |
| Health and readiness profile | Preview/unqualified | Upstream-independent liveness, upstream-reflecting readiness, failure-only probe logging, and a default-deny status surface are tested; probe tuning, startup probes, and an allow-listed status surface are not. |
| TLS termination and mTLS profiles | Preview/unqualified | TLS 1.2/1.3, client authentication, leaf renewal, CRL enforcement, and negative cases are tested; production PKI operations and exact-host cryptographic policy remain unqualified. |
| Verified HTTPS upstream profile | Preview/unqualified | Chain, hostname, SNI, revocation, overlapping-CA rotation, and restricted-runtime behavior are tested; deployment DNS, egress, and PKI remain operator-owned. |
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
