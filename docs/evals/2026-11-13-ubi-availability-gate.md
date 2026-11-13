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
this policy PR does not remediate those packages.

The unit suite demonstrates unavailable-to-deferred and available-to-block
behavior with generic fixtures, including the epoch and release boundary. It
also covers issue creation, unchanged state, publication, severity changes,
resolution, recurrence, and retry deduplication. Actual scheduled execution and
issue notification delivery remain unverified until trusted default-branch
execution after merge; the PR deliberately cannot write tracking issues.
Within a day of deployment, verify the issue assignment, artifact links,
initial notification, and suppression of a repeated unchanged observation.

No stalled util-linux refresh PR existed: the earlier investigation stopped
without pushing or opening one. No locks, image bases, runtime properties or
provenance labels were changed by this work.
