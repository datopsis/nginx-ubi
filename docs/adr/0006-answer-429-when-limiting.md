---
status: accepted
date: 2026-09-16
decision-makers: Joey
---

# Answer `429` rather than `503` when a limit rejects a request

## Context and Problem Statement

`limit_req` and `limit_conn` answer `503 Service Unavailable` by default.

`503` means the server cannot handle the request, which is what a client sees
during an outage. A rate-limited client and a client hitting a broken service
receive the same answer, and neither the client nor the monitoring can tell
which happened.

The practical consequence runs the wrong way. A client that believes it is
seeing an outage retries, often more aggressively, against a server that is
already shedding load deliberately. Dashboards counting `5xx` as errors record
a functioning control as a service failure, which makes intentional shedding
look like an incident.

## Decision Drivers

* A client should be able to tell "you are sending too much" from "I am broken"
* Monitoring should not record a working control as an outage
* The response should discourage immediate retry rather than invite it
* `429 Too Many Requests` exists for exactly this and is widely understood

## Considered Options

* **Keep the `503` default** — no configuration, conventional NGINX behaviour
* **Answer `429`** — the semantically correct status
* **Answer `429` with `Retry-After`** — also tell the client when to come back

## Decision Outcome

Chosen option: **answer `429`**, without `Retry-After`.

Keeping `503` was rejected: the only argument for it is that it is the default,
and the default is actively misleading here.

`Retry-After` is the interesting rejection, and it is deferred rather than
dismissed. A useful value would state when the client's budget actually
refills, which depends on the current state of its bucket. NGINX does not
expose that, so any value in the header would be a fixed guess — and a fixed
guess is worse than no header, because clients that honour it would synchronise
their retries into a thundering herd at the same instant.

A correct `Retry-After` needs information the open source limit modules do not
provide. It stays unset until there is a way to compute it truthfully.

### Consequences

* Good: clients and monitoring can distinguish deliberate shedding from failure
* Good: `4xx` rather than `5xx` keeps a working control out of the error budget
* Good: well-behaved HTTP clients already treat `429` as back-off-and-retry
* Bad: no `Retry-After`, so clients must choose their own back-off. A client
  with no back-off logic retries just as fast as it would against a `503`
* Bad: a client or intermediary that treats only `5xx` as retryable may now fail
  the request outright rather than retrying later
* Bad: it differs from the NGINX default, so a configuration assembled from
  elsewhere silently reverts to `503`

### Enforcement

`tests/profiles.sh` asserts that exhausting the request rate produces `429`
recorded as `REJECTED`, and that requests beyond the connection maximum are
rejected by the connection limit specifically. A change back to `503` fails
those assertions.
