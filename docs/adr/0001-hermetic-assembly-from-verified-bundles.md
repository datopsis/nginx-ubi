---
status: accepted
date: 2026-09-16
decision-makers: Joey
---

# Assemble the image from verified local bundles with networking disabled

## Context and Problem Statement

The builder stage resolved RPMs with DNF during the build. The image therefore
had no record of what it had installed, the resolution depended on whatever the
repositories offered at build time, and CI restored the `dnf install` layer
from a GitHub Actions cache.

That combination failed silently, and was found on 2026-09-16 rather than
theorised. A newly published advisory for `openssl-libs` tripped the Grype gate
on a build whose image had not changed. Refreshing the base digests invalidated
the cached layer, and the build then failed outright: the pinned
`nginx-core-2:1.26.3-9.module+el9.8.0+24599+8fde0ff7.3` had been **superseded
and removed** from UBI AppStream some time earlier.

So `main` had not genuinely rebuilt for an unknown period. Every green run was
replaying a cached layer containing a package set the repositories no longer
offered, and nothing detected it. The pipeline was not verifying what it
claimed to verify; it was verifying a cache.

## Decision Drivers

* Build inputs must be reviewable before they are used, not discovered afterwards
* Upstream drift must surface as a failure, not be absorbed invisibly
* Controlled networks require assembly with no network access at all
* SBOM and provenance claims are only as good as knowing what was installed
* A rebuild of the same commit should install the same packages

## Considered Options

* **Keep DNF resolution in the build, with pinned versions** — the status quo
  plus discipline
* **Resolve outside the build; assemble from a verified local bundle** — a
  reviewed lock enumerates every artifact, and the build consumes only that
* **Vendor the RPMs into the repository** — maximum reproducibility, no
  acquisition step

## Decision Outcome

Chosen option: **resolve outside the build; assemble from a verified local
bundle.**

Pinning versions inside the build was not rejected as useless — the versions
*were* pinned, and that is precisely what failed. Pinning describes intent; it
does not verify outcome, and it cannot detect that the intended artifact has
stopped existing while a cache still holds a copy.

Vendoring the RPMs would reproduce well but puts ~43 MB of binary artifacts per
architecture under version control, makes every security update a large commit,
and still needs a reviewed process to decide what goes in. The acquisition step
it removes is the same step that produces the verification evidence.

The lock enumerates every RPM with its digest, size, signer, NEVRA, and source
RPM. Installation compares the installed inventory against the lock and fails
closed on any difference. Assembly runs with `--network none` and
`--pull=never`.

### Consequences

* Good: a superseded or withdrawn upstream package becomes an explicit
  validation failure instead of a silent cache hit
* Good: assembly works with no network, which is what a disconnected build
  requires
* Good: the exact package set is knowable from the repository, and the image
  carries the verified manifest
* Bad: refreshing a lock is an explicit reviewed operation needing a networked
  resolver run per architecture — roughly 790 MB of downloads and a
  dependency-closure resolution, not an edit
* Bad: the repository carries two large generated lock files whose diffs are
  long even when the change is small
* Bad: contributors building locally need `rpm`, `gpg`, and a container runtime,
  and host-side verification is sensitive to the RPM version — Fedora 44's
  `rpm` 6 handles `--define _dbpath` differently from the RPM 4.18 on CI

### Enforcement

`scripts/install-rpm-bundle.sh` compares the installed inventory against the
lock and fails the build on any difference. `tests/hermetic-build-negative.sh`
proves a wrong lock identity and an unavailable base are rejected.
`tests/rpm-bundle-negative.py` mutates copies of the real bundle to prove
tampering, signature removal, signer mismatch, wrong version, wrong
architecture, and missing or extra RPMs are all rejected.
