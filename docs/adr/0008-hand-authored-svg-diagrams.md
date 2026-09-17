---
status: accepted
date: 2026-09-17
decision-makers: Joey
---

# Author diagrams as hand-written SVG with no rendering toolchain

## Context and Problem Statement

The roadmap calls for profile, use-case, architecture, data-flow, trust, and
control-ownership diagrams. Diagrams in a repository like this are reviewed
material: they appear in a cyber-review package, and a reader has to be able to
tell what they assert.

The usual approach is a text source compiled to an image. That makes the
diagram diffable, but it introduces a renderer, and the renderer becomes a
prerequisite for anyone who needs to change a diagram — including on a
locked-down host where installing one is a request rather than a command.

It also introduces a drift problem. A committed source and a committed render
can disagree, so the repository needs a check that they match, which is another
moving part that exists only because of the toolchain.

## Decision Drivers

* Diagrams must render on GitHub without a build step
* Changing a diagram should not require installing anything
* Reviewers need to see exactly what is published, not a source that produces it
* This project already treats added prerequisites as a cost, not a detail
* Layout control matters: these diagrams carry trust boundaries and ownership
  splits, where an auto-layout engine placing a box in the wrong region changes
  what the picture claims

## Considered Options

* **PlantUML source compiled to SVG** — the approach used in the reference
  repository; needs Java and the PlantUML jar
* **Mermaid** — renders natively in GitHub markdown with no toolchain at all
* **Hand-authored SVG** — the published file is the source

## Decision Outcome

Chosen option: **hand-authored SVG.**

Mermaid is the strongest rejected option and deserves a real answer, because it
needs no toolchain either. It loses on two counts. Its layout is chosen by the
renderer, so a trust-boundary diagram cannot reliably put a box on the correct
side of a boundary — and in a diagram whose entire purpose is which side of a
line something sits on, that is not cosmetic. It also renders only inside a
Markdown code fence on platforms that support it, so a diagram cannot be
referenced as an image from a document, an issue, or a release asset, and does
not exist as a file at all.

PlantUML fixes the referencing problem and keeps a diffable source, at the cost
of a Java prerequisite and a source-versus-render drift check. For the number of
diagrams this project needs, that machinery costs more than it returns.

Hand-authored SVG makes the published file the source. There is nothing to
compile, nothing to install, and no possibility of the source and the render
disagreeing, because they are the same file.

### Consequences

* Good: no prerequisite to view or change a diagram, on any host
* Good: exact layout control, which matters most for the boundary and ownership
  diagrams these are mostly going to be
* Good: the reviewed artifact and the published artifact are the same bytes
* Good: the source-versus-render drift check the roadmap called for has no
  subject and is not needed
* Bad: diffs are XML and read poorly. A moved box shows as changed coordinates
  rather than as a changed relationship
* Bad: authoring is slower, and geometry is maintained by hand. A diagram that
  needs frequent structural change will be painful
* Bad: consistency between diagrams is a convention rather than a property of a
  renderer, so it has to be held by review
* Bad: no automatic layout means a large diagram is genuinely laborious, which
  is a standing pressure toward keeping them small — usually a good outcome, but
  it will occasionally be the wrong reason to split one

### Enforcement

`tests/test_diagrams.py` checks every committed SVG: it must parse as XML, must
declare a `viewBox` so it scales, and must contain no script element and no
reference to an external resource. A diagram that reaches for a remote font or
image would render differently for different readers, and one carrying script
is not a diagram.

Consistency of visual style is not enforced and is held by review.
