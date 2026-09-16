# Runtime component accountability

The authoritative runtime-component inventory is
[`artifacts/components.json`](../artifacts/components.json). It accounts for
all 79 binary RPMs in both reviewed architecture locks and records each
package name, exact RPM `License` tag, source RPM identity, publisher policy,
redistribution terms, support-lifecycle boundary, and update owner.

The inventory is bound to the SHA-256 digest of each architecture lock. A lock
refresh therefore cannot retain a stale component record: validation fails
until the inventory is reviewed and rebound. The common inventory is valid
only while AMD64 and ARM64 contain the same package names, source RPMs, and
publisher classification.

## Publisher and terms boundary

| Policy | Components | Source and redistribution | Lifecycle and support | Update owner |
| --- | ---: | --- | --- | --- |
| `nginx-stable` | 1 | Official NGINX stable RPM repository; NGINX two-clause BSD terms and required acknowledgements | The project identified no fixed support term for the open-source stable channel and makes no F5 or NGINX support claim | Datopsis maintainers |
| `redhat-ubi9` | 78 | Public Red Hat UBI repositories; redistribution remains subject to the UBI EULA and each component license | UBI content follows the RHEL lifecycle; Red Hat support requires an eligible subscription and supported deployment combination | Datopsis maintainers |

Authoritative upstream references:

- [NGINX Linux packages](https://nginx.org/en/linux_packages.html)
- [NGINX license and copyright FAQ](https://nginx.org/en/docs/faq/license_copyright.html)
- [NGINX two-clause BSD license](https://nginx.org/LICENSE)
- [Red Hat UBI FAQ](https://developers.redhat.com/articles/ubi-faq)
- [Red Hat UBI EULA](https://cdn-ubi.redhat.com/content/public/ubi/EULA.html)
- [Red Hat UBI content availability](https://access.redhat.com/support/policy/updates/ubi)
- [Red Hat container support policy](https://access.redhat.com/support/policy/container-support-policy)

The RPM `License` value is publisher-supplied package metadata. It is retained
verbatim for change detection and review; it is not a project-authored SPDX
normalization or a legal conclusion. The release SBOM and embedded license
files remain required evidence. Final license and third-party-notice review is
a separate release gate.

## Validation

The download-free check validates the inventory structure, exact coverage,
publisher classification, source RPM identities, and both lock bindings:

```console
python scripts/components.py
```

After acquiring an architecture bundle, validate the recorded license, source
RPM, and vendor directly against every signed RPM header:

```console
python scripts/components.py \
  --lock artifacts/locks/amd64.json \
  --bundle .artifact-bundle/amd64
```

Native CI runs the second check for AMD64 and ARM64. A package addition,
removal, source change, publisher change, license-tag change, or lock change
blocks CI until the corresponding record receives review.

## Maintenance responsibility

Datopsis maintainers own monitoring official NGINX stable releases, Red Hat
UBI errata and lifecycle notices, vulnerability findings, and dependency-lock
changes. They decide when to propose, test, and publish an updated image.
Operators remain responsible for selecting supported deployment combinations,
maintaining any required vendor subscriptions, and replacing superseded image
digests in their environments.

This record is operational supply-chain documentation, not legal advice and
not a statement that Red Hat, F5, or NGINX supports this image.
