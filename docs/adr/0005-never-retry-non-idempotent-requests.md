---
status: accepted
date: 2026-09-16
decision-makers: Joey
---

# Never retry a non-idempotent request against another upstream

## Context and Problem Statement

`proxy_next_upstream` decides when NGINX abandons one upstream and tries the
next. Its `non_idempotent` flag extends that to `POST`, `PATCH`, `LOCK`, and
`PATCH`-like methods, which NGINX otherwise refuses to retry.

Enabling it is a common availability tweak, and it is usually reached for after
an incident where a transient upstream failure surfaced to users. It converts
some visible failures into successes.

It also converts some invisible failures into duplicates. A request that timed
out may have been received, acted upon, and had its response lost. Retrying it
runs the operation twice. For a payment, a message dispatch, or a row insert,
the second attempt is a correctness defect rather than a recovery.

## Decision Drivers

* A duplicated write is harder to detect and more expensive to repair than a
  failed one
* The proxy cannot know whether an upstream already applied a request
* One client request should not be able to multiply into unbounded upstream work
* Availability improvements that trade correctness should be an application's
  choice, not a default in shared infrastructure

## Considered Options

* **Enable `non_idempotent`** — maximum availability, retries everything
* **Retry only `error` and `timeout`** — the NGINX default, idempotent methods
  only, with explicit bounds
* **Disable retries entirely** — no failover at all

## Decision Outcome

Chosen option: **retry only `error` and `timeout`, never `non_idempotent`,
with both bounds set explicitly.**

`non_idempotent` was rejected on the grounds that the proxy is the wrong layer
to make that trade. It has no way to know whether a request was applied, and
the cost of being wrong is borne by the application's data rather than by its
uptime graph. An application that can safely retry a write knows that because
of idempotency keys or deduplication it implemented itself, and it can retry.

Disabling retries entirely was rejected for the load-balancing profile, where
failing over a `GET` after a connection error is exactly the value of having a
pool. It *is* the choice where there is no peer set to fail over to — the
WebSocket upgrade, the ClickHouse query location, and the dynamic-upstream
profile all set `proxy_next_upstream off`, since a retry there repeats work
without improving the odds.

`proxy_next_upstream_tries` and `proxy_next_upstream_timeout` are both set so a
failing pool cannot turn one client request into an unbounded amount of
upstream work.

### Consequences

* Good: no silent duplicate writes originating in the proxy layer
* Good: retry amplification is bounded, so a pool failure degrades rather than
  cascades
* Bad: a `POST` that fails mid-flight surfaces to the client instead of being
  retried, and clients must handle that
* Bad: availability measured naively looks slightly worse than a configuration
  that retries everything, and the difference is visible while the duplicates it
  avoids are not
* Bad: the reasoning is easy to lose. `non_idempotent` looks like an obvious
  improvement to anyone reading the directive without this context, which is
  why the configuration comments carry the rationale inline

### Enforcement

Nothing automated. The absence of a flag is not something the current suites
assert. A check that no profile *enables* `non_idempotent` would be cheap and
does not exist — it would have to distinguish the directive from the comments
that explain its deliberate absence, which are currently the only thing arguing
against adding it.
