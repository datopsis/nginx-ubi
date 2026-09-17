# nginx-ubi — requirement trace matrix

**This file is generated. Do not edit it.**

Regenerate with `python scripts/build-trace-matrix.py`; CI runs
`--check` and fails when the committed file has drifted from its
sources.

Status is derived here rather than recorded in the requirement
documents, so the two cannot disagree. A requirement is *covered* when
it has a verifying artifact or when every child beneath it is covered.
A requirement whose declared verification method is not Test is
reported as *not test-verified*, because no marker can exist for it,
and counting it as a gap would bury the real gaps.

## Coverage

| Measure | Count |
| --- | --- |
| L1 requirements | 30 |
| L2 requirements | 43 |
| L3 requirements | 47 |
| Counted for coverage | 90 |
| Covered | 86 |
| Not test-verified | 4 |
| **Uncovered** | **0** |

Composite L1 requirements are excluded from the count: they are verified through their children, which are counted, so counting both would double-count.

## L1 requirements

| Requirement | Methods | Parent | Children | Verifying artifacts | Status |
| --- | --- | --- | --- | --- | --- |
| `L1-EVD-001` | I | — | `L2-EVD-002` | — | covered |
| `L1-EVD-002` | I | — | `L2-EVD-001` | — | **uncovered** |
| `L1-HLT-001` | T | — | `L2-HLT-001`, `L2-HLT-002` | — | covered |
| `L1-HLT-002` | T | — | `L2-HLT-003` | — | covered |
| `L1-IMG-001` | TI | — | `L2-IMG-001` | — | covered |
| `L1-IMG-002` | T | — | `L2-IMG-002` | — | covered |
| `L1-IMG-003` | TA | — | `L2-IMG-003`, `L2-IMG-004` | — | covered |
| `L1-LIM-001` | T | — | `L2-LIM-001`, `L2-LIM-002`, `L2-LIM-004` | — | covered |
| `L1-LIM-002` | TI | — | `L2-LIM-003` | — | covered |
| `L1-LOG-001` | T | — | `L2-LOG-001` | — | covered |
| `L1-LOG-002` | T | — | `L2-HLT-004`, `L2-LOG-002`, `L2-LOG-004` | — | covered |
| `L1-LOG-003` | T | — | `L2-LOG-003` | — | covered |
| `L1-OPS-001` | TD | — | `L2-OPS-001` | — | covered |
| `L1-OPS-002` | ID | — | `L2-OPS-002` | — | **uncovered** |
| `L1-PRX-001` | T | — | `L2-PRX-001`, `L2-PRX-005` | — | covered |
| `L1-PRX-002` | TI | — | `L2-PRX-002` | — | covered |
| `L1-PRX-003` | I | — | `L2-PRX-003`, `L2-PRX-004` | — | partial |
| `L1-RUN-001` | T | — | `L2-RUN-001` | — | covered |
| `L1-RUN-002` | T | — | `L2-RUN-002` | — | covered |
| `L1-RUN-003` | T | — | `L2-RUN-003` | — | covered |
| `L1-RUN-004` | T | — | `L2-RUN-004` | — | covered |
| `L1-RUN-005` | T | — | `L2-RUN-005`, `L2-RUN-006` | — | covered |
| `L1-RUN-006` | T | — | `L2-RUN-007` | — | covered |
| `L1-SUP-001` | TA | — | `L2-SUP-001`, `L2-SUP-002`, `L2-SUP-006` | — | covered |
| `L1-SUP-002` | T | — | `L2-SUP-003` | — | covered |
| `L1-SUP-003` | T | — | `L2-SUP-004` | — | covered |
| `L1-SUP-004` | AI | — | `L2-SUP-005` | — | **uncovered** |
| `L1-TLS-001` | T | — | `L2-TLS-001`, `L2-TLS-005` | — | covered |
| `L1-TLS-002` | TI | — | `L2-TLS-002` | — | covered |
| `L1-TLS-003` | T | — | `L2-TLS-003`, `L2-TLS-004` | — | covered |

## L2 requirements

| Requirement | Methods | Parent | Children | Verifying artifacts | Status |
| --- | --- | --- | --- | --- | --- |
| `L2-EVD-001` | I | `L1-EVD-002` | — | — | not test-verified |
| `L2-EVD-002` | I | `L1-EVD-001` | — | `tests.test_diagrams.test_each_diagram_is_described_for_a_reader_who_cannot_see_it` | covered |
| `L2-HLT-001` | T | `L1-HLT-001` | `L3-HLT-001` | — | covered |
| `L2-HLT-002` | T | `L1-HLT-001` | `L3-HLT-002` | — | covered |
| `L2-HLT-003` | T | `L1-HLT-002` | `L3-HLT-003` | — | covered |
| `L2-HLT-004` | T | `L1-LOG-002` | `L3-HLT-004` | — | covered |
| `L2-IMG-001` | TI | `L1-IMG-001` | — | `tests.test_profile_policy.test_containerfile_bases_match_every_architecture_lock` | covered |
| `L2-IMG-002` | T | `L1-IMG-002` | `L3-IMG-002` | — | covered |
| `L2-IMG-003` | T | `L1-IMG-003` | `L3-IMG-001` | — | covered |
| `L2-IMG-004` | T | `L1-IMG-003` | `L3-IMG-003`, `L3-IMG-004` | — | covered |
| `L2-LIM-001` | T | `L1-LIM-001` | `L3-LIM-001`, `L3-LIM-002` | — | covered |
| `L2-LIM-002` | T | `L1-LIM-001` | `L3-LIM-003` | — | covered |
| `L2-LIM-003` | TI | `L1-LIM-002` | — | `tests/profiles.sh:538` | covered |
| `L2-LIM-004` | T | `L1-LIM-001` | `L3-LIM-004` | — | covered |
| `L2-LOG-001` | T | `L1-LOG-001` | `L3-LOG-001`, `L3-LOG-004` | — | covered |
| `L2-LOG-002` | T | `L1-LOG-002` | `L3-LOG-002` | — | covered |
| `L2-LOG-003` | T | `L1-LOG-003` | `L3-LOG-003` | — | covered |
| `L2-LOG-004` | T | `L1-LOG-002` | `L3-LOG-005` | — | covered |
| `L2-OPS-001` | TD | `L1-OPS-001` | `L3-OPS-001` | — | covered |
| `L2-OPS-002` | ID | `L1-OPS-002` | — | — | not test-verified |
| `L2-PRX-001` | T | `L1-PRX-001` | `L3-PRX-001`, `L3-PRX-007` | — | covered |
| `L2-PRX-002` | TI | `L1-PRX-002` | `L3-PRX-002` | — | covered |
| `L2-PRX-003` | I | `L1-PRX-003` | — | — | not test-verified |
| `L2-PRX-004` | T | `L1-PRX-003` | `L3-PRX-003`, `L3-PRX-004`, `L3-PRX-006` | — | covered |
| `L2-PRX-005` | T | `L1-PRX-001` | `L3-PRX-005` | — | covered |
| `L2-RUN-001` | T | `L1-RUN-001` | `L3-RUN-001` | — | covered |
| `L2-RUN-002` | T | `L1-RUN-002` | `L3-RUN-002` | — | covered |
| `L2-RUN-003` | T | `L1-RUN-003` | `L3-RUN-003` | — | covered |
| `L2-RUN-004` | T | `L1-RUN-004` | `L3-RUN-004` | — | covered |
| `L2-RUN-005` | T | `L1-RUN-005` | `L3-RUN-005` | — | covered |
| `L2-RUN-006` | T | `L1-RUN-005` | `L3-RUN-006` | — | covered |
| `L2-RUN-007` | T | `L1-RUN-006` | `L3-RUN-007`, `L3-RUN-008` | — | covered |
| `L2-SUP-001` | TI | `L1-SUP-001` | `L3-SUP-001`, `L3-SUP-002`, `L3-SUP-006` | — | covered |
| `L2-SUP-002` | T | `L1-SUP-001` | `L3-SUP-003`, `L3-SUP-004`, `L3-SUP-007` | — | covered |
| `L2-SUP-003` | T | `L1-SUP-002` | `L3-SUP-008` | — | covered |
| `L2-SUP-004` | T | `L1-SUP-003` | — | `tests/hermetic-build-negative.sh:2` | covered |
| `L2-SUP-005` | AI | `L1-SUP-004` | — | — | not test-verified |
| `L2-SUP-006` | T | `L1-SUP-001` | `L3-SUP-005` | — | covered |
| `L2-TLS-001` | T | `L1-TLS-001` | — | `tests/tls.sh:174` | covered |
| `L2-TLS-002` | T | `L1-TLS-002` | `L3-TLS-004` | — | covered |
| `L2-TLS-003` | T | `L1-TLS-003` | `L3-TLS-001`, `L3-TLS-002`, `L3-TLS-006` | — | covered |
| `L2-TLS-004` | T | `L1-TLS-003` | `L3-TLS-003` | — | covered |
| `L2-TLS-005` | T | `L1-TLS-001` | `L3-TLS-005` | — | covered |

## L3 requirements

| Requirement | Methods | Parent | Children | Verifying artifacts | Status |
| --- | --- | --- | --- | --- | --- |
| `L3-HLT-001` | T | `L2-HLT-001` | — | `tests/profiles.sh:645` | covered |
| `L3-HLT-002` | T | `L2-HLT-002` | — | `tests/profiles.sh:652` | covered |
| `L3-HLT-003` | T | `L2-HLT-003` | — | `tests/profiles.sh:634` | covered |
| `L3-HLT-004` | T | `L2-HLT-004` | — | `tests/profiles.sh:664` | covered |
| `L3-IMG-001` | T | `L2-IMG-003` | — | `tests/smoke.sh:282` | covered |
| `L3-IMG-002` | T | `L2-IMG-002` | — | `tests/smoke.sh:282` | covered |
| `L3-IMG-003` | T | `L2-IMG-004` | — | `tests/smoke.sh:282` | covered |
| `L3-IMG-004` | T | `L2-IMG-004` | — | `tests.test_nginx_features.test_missing_or_unexpected_module_is_rejected`<br>`tests.test_nginx_features.test_reviewed_feature_inventory_is_accepted`<br>`tests/smoke.sh:282` | covered |
| `L3-LIM-001` | T | `L2-LIM-001` | — | `tests/profiles.sh:569` | covered |
| `L3-LIM-002` | T | `L2-LIM-001` | — | `tests/profiles.sh:538` | covered |
| `L3-LIM-003` | T | `L2-LIM-002` | — | `tests.test_profile_logs.test_rate_limited_rejects_unknown_limit_outcomes`<br>`tests.test_profile_logs.test_rate_limited_requires_recognised_limit_outcomes` | covered |
| `L3-LIM-004` | T | `L2-LIM-004` | — | `tests/profiles.sh:580` | covered |
| `L3-LOG-001` | T | `L2-LOG-001` | — | `tests.test_profile_logs.test_uri_must_be_absolute_and_query_free` | covered |
| `L3-LOG-002` | T | `L2-LOG-002` | — | `tests.test_profile_logs.test_json_escaped_path_round_trips`<br>`tests.test_profile_logs.test_upstream_profiles_require_exact_timing_fields` | covered |
| `L3-LOG-003` | T | `L2-LOG-003` | — | `tests/profiles.sh:219` | covered |
| `L3-LOG-004` | T | `L2-LOG-001` | — | `tests/profiles.sh:725` | covered |
| `L3-LOG-005` | T | `L2-LOG-004` | — | `tests/validate_profile_logs.py:2` | covered |
| `L3-OPS-001` | T | `L2-OPS-001` | — | `tests/smoke.sh:363` | covered |
| `L3-PRX-001` | T | `L2-PRX-001` | — | `tests/profiles.sh:219` | covered |
| `L3-PRX-002` | T | `L2-PRX-002` | — | `tests.test_profile_policy.test_no_commercial_directive_is_used`<br>`tests.test_profile_policy.test_no_profile_enables_non_idempotent_retries` | covered |
| `L3-PRX-003` | T | `L2-PRX-004` | — | `tests/profiles.sh:298` | covered |
| `L3-PRX-004` | T | `L2-PRX-004` | — | `tests/profiles.sh:379` | covered |
| `L3-PRX-005` | T | `L2-PRX-005` | — | `tests/profiles.sh:451` | covered |
| `L3-PRX-006` | T | `L2-PRX-004` | — | `tests/profiles.sh:835` | covered |
| `L3-PRX-007` | T | `L2-PRX-001` | — | `tests/profiles.sh:252` | covered |
| `L3-RUN-001` | T | `L2-RUN-001` | — | `tests/smoke.sh:49` | covered |
| `L3-RUN-002` | T | `L2-RUN-002` | — | `tests/smoke.sh:49` | covered |
| `L3-RUN-003` | T | `L2-RUN-003` | — | `tests/smoke.sh:282` | covered |
| `L3-RUN-004` | T | `L2-RUN-004` | — | `tests/smoke.sh:282` | covered |
| `L3-RUN-005` | T | `L2-RUN-005` | — | `tests/smoke.sh:135` | covered |
| `L3-RUN-006` | T | `L2-RUN-006` | — | `tests/smoke.sh:168` | covered |
| `L3-RUN-007` | T | `L2-RUN-007` | — | `tests/smoke.sh:349` | covered |
| `L3-RUN-008` | T | `L2-RUN-007` | — | `tests/smoke.sh:363` | covered |
| `L3-SUP-001` | T | `L2-SUP-001` | — | `tests.test_artifacts.test_malformed_and_unexpected_fields_fail_closed`<br>`tests.test_artifacts.test_repository_inputs_and_generated_locks_are_valid` | covered |
| `L3-SUP-002` | T | `L2-SUP-001` | — | `tests.test_artifacts.test_base_digest_drift_from_reviewed_inputs_is_rejected`<br>`tests.test_artifacts.test_duplicate_and_unapproved_signer_or_url_are_rejected`<br>`tests.test_artifacts.test_wrong_arch_version_nevra_source_and_base_are_rejected` | covered |
| `L3-SUP-003` | T | `L2-SUP-002` | — | `tests.test_artifacts.test_acquisition_publishes_only_a_complete_verified_bundle` | covered |
| `L3-SUP-004` | T | `L2-SUP-002` | — | `tests.test_artifacts.test_alternate_source_map_requires_an_exact_safe_mapping` | covered |
| `L3-SUP-005` | T | `L2-SUP-006` | — | `tests.test_transfer.test_exact_transfer_set_is_accepted`<br>`tests.test_transfer.test_modified_missing_and_unexpected_payloads_are_rejected`<br>`tests.test_transfer.test_repository_context_binds_the_reviewed_lock_and_inventory` | covered |
| `L3-SUP-006` | T | `L2-SUP-001` | — | `tests.test_components.test_lock_hash_drift_is_rejected`<br>`tests.test_components.test_repository_inventory_covers_both_reviewed_locks`<br>`tests.test_components.test_rpm_headers_must_match_the_reviewed_metadata` | covered |
| `L3-SUP-007` | T | `L2-SUP-002` | — | `tests.test_artifacts.test_tampered_missing_unexpected_and_wrong_lock_bundles_fail_closed`<br>`tests/rpm-bundle-negative.py:2` | covered |
| `L3-SUP-008` | T | `L2-SUP-003` | — | `tests/hermetic-build-negative.sh:2` | covered |
| `L3-TLS-001` | T | `L2-TLS-003` | — | `tests/tls.sh:306` | covered |
| `L3-TLS-002` | T | `L2-TLS-003` | — | `tests/tls.sh:314` | covered |
| `L3-TLS-003` | T | `L2-TLS-004` | — | `tests/tls.sh:366` | covered |
| `L3-TLS-004` | T | `L2-TLS-002` | — | `tests/tls.sh:327` | covered |
| `L3-TLS-005` | T | `L2-TLS-005` | — | `tests.test_tls_material.test_certificate_inspection_uses_public_metadata_only`<br>`tests.test_tls_material.test_crl_inspection_reports_warning`<br>`tests.test_tls_material.test_openssl_failure_is_fail_closed_without_stderr_leak` | covered |
| `L3-TLS-006` | T | `L2-TLS-003` | — | `tests/tls.sh:333` | covered |

## Non-requirements

| ID | Non-requirement | Reason |
| --- | --- | --- |
| `NR-001` | NGINX Plus capability | Open source only; see ADR-0002 |
| `NR-002` | FIPS validation | No cryptographic boundary has been defined or evidenced |
| `NR-003` | STIG certification | Tailored SCAP results describe selected rules only |
| `NR-004` | Enforcing query semantics at the proxy | NGINX parses HTTP, not SQL; belongs to the database |
| `NR-005` | Active upstream health checking | Commercial feature; passive checks used instead |
| `NR-006` | Session persistence | Commercial feature; hash-based affinity is the open source option |
| `NR-007` | Selecting a Bash scenario by requirement | Suites are linear scripts; markers give traceability only |
| `NR-008` | Forward proxying, WAF, mail proxying, stream proxying | Deferred; see the roadmap |
| `NR-009` | Interoperation with a real ClickHouse server | Tested against a stand-in; a deployment qualifies its own server |
