# Security policy

## Supported versions

No supported image has been published. Repository revisions and development
images are available for evaluation but receive no security-support commitment.
Each future release will document its exact support status and supersession
policy; support must not be inferred from a tag, branch, successful build, or
scanner result.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use the repository's
**Security** tab and select **Report a vulnerability** to submit a private
security advisory:

<https://github.com/datopsis/nginx-ubi/security/advisories/new>

Include the affected image tag and digest when available, architecture,
runtime and host versions, configuration profile, reproduction steps, and
whether the issue appears to originate in this packaging, NGINX, or UBI. Remove
credentials, private keys, internal hostnames, customer data, and other secrets.

Upstream vulnerabilities should also follow the applicable upstream process:

- NGINX: <https://nginx.org/en/security_advisories.html>
- Red Hat: <https://access.redhat.com/security/team/contact>

## Handling and disclosure

Maintainers will acknowledge a private report when practical, validate its
scope, coordinate with upstream suppliers when appropriate, and agree on a
disclosure plan before publishing details. No response or remediation SLA is
promised until the first supported release defines one.

Scanner matches require vendor context. Red Hat can backport corrections
without adopting the upstream version number a scanner expects. Review the
exact RPM build and Red Hat advisory data before classifying a match.

## Vulnerability gate: fixes available from UBI

The owner-approved gate defines a fixable High/Critical RPM finding as one
whose vendor fixed version, or a newer version, is available from the UBI
repositories used to resolve this image's lock. This is evaluated independently
for AMD64 and ARM64, for both Trivy and Grype. It is a general availability
rule, with no CVE, package, or date exceptions.

CI queries DNF inside the architecture's digest-pinned builder. It copies that
image's original repository files before installing query tools and uses only
those files, the same release version as the lock resolver, and fresh metadata.
All three enabled UBI repositories must load successfully. The check compares
RPM epoch, version, and release using RPM's own comparator, and considers only
the package's architecture and `noarch`. Availability means a matching package
is advertised by those repositories at or above a vendor fixed version; it is
not a guarantee that an entire future lock transaction will resolve. An
available fix blocks even if a later transaction or download might fail.

An absent fixed RPM is **deferred**, not ignored, accepted as safe, or removed
from scanner results. The job summary names the scanner, finding, package,
severity, vendor fixed version and decision. CI retains both complete scanner
reports and the gate evidence, including queried versions, architecture, lock
hash, builder digest, repository-file hashes and repository metadata hashes.
Findings without a vendor fix also remain reported.

The gate fails closed on missing reports, invalid package or version data,
missing/empty repositories, metadata/query errors, and timeouts. A fixable
non-RPM finding (including Java, Go or Python dependencies) remains blocking;
Trivy High/Critical secret findings also block. RPM findings must match the
reviewed lock's package identity, installed version and architecture before
deferral is considered. No image content, runtime hardening, provenance label,
or release-signing requirement is changed by this policy.

Daily native CI rechecks availability; default-branch push and manual runs do
so too. One tracking issue, **UBI vulnerability fix availability**, is assigned
to the same maintainer as input-drift notifications. It is updated in place,
with comments only when findings or their decisions change. Publication turns
a deferred finding into a blocker on the next successful check and sends a
change notification. Missing architecture evidence is reported as an error,
never as resolution. The issue closes when no deferred/blocking findings or
verification errors remain and reopens on recurrence. Notification writes run
only from trusted default-branch CI, never from pull requests. A notification
failure is a failed job; it does not relax the image gate.

This rule addresses the gap between vendor advisories and public UBI package
publication. Exposure persists during that gap. Maintainers must review the
tracking issue and refresh both locks once fixes become available. The rule
has no automatic expiry or vulnerability-specific waiver; every run must
establish availability again. GitHub schedules and notifications are best
effort, so this is not an immediate-alert or remediation SLA.
