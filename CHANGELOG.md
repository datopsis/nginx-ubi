# Changelog

All notable changes to this project are recorded in this file.

The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
but container releases use the upstream-derived format documented in
`docs/VERSION.md` rather than Semantic Versioning.

## [Unreleased]

### Added

- Added the Apache License 2.0 for Datopsis-authored work, third-party notices,
  contribution guidance, and a private vulnerability-reporting policy.
- Defined support classifications, published the current development support
  matrix and ownership boundary, and documented repository governance.
- Added Code Owners, a security-aware pull request template, and structured
  public bug-report and private security-reporting routes.
- Established repository guidance for secure, rootless image development and
  review.
- Defined the forward-looking first-release roadmap and evidence lifecycle.
- Defined independent versioning for container releases and repository-only
  revisions.
- Adopted NGINX-version, UBI-major, and UTC release-date versioning; omitted
  the UBI minor version from release tags; and prohibited mutable convenience
  tags for the first release.
- Added the project overview, intended use cases, security design, rootless
  runtime model, and release status.
- Added pinned local pre-commit checks for repository hygiene, shell code,
  container build files, GitHub Actions, private keys, and attribution trailers.
- Added least-privilege CI, CodeQL Actions, Trivy configuration, Zizmor, and
  OpenSSF Scorecard workflows with immutable third-party Action references.
- Added grouped Dependabot updates for Actions, pre-commit hooks, and the
  hash-locked CI Python environment.
- Documented local checks, GitHub automation, planned image assurance, and the
  evidence boundary of Podman Desktop or a remote Podman machine.
- Added a contributor environment record for the exercised Ubuntu WSL2 and
  rootless Podman development setup.
- Added an initial package-manager-free UBI 9 Micro development image using an
  exact Red Hat NGINX RPM build.
- Added rootless NGINX defaults for unprivileged HTTP, read-only-root operation,
  container log streams, `/tmp` runtime state, health checking, and graceful
  shutdown.
- Added a restricted-runtime smoke suite, static landing page, and hardened
  Compose development service.
- Added native PowerShell smoke testing for Podman Desktop development.
- Standardized local runtime testing on the canonical Bash suite with rootless
  Podman under native Linux or WSL2, removing the duplicated PowerShell suite.
- Preserved the complete restricted-runtime test matrix while allowing the
  Shell harness to enforce `no-new-privileges` using the syntax accepted by
  older rootless Podman development engines.
- Added a preview standalone Linux deployment runbook and rootless Podman
  Quadlet covering systemd lifecycle, journald logging, updates, rollback, and
  exact-host qualification.
- Added a component threat model, security-control ownership model, requirement
  analysis method, and cybersecurity evidence checklist.
- Expanded the first-release roadmap with deployment qualification, systemd and
  logging tests, OSCAL/control engineering, requirement-source review, FIPS
  boundary analysis, go-live evidence, and an assurance-completeness gate.
- Added GitHub topics for NGINX, containers, Podman, OpenShift, UBI 9, and
  supply-chain security.
- Extended CI with native AMD64 and ARM64 builds, restricted-runtime tests,
  Trivy image scanning, Syft SPDX inventories, blocking Grype analysis, full
  finding retention, and an aggregate image result.
- Added an initial use-case catalog covering static serving, reverse proxying,
  load balancing, TLS, WebSockets, ClickHouse, health endpoints, and limiting.
- Added a logging guide for container streams, use-case fields, sensitive-data
  rules, and controlled-network responsibilities.
- Documented the exact Red Hat UBI AppStream source and build path for the
  NGINX RPMs, including trust checks and reproducibility limits.
- Evaluated official NGINX stable RPMs as the proposed first-release package
  source and defined migration and acceptance requirements.
- Refreshed the digest-pinned UBI 9.8 Minimal and Micro base images and the
  pinned NGINX module build so the development build resolves
  `openssl-libs-1:3.5.8-1.el9_8` from RHSA-2026:67165 and no longer reuses a
  cached package layer that predates the errata. The previously pinned
  `nginx-core` build had been superseded and was no longer resolvable, so the
  legacy pipeline was succeeding only from that cache.
- Approved the official NGINX stable channel, selected
  `nginx-2:1.30.4-1.el9.ngx` for first-release implementation qualification,
  and retired the completed source-selection item from the forward roadmap.
- Added reviewed AMD64 and ARM64 artifact locks for the selected NGINX RPM,
  its complete UBI dependency closure, source RPMs, signing identities, and
  base-image digests, with fail-closed validation and lock-update tooling.
  The locks record the refreshed UBI 9.8 bases and therefore
  `openssl-1:3.5.8-1.el9_8` from RHSA-2026:67165 and the
  `systemd-0:252-67.el9_8.6` rebuild.
- Added atomic official and protected alternate-source acquisition for locked
  artifact bundles, including exact inventory, digest, RPM signature, signer,
  NEVRA, architecture, and lock-manifest verification without storing source
  credentials or private trust material in the repository or image build.
- Migrated the development image to the selected official NGINX 1.30.4 RPM and
  its exact architecture lock, with local-only RPM installation, installed
  inventory comparison, digest-pinned base preloading, network-disabled
  assembly, and an enforceable no-pull policy in local and native CI builds.
- Added hermetic-build rejection checks for a wrong lock identity and an
  unavailable base, and removed repository configuration from the final
  filesystem.
- Added native real-RPM negative tests for modified, unsigned, signer-mismatched,
  wrong-version, wrong-architecture, missing, and unexpected bundle content;
  bound production lock validation to the reviewed base images, NGINX seed,
  and signing-key inputs; and required filenames to agree with RPM metadata
  and official source URLs.
- Added a lock-bound accountability inventory for all 79 runtime RPMs with
  exact license and source-RPM metadata, publisher and redistribution policy,
  lifecycle boundary, and named update ownership; native CI now checks the
  recorded metadata against every acquired AMD64 and ARM64 RPM.
- Defined reviewed lock refresh, signing-key rotation and revocation, immutable
  artifact mirroring, image rollback, and disconnected-transfer procedures;
  added a schema and fail-closed transfer manifest that binds payload hashes to
  the repository revision, architecture lock, and component inventory.
- Embedded the exact verified 79-RPM manifest in the package-manager-free final
  image; added a reviewed inventory for 22 optional NGINX compile-time modules
  and features; and made native Podman plus Docker compatibility tests reject
  package, module, or NGINX build drift.
- Strengthened rootless failure and lifecycle tests to require precise mounted
  configuration and unwritable-temporary-path diagnostics, worker-replacing
  reloads with PID 1 retained, and complete active-request draining on
  `SIGQUIT` before a clean exit.
- Added qualified preview static-serving and HTTP reverse-proxy configurations
  with bounded request handling, validated correlation IDs, query-free JSON
  access events, safe forwarding-header behavior, explicit upstream failure,
  and native Podman plus Docker compatibility tests under restricted runtime
  controls on AMD64 and ARM64.
- Added qualified preview TLS 1.2/1.3 termination, mandatory mutual-TLS, and
  verified HTTPS-upstream profiles with an ephemeral CA-issued rehearsal for
  protocol bounds, hostname and chain validation, client authentication, leaf
  renewal, untrusted roots, missing keys, restricted runtime, and secret-safe
  structured logging on native Podman and Docker compatibility execution.
- Added 14 focused unit tests for structured profile logs, covering exact
  schemas, JSON escaping, type confusion, numeric bounds, timestamps,
  correlation IDs, query exclusion, TLS results, upstream timing fields,
  secret detection, and unique scenario selection.
- Added a qualified preview HTTP load-balancing profile with weighted
  round-robin distribution, passive member failure handling, retries restricted
  to pre-application failures, bounded retry attempts and time, and structured
  failover events; native Podman and Docker compatibility tests require that
  every healthy member receives traffic, that a stopped member causes no
  client-visible failure, and that a retry is actually recorded.
- Fixed a race in the reload test that read `/proc/PID/status` for a worker
  that had already exited, which aborted the listing instead of skipping the
  vanished process.
- Added a dated status snapshot recording where the work stands, what is
  blocked and on what, and which parts of the control model transfer to the
  cross-repository container hardening standard.
- Resolved the Application Server SRG, pinning V4R5 by digest and recording it
  as not applicable to this component: 27 of its 137 rules presuppose a
  management interface or hosted applications and 18 refer to accounts, none of
  which exist here. Pinned rather than dropped so the determination stays tied
  to the revision it was made against.
- Recorded why the DISA Container Platform SRG cannot be retrieved: V2R1 is
  officially released and its filename follows DISA's convention, but it is no
  longer served from the public download path, and the download index is now a
  JavaScript-rendered portal whose HTML contains no download links. It stays
  unresolved with the release, filename, and finding recorded, so the search is
  not repeated.
- Established the requirement-source register, pinning the 800-53 Rev 5.2.0
  catalogue, its High baseline profile, the DISA Web Server SRG, and the RHEL 9
  STIG by digest, and recording the Container Platform SRG, Application Server
  SRG, and CIS benchmark as unresolved or unavailable with the reason rather
  than omitting them.
- Fixed the control representation before authoring controls: six origination
  values, a responsible role that must match, a verification pointer into the
  requirement tree required of every image-owned control, and assessment
  methods permitted only where the image owns the control.
- Added the structural checks over the component definition, including that a
  control cannot claim to be image-owned while citing a requirement the product
  never stated, and that a hand-off control must say what the responsible party
  has to do.
- Corrected the recorded scale of the control work: the High baseline selects
  370 controls, being 188 base and 182 enhancements, not the roughly 370 base
  controls estimated before the catalogue was retrieved.
- Settled the control catalogue, baseline, consumer, scope, enhancement
  sequencing, origination representation, source pinning, and authoring order
  as one decision, since each changes the shape of every control entry and
  deciding them late would mean re-doing the early ones.
- Restructured the control package into foundation, authoring, publication, and
  scanning stages, placing the structural checks before the bulk authoring
  because an origination property that is merely conventional gets omitted
  under deadline, which is when the overclaim it prevents is most likely.
- Upgraded the locked NGINX package to 1.30.5, which fixes CVE-2026-90439, a
  major-severity buffer overflow when using `map` with a regular expression.
  Every profile validates the inbound correlation identifier with exactly that
  construct over a client-supplied header, so the affected path was reachable
  on every request in every profile.
- Refreshed both architecture locks and the builder base digest alongside it.
  The closure did not otherwise move: 79 packages, none added or removed, and
  `nginx` the only version change on either architecture.
- Added a connect timeout and a transfer-speed floor to source-RPM downloads in
  the lock resolver, after a stalled CDN connection hung a refresh indefinitely
  with no way out; `--retry` covers a transient error, not a transfer that
  connects and then stops.
- Fixed a feature-inventory test that hardcoded the pinned NGINX version, so
  its drift check silently stopped testing anything once the version moved.
- Corrected the package-source record, which stated that the previously
  selected version was not vulnerable to its current 1.30-series advisories.
  That stopped being true when CVE-2026-90439 published.
- Proved assembly isolation from its inputs as well as at run time: no
  resolving or fetching command may appear in the build definition, staging
  directories are excluded from both the build context and version control, and
  no build argument may be credential-shaped, since a build argument is
  recorded in image history.
- Added scheduled drift reporting for the inputs Dependabot cannot see: the
  NGINX package, its signing key, the UBI base digests, and the locked closure.
  It reports into a single standing issue, opens no pull request, and cannot
  edit a lock, because a refresh is a reviewed operation. An unreadable source
  is reported as unreachable rather than as unchanged.
- Added a least-privilege release workflow that runs only for a pushed tag,
  widens permissions per job, requires the tagged commit to be an ancestor of
  `main`, publishes a native multi-architecture manifest, and binds provenance,
  SBOM attestation, and signature to the manifest digest rather than to a tag.
  The workflow has not been executed; rehearsing it remains an open item.
- Added release tag validation covering the pattern, a real and non-future UTC
  date, agreement with the artifact lock on NGINX version and UBI major,
  immutability, and a daily sequence that continues from the highest used
  instead of back-filling a withdrawn one.
- Published one page per configuration profile with its own request-path
  diagram, the behaviour its tests qualify, and the behaviour they do not, and
  pointed every support-matrix row at the profile's page rather than restating
  it. The pages and diagrams are generated from one table, so a page cannot
  describe a path its diagram contradicts.
- Completed the diagram set with runtime data-flow, TLS trust, assurance
  pipeline, controlled-network transfer, and control-ownership diagrams, each
  stating on its face what the image does not provide, and cross-linked them
  from the documents they explain.
- Added the architecture section with hand-authored runtime-contract and
  profile-map diagrams, and recorded the decision to author diagrams as SVG
  with no rendering toolchain, so the published file is the reviewed file and
  no source-versus-render check is required.
- Added diagram checks requiring well-formed, scalable SVG carrying a text
  description, with no script and no external reference, and requiring every
  diagram to be referenced by a document.
- Stated in the security-controls document that it does not yet enumerate
  controls, listing what it deliberately does not contain and naming the
  roadmap package that produces the OSCAL component definition, so it cannot be
  cited as the control deliverable it precedes.
- Established the three-level requirement tree with permanent identifiers,
  stated exclusions as numbered non-requirements, and added a marker convention
  that lets a `unittest` case declare which requirements it verifies and lets
  those tests be run by requirement.
- Added a generated requirement trace matrix that derives status from the
  requirement documents and the test markers, so status cannot drift between
  them, with a check that fails when the committed matrix is stale.
- Closed every requirement the first matrix reported as uncovered, including one
  obligation with no test at all: the Containerfile's base images are now
  asserted to match every architecture lock, which nothing previously checked.
- Added configuration policy checks that reject a commercial NGINX directive or
  an enabled non-idempotent retry in any shipped configuration, closing the two
  accepted decisions that had no automated enforcement. The checks strip
  comments first, so a comment explaining a deliberate absence is not mistaken
  for the thing it describes.
- Backfilled architecture decision records for the seven decisions previously
  recorded only in commit messages and configuration comments, each carrying
  the options weighed, the reason the rejected options lost, what the decision
  costs, and whether anything enforces it.
- Recorded that two of those decisions have no automated enforcement: nothing
  prevents a commercial NGINX directive or a non-idempotent retry flag being
  added to an example configuration.
- Qualified upstream resolution in both modes: the existing profiles resolve
  once at load and recover from a replaced endpoint on reload, and a new
  mountable dynamic-upstream profile re-resolves per request and recovers
  without one. Recorded what the dynamic mode gives up in exchange, since
  holding the endpoint in a variable removes the upstream block and with it
  balancing, passive failure tracking, failover, and connection reuse.
- Recorded that the resolver address is supplied by the deployment through a
  mounted include, that resolver validity bounds how long traffic can reach a
  replaced endpoint, and that DNS becomes part of the trust boundary in that
  mode because no reload or review step stands between a resolver answer and
  live traffic.
- Recorded that upstream certificate verification applies only to HTTPS
  upstreams, that the plain-HTTP proxying profiles assume an already-trusted
  segment, and that adding `https://` without the verified-upstream pattern is
  worse than plain HTTP because it looks verified and is not.
- Added a configuration-operations guide covering mounting, offline validation
  of a candidate with the same image, reload, rollback, troubleshooting, and
  secret redaction.
- Established that configuration is mounted as a directory rather than a single
  file, because replacing a bind-mounted file by rename leaves the container on
  the previous inode and the subsequent reload reports success while the old
  configuration stays live.
- Added README status badges for the build, code-scanning, and OpenSSF
  Scorecard workflows, the license, and the release and support position,
  keeping the last two static so no badge implies a qualification the project
  has not completed.
- Added a release-gating roadmap package for the product requirement tree, its
  generated trace matrix, architecture decision records, and profile and
  use-case diagrams, and bound it to the control-mapping work so no published
  control cites a requirement the product never stated.
- Added a qualified preview ClickHouse HTTP proxying profile that bounds
  methods, body size, timeouts, and temporary storage, reports failures by
  exception code rather than by statement, and records `NONE` upstream fields
  for a request the proxy refused; tests prove a password and column name sent
  as request parameters reach neither the access stream nor the error stream.
- Stated that the ClickHouse proxy is not an authorization boundary, because
  NGINX parses HTTP rather than SQL and cannot enforce read-only access,
  restrict statements, or bound returned rows; those remain ClickHouse
  `readonly` settings, quotas, row policies, and grants.
- Added a qualified preview health-endpoint profile separating
  upstream-independent liveness from upstream-reflecting readiness, logging
  only failing probes, and exposing `stub_status` on a separate listener that
  denies every source by default; tests prove liveness keeps answering while
  the upstream is stopped, that readiness then reports `503`, and that
  publishing the status port does not make it readable.
- Recorded that this project packages open source NGINX only, that no NGINX
  Plus capability is used or assumed, and that profiles needing behaviour those
  features provide solve it with open source directives and state the
  limitation instead.
- Added a qualified preview request-limiting profile applying independent
  request-rate, concurrent-connection, and per-connection bandwidth budgets,
  answering `429` rather than the default `503`, keeping the health endpoint
  outside every limit, and recording limit outcomes without recording the limit
  key; tests prove rate rejection, connection rejection specifically, and that
  health checks keep answering while a client's request budget is exhausted.
- Documented that a limit keyed on the direct peer address becomes a global cap
  behind a proxy, that keying on a client-controlled header removes the limit
  entirely, and that `limit_req` is evaluated before `limit_conn` so a
  rate-rejected request records the connection limit as not evaluated.
- Added a qualified preview WebSocket-proxying profile that derives the
  upstream connection disposition from a map rather than copying it from the
  client, scopes the long idle timeout to the upgrade location, and never
  retries an upgrade; tests prove upgrade forwarding, `101` relay, the derived
  `close` disposition under a conflicting client header, and unaffected plain
  HTTP traffic.
- Documented that the WebSocket profile performs no `Origin` validation and
  that cross-site WebSocket hijacking remains an application or
  authenticating-layer responsibility.
- Made profile log assertions wait for the access event instead of reading the
  container log once, which removes an intermittent "found 0 matching events"
  failure.
- Suppressed structured access events for connections that never produce a
  request, such as a rejected TLS handshake or a malformed request line, so the
  access schema no longer has to tolerate empty required fields.
- Enforced mounted CRLs for mutual-TLS clients and HTTPS upstreams; extended the
  ephemeral PKI rehearsal to reject revoked certificates and to prove old,
  overlapping, and new-only CA trust states without disabling chain or hostname
  verification.
- Added a public-metadata TLS lifecycle checker with stable JSON output and 12
  boundary-focused unit tests for certificate expiry, CRL freshness, timezone
  handling, exact alert thresholds, malformed output, and fail-closed OpenSSL
  inspection errors.
- Expanded logging guidance with a field-by-field explanation of `$request`,
  a sensitive ClickHouse example, and safer variable choices.
- Defined a source-independent pipeline contract that downloads and verifies
  locked artifacts outside a network-disabled container build.
- Expanded native and local runtime tests to prove non-root processes, zero
  effective capabilities, `no-new-privileges`, arbitrary-UID operation,
  read-only-root behavior, hardened temporary storage, log routing, graceful
  reload and shutdown, and actionable negative startup cases.

### Changed

- Renamed the source repository and planned GHCR image from `nginx-ubi9` to
  `nginx-ubi` so their identities do not prevent future work on other UBI major
  versions; UBI 9-specific service and development identifiers remain
  unchanged.
- Upgraded the reference contributor environment from Ubuntu 22.04.5 and
  Podman 3.4.4 to Ubuntu 24.04.5 and Podman 5.8.2, verified the restricted
  runtime and Quadlet lifecycle after a cold WSL restart, and retired the
  completed upgrade plan from the forward-looking roadmap.
- Retired the completed project-contract package from the forward-looking
  roadmap after its repository files and current support boundary were added.

### Security

- Enabled GitHub vulnerability alerts, Dependabot security updates, secret
  scanning with push protection, and private vulnerability reporting.

### Fixed

- Prevented the Docker smoke suite from failing with SIGPIPE when short-circuit
  log and response assertions run under `pipefail`.
