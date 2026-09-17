---
status: proposed
date: YYYY-MM-DD
decision-makers: Name
---

# Short imperative title naming the decision

## Context and Problem Statement

What forced the decision. State the problem as it was actually encountered,
including what was observed rather than only what was feared. A reader who
arrives years later should be able to tell whether the problem still exists.

## Decision Drivers

* The constraints and priorities that shaped the choice
* One per line, specific enough to argue with

## Considered Options

* **Option A** — one line on what it is
* **Option B** — one line on what it is
* **Do nothing** — the status quo, where that was a real candidate

## Decision Outcome

Chosen option: **Option B.**

Why this one, and — more usefully — why the rejected options were rejected. An
option that was genuinely viable should be recorded as viable, with the reason
it lost, rather than dismissed.

### Consequences

* Good: what this buys
* Bad: what this costs, stated plainly
* Bad: what a future maintainer is likely to trip over

### Enforcement

How the decision is held in place: a test, a CI gate, a lint rule, or nothing
at all. Say "nothing" where that is the truth, because an unenforced decision
decays quietly.
