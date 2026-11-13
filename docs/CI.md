# Continuous integration

The automation protects repository, workflow, and container development. A
green job represents only checks that have an implemented target and an
inspectable result; planned controls are not represented as passing jobs.

## Current workflows

| Workflow | Triggers | Current purpose |
| --- | --- | --- |
| `CI` | Pull requests, `main`, weekly, manual | Run pinned repository checks, audit Actions, scan configuration, and build, test, inventory, and scan native AMD64 and ARM64 images. |
| `CodeQL` | Workflow changes, `main`, weekly, manual | Analyze GitHub Actions with the security-extended query suite. |
| `OpenSSF Scorecard` | `main`, branch-protection changes, weekly, manual | Publish repository supply-chain findings and SARIF. |

Workflow permissions default to read-only. A job receives a write scope only
when it must publish code-scanning results. The Scorecard job also receives an
OIDC token for authenticated result publication. Third-party Actions are pinned
to full commit SHAs and are tracked by Dependabot.

## Local repository checks

Install the hash-locked pre-commit environment with Python 3.13 or a compatible
Python version:

```console
python -m pip install --require-hashes --only-binary=:all: \
  --requirement .github/requirements/pre-commit.txt
pre-commit install --install-hooks
pre-commit run --all-files --show-diff-on-failure
```

The configured hooks check text normalization, YAML and JSON syntax, merge
markers, unsafe or broken symlinks, oversized files, private keys, shell code,
container build files, GitHub Actions, and prohibited co-author trailers.
The lint job regenerates the requirement trace matrix and fails when the
committed copy has drifted from the requirement documents or the test markers,
so a requirement cannot lose its evidence silently.

The lint job also runs
`python -m unittest tests.test_artifacts tests.test_components
tests.test_nginx_features tests.test_profile_policy tests.test_transfer -v`
to validate the reviewed
lock inputs, both architecture locks, the lock-bound 79-package component
accountability inventory, the NGINX compile-feature inventory,
disconnected-transfer integrity, and fail-closed negative cases without
downloading artifacts.

The `commit-msg` hook applies only after `pre-commit install` installs the
configured hook types. CI separately evaluates repository files but cannot
retroactively validate a local commit message that was never pushed.

## Local Podman development

Rootless Podman under native Linux or WSL2 is the primary local container
workflow. Before relying on a result, record both client and engine details:

```console
podman version
podman info
```

Podman Desktop or a remote Podman machine can run a container process as a
non-root UID while its Linux VM engine itself operates rootfully. That proves
the image's non-root process behavior but does not qualify rootless-host user
namespace behavior. Release evidence will distinguish these cases.

Use Podman inside WSL2 or on native Linux for local rootless-host evidence.
The Bash harness retains compatibility with older development engines where
safe, but compatibility does not make an engine part of the production support
boundary. Quadlet deployment requires Podman 4.6 or newer, and first-release
qualification will record a newer exact vendor-supported baseline.

The README contains the exercised Podman build and smoke commands. Bash is the
single canonical smoke implementation for local Podman and Linux CI, avoiding
behavioral drift between platform-specific suites. Native AMD64 and ARM64 CI
remains required before an image receives supported multi-architecture status.

## External acquisition

Reviewed AMD64 and ARM64 locks, explicit update tooling, and official and
alternate-source acquisition paths are in the repository. The acquisition and
verification tools check exact inventory, size, SHA-256, lock identity, RPM
signatures, approved signing fingerprints, NEVRA, architecture, and source-RPM
identity before a bundle is exposed to assembly. Unit tests cover atomic
publication and fail-closed inventory and source-map behavior without
downloading artifacts.

Native image jobs acquire and verify their matching bundle, preload the exact
digest-pinned UBI bases, and build with Podman using `--network none` and
`--pull=never`. They also prove that the build rejects a wrong lock identity
and cannot fetch an unavailable base. Before assembly, isolated copies of the
real bundle prove rejection of tampering, signature removal, signer mismatch,
wrong version, wrong architecture, missing RPMs, and additional RPMs. The
jobs also compare every RPM's publisher-supplied license tag, source RPM, and
vendor header with `artifacts/components.json`. The completed image is
transferred by local archive into Docker solely for the
existing compatibility smoke, HTTP and TLS profile qualification, and scanner
steps; that transfer performs no image build or registry pull.

The official public source is the default. An alternate approved source can be
selected through protected CI configuration, but private endpoints,
credentials, and private CA configuration must not enter this repository or
the container build. Verification remains identical after either source
downloads the artifacts. See
[External artifact acquisition](ARTIFACT-ACQUISITION.md).

[The assurance-pipeline diagram](architecture/README.md#assurance-pipeline)
shows the order these stages run in and what each produces.

## Assembly isolation

Four properties are claimed of assembly: it cannot pull an image, reach a
package network, recalculate the dependency closure, or expose acquisition
credentials.

The first two are enforced at run time and proven by the native negative
suites. The remaining evidence reads the build definition and context rules
rather than running a build, because a context carrying a credential or a
definition that *would* resolve given the chance is a latent failure that a
passing hermetic build does not reveal. Those checks run in the lint job on
every change.

## Reviewed input drift

Dependabot proposes updates for GitHub Actions, pre-commit hooks, and the
pinned Python assurance tools. It cannot see the inputs this project pins
itself, so a scheduled workflow compares the reviewed NGINX package, its
signing key, the UBI base digests, and the locked closure against what the
publishers currently offer, and keeps one `input-drift` issue current with the
result. RPM closure resolution remains a reviewed operation: this check reports
its size and explains that base/package changes imply a closure refresh; it does
not resolve packages.

The issue body is the current-state dashboard. Body edits do not notify the
owner, so the workflow assigns the issue to `joey-huckabee` while drift is
present and posts a short comment only when the drift state changes. Comments
list newly moved inputs, changed pinned/available values, and resolved inputs.
There are no mentions or weekly comments for unchanged drift. Assignment lets
the owner receive issue comments without watching the whole repository; delivery
still follows the owner's GitHub notification preferences.

A complete zero-drift report produces one resolution comment and closes the
issue. When drift returns, the workflow reopens that issue, assigns it, and
comments. With no previous issue and no drift it does nothing. Open issues
without a checkpoint (including #42) get a one-time baseline notification on the
first complete run. It prefers an open labeled issue, otherwise the most recent
closed one, rather than creating a weekly issue.

It **reports only**. It edits no lock, makes no commit, and opens no pull request.
A refresh is a reviewed operation. Top-level permissions remain `contents: read`; only the reporting job adds
`issues: write`. Actions remain pinned by
full SHA. Scheduled and manual reporting runs share a concurrency group and do
not cancel an in-progress report.

A source that cannot be read is reported as unreachable rather than as
unchanged. Silence from a publisher is not evidence that nothing moved. An
incomplete snapshot (including an absent digest or empty package index) fails
the reporting step before changing the issue, so it cannot falsely close it.
The workflow retains the report artifacts and step summary for diagnosis;
the next complete run compares with the last complete checkpoint.

A changed signing key is surfaced as a key rotation rather than an update,
because confirming a new fingerprint needs independent publisher-controlled
references before it is trusted.

### State and reuse in sibling repositories

`scripts/check_input_drift.py --json-output drift.json > drift.md` produces both
formats from one collection. JSON retains full key and base digests. The pure
`decide(report, issue)` function in `scripts/report_input_drift.py` hashes a
canonical, sorted mapping of moved input names to their pinned/available values.
Notes, row order, and unchanged inputs do not affect the fingerprint. The hidden
`input-drift:v1` body marker contains the fingerprint, previous values, and a
transition sequence, encoded as base64 JSON. Keep this marker when editing the
issue; malformed checkpoints fail reporting rather than silently resetting it.

The adapter verifies assignment and reopens before commenting, and writes the
body checkpoint only after the comment succeeds. It skips assignment requests
when the owner is already assigned and fails reporting if assignment is refused. A hidden sequence/fingerprint marker on each
comment lets a retry detect an already-posted notification if the subsequent
body write failed. The sequence permits the same transition to notify again
after resolution and recurrence. A failed comment leaves the checkpoint and
open issue intact for retry.

To reuse this pattern, copy the reporter and its tests, keep a stable unique
`area` per input, and provide the detector's JSON fields: `drift` plus `findings`
with `area`, `pinned`, `available`, and `drifted`. Supply a Markdown dashboard from
the same snapshot. Set `--repository` and `--assignee` for the sibling repo, use
one dedicated issue label, retain the workflow concurrency and permission
boundaries, and include the tests in that repo's lint job. No additional Python
dependencies or secrets are needed. Here the tests are already included through
`python -m unittest tests.test_input_drift -v`.

### Verify notifications after merge

The live reporting workflow is verified on `main` after this PR merges. Do not
edit locks or fabricate drift in the production issue to test notifications.

1. In Actions, select **Reviewed input drift**, then **Run workflow**, selecting
   `main`. CLI equivalent:
   `gh workflow run input-drift.yml --repo datopsis/nginx-ubi --ref main`.
2. Inspect the run's `report drift` job, step summary, and `input-drift-report`
   artifact. On a complete report with drift, #42 should remain the single open
   issue, be assigned to `joey-huckabee`, contain the current table and hidden
   checkpoint (visible when editing the body), and have one baseline/change
   comment. Check the owner's GitHub notification inbox for that issue. If no
   drift remains, expect one resolution comment and a closed issue instead.
3. Dispatch again while upstream values are unchanged. Confirm the body is
   refreshed and the comment count does not increase. The reporting log should
   say `comment: False`.
4. After a genuine upstream change, dispatch again and check that exactly one
   comment describes the delta. After a reviewed input refresh resolves all
   drift, dispatch to confirm one resolution comment and closure; dispatch once
   more to confirm silence. On subsequent upstream drift, confirm the same
   issue reopens with assignment and one new comment.

The offline tests cover all those transitions, legacy migration, incomplete
reports, full digest comparison, and failures between comment and checkpoint
writes without sending GitHub notifications. If a source is unavailable during
verification, inspect the retained report and rerun when it recovers; the old
issue state is deliberately preserved.

## Release workflow

`.github/workflows/release.yml` runs only for a pushed tag. There is no branch
trigger, no schedule, and no manual dispatch, so a release is caused by
creating an immutable tag and by nothing else.

Permissions are read-only at the workflow level and widened per job: the
validation job stays read-only, the build jobs add `packages: write` and
`id-token: write`, and only the final job holds `contents: write` and
`attestations: write`.

Before anything is built, the workflow requires that the tagged commit is an
ancestor of `main` and that the tag satisfies
[the version contract](VERSION.md). `scripts/release_tag.py` checks the
pattern, that the date is a real calendar date and not in the future, that the
NGINX version and UBI major match the artifact lock, that the tag is not
already published, and that the daily sequence continues from the highest used
rather than back-filling a gap. `tests/test_release_tag.py` covers those rules
in the lint job, so they are exercised on every change rather than only during
a release.

The signature and both attestations are bound to the **manifest digest**, never
to a tag, and the workflow verifies its own signature before publishing
evidence.

**This workflow has never been executed.** Rehearsing it end to end from an
untagged candidate is an open roadmap item; until then its behaviour is
asserted by reading rather than by evidence.

## Image assurance

The `main` branch is protected and requires these checks. The README carries
status badges for the build and code-scanning workflows and for the OpenSSF
Scorecard result, so a failing gate is visible without opening the Actions tab.

The stable protected check names are `lint`, `configuration security`, and
`image`. The aggregate `image` check requires both native architecture jobs.
The implemented image pipeline performs:

1. Trivy build-configuration scanning.
2. Verified, network-disabled, no-pull native architecture builds followed by
   native Podman and Docker-compatibility restricted-runtime, HTTP, and TLS
   profile
   tests. They cover
   the exact 79-RPM manifest, NGINX compile-feature and empty dynamic-module
   inventories, declared and arbitrary runtime identities, process privileges,
   a read-only root, hardened temporary storage, static content, health and log
   behavior, worker-replacing reload, active-request graceful shutdown, and
   actionable startup failures. The profile suite additionally qualifies
   static-serving and reverse-proxy defaults, structured JSON events,
   correlation IDs, query exclusion, forwarded headers, method and path denial,
   and upstream failure. The TLS suite generates ephemeral CAs and leaf
   certificates to test TLS 1.2/1.3, mTLS, leaf renewal, hostname and chain
   verification, client and upstream CRL enforcement, overlapping-CA trust
   rotation, lifecycle deadline monitoring, negative trust cases, and secret-
   safe diagnostics.
3. Trivy image vulnerability scanning.
4. SPDX inventory generation with Syft.
5. Independent fixed High/Critical vulnerability gating with Grype and a
   retained full finding inventory.
6. Architecture-specific artifacts and non-pull-request SARIF publication.

Tailored OpenSCAP evaluation against an ownership-preserving filesystem export
will be inserted after the runtime tests when its profile and result semantics
are reviewed. Branch protection must not require `image` until its aggregate
check exists on the default branch. Once present and proven, `image` becomes a
strict, required, up-to-date check alongside the current repository checks.

## Phase A proxy rehearsal and label binding

Both native image jobs run `tests/image-labels.py` immediately after assembly.
It compares `org.opencontainers.image.revision` to `git rev-parse HEAD` and
`io.datopsis.artifact-lock.sha256` to SHA-256 of the exact architecture's
`artifacts/locks/<arch>.json`, and checks image architecture. For pull requests,
HEAD is the checkout's synthetic merge commit; release builds use the tagged
source commit. The release workflow runs the same check.

`tests/tls-proxies.sh` then exercises the Lakekeeper and Sail stand-ins under
rootless Podman on both architectures, before image vulnerability scanning.
It uses the runner's Go 1.24+ standard library, disables module acquisition,
and mounts the native static fixture without altering image contents.
See the [profile guide](CONFIGURATION-PROFILES.md#lakekeeper-and-sail-tls-fronts-phase-a)
for each positive and negative assertion. Each assertion prints a PASS record;
failures stop the job. Existing Podman and Docker smoke/profile/TLS tests,
mutation tests, scanners and aggregate gates remain required and unchanged.
