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
