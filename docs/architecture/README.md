# Architecture

Diagrams and per-profile documentation.

Diagrams are hand-authored SVG with no rendering step, so the file published
here is the file that was reviewed. The reasoning, and what it costs, is in
[ADR-0008](../adr/0008-hand-authored-svg-diagrams.md).

## Conventions

- One diagram per file, sized to be readable without zooming
- Every diagram carries a `<title>` and a `<desc>` describing what it asserts,
  so it is evidence to a reader who cannot see it
- No external references and no script: a diagram must render identically for
  every reader, offline
- Colour distinguishes ownership, not decoration — amber is supplied by the
  deployment, green leaves the container, grey is internal

`tests/test_diagrams.py` enforces the mechanical parts. Visual consistency is
held by review.

## Runtime contract

![Runtime contract of the container: non-root identity with no capabilities, a
read-only root with one writable tmpfs, read-only mounted configuration and
trust material, unprivileged listeners, and log streams leaving on stdout and
stderr.](runtime-contract.svg)

What the image provides, and where the boundary falls. Everything inside the
container outline is a property of the image; everything crossing it is
supplied and owned by the deployment. The band along the bottom lists what the
image **cannot** enforce, which is the part most often assumed.

Related: [runtime contract](../RUNTIME-CONTRACT.md),
[security controls](../SECURITY-CONTROLS.md).

## Configuration profiles

![Map of the eleven configuration profiles grouped into serving, proxying,
transport security, and operational surfaces, all inheriting one shared
baseline.](profile-map.svg)

The eleven profiles and what each adds to the shared baseline. Two things the
map is drawn to make obvious: every proxying profile replaces the client
forwarding chain and never enables non-idempotent retries, and the
`dynamic-upstream` profile trades away balancing, failure tracking, failover,
and connection reuse in exchange for per-request re-resolution.

Profiles are mounted rather than composed — one configuration file per
container.

Related: [profile guide](../CONFIGURATION-PROFILES.md),
[support matrix](../SUPPORT.md).

## Still to come

Per-profile pages carrying each profile's own diagram and complete description,
linked from the support matrix, are an open roadmap item. So are the
assurance-pipeline, TLS trust, controlled-network, and control-ownership
diagrams, which use the same convention.
