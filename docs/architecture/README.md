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
- Colour carries meaning rather than decoration — amber is supplied or operated
  by the deployment, green leaves the container or is retained evidence, red
  marks a boundary or an exclusion, grey is internal

`tests/test_diagrams.py` enforces the mechanical parts, including that every
diagram is referenced by a document. Visual consistency is held by review.

---

## Runtime contract

![Runtime contract of the container: non-root identity with no capabilities, a
read-only root with one writable tmpfs, read-only mounted configuration and
trust material, unprivileged listeners, and log streams leaving on stdout and
stderr.](runtime-contract.svg)

Where the boundary falls. Everything inside the container outline is a property
of the image; everything crossing it is supplied and owned by the deployment.
The band along the bottom lists what the image **cannot** enforce, which is the
part most often assumed.

Related: [runtime contract](../RUNTIME-CONTRACT.md).

## Configuration profiles

![Map of the eleven configuration profiles grouped into serving, proxying,
transport security, and operational surfaces, all inheriting one shared
baseline.](profile-map.svg)

The eleven profiles and what each adds to the shared baseline. Drawn to make
two things obvious: every proxying profile replaces the client forwarding chain
and never enables non-idempotent retries, and `dynamic-upstream` trades away
balancing, failure tracking, failover, and connection reuse in exchange for
per-request re-resolution.

Profiles are mounted rather than composed — one configuration file per
container.

Related: [profile guide](../CONFIGURATION-PROFILES.md),
[support matrix](../SUPPORT.md).

## Runtime data flow

![A request crosses the ingress boundary carrying a path, query string,
headers, and body; the proxy validates the correlation identifier and replaces
the forwarding chain; the access event records only the path and derived
fields, while query strings, bodies, headers, and credentials never reach any
log.](runtime-dataflow.svg)

What a request carries, what the proxy changes, and what never reaches the log.
The excluded set is marked as *structurally absent rather than filtered out*:
the query string never reaches the log formatter, so there is no list to
maintain and no new parameter that leaks.

Related: [logging](../LOGGING.md), [ADR-0004](../adr/0004-log-the-path-never-the-request-line.md).

## TLS trust

![Three independent directions of trust: clients verify the ingress
certificate, the proxy verifies client certificates against a mounted authority
and revocation list, and the proxy verifies HTTPS upstream chains and hostnames
against a separate mounted authority.](tls-trust.svg)

Three independent trust directions, all rooted in material the deployment
operates. The image issues nothing and stores nothing. The panel at the bottom
lists what TLS support here does *not* include — CA operation, renewal
automation, alert delivery, OCSP, host cryptographic policy, and any FIPS
claim.

Related: [TLS lifecycle](../TLS-LIFECYCLE.md).

## Assurance pipeline

![A change passes repository checks, then on each native architecture the
locked artifacts are acquired and verified, invalid bundles are rejected, the
image is assembled with no network, hermetic boundaries are proven, the suites
run under Podman and repeat under Docker, and the image is scanned into
retained evidence.](assurance-pipeline.svg)

What runs on every change, in order, and what it produces. Two properties the
diagram is drawn to show: acquisition is the only stage permitted to reach the
network, and Docker receives the *same* image by local archive rather than a
second build.

Related: [continuous integration](../CI.md).

## Controlled-network transfer

![A reviewed lock drives acquisition and hermetic assembly in the connected
environment; a transfer manifest binds the payload to the repository revision,
lock, and inventory; the payload crosses an approved boundary while the
manifest digest travels separately; the disconnected side verifies, mirrors,
and deploys by digest.](controlled-network.svg)

How an image and its inputs reach an environment with no route to an upstream
repository. The manifest digest deliberately travels by a separate channel — a
digest carried alongside the payload it describes proves nothing.

This procedure is documented and unit-tested. It has **not** been rehearsed end
to end across a real boundary, which the diagram states rather than implies.

Related: [artifact lifecycle](../ARTIFACT-LIFECYCLE.md).

## Control ownership

![Four concentric layers of ownership: the image project inside the deployment
profile, inside the host or orchestrator, inside the organization, each
depending on the layers outside it.](control-ownership.svg)

Who owns what, drawn as containment because each layer depends on the ones
outside it. The point the diagram exists to make is stated on it: contributing
to a control is not satisfying it, and the image can be configured insecurely
by the layer above it without being able to prevent that.

Related: [security controls](../SECURITY-CONTROLS.md).

---

## Profile pages

[One page per profile](profiles/README.md), each with its own request-path
diagram, the behaviour its tests qualify, and the behaviour they deliberately
do not. The support matrix links to these rather than restating them.

The pages and their diagrams are generated from a single table, so a page
cannot describe a request path its diagram contradicts.
