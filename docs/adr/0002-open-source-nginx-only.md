---
status: accepted
date: 2026-09-16
decision-makers: Joey
---

# Package open source NGINX only

## Context and Problem Statement

Several capabilities this project's profiles would naturally reach for are
NGINX Plus features rather than open source ones: active upstream health
checking (`health_check`), session persistence (`sticky`), the `/api` and
extended `status` surfaces, `keyval`, and `zone_sync`.

The pull is strongest exactly where the profiles are most useful. A load
balancer wants active health checks. A readiness endpoint wants to know whether
the upstream is healthy. An operator wants a richer status surface than
`stub_status` provides.

The risk is not that someone deliberately adds a commercial dependency. It is
that a profile is written assuming a capability the shipped image does not
have, or that documentation describes behaviour that only appears with a
licence nobody bought.

## Decision Drivers

* No licensing or commercial support decision has been taken, and this is not
  the place to take one implicitly
* Every example must run on the image as shipped, by anyone who pulls it
* A configuration that silently requires a licence is worse than one that
  states a limitation
* The project's support claims must be verifiable against what is actually built

## Considered Options

* **Open source only, stated as a constraint** — profiles solve problems with
  open source directives and record the resulting limitation
* **Allow Plus-conditional configuration** — ship examples with commented
  Plus-only blocks for those who have a licence
* **Stay silent** — use open source in practice without writing the constraint
  down

## Decision Outcome

Chosen option: **open source only, stated as a constraint.**

Staying silent is what the project was already doing, and it was working by
accident rather than by design. Nothing prevented a future profile from
reaching for `health_check`, and nothing would have caught it.

Plus-conditional examples were rejected because they make every example
ambiguous. A reader cannot tell which parts apply to them without knowing their
own licence status, and the tests can only exercise one branch, so the other
becomes untested configuration shipped as guidance.

The constraint is recorded in `docs/PACKAGE-SOURCE.md` with a rule attached:
where a profile needs behaviour a commercial feature provides, it solves the
problem with open source directives **and states the limitation** rather than
implying the capability exists.

That rule is already visible in the profiles. Load balancing uses passive
`max_fails` and `fail_timeout`, and says plainly that open source NGINX has no
active probing. Readiness is expressed as a real request to the upstream's own
health endpoint. The operator status surface is `stub_status`.

### Consequences

* Good: every example runs on the image as shipped
* Good: the limitations are visible to a reader deciding whether this image
  suits them, rather than discovered during deployment
* Bad: no active upstream health checking, so a failed member is detected only
  by real requests failing and is returned to rotation on a timer rather than
  on evidence of recovery
* Bad: no session persistence, so affinity needs a hash method with its own
  rebalancing behaviour
* Bad: the observability surface is `stub_status` counters, which is
  considerably less than the Plus API offers
* Bad: a future decision to adopt NGINX Plus is not merely a configuration
  change — it would supersede this record and require a licensing, support, and
  redistribution review

### Enforcement

Nothing automated. A grep for the commercial directive names finds no
occurrences today, but no check prevents one being added. A lint rule rejecting
Plus-only directives in `examples/profiles/` would close that gap and has not
been written.
