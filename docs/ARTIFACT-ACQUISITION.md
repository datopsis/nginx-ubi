# External artifact acquisition

Status: reviewed architecture locks, lock-update tooling, and verified
official and alternate-source acquisition are implemented. The `Containerfile`
still resolves RPMs during the builder stage and must be migrated to consume
the verified bundle.

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

Each architecture-specific lock manifest identifies:

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

### Implemented lock set

The reviewed lock inputs are in `artifacts/lock-inputs.json`; the JSON schema
is `artifacts/artifact-lock.schema.json`; and the rendered locks are
`artifacts/locks/amd64.json` and `artifacts/locks/arm64.json`. Each lock pins
the selected NGINX RPM, the complete 79-package installation closure, 59
corresponding source RPMs, artifact sizes and SHA-256 values, the actual RPM
signer fingerprint, and the builder and runtime manifest-list digests.

The two architectures have the same package-name and source-package sets.
Architecture-specific binary hashes and sizes remain separate. Identical
source RPM content is retained by URL and digest in both locks so either
architecture record is independently complete.

Validate the reviewed inputs, both locks, and negative validation cases with:

```console
python scripts/artifacts.py validate-inputs artifacts/lock-inputs.json
python scripts/artifacts.py validate-lock artifacts/locks/amd64.json \
  --inputs artifacts/lock-inputs.json
python scripts/artifacts.py validate-lock artifacts/locks/arm64.json \
  --inputs artifacts/lock-inputs.json
python -m unittest tests.test_artifacts -v
```

`scripts/fetch-lock-inputs.py`, `scripts/resolve-lock.sh`, and
`scripts/render-lock.py` implement the explicit lock-update path. The fetcher
admits only HTTPS URLs on approved public hosts and verifies the reviewed
SHA-256 before exposing an input. The resolver independently checks input
inventory, hashes, full signing-key fingerprints, RPM signatures, NEVRA,
architecture, dependency closure, and source-RPM signatures. The renderer
maps the observed RPM signing key ID to exactly one approved full fingerprint
and fails closed on malformed or inconsistent output.

An ARM64 lock can be dependency-resolved with DNF's explicit `aarch64` mode
without executing an ARM binary. Native ARM64 assembly and runtime evidence is
still required before release and will independently exercise the lock on the
target architecture.

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

Acquire the binary bundle for the native architecture from the official
publisher URLs and then perform RPM-level verification:

```console
python scripts/artifacts.py acquire \
  --lock artifacts/locks/amd64.json \
  --output .artifact-bundle/amd64
bash scripts/verify-rpm-bundle.sh \
  artifacts/locks/amd64.json .artifact-bundle/amd64
```

Add `--include-sources` to both commands when preparing a redistribution and
source-compliance bundle. Acquisition is atomic and refuses to replace an
existing output directory. The published directory contains only the exact
locked inputs plus lock-bound key, RPM, and optional source manifests.

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

Pass an external JSON source map with `--source-map`. It must contain exactly
one HTTPS URL for every logical path required by the selected lock and bundle
mode:

```json
{
  "schema_version": 1,
  "artifacts": {
    "keys/nginx_signing.key": "https://approved.example/keys/nginx_signing.key",
    "rpms/example.rpm": "https://approved.example/rpms/example.rpm"
  }
}
```

This abbreviated shape illustrates the interface; a real map must enumerate
the complete lock. URLs containing credentials, query strings, or fragments
are rejected. Redirects may remain only on the original HTTPS host. Use
`--token-env VARIABLE_NAME` to read a bearer token from the runner
environment and `--ca-bundle PATH` for externally provisioned CA trust. The
tool does not print source URLs or token values on download errors. Source
maps, credentials, and private CA material are protected runner inputs and
must not be committed or added to the build context.

## Local development

Local development uses the same preparation and assembly interface. A developer
first prepares or receives a verified artifact bundle, then builds without
network access. A cached but unverified file is not accepted merely because it
is local.

The preparation tooling provides actionable messages for missing source
configuration and will use the official public source by default. The artifact
lock, verification semantics, and network-disabled assembly remain identical
when an alternate source is deliberately selected.

Local preparation consumes an existing lock by default. Refreshing a lock is a
separate explicit command so an ordinary local build cannot silently upgrade a
dependency.

## Required tests

Unit tests exercise schema, reviewed-input, digest, and inventory rejection
without downloads.

The implementation is incomplete until automated tests additionally
demonstrate rejection of:

- a modified RPM;
- an RPM signed by an unapproved key;
- the wrong NEVRA or architecture;
- an extra or missing dependency RPM;
- a base image with the wrong digest;
- any attempted network access during assembly; and
- repository credentials or trust material found in the image or its history.
