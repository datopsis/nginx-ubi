# NGINX package-source decision

Status: proposed for the first release; the current image still uses the Red
Hat UBI AppStream RPM documented in [RPM provenance](RPM-PROVENANCE.md).

## Recommendation

Use the official NGINX stable RPM repository for the first release while
retaining digest-pinned Red Hat UBI 9 Minimal and Micro base images. Pin one
exact NGINX RPM epoch, version, and release for each architecture. Do not track
the newest package implicitly during a release build.

Package publication and package acquisition are separate decisions. NGINX
remains the publisher even when an approved intermediary transfers the
unchanged, signed RPM. All downloading and verification will occur before the
container build as defined in
[External artifact acquisition](ARTIFACT-ACQUISITION.md).

As observed on 2026-09-08, the stable repository offers
`nginx-2:1.30.4-1.el9.ngx` for RHEL 9 on both `x86_64` and `aarch64`. This is an
observed development candidate, not yet the selected first-release version.
The exact candidate must be frozen only after its tests and vulnerability
review pass.

Prefer stable over mainline for the initial release. Mainline provides features
sooner but creates a faster qualification and update cadence. A mainline-only
feature should be identified and approved before accepting that cost.

## Why change

The official NGINX repository makes upstream stable releases available sooner
than the RHEL application stream. That reduces dependence on Red Hat's module
stream cadence and makes the image's displayed NGINX version easier to compare
with upstream security advisories.

An older Red Hat version is not automatically unpatched. Red Hat can backport
security corrections while retaining the upstream version and identifying the
change in the RPM release. Moving suppliers trades that backport and RHEL
integration model for NGINX's release cadence; it does not eliminate patch
management.

## Comparison

| Area | Red Hat UBI AppStream RPM | Official NGINX RPM |
| --- | --- | --- |
| Release cadence | RHEL module-stream lifecycle with Red Hat backports. | NGINX stable or mainline release cadence. |
| Current observed package | `nginx-core-2:1.26.3-9.module+el9.8.0+24599+8fde0ff7.3` | Stable candidate `nginx-2:1.30.4-1.el9.ngx`. |
| Package trust | Red Hat repository metadata and release key. | NGINX repository and NGINX signing key. |
| Platform statement | Packaged as part of UBI/RHEL content. | NGINX documents RHEL 9 packages for x86_64 and aarch64; this project must qualify them on UBI 9. |
| Security maintenance | Red Hat errata and backported fixes. | New upstream NGINX package releases. |
| Package shape | Minimal `nginx-core` plus `nginx-filesystem`. | One main `nginx` RPM containing standard binary, debug binary, service files, defaults, and documentation. |
| Scanner interpretation | Red Hat package metadata and advisories. | NGINX `.el9.ngx` metadata; scanner matching and advisory coverage require validation. |
| Controlled network | Mirror or snapshot UBI repositories. | Mirror or snapshot both UBI dependencies and NGINX packages, keys, metadata, and source RPMs. |
| Vendor support | Aligns with Red Hat's packaged content boundary. | Introduces NGINX as an additional software supplier; no Red Hat support claim for this combination. |

## Change difficulty

This is a moderate change. The multi-stage UBI design, rootless runtime,
unprivileged ports, custom configuration, and package-manager-free final image
can remain. The package acquisition and assurance boundary must change.

Implementation requires:

1. Choose official stable or mainline; stable is recommended.
2. Acquire the NGINX signing key outside the container build through a reviewed
   process, verify its full fingerprint, pin its checksum, and define
   key-expiration and rotation handling. The official instructions currently
   identify fingerprint
   `573B FD6B 3D8F BC64 1079 A6AB ABF5 BD82 7BD9 BF62` and advise independent
   authenticity verification.
3. Resolve and download the exact NGINX RPM and dependency closure outside the
   build through the configured approved artifact source.
4. Verify RPM signatures, fingerprints, checksums, NEVRA, architecture, and
   bundle completeness before starting the build.
5. Install the verified local bundle into `/runtime` with build networking and
   pulling disabled, then remove package tools and service-management content
   not needed at runtime from the final image.
6. Reconcile package-created users, directories, default configuration, debug
   binary, service files, and dependencies with the arbitrary-UID design.
7. Compare installed modules from `nginx -V` with every intended use case and
   record any added or removed capability.
8. Repeat rootless, arbitrary-UID, read-only-root, dropped-capability, logging,
   graceful shutdown, reverse-proxy, and TLS tests.
9. Regenerate native AMD64 and ARM64 SBOMs and vulnerability results. Verify
   that both scanners correctly identify the NGINX package and findings.
10. Record binary RPM and source RPM locations, checksums, signatures, licenses,
   update ownership, mirror procedure, and release evidence.

The official RPM declares dependencies including UBI-provided OpenSSL, PCRE2,
zlib, shell, user-management, process, and service packages. Some of those are
packaging-time conveniences rather than runtime requirements, so the prototype
must measure the final dependency closure and remove files only when tests and
license records show that doing so is safe.

## Versioning impact

Changing package suppliers changes image contents and release evidence. Because
no image release exists yet, the first accepted direct-NGINX build uses the
approved date-based release identifier. A supplier or channel change after
release requires a new immutable release date and daily sequence even when the
displayed NGINX version remains the same.

The package supplier and exact RPM EVR belong in OCI labels, the SBOM,
provenance, and the release evidence. They do not need another field in the
human-readable release tag.

## Acceptance criteria

Approve the direct RPM only when:

- an exact stable RPM exists for both release architectures;
- signing-key authenticity and package signature verification are automated;
- all direct downloads and base images are immutably selected;
- CI downloads and verifies all artifacts before a network-disabled build;
- the acquisition process introduces no credentials or private trust material
  into the build context or image;
- required NGINX modules and configuration behavior match the supported uses;
- rootless and restricted-runtime tests pass on both architectures;
- Trivy and Grype findings receive vendor-advisory review;
- the final image contents and size are understood;
- source, license, support, update, and controlled-network responsibilities are
  documented; and
- a rollback to the last accepted package input has been rehearsed.

## Authoritative NGINX references

- [Official Linux packages, repositories, keys, and supported platforms](https://nginx.org/en/linux_packages.html)
- [Stable RHEL 9 x86_64 RPM repository](https://nginx.org/packages/rhel/9/x86_64/RPMS/)
- [Stable RHEL 9 aarch64 RPM repository](https://nginx.org/packages/rhel/9/aarch64/RPMS/)
- [NGINX security advisories](https://nginx.org/en/security_advisories.html)
