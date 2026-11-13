# UBI availability gate: native evaluation

The owner decision defines an RPM fix as blocking when the fixed-or-newer
package is advertised by the image's UBI repositories. This evaluation records
actual observations, not exceptions or inputs to the policy.

## Assumptions and method

- Repository identity: inspected both architecture manifests of the exact
  lock-selected UBI 9.8 minimal builder. Both enable BaseOS, AppStream and
  CodeReady Builder. The native query retained the original `ubi.repo` hash
  `f59e1e4c2f20048ef3204f5c81d23b04aac53a7d789b1f4d055a937867109f13`.
- Query semantics: use [DNF's available-package query](https://dnf.readthedocs.io/en/latest/api_queries.html)
  with exact name and architecture filters, after
  [loading fresh repository metadata](https://dnf.readthedocs.io/en/latest/api_base.html).
  Unavailable repos cannot be skipped. This has the same publication meaning
  as repoquery; it does not promise a complete future dependency transaction.
- Ordering: use the distribution's RPM comparator, including epoch and release,
  rather than lexical or semantic-version comparisons. The unit tests exercise
  numeric releases, epochs, prereleases, and an additional release suffix.
- Input semantics: independently parse full Trivy and Grype reports. Native
  results below establish the actual report shapes, package identities and
  repository results. Non-RPM fixes cannot use the availability deferral.
- Failure behavior: tests exercise missing repos, query exceptions, timeouts,
  invalid versions, identity mismatches, missing reports, and a container that
  exits zero without writing evidence. Each blocks.

## Live result

[Native CI run 43366111788](https://github.com/datopsis/nginx-ubi/actions/runs/43366111788)
exercised commit `994d3fb840be38edeaa026c41de47c6c546a09ec` on both native
architectures. Raw reports and `security-results/ARCHITECTURE/gate.json` are
retained in that run's `image-security-*` artifacts. No scanner artifacts are
committed here.

The previous assumption that the util-linux fixes were absent is now false.
Both public UBI repositories advertise `2.37.4-28.el9_9.1`, which satisfies the
vendor fixes for CVE-2026-53613 and CVE-2026-53615. The gate correctly blocks
both; demonstrating live deferral would misrepresent the repository state.
Expat `2.5.0-9.el9_9.4` is also available and correctly blocks the three fixable
Trivy expat findings. No repository-query errors occurred.

| Scanner | Architecture | Blocking High | Deferred High | Unfixed High | Critical (all states) |
| --- | --- | ---: | ---: | ---: | ---: |
| Trivy | amd64 | 17 | 0 | 2 | 0 |
| Trivy | arm64 | 17 | 0 | 2 | 0 |
| Grype | amd64 | 14 | 0 | 3 | 0 |
| Grype | arm64 | 14 | 0 | 3 | 0 |

Counts are package/finding matches, not unique CVEs. The live cases covered
16 distinct package/architecture queries: expat plus libblkid, libfdisk,
libmount, libsmartcols, libuuid, util-linux and util-linux-core on each
architecture. Across both scanners and architectures, 62 vendor-fixed matches
blocked and 10 matches without a vendor fix remained reported. The query/gate
step, including query-tool installation, took five seconds on AMD64 and three
seconds on ARM64 in this run; these are observations, not performance promises.

The fourteen util-linux matches per scanner/architecture consist of each of
the two CVEs on seven binary RPMs. Trivy additionally blocked expat findings
CVE-2026-66046, CVE-2026-77214 and CVE-2026-93990. Both scanners retained the
unfixed expat findings CVE-2026-115506 and CVE-2026-76641. Grype additionally
retained the unfixed nginx finding CVE-2026-93479. Scanner databases differ;
the gate evaluates each independently rather than requiring agreement.

## CI and remaining evidence boundary

Lint, configuration security and CodeQL passed. Both native image jobs passed
acquisition, signature/component verification, negative RPM and hermetic-build
tests, and all Podman/Docker restricted-runtime, HTTP and TLS tests. Both
failed only at the new vulnerability gate, and the required aggregate failed
accordingly. This is the expected result for the unchanged, vulnerable locks;
that initial revision had not yet remediated those packages.

The unit suite demonstrates unavailable-to-deferred and available-to-block
behavior with generic fixtures, including the epoch and release boundary. It
also covers issue creation, unchanged state, publication, severity changes,
resolution, recurrence, and retry deduplication. Actual scheduled execution and
issue notification delivery remain unverified until trusted default-branch
execution after merge; the PR deliberately cannot write tracking issues.
Within a day of deployment, verify the issue assignment, artifact links,
initial notification, and suppression of a repeated unchanged observation.

No stalled util-linux refresh PR existed: the earlier investigation stopped
without pushing or opening one. The initial gate evaluation used the original locks and image bases. The
subsequent refresh below updates the locks in the same PR.


## Native lock refresh in the same PR

[Resolver run 43367684307](https://github.com/datopsis/nginx-ubi/actions/runs/43367684307)
passed on native AMD64 and ARM64 using the existing `fetch-lock-inputs.py`,
`resolve-lock.sh` and `render-lock.py` tooling. Both candidates were independently
re-rendered from retained binary/source inventories and compared before adoption.
The only rendering difference was the independent rendering time; the committed
locks are the original candidate bytes from CI.

Both architectures retain 79 packages with no additions/removals, unchanged
NGINX seeds, signing keys, package signers, repositories, vendors, and license
tags. Their RPM component headers agree exactly. Thirty-six binary RPM versions
changed on each architecture as part of resolving the full dependency closure;
source RPM identities and hashes changed accordingly. No unchanged NEVRA was
republished with different bytes. The component inventory is rebound to both
new locks and retains the publisher-supplied license tags verbatim.

| Packages (both architectures) | Old epoch:version-release | New epoch:version-release |
| --- | --- | --- |
| acl, libacl | `0:2.4.0-1.el9_8` | `0:2.4.0-2.el9` |
| audit-libs | `0:3.1.5-8.el9` | `0:3.1.5-9.el9` |
| coreutils, coreutils-common | `0:8.32-41.el9_8.1` | `0:8.32-43.el9` |
| crypto-policies | `0:20260224-1.gitea0f072.el9_8` | `0:20260714-1.git65b74f7.el9` |
| dbus, dbus-common | `1:1.12.20-8.el9` | `1:1.12.20-10.el9` |
| dbus-broker | `0:28-9.el9_8` | `0:28-10.el9_9` |
| expat | `0:2.5.0-6.el9_8.7` | `0:2.5.0-9.el9_9.4` |
| glibc, glibc-common, glibc-minimal-langpack | `0:2.34-284.el9_8.4` | `0:2.34-290.el9_9` |
| libattr | `0:2.6.0-1.el9_8` | `0:2.6.0-2.el9` |
| libblkid, libfdisk, libmount, libsmartcols, libuuid, util-linux, util-linux-core | `0:2.37.4-25.el9` | `0:2.37.4-28.el9_9.1` |
| libgcc | `0:11.5.0-14.el9` | `0:11.5.0-17.el9_9` |
| libseccomp | `0:2.5.2-2.el9` | `0:2.5.6-1.el9` |
| libselinux | `0:3.6-3.el9` | `0:3.6-4.el9` |
| openssl, openssl-libs | `1:3.5.8-2.el9_8` | `1:3.5.9-1.el9_9` |
| pam | `0:1.5.1-28.el9_8.1` | `0:1.5.1-29.el9` |
| procps-ng | `0:3.3.17-14.el9` | `0:3.3.17-15.el9` |
| redhat-release | `0:9.8-1.0.el9` | `0:9.9-1.0.el9` |
| shadow-utils | `2:4.9-16.el9` | `2:4.9-17.el9` |
| systemd, systemd-libs, systemd-pam, systemd-rpm-macros | `0:252-67.el9_8.6` | `0:252-79.el9_9` |
| tzdata | `0:2026f-1.el9_8` | `0:2026f-1.el9_9` |
| xz-libs | `0:5.2.5-8.el9_8.1` | `0:5.2.5-8.el9_9.1` |

The UBI 9.8 minimal/micro manifest-list pins stay unchanged because their
public `/ubi9/9/` repository configuration already exposes the fixes. The
resolved `redhat-release` RPM is now 9.9; base tag and resolved RPM release
are recorded separately rather than pretending the original base was rebuilt.

| Input | Previous SHA-256 | New SHA-256 |
| --- | --- | --- |
| amd64 lock | `24e544b4085ecaef7d9bb486a42936f9dd57457ccd4d3c6fd1107f8620454214` | `5eda00936d279befa19bce2dff5592dbcff3bf6d5067899025dbd431d8a54216` |
| arm64 lock | `37131798777f2e17d26a96f7bdea3fc8c6c7e3e295ddaad5fe75f0a1b44faa92` | `733d912e914cd94eeefa48da08671f768ee49ea26bcd2762370bc8b5a107552a` |
| builder base manifest list | `4b79c93106c14ad1c234907f83441ff0e4f8d24e78426a36e159098e9f7e6fa5` | unchanged |
| runtime base manifest list | `6d9eff186ce3ccf399c1835265e7fd3f83bd112cc3422da2d39fd44e234aab59` | unchanged |

The existing build did not set this repository's revision or artifact-lock
labels. Assembly now sets `org.opencontainers.image.revision` from the actual
Git checkout and `io.datopsis.artifact-lock.sha256` from the architecture lock.
Native smoke tests compare both labels with those exact inputs under Podman
and Docker. These labels do not replace release attestations or signatures.

Post-refresh native runtime, RPM verification, and scanner results are retained
in the PR's CI artifacts and summarized in its description. The earlier table
above remains the measured pre-refresh baseline, not the final image result.
