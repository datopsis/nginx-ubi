# NGINX RPM provenance

The NGINX binaries in this image come from Red Hat's public UBI 9 AppStream
RPM repository. They are not downloaded from nginx.org, EPEL, or an
uncontrolled third-party repository, and this project does not compile NGINX
from source.

## Exact development input

The current `Containerfile` selects the UBI 9 NGINX `1.26` module stream and
installs this exact package build:

```text
nginx-core-2:1.26.3-9.module+el9.8.0+24599+8fde0ff7.3
```

RPM metadata from the built AMD64 builder stage identifies:

| Field | Value |
| --- | --- |
| Repository | `ubi-9-appstream-rpms` |
| Repository description | Red Hat Universal Base Image 9 (RPMs) - AppStream |
| Repository base URL | `https://cdn-ubi.redhat.com/content/public/ubi/dist/ubi9/9/$basearch/appstream/os` |
| Package vendor and packager | Red Hat, Inc. |
| Architecture | `x86_64` on the AMD64 build; the native ARM64 job resolves its architecture build. |
| Source RPM | `nginx-1.26.3-9.module+el9.8.0+24599+8fde0ff7.3.src.rpm` |
| Automatic NGINX dependency | `nginx-filesystem` at the same epoch, version, and release |
| Upstream project URL in metadata | `https://nginx.org` |

The upstream URL describes the software's origin. Red Hat builds, packages,
signs, publishes, and maintains the RPM delivered by the UBI repository. RPM
epoch `2` and the full Red Hat release value are significant; `1.26.3` alone
does not uniquely identify the installed code or Red Hat backports.

## Build path and trust checks

The build uses digest-pinned Red Hat UBI 9 images for both stages:

1. UBI Minimal supplies package-management tools in the temporary builder.
2. DNF enables `nginx:1.26` inside a separate `/runtime` install root.
3. DNF installs the exact `nginx-core` build plus its dependency closure,
   `ca-certificates`, and `tzdata` with weak dependencies disabled.
4. The UBI repository configuration uses HTTPS, `gpgcheck=1`, and Red Hat's
   release key. A metadata or RPM verification failure makes the build fail.
5. Only the resulting `/runtime` filesystem is copied into digest-pinned UBI
   Micro.
6. Package managers and builder caches are absent from the final image.

The exact NGINX RPM prevents a silent switch to a later NGINX package build.
The full dependency closure can still change when Red Hat publishes compatible
dependency updates. The architecture-specific SPDX SBOM produced by CI records
what was actually installed. Strict byte-for-byte rebuild requirements would
also require an approved, immutable repository snapshot or internal mirror;
that controlled-network design remains a release gate.

Digest pinning protects selection of the two base-image manifests. It does not
replace signature verification, SBOM review, vulnerability analysis, or
release-digest verification.

## How to verify it locally

Build the package stage and inspect the installed RPM database without adding
RPM tooling to the runtime image:

```console
podman build --target builder --tag localhost/nginx-ubi9-builder:development .
podman run --rm --entrypoint rpm \
  localhost/nginx-ubi9-builder:development --root /runtime \
  -q --qf '%{NAME}|%{EPOCHNUM}:%{VERSION}-%{RELEASE}|%{ARCH}|%{VENDOR}|%{SOURCERPM}\n' \
  nginx-core nginx-filesystem
```

Inspect the enabled UBI repository from the same builder image:

```console
podman run --rm --entrypoint dnf \
  localhost/nginx-ubi9-builder:development repoinfo ubi-9-appstream-rpms
```

CI generates a Syft SPDX inventory for each native architecture and scans that
inventory with Grype in addition to Trivy's image scan.

The runtime image deliberately has no `rpm`, `dnf`, `microdnf`, or `yum`
command. Absence of those commands reduces runtime tooling but does not erase
the installed RPM database or replace the SBOM.

## Authoritative Red Hat references

- [Red Hat Universal Base Images](https://catalog.redhat.com/en/software/base-images)
- [Red Hat UBI 9 Minimal catalog entry](https://catalog.redhat.com/en/software/containers/ubi9/ubi-minimal/615bd9b4075b022acc111bf5)
- [Red Hat UBI licensing information](https://www.redhat.com/en/about/agreements)

The release-candidate review will record source availability, redistribution
terms, support boundaries, update ownership, and the exact inputs used for each
published image digest.

The proposed move to official NGINX stable RPMs is evaluated in
[NGINX package-source decision](PACKAGE-SOURCE.md). This file continues to
describe the image as it exists until that migration is implemented and
verified.

The current builder downloads RPMs and therefore does not yet satisfy the
planned [external artifact-acquisition contract](ARTIFACT-ACQUISITION.md).
