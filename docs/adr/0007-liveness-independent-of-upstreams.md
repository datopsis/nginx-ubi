---
status: accepted
date: 2026-09-16
decision-makers: Joey
---

# Keep liveness independent of upstream health

## Context and Problem Statement

A proxy is commonly given one health endpoint, wired to both the liveness and
readiness probes, and made to report the upstream's health so that "health"
means something useful.

That arrangement fails badly during a dependency outage. When the upstream goes
down, the liveness probe fails on every proxy instance at once. The
orchestrator does what it is told to do with a failed liveness probe: it kills
and restarts them. The proxies were healthy. Restarting them does not bring the
upstream back, it drops every in-flight connection, and it removes the capacity
needed to absorb the recovery when the upstream does return.

A dependency outage becomes a restart storm, and the restart storm is usually
worse than the outage.

## Decision Drivers

* Liveness and readiness answer different questions and have different remedies
* Restarting a healthy process cannot fix a failure outside it
* An instance that cannot serve should stop receiving traffic, which is not the
  same as being replaced
* The distinction is invisible in configuration unless it is deliberate

## Considered Options

* **One endpoint for both probes, reporting upstream health** — the common
  arrangement
* **Separate endpoints: liveness local, readiness upstream-dependent** — each
  probe answers its own question
* **Liveness only, no readiness** — never remove an instance from rotation

## Decision Outcome

Chosen option: **separate endpoints.**

`/healthz` answers for the process alone and never consults the upstream. Its
only claim is that this NGINX is running and able to serve, which is precisely
the question whose remedy is a restart.

`/readyz` proxies to the upstream's own health endpoint and reports `503` when
that fails. Its remedy is removal from rotation, which is reversible in seconds
and costs nothing when it turns out to be transient.

Liveness-only was rejected because it leaves an instance that genuinely cannot
serve still receiving traffic, turning a partial outage into errors that a
readiness probe would have avoided.

Readiness timeouts are deliberately shorter than a typical probe interval: a
check that outlives its own probe period stacks concurrent probes against an
already struggling upstream.

### Consequences

* Good: a dependency outage removes instances from rotation without restarting
  them, so capacity is intact when the upstream returns
* Good: the two signals mean different things, so an operator can tell "this
  instance is broken" from "its dependency is"
* Good: liveness stays cheap and local, so it cannot time out under load
* Bad: two endpoints must be wired correctly. An orchestrator configured to use
  `/readyz` as its liveness probe reintroduces the whole problem, and nothing in
  this image can prevent that
* Bad: readiness costs a real request to the upstream on every probe, which is
  load the upstream would not otherwise see
* Bad: open source NGINX has no active health checking, so readiness is a
  request made when asked rather than a background probe — the signal is only as
  fresh as the probe interval

### Enforcement

`tests/profiles.sh` stops the upstream and asserts `/healthz` still answers
`200` while `/readyz` reports `503` and records a structured event. A change
making liveness depend on the upstream fails the first assertion.
