---
status: accepted
date: 2026-09-18
decision-makers: Joey
---

# Treat the Application Server SRG as not applicable to this component

## Context and Problem Statement

[ADR-0009](0009-control-catalogue-and-baseline.md) settled that DISA SRGs and
STIGs are cross-references attached to the 800-53 spine, and that every source
is pinned by URL, release, and SHA-256 before any mapping is made against it.

The requirement-source register named four DISA cross-references. Two resolved
immediately: the Web Server SRG and the RHEL 9 STIG. Two did not, and were
recorded as `unresolved` with the reason rather than omitted. The register also
recorded an open question about one of them: whether the **Application Server
SRG** applies to this component at all, given that the image serves and proxies
HTTP rather than hosting an application runtime.

That question had been answered by assumption. An SRG is either in scope or it
is not, and an assessor reading the component definition is entitled to know
which, and on what basis. Guessing in either direction is the failure mode:
including an inapplicable SRG manufactures 137 rules of hand-waving, and
excluding an applicable one silently drops a body of guidance.

## Decision Drivers

* The applicability of a cross-reference should be decided from its contents,
  not from its title
* An assessor will ask why a named SRG is absent; "we assumed" is not an answer
* A not-applicable determination is a claim in its own right and needs evidence
* The decision must be cheap to reverse if the component's function changes

## Considered Options

* **Map it** — treat the Application Server SRG as a cross-reference alongside
  the Web Server SRG, marking individual rules not applicable as they arise
* **Exclude it without pinning** — leave it `unresolved` and out of scope
* **Pin it, and record it as assessed not applicable** — retrieve the package,
  fix its identity by digest, read it, and record the determination against
  that exact revision

## Decision Outcome

**Pin it, and record it as assessed not applicable.**

The package was retrieved and pinned as `V4R5`, benchmark date 01 Jul 2026,
SHA-256 `ea33d7f1…`, in `artifacts/requirement-sources.json` with
`"role": "not-applicable"`. Pinning a source this project does not map against
looks redundant until the determination is questioned: the digest is what ties
the determination to the revision it was made against.

### The evidence

The V4R5 XCCDF contains 137 rules. Counted across them:

| | |
| --- | --- |
| Rules presupposing a management or administrative interface | 23 |
| Rules presupposing hosted applications | 6 |
| Rules presupposing either | **27** |
| Rules referring to accounts | 18 |

This image has no management interface, no user accounts, and hosts no
application. Those rules are not merely unsatisfied; the objects they govern do
not exist here. The remainder — logging, TLS, session handling — are the
general requirements the **Web Server SRG** states for a component of this
kind, and it states them in terms that match what this image actually is.

The Web Server SRG therefore remains the applicable DISA cross-reference for
this component's function, as the register already recorded.

### Consequences

* Good: the determination cites a revision and a count, so a reader can check it
  rather than accept it
* Good: no cross-reference work is spent on a body of guidance whose subject
  this component is not
* Good: reversal is cheap. The source is already pinned, so revisiting means
  changing a role and authoring mappings, not re-establishing identity
* Bad: a reader scanning the register for DISA coverage sees an
  application-server SRG present and may assume it is mapped. The
  `not-applicable` role and this ADR are the mitigation, and a structural check
  requires the basis to be recorded
* Bad: the determination is made against V4R5 only. If DISA broadens the SRG's
  scope in a later release, this must be revisited — which is exactly what
  pinning by digest makes visible

### The Container Platform SRG is a different problem

It is not a scope question. The document exists and is officially released —
**V2R1**, 24 July 2024 — and the filename follows DISA's published convention,
`U_Container_Platform_V2R1_SRG.zip`. It is simply no longer served from the
public download path: that URL returns 404 while `U_Web_Server_V3R3_SRG.zip`
returns 200 from the same directory, so the path and method are sound and the
file is genuinely not there.

The download index cannot be used to find its current location either. It is
now a JavaScript-rendered portal whose HTML contains no download links at all,
so it cannot be resolved programmatically.

It therefore stays `unresolved` — with the release, filename, and this finding
recorded, so whoever retrieves it is not repeating the search. It is a missing
cross-reference, not a missing part of the spine, and it blocks nothing.

### Enforcement

`tests/test_control_model.py` requires a source whose role is `not-applicable`
to record the basis for that determination, on the same principle that an
unpinned source must record why it is unpinned: a determination without a
stated reason is indistinguishable from an omission.
