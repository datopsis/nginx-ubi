# External artifact acquisition

Status: required design for the first release; the current `Containerfile`
still resolves RPMs during the builder stage and must be migrated.

## Build contract

The container build must not download packages, keys, repository metadata, or
other files. CI or a local preparation tool acquires and verifies every input
before starting the build. The build then runs with network access disabled
and consumes only local, immutable inputs.

This separates three concerns:

1. **Acquisition** authenticates to an approved repository and downloads
   inputs.
2. **Verification** proves publisher identity and exact content before an
   input is admitted to the build context.
3. **Assembly** creates the image without network access, repository
   credentials, or mutable dependency resolution.

The same assembly process should accept a bundle prepared from the public
official source during open development or from an approved Nexus repository
inside a controlled work network. Changing the transfer location must not
silently change the selected artifacts.

## Repository process versus work-network process

This public repository defines provider-independent lock, acquisition,
verification, and assembly interfaces. Its default public adapter obtains
locked artifacts from the official NGINX and Red Hat UBI sources. It does not
contain an organization's Nexus address, repository name, credential, or
private CA.

This repository will contain a generic Nexus adapter with no configured
endpoint. The work-network adaptation supplies its protected CI configuration.
The adapter maps each locked publisher artifact to the approved Nexus location
but does not change the artifact identity or relax verification. A controlled
overlay or fork may hold additional policy when even repository names are
sensitive.

| Concern | Public repository | Work-network adaptation |
| --- | --- | --- |
| Artifact selection | Reviewed architecture-specific lock manifest. | The same reviewed lock manifest or an internally reviewed derivative. |
| Download endpoint | Official NGINX and Red Hat endpoints. | Approved Nexus repositories. |
| Authentication | None for public artifacts. | Read-only CI secret and internal CA trust. |
| Publisher verification | NGINX or Red Hat RPM signature plus locked checksum. | Preserve and verify the same publisher signature and checksum unless an approved internal re-signing policy replaces it. |
| Container assembly | Local bundle, no network, no pulling. | Identical. |
| Internal information | None. | Kept in protected variables, secrets, runner trust, or a controlled overlay. |

## Publisher versus transfer location

For the proposed package change, NGINX is the RPM publisher and signing
authority. Nexus is the controlled storage and transfer point. The work-network
pipeline should preserve the original RPM bytes and NGINX signature so CI can
verify publisher authenticity after download.

If organizational policy requires Nexus or an internal authority to re-sign
packages, that becomes a different trust model. The internal signing key,
approval process, traceability to the original NGINX artifact, and key rotation
must then be documented and verified separately.

## Pipeline phases

### 1. Update locked inputs deliberately

Dependency resolution is an update activity, not part of every CI build. A
dedicated lock-update workflow or maintainer command queries approved
repositories, calculates the complete closure, and proposes a lock-file change
for review. Its pull request receives normal image tests and security review.

An ordinary pull-request, `main`, or release build never selects "latest" and
never recalculates the dependency closure. It downloads only entries already
present in the merged lock.

An architecture-specific lock manifest will identify:

- each base-image registry, repository, tag, and expected manifest digest;
- NGINX channel, RPM name, epoch, version, release, and architecture;
- every RPM in the resolved runtime dependency closure;
- expected byte size and SHA-256 digest for every downloaded file;
- expected RPM signing identity and full key fingerprint;
- source RPM location and digest;
- approved Nexus repository identifier or public acquisition adapter; and
- lock schema and artifact-bundle version.

The lock manifest is reviewable repository content. Credentials, tokens,
private CA keys, and internal secrets are not.

### 2. Acquire locked files outside the build

The CI runner downloads artifacts into an ephemeral staging directory. In the
work network, this phase connects to Nexus using a least-privilege read-only
identity and the organization's approved CA trust. Authentication must use the
CI secret store and must not be passed as a container build argument.

Native AMD64 and ARM64 jobs acquire only their matching RPM set. Repository
resolution does not occur here or in `RUN` instructions; it occurred in the
reviewed lock update. Unexpected files, missing locked files, redirects to
unapproved hosts, or changes to locked content fail the job.

Base images are also pulled before assembly and checked against their expected
manifest digests. The build uses the already-present local image and disables
pulling.

### 3. Verify outside the build

Before the artifact bundle is exposed to the build:

- compare every file with its locked SHA-256 digest and expected size;
- verify every RPM signature against the approved full signing fingerprint;
- verify that RPM NEVRA and architecture match the lock;
- reject unsigned, expired-policy, wrong-architecture, duplicate, and
  additional RPMs;
- confirm the base-image manifest digest and platform;
- retain sanitized acquisition and verification results; and
- ensure logs do not contain Nexus credentials or sensitive internal URLs.

Checksum verification proves exact bytes; RPM signature verification proves
publisher authorization under the accepted key. Both are required. TLS to
Nexus protects transport but does not replace either check.

### 4. Assemble without network access

The verified bundle is provided through an ephemeral build context or named
build context that is excluded from Git. The `Containerfile` copies local RPMs
into the temporary builder, installs them into `/runtime`, cleans packaging-only
content, and copies the runtime filesystem into UBI Micro.

Assembly must enforce:

- no network access;
- no image pulling;
- no repository configuration or dependency resolution;
- no Nexus address, credential, token, or private CA material in context,
  layers, labels, history, SBOM, or provenance; and
- failure when the complete verified bundle is not present.

The build may validate the shape of its local input for defensive diagnostics,
but publisher and download verification remain CI preparation responsibilities.

### 5. Prove hermetic behavior

CI will run an assembly with network disabled and inspect image history and
content for forbidden repository material. The resulting image then receives
the normal rootless runtime tests, SBOM generation, vulnerability scans, and
architecture checks.

The acquisition result, lock manifest digest, base-image digest, image digest,
SBOM, scanner inputs, and workflow revision form one evidence chain. A change
to any locked artifact invalidates prior release-candidate evidence.

## Nexus integration contract

The public repository must not embed organization-specific Nexus endpoints or
credentials. The work-network configuration will supply, through protected CI
configuration:

- Nexus base URL and repository identifier;
- authentication secret references;
- approved CA certificate location or runner trust configuration;
- permitted redirect and egress policy;
- timeout and retry policy;
- audit-event and retention requirements; and
- availability and break-glass ownership.

A GitHub-hosted runner can use private Nexus only when an approved network path
exists. Otherwise the controlled workflow needs a hardened self-hosted runner
or a separately approved artifact-transfer stage. Runner trust and cleanup are
part of the assessed boundary.

## Local development

Local development uses the same preparation and assembly interface. A developer
first prepares or receives a verified artifact bundle, then builds without
network access. A cached but unverified file is not accepted merely because it
is local.

The preparation tooling will provide actionable messages for a missing Nexus
configuration and will support a deliberately selected public-source adapter
for this open repository. The artifact lock, verification semantics, and
network-disabled assembly remain identical between adapters.

Local preparation consumes an existing lock by default. Refreshing a lock is a
separate explicit command so an ordinary local build cannot silently upgrade a
dependency.

## Required tests

The implementation is incomplete until automated tests demonstrate rejection
of:

- a modified RPM;
- an RPM signed by an unapproved key;
- the wrong NEVRA or architecture;
- an extra or missing dependency RPM;
- a base image with the wrong digest;
- any attempted network access during assembly; and
- repository credentials or trust material found in the image or its history.
