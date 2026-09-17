---
status: accepted
date: 2026-09-16
decision-makers: Joey
---

# Log the request path, never the request line

## Context and Problem Statement

NGINX's default access log records `$request`, the full request line including
the query string. That is the conventional choice and it is what almost every
example configuration on the internet does.

Query strings routinely carry material that should not be written down:
signed-link tokens, session identifiers, API keys, and application parameters
containing personal data. The ClickHouse HTTP interface makes the point
sharply — it accepts `?query=...` and, on many deployments,
`?user=...&password=...`, so the request target carries a credential and a
database query in the same string.

Access logs are not a contained artifact. They flow to collectors, get indexed,
land in retention, and end up in backups. Anything written there should be
assumed to have spread.

## Decision Drivers

* Secrets in logs are discovered late and are expensive to expunge once
  propagated
* Filtering is a runtime behaviour that can be misconfigured; absence is not
* The rule has to hold across every profile, not just the ones handling
  obvious credentials
* An operator should be able to verify the property rather than trust it

## Considered Options

* **Log `$request` and scrub downstream** — conventional, with redaction in the
  collector
* **Log `$request_uri` with a scrubbing map** — keep the query string but strip
  known-sensitive parameters
* **Log `$uri` only** — the normalised path, with the query string structurally
  absent

## Decision Outcome

Chosen option: **log `$uri` only.**

Downstream scrubbing was rejected because it makes the guarantee depend on a
component this project does not ship, configure, or test. The log is already
written by then; scrubbing is damage control, and it fails open.

Scrubbing known-sensitive parameter names is worse than it looks. It requires
enumerating the parameters worth hiding, which means the default is to leak
anything not on the list, and the list cannot anticipate an application's own
parameters.

Logging `$uri` makes the query string **structurally absent** rather than
filtered. There is no list to maintain and no failure mode where a new
parameter leaks, because no query string reaches the formatter at all.

### Consequences

* Good: credentials, tokens, and query text cannot reach the access stream,
  regardless of what an application puts in its URLs
* Good: the property is directly testable — the suites issue requests carrying a
  password and a column name as parameters and assert neither string appears
  anywhere in the container's output
* Bad: query strings are unavailable for debugging. Reproducing a
  parameter-dependent bug needs the client's own record of the request
* Bad: the guarantee is only as strong as the whole pipeline. A collector, error
  tracker, or front proxy recording full request lines reintroduces exactly what
  this removes, and this project cannot enforce that
* Bad: it differs from the NGINX default, so a contributor copying a
  conventional `log_format` from elsewhere silently undoes it

### Enforcement

`tests/validate_profile_logs.py` rejects any event whose `uri` contains `?`,
and takes `--forbidden` values that must appear nowhere in the captured output.
The profile suites use it to assert that credentials and query text passed as
request parameters do not appear. The assertion was checked against a
deliberately broken configuration logging `$request_uri`, where it fails as it
should rather than passing vacuously.
