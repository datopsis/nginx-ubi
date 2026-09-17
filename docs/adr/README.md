# Architecture decision records

Each record captures one accepted decision, the problem it answered, the
options weighed, and what the project gave up in exchange.

## Conventions

Records are numbered sequentially from `0001`. **A number is permanent.** A
decision that is later reversed is not deleted or renumbered: its record is
marked `superseded` and names the record that replaced it, so the reasoning
behind the original choice survives the choice itself.

The file name is `NNNN-short-slug.md`. Every record carries frontmatter with
`status`, `date`, and `decision-makers`, and the sections in
[`0000-template.md`](0000-template.md).

`status` is one of:

| Status | Meaning |
| --- | --- |
| `proposed` | Written, not yet accepted |
| `accepted` | In force |
| `superseded` | Replaced; names the superseding record |
| `deprecated` | No longer applies, with nothing replacing it |

The `date` is the date the decision was accepted, not the date the record was
written. The records below were written after the fact, so their dates are the
dates the decisions actually took effect in the repository.

## What belongs here

A decision belongs in an ADR when reversing it would be expensive, when it
gave up something a reader would otherwise expect to have, or when the
reasoning is not recoverable from the code. A decision that is obvious from
reading the configuration does not need a record.

Where a decision is also enforced — by a test, a CI gate, or a lint rule — the
record says so, because an unenforced decision decays quietly.

## Index

| # | Decision | Status |
| --- | --- | --- |
| [0001](0001-hermetic-assembly-from-verified-bundles.md) | Assemble the image from verified local bundles with networking disabled | accepted |
| [0002](0002-open-source-nginx-only.md) | Package open source NGINX only | accepted |
| [0003](0003-podman-primary-docker-compatibility.md) | Podman is the primary runtime; Docker is a compatibility target | accepted |
| [0004](0004-log-the-path-never-the-request-line.md) | Log the request path, never the request line | accepted |
| [0005](0005-never-retry-non-idempotent-requests.md) | Never retry a non-idempotent request against another upstream | accepted |
| [0006](0006-answer-429-when-limiting.md) | Answer `429` rather than `503` when a limit rejects a request | accepted |
| [0007](0007-liveness-independent-of-upstreams.md) | Keep liveness independent of upstream health | accepted |
| [0008](0008-hand-authored-svg-diagrams.md) | Author diagrams as hand-written SVG with no rendering toolchain | accepted |
