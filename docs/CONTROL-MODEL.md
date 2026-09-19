# Control model

How a control is represented in the OSCAL Component Definition, decided before
any control is authored so that the first entries and the last ones have the
same shape.

The catalogue, baseline, consumer, and scope decisions behind this are in
[ADR-0009](adr/0009-control-catalogue-and-baseline.md). The pinned sources are
in `artifacts/requirement-sources.json`.

## What is being produced

A component definition describing what **this image** contributes to a control,
and what it does not. It is not a System Security Plan, and it cannot become
one: an SSP depends on the deployed boundary, the organization's parameters,
and an assessor's judgement.

The reader is an external assessor who will ingest this into their own package.
That reader decides what the artifact must make unambiguous.

## Scale

| | |
| --- | --- |
| Catalogue | 800-53 Rev 5.2.0, 20 families, 1196 controls and enhancements |
| High baseline selects | 370 |
| Base controls, first pass | **188** |
| Enhancements, second pass | **182** |

## Origination is mandatory

Host expectations are in scope and the reader is an assessor. A control
without a machine-readable origination value can be read as a claim that
something is satisfied, so every control carries one, and a responsible role.

| Origination | Meaning | Who acts |
| --- | --- | --- |
| `image-owned` | The image implements this, and this repository can evidence it | Image project |
| `deployment-configured` | Satisfied only if the deployment configures it correctly; the image makes it possible | Deployment profile |
| `host-inherited` | The host or orchestrator satisfies this; the image relies on it | Host or orchestrator |
| `organization-inherited` | The organization satisfies this outside any technology | Organization |
| `not-applicable` | The control does not apply to a component of this kind, with a reason | — |
| `research-required` | Applicability is not yet determined; not a claim in either direction | Image project |

`image-owned` is the only value that asserts this project satisfies anything.
Every other value is a hand-off, and must name what the other party has to do.

**A control may not be marked `image-owned` without a verification pointer.**
That pointer cites a requirement identifier from [the requirement
tree](L1-REQ.md), whose evidence is resolved by [the trace
matrix](TRACE-MATRIX.md). This is what stops a control claiming an obligation
the product never stated.

## Structure of one control

```json
{
  "control-id": "cm-6",
  "props": [
    {"name": "origination", "ns": "https://datopsis.example/ns/oscal", "value": "image-owned"},
    {"name": "requirement", "ns": "https://datopsis.example/ns/oscal", "value": "L1-IMG-002"},
    {"name": "cross-reference", "ns": "https://datopsis.example/ns/oscal",
     "value": "disa-rhel9-stig:RHEL-09-215015", "class": "disa-rhel9-stig"}
  ],
  "responsible-roles": [{"role-id": "image-project"}],
  "description": "What the image does, in terms an assessor can check.",
  "remarks": "Limitations, and what the image cannot do."
}
```

Rules:

- `origination` exactly once, from the table above
- `responsible-roles` at least one, matching the origination
- `requirement` at least once when `origination` is `image-owned`, and each
  value must exist in the requirement tree
- `cross-reference` zero or more, each prefixed with a source `id` from the
  requirement-source register, so a reader can tell which pinned revision the
  mapping was made against
- `remarks` carries limitations; an `image-owned` control that has none is
  usually one that has not been thought about

## Cross-references attach to the spine

A cross-reference is a property on an 800-53 control, never a separate entry.
The spine is the only place a control exists, so there is one record per
control rather than three that can disagree.

A cross-reference cites the source `id` from the register, which is pinned by
digest. A mapping made against `V3R3` stays attached to `V3R3` when DISA
replaces it, and the difference is then visible rather than silent.

CIS is cited by identifier only. Its terms restrict redistribution, so no
benchmark text is reproduced here.

## Assessment methods

Every `image-owned` control carries an examine, test, or interview method with
the owner, defaults, configuration and restart behaviour, dependencies, impact,
loss-of-function statement, limitations, and an evidence pointer.

Controls that are not `image-owned` do not carry an assessment method. Supplying
one would describe an assessment this project cannot perform.

## What a High baseline looks like here

Most of 188 base controls will not be `image-owned`. A container image does not
satisfy personnel screening, physical access, or contingency planning, and
saying so precisely is more useful to an assessor than a thin claim.

That distribution is the expected outcome. A component definition claiming a
large share of a High baseline would be the result worth doubting.

## Enforcement

`tests/test_control_model.py` holds the structural rules: origination present
and valid, responsible role present, requirement identifiers resolving against
the tree, cross-references naming a registered source, and assessment methods
only where the control is `image-owned`.

These checks exist before the controls do. A property that is merely
conventional gets dropped under deadline, which is exactly when the overclaim
it prevents matters most.
