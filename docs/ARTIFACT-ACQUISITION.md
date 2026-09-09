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

The assembly process accepts only a bundle that conforms to the repository's
lock and verification contract. Changing a download location must not silently
change selected artifacts or weaken publisher verification.

## Artifact-source interface

This repository defines source-independent lock, acquisition, verification,
and assembly interfaces. The default source obtains locked artifacts from the
official NGINX and Red Hat UBI endpoints. An alternate approved source can be
selected through protected CI configuration without changing the artifact
identity, lock, or verification requirements.

The repository must not contain private endpoints, repository identifiers,
credentials, tokens, or private CA material. Environment-specific configuration
belongs in protected variables, secrets, or runner trust.

NGINX and Red Hat remain the RPM publishers and signing authorities even when
an intermediary transfers the files. The acquisition process must preserve the
original RPM bytes and signature so CI can verify publisher authenticity after
download. A process that modifies or re-signs packages is a different trust
model and requires its own documented approval and traceability controls.

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
- approved artifact-source identifier; and
- lock schema and artifact-bundle version.

The lock manifest is reviewable repository content. Credentials, tokens,
private CA keys, and internal secrets are not.

### 2. Acquire locked files outside the build

The CI runner downloads artifacts into an ephemeral staging directory. When a
source requires authentication, this phase uses a least-privilege read-only
identity and approved CA trust. Authentication must use the CI secret store and
must not be passed as a container build argument.

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
- ensure logs do not contain acquisition credentials or sensitive source URLs.

Checksum verification proves exact bytes; RPM signature verification proves
publisher authorization under the accepted key. Both are required. TLS to the
artifact source protects transport but does not replace either check.

### 4. Assemble without network access

The verified bundle is provided through an ephemeral build context or named
build context that is excluded from Git. The `Containerfile` copies local RPMs
into the temporary builder, installs them into `/runtime`, cleans packaging-only
content, and copies the runtime filesystem into UBI Micro.

Assembly must enforce:

- no network access;
- no image pulling;
- no repository configuration or dependency resolution;
- no artifact-source address, credential, token, or private CA material in context,
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

## Alternate-source configuration

An alternate source is supplied through protected CI configuration. Its
security boundary includes authentication secret references, approved CA
trust, permitted redirects and egress, timeout and retry policy, audit-event
retention, availability ownership, runner trust, and workspace cleanup.

A runner can reach a private source only when an approved network path exists.
Otherwise the controlled workflow needs a hardened runner within that boundary
or a separately approved artifact-transfer stage.

## Local development

Local development uses the same preparation and assembly interface. A developer
first prepares or receives a verified artifact bundle, then builds without
network access. A cached but unverified file is not accepted merely because it
is local.

The preparation tooling will provide actionable messages for missing source
configuration and will use the official public source by default. The artifact
lock, verification semantics, and network-disabled assembly remain identical
when an alternate source is deliberately selected.

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
