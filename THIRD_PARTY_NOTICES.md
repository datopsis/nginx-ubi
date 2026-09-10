# Third-party software and terms

The root [Apache License 2.0](LICENSE) applies to Datopsis-authored packaging
code and documentation in this repository. It does not replace the licenses or
terms of software assembled into the container image.

## NGINX

The image installs the exact NGINX RPM selected by the project. NGINX
open-source software is distributed under its
[two-clause BSD license](https://nginx.org/LICENSE). NGINX names and marks
remain the property of their respective owners. This independent packaging
project is not affiliated with or endorsed by F5 or the NGINX project.

## Red Hat Universal Base Image

The base and installed runtime RPMs come from Red Hat UBI images and UBI
repositories. UBI content is redistributable subject to the
[Red Hat UBI terms and component licenses](https://developers.redhat.com/articles/ubi-faq).
Red Hat support is not included with this community image; eligibility depends
on the applicable subscription and supported deployment combination.

The image retains installed component license material. Release SBOMs must
identify the exact RPM inventory and licenses. The OCI license expression
describes the principal packaging and NGINX license relationship; consumers
must also review the SBOM, embedded notices, UBI terms, and every component's
license.

## Release review

Before publishing a release:

1. Confirm all Red Hat packages came from approved UBI repositories and remain
   redistributable.
2. Confirm the selected NGINX package source, license, signature, and source RPM
   are recorded.
3. Inspect the SBOM for new packages, unknown licenses, and missing notices.
4. Retain upstream copyright, license, attribution, and trademark notices.
5. Update this file when package sources, image contents, branding, or
   distribution channels change.

This notice is operational documentation, not legal advice.
