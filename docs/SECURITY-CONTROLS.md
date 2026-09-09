# Security controls and cyber-review evidence

This repository supplies component-level implementation descriptions and
evidence. It cannot produce a completed system Security Control Traceability
Matrix (SCTM), System Security Plan, risk acceptance, or authorization because
those depend on the deployed boundary, baseline, overlays, organization-defined
parameters, inherited services, data impact, and assessor decisions.

The planned machine-readable deliverable is a NIST OSCAL Component Definition
with deterministic CSV and human-readable views. It will describe how the image
can support a control objective and how to examine and test it; it will not claim
that a deployed system is authorized.

## Ownership model

| Owner | Examples of responsibility |
| --- | --- |
| Image project | Verified inputs, minimal package-manager-free filesystem, non-root default, safe baseline configuration, documented writable paths and log streams, SBOM/provenance/signature, native tests, vulnerability response, and image-owned SCAP rules. |
| Deployment profile | Digest pinning, mounted configuration/content/trust/secrets, TLS mode, published ports, upstream and DNS policy, capabilities, resource limits, probes, reload/rollback, and workload-specific tests. |
| Host or orchestrator | Kernel/runtime patching, namespaces, cgroups, seccomp, SELinux, firewall/NetworkPolicy, node identity, time, journal/collector, secret service, admission policy, availability, and node monitoring. |
| Organization/system | Control baseline and parameters, data classification, identities and separation of duties, central PKI/logging/SIEM, incident response, continuous monitoring, exceptions, evidence retention, physical controls, and authorization. |

A control can be shared by more than one owner. Every matrix row must state the
part this component implements, what must be configured, what is inherited, and
what remains for the system owner.

## Initial control families

| Control objective | Image contribution | Deployment/host contribution | Verification evidence |
| --- | --- | --- | --- |
| Software integrity and provenance | Pinned inputs, external verification contract, package inventory, SBOM, provenance, digest signature. | Verify at acquisition and admission; protect registry/transfer; retain approved digest mapping. | Locks, verification logs, attestations, signature result, image digest. |
| Least privilege and isolation | UID `999:0`, high ports, no privileged entrypoint, no package manager in final image. | Rootless runtime, dedicated account, drop all capabilities, no new privileges, seccomp, SELinux, read-only root, narrow mounts. | Image config, `/proc` status, mount/capability inspection, SELinux/runtime record, negative writes. |
| Secure configuration and change control | Reviewed baseline and tested examples; configuration test and reload interface. | Approve and hash mounted files; protect writers; stage, validate, reload, monitor, and roll back. | Configuration digest/review, `nginx -t`, functional/negative tests, change ticket and rollback result. |
| Identification, authentication, and authorization | Does not invent application identity; can enforce mTLS in a qualified profile. | Application identity, trusted proxy chain, PKI, secret store, administrator RBAC, and break-glass controls. | Architecture/data-flow review, identity configuration, certificate tests, access review. |
| Communications protection | Planned TLS 1.2/1.3 ingress and verified upstream examples. | Certificates/keys/trust, renewal, revocation decision, firewall and egress policy, approved termination boundary. | TLS scans and negative tests, key permissions, expiry/rotation evidence, network rules. |
| Audit and accountability | Access/error streams, reviewed structured fields, health-log suppression, sensitive-data rules. | Journald/collector/SIEM, time sync, access, forwarding, capacity, retention, alerting, integrity protection, disposal. | Sample events, schema/config digest, journal/collector settings, failure and access tests. |
| Vulnerability and flaw remediation | Scheduled independent scans, full inventory, advisory triage, rebuild and exception policy. | Host/platform scanning, deployment exposure analysis, promotion cadence, patch window, incident process. | Scanner/tool/database metadata, vendor advisory analysis, owner/expiry, rebuilt digest. |
| Resource protection and availability | Small image, bounded writable-path contract, health metadata, graceful stop signal. | CPU/memory/PID/file/tmpfs/connection limits, external rate and DDoS controls, redundancy, capacity and failure tests. | Runtime limits, load/soak results, restart/health/shutdown tests, alerts. |
| System and information integrity | Immutable image and configuration validation; server-version suppression. | Admission by digest/signature, file/change monitoring, network detection, incident containment and recovery. | Admission result, runtime drift/config review, alert and incident exercises. |
| Media, transfer, and controlled networks | Source-independent verified artifact bundle and offline-capable assembly design. | Approved transfer, malware inspection, hash verification at both boundaries, internal registry/trust, offline data refresh. | Transfer record, hashes/digests, internal mapping, disconnected rehearsal. |
| Assessment and continuous monitoring | Evidence lifecycle, native architecture jobs, qualification ledger, tailored SCAP plan. | Select baseline/depth, assess inherited controls, review changes and evidence, approve residual risks. | Component matrix/OSCAL, qualification record, assessment procedure and findings. |

## Requirement analysis method

The system's selected NIST SP 800-53 Rev. 5 baseline, overlays, and parameters
define the actual requirements. NIST SP 800-53A supplies assessment structure.
Where the deployment is subject to DISA guidance, review the current Container
Platform SRG and RHEL 9 STIG for objectives genuinely owned by the image or
host. A web-server or application-server SRG may inform NGINX behavior only
after applicability is analyzed. Product-specific fixes must never be copied
as if they automatically apply.

For every authoritative source, record publisher, title, release/version,
release date, retrieval date, URL, SHA-256, status, and license. Compare every
in-scope requirement and assign one disposition:

- adopted as an image implementation;
- supported through deployment configuration;
- inherited from host/platform/organization;
- not applicable with rationale;
- unsupported with documented consequence; or
- research required before a claim is made.

Every adopted or supported row needs stable source identifiers and wording,
implementation detail, defaults, enable/disable and restart behavior,
dependencies, operational impact, loss of function, owner, limitations,
residual risk, and an assessment procedure with examine, test, and—where
needed—interview steps. Source interpretation and mapping require independent
review before first release.

## Evidence quality and lifecycle

Evidence progresses from development to integration to release candidate. The
release-candidate record binds the exact commit and image digest to architecture,
base and RPM inputs, configuration profile/digest, host/runtime/platform,
scanner/tool/database versions, result, limitations, reviewer, artifact
location, and retention. Image-affecting or assessment-method changes invalidate
the affected candidate evidence but never erase historical records.

Automated tests are strongest for deterministic component behavior. They do not
replace examination of architecture and procedures or interviews about actual
operations. A passing control matrix row must not be inferred from a green job
whose scope does not match the requirement.

## Required cyber-review deliverables

Before first release, publish or retain as appropriate:

- system-context, runtime-data-flow, trust-boundary, TLS-flow, assurance-pipeline,
  controlled-network, and control-ownership diagrams;
- the [threat model](THREAT-MODEL.md) and reviewed residual-risk register;
- OSCAL Component Definition, generated component matrix, source-comparison
  register, schema validation, and traceability/change checks;
- support matrix and qualification ledger for exact architectures, hosts,
  runtimes, platforms, configuration profiles, TLS modes, and evidence levels;
- image digest, SBOM, provenance, signature, licensing/notices, module and RPM
  inventory, tailored SCAP, vulnerability and exception evidence;
- deployment runbook and exact runtime configuration, logging, monitoring,
  incident, update, rollback, controlled-network, and decommission procedures;
  and
- a limitation statement distinguishing component evidence from system-level
  compliance, accreditation, certification, and authorization.

See [Deployment](DEPLOYMENT.md) for the standalone-host evidence checklist and
[Roadmap](ROADMAP.md) for the forward-looking implementation gates.

## SCAP and FIPS boundaries

An unmodified RHEL host profile is not an image release gate. Kernel, boot,
partition, systemd, audit-daemon, host-network, SELinux-enforcement, and host
crypto-policy checks are normally host owned. The project will select only
reviewed image-filesystem rules, preserve numeric ownership during offline
inspection, separate operational scanner errors from findings, and publish all
selection/exclusion rationales. Passing those rules is not STIG certification.

TLS protocol configuration is not a FIPS claim. FIPS status depends on the
host mode, exact cryptographic modules and validations, NGINX linkage and code
paths, certificate algorithms, and complete deployed boundary. The first
release will state that boundary and evidence gaps rather than infer validation
from UBI 9 or TLS 1.2/1.3.

## Authoritative references

- [NIST OSCAL Component Definition model](https://pages.nist.gov/OSCAL/learn/concepts/layer/implementation/component-definition/)
- [NIST SP 800-53 Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final)
- [NIST SP 800-53A Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/a/r5/final)
- [DISA STIG document library](https://public.cyber.mil/stigs/downloads/)
