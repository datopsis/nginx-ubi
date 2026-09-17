---
status: accepted
date: 2026-09-16
decision-makers: Joey
---

# Podman is the primary runtime; Docker is a compatibility target

## Context and Problem Statement

The image is expected to run under rootless Podman, under Docker, and on
OpenShift with an arbitrary assigned UID. These are not the same environment,
and a test that passes under one does not establish behaviour under another.

The difference is not cosmetic. Rootless Podman maps the invoking user onto
container GID `0`, so a file owned by that user and group-readable is readable
inside the container. Rootful Docker preserves host ownership, and its
container GID `0` is host root, so the identical file is unreadable. A mounted
TLS private key that works perfectly under one runtime fails to open under the
other.

Without a stated position, "it works in CI" means whichever runtime CI happened
to use, and a support claim inherits that ambiguity.

## Decision Drivers

* The security posture is built around rootless operation, which Podman does
  natively
* OpenShift's arbitrary-UID model is closer to the Podman case than the Docker one
* Evidence has to name the runtime that produced it, or it is not evidence
* Docker is too widely used to leave untested

## Considered Options

* **Support both equally** — every claim qualified on both runtimes
* **Podman only** — test and support one runtime, say nothing about Docker
* **Podman primary, Docker compatibility** — qualify on Podman, and run a
  reduced compatibility pass on Docker without extending the support boundary

## Decision Outcome

Chosen option: **Podman primary, Docker compatibility.**

Supporting both equally sounds stronger and is mostly a way of promising twice
as much qualification as will actually be done. Every platform statement would
need host, runtime version, and storage-driver evidence on both, and the
release gate would double.

Saying nothing about Docker was rejected because people will run it there
regardless, and silence is not neutral — it just moves the discovery of a
difference to the user.

CI builds once with Podman and transfers the result into Docker by local
archive, so the compatibility pass exercises the identical image rather than a
second build. The transfer performs no build and no registry pull.

### Consequences

* Good: one artifact, tested twice, with no chance the two runs diverge because
  the builds differed
* Good: runtime differences surface in CI rather than in a deployment. The TLS
  key-permission difference above was found exactly this way
* Bad: the compatibility leg sometimes needs accommodations that are **not**
  deployment guidance. The TLS rehearsal widens key permissions on the Docker
  leg only, because setting group `0` on the host would fix Docker and break
  rootless Podman. That is commented as a harness accommodation, and the risk
  of it being read as advice is real
* Bad: every support statement has to name the runtime, which makes the support
  matrix wordier and easier to get subtly wrong
* Bad: "compatible" invites the reading "supported", and the distinction has to
  be restated wherever it matters

### Enforcement

Native CI runs the full smoke, profile, and TLS suites under Podman on both
architectures, then repeats them under Docker after a local-archive transfer.
`docs/SUPPORT.md` states the distinction; nothing automated prevents a future
document from blurring it.
