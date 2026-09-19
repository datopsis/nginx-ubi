---
status: accepted
date: 2026-09-18
decision-makers: Joey
---

# Map controls against 800-53 High as the spine, with SRG, STIG and CIS as cross-references

## Context and Problem Statement

`docs/SECURITY-CONTROLS.md` groups the product's behaviour into control
objectives and names who owns what. It does not enumerate controls, and it says
so. The deliverable it precedes is an OSCAL Component Definition with generated
CSV and human-readable views.

That work cannot start until several questions are answered together, because
each one changes the shape of every control entry: which catalogue, at which
baseline, for whom, covering what, and how a control this image does not
satisfy is represented. Answering them one at a time as the writing proceeds
would produce a document whose early entries do not match its later ones.

None of these are technical questions with a correct answer. They are scoping
decisions about who the artifact is for.

## Decision Drivers

* An assessor must be able to ingest the result into a System Security Plan
* This project can only evidence what it can test, and most controls in any
  catalogue are not the image's to satisfy
* A control mapping is meaningless without a known catalogue revision
* The requirement tree and trace matrix already exist and should supply the
  verification evidence rather than a parallel set of claims
* Scope decided late is scope re-done

## Considered Options

Each question was put separately.

* **Catalogue** — 800-53 Rev 5, DISA SRG plus RHEL 9 STIG, both, or CIS
* **Baseline** — Low, Moderate, High, or component-tailored with no baseline
* **Consumer** — external assessor, internal engineering, customer evidence, or
  all three from one source
* **Scope** — image only, image plus deployment, or image plus deployment plus
  host expectations
* **Enhancements** — base controls first, base and enhancements together, or
  base only with enhancements excluded
* **Origination** — an explicit property per control, omit what the image does
  not satisfy, or describe the split in prose
* **Sources** — pinned by URL and SHA-256, referenced by version, or vendored
* **Sequencing** — spine then cross-references, relevant families first, or
  strict catalogue order

## Decision Outcome

| Question | Decision |
| --- | --- |
| Catalogue | **800-53 Rev 5 as the spine**, SRG, STIG and CIS as cross-references |
| Baseline | **High** |
| Consumer | **External assessor**, as RMF package input |
| Scope | **Image, deployment, and host expectations** |
| Enhancements | **Base controls first**, enhancements in a second pass |
| Origination | **Explicit property and responsible role on every control** |
| Sources | **Pinned by URL, release, and SHA-256** |
| Sequencing | **Spine complete, then cross-references** |

CIS was not rejected so much as reclassified. It is a hardening benchmark
rather than a control catalogue, so it cannot carry an authorization
conversation and cannot be a spine. As a cross-reference it is the most
directly checkable of the three against a container image, which is where its
value is.

800-53 is the spine because OSCAL is NIST's own format and ships a Rev 5
catalogue, so control identifiers resolve natively. Making SRG or STIG the
spine would require a mapping layer between the identifiers and the format
carrying them, maintained by this project, for no gain.

### The two decisions that interact

Choosing **host expectations** as in-scope and **an external assessor** as the
consumer is the combination that needs care. An assessor ingesting this into an
SSP may read a host expectation as a claim that something is satisfied, and
host controls are the furthest thing from anything this repository can test.

The origination decision is what makes that scope safe rather than reckless.
Every control carries a machine-readable origination value — image-owned,
deployment-configured, host-inherited, organization-inherited, or not
applicable — and a responsible role. An assessor filtering on that property can
see what this component actually claims, rather than inferring it from prose.

**Prose alone would not have been sufficient at this scope.** Had the
origination answer been the narrative option, the honest choice would have been
to narrow the scope instead.

### Consequences

* Good: control identifiers resolve against a catalogue an assessor already has
* Good: the requirement tree supplies verification evidence, so a control cannot
  cite an obligation the product never stated
* Good: base-first produces a complete, usable artifact at full family coverage
  before depth is added
* Good: pinned sources mean a mapping is always against a known revision, the
  same discipline the build inputs use
* Bad: this is large, though smaller than estimated when the decision was
  taken. The pinned Rev 5.2.0 catalogue holds 1196 controls and enhancements
  across 20 families; the High baseline selects **370** of them, being **188
  base controls and 182 enhancements**. The first pass is therefore 188, not
  the "roughly 370 base controls" estimated before the catalogue was retrieved.
  The cross-reference pass still revisits every one
* Bad: a High baseline means a large share of controls will record
  organization-inherited or not applicable. That is accurate, and it will look
  sparse to anyone expecting satisfied claims
* Bad: spine-then-cross-reference means every control is visited twice, which is
  more total work than doing both at once, in exchange for each pass being
  conceptually clean
* Bad: the enhancement pass is deferred, so until it lands an assessor working a
  genuine High baseline has a gap to close themselves. It must be recorded as
  outstanding rather than left to be discovered

### Enforcement

Nothing yet. The obligations that need holding are: every control carries an
origination property and a responsible role, every cited requirement identifier
exists in the tree, and every catalogue source resolves to its pinned digest.

Each is mechanically checkable and none is checked today. The checks belong
with the first controls, not after them — an origination property that is
merely conventional will be omitted under deadline, which is exactly when the
overclaim it prevents becomes most likely.
