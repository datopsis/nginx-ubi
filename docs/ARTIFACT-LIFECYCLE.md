# Artifact lifecycle and controlled transfer

This procedure governs artifact-lock refresh, publisher signing-key changes,
alternate-source mirrors, rollback, and transfer into a disconnected build
environment. It extends the verification contract in
[External artifact acquisition](ARTIFACT-ACQUISITION.md); it does not replace
publisher signatures, reviewed locks, or native release evidence.

## Roles and approval

| Activity | Preparer | Required reviewer | Evidence owner |
| --- | --- | --- | --- |
| Routine lock refresh | Datopsis maintainer | Code owner who did not prepare the change | Datopsis maintainers |
| Signing-key addition, removal, or emergency revocation | Datopsis security maintainer | Independent code owner | Datopsis maintainers |
| Mirror configuration and credentials | Environment owner | Environment security owner | Environment owner |
| Connected-to-disconnected transfer | Transfer custodian | Receiving security owner | Environment owner |
| Deployment rollback | Deployment operator | Service owner under local change policy | Environment owner |

No ordinary build may refresh a lock, select a newer dependency, rotate a key,
or fall back to an unreviewed source. A lock update is an image-affecting
change and invalidates affected release-candidate evidence.

## Lock refresh

1. Open a change that records the reason, preparer, intended NGINX and UBI
   versions, both base-image manifest digests, upstream advisory references,
   and whether any package, source RPM, key, license tag, or repository changed.
2. Independently retrieve the proposed NGINX RPM and public signing keys from
   the publisher. Record full key fingerprints and SHA-256 values in
   `artifacts/lock-inputs.json`; never approve a key from a short key ID alone.
   Resolve each base tag to its architecture-covering manifest-list digest and
   record that digest before resolution.
3. Fetch only the reviewed seeds into a new directory:

   ```console
   python scripts/fetch-lock-inputs.py \
     --inputs artifacts/lock-inputs.json \
     --architecture amd64 \
     --output .artifact-inputs/amd64
   ```

4. Run `scripts/resolve-lock.sh ARCHITECTURE INPUT_DIR OUTPUT_DIR` for AMD64 and
   ARM64 in a clean, networked UBI 9 resolver environment. This is the only
   phase permitted to resolve dependencies. Retain resolver version, platform,
   repository metadata timestamp, stdout/stderr, and the input hashes.
5. Render each result to a new candidate path; do not overwrite a reviewed
   lock in place:

   ```console
   python scripts/render-lock.py \
     --inputs artifacts/lock-inputs.json \
     --architecture amd64 \
     --binary-inventory .artifact-resolver/amd64/binary-inventory.tsv \
     --source-inventory .artifact-resolver/amd64/source-inventory.tsv \
     --output .artifact-resolver/amd64.json
   ```

6. Review both lock diffs. Explain package additions and removals, version and
   repository changes, signer changes, source changes, and base digest changes.
   Confirm both architectures still have an intentional component set.
7. Update `artifacts/components.json` from the candidate RPM headers, review
   every changed license/source/vendor record, and bind it to both final lock
   hashes. Do not relabel an upstream license merely to make it SPDX-shaped.
8. Acquire both candidate bundles from official sources, execute RPM and
   component verification plus negative tests, build without network or pulls,
   and complete native runtime and vulnerability evidence.
9. Merge the inputs, both locks, and component inventory as one reviewed
   change. Delete local resolver material after retaining approved evidence in
   the change record or CI; do not commit downloaded RPMs or resolver caches.

If either architecture fails or differs without an approved explanation, stop
the refresh. Do not publish a one-architecture lock generation as a supported
multi-architecture release candidate.

## Publisher signing-key rotation

A key change is never inferred from a failed signature or fetched blindly from
an RPM header. Confirm the new fingerprint and transition through at least two
independent publisher-controlled references or an authenticated publisher
notice, then have an independent reviewer compare the full fingerprint.

For a planned overlap, add the new key URL, SHA-256, and full fingerprint to
the reviewed inputs; regenerate both locks; and prove that every RPM signer
maps to exactly one approved fingerprint. Keep the old key only while current
locked artifacts require it. Remove it from the current inputs and locks after
the package transition. Historical Git revisions retain the data needed to
verify historical locks.

For suspected compromise or publisher revocation, block lock refreshes and
releases, preserve the incident evidence, remove the key from current trust,
select publisher-reissued artifacts, regenerate the entire affected lock
generation, and repeat all image evidence. Never solve revocation by disabling
signature checks, accepting an unknown signer, or re-signing upstream RPMs.

Key expiry, revocation, or announcement status is a review-time decision using
current publisher information; possession of a formerly accepted key file is
not sufficient approval.

## Artifact mirror

An approved mirror stores the exact publisher bytes under immutable object
identities. It must not rebuild, modify, decompress/recompress, or re-sign an
RPM. Populate it only after official-source acquisition and verification.
Record the source lock SHA-256, object SHA-256, upload identity, time, mirror
object/version identifier, retention policy, and deletion authority.

Mirror credentials and private CA material remain protected environment
configuration. Generate the complete external source-map JSON for the chosen
lock and bundle mode, then reacquire into a clean directory with
`--source-map`, `--token-env`, and, when required, `--ca-bundle`. Verification
must use repository-trusted publisher keys rather than mirror-controlled keys.
Compare the mirror-acquired bundle with the same lock and run the normal RPM
verification before assembly.

A missing mirror object, changed byte, redirect to another host, expired
credential, or TLS failure stops acquisition. Automatic fallback from a
protected mirror to the public internet is prohibited because it can bypass
the environment's egress and audit boundary.

## Rollback

The preferred deployment rollback selects the previously approved immutable
image digest and its matching configuration digest. Retain that image in the
deployment registry for the locally approved rollback window. Record the
failed digest, restored digest, reason, authorization, start/end time, health
result, and any security exposure caused by returning to older software.

Do not edit a current lock to resemble an older generation or mix an older
lock with current inputs, keys, or component inventory. If rebuilding is
unavoidable, check out the exact historical repository revision, acquire its
exact locked artifacts, repeat its verification and current vulnerability
review, and publish the result as a new immutable image with new evidence.
An old build that succeeds is not automatically safe to redeploy.

Before an update, rehearse the digest rollback in staging and confirm the old
configuration remains compatible. After rollback, diagnose the failed update
and issue a new reviewed candidate; never move or overwrite a published tag.

## Disconnected transfer

The transfer manifest schema is
`artifacts/transfer-manifest.schema.json`. `scripts/transfer.py` inventories
every payload file by path, byte size, and SHA-256 and binds the set to a full
repository revision, architecture lock, and component inventory. The tool
rejects missing, additional, modified, or symbolic-link payloads.

The manifest is not a signature. Its SHA-256 must travel through a separately
authenticated channel, such as an approved signed change record, and be
compared before trusting tools or metadata carried on the transfer medium.

### Connected preparation station

For each architecture, use an empty staging directory and:

1. Check out the reviewed full repository revision and ensure the worktree is
   clean. Record `git rev-parse HEAD` as `REVISION`.
2. Acquire `.artifact-transfer/ARCHITECTURE/bundle` with `--include-sources`; run
   `verify-rpm-bundle.sh` with source verification and run
   `scripts/components.py` against the bundle.
3. Pull the two exact lock-selected base references and save each with Podman
   as an OCI archive under `.artifact-transfer/ARCHITECTURE/bases/`. The archive hash is
   transport evidence; the lock-selected image digest remains the image
   identity checked after import.
4. Create `.artifact-transfer/ARCHITECTURE/source/nginx-ubi.bundle` with `git bundle`
   from the exact revision so the receiver can reconstruct and inspect the
   reviewed source without network access.
5. Add only approved, public evidence needed by the receiving procedure. Do
   not include credentials, tokens, private CA keys, scanner caches, unrelated
   files, or writable runtime secrets.
6. Seal the set and print its manifest digest:

   ```console
   python scripts/transfer.py create \
     --root .artifact-transfer/amd64 \
     --architecture amd64 \
     --repository-revision REVISION \
     --lock artifacts/locks/amd64.json
   ```

7. Record the printed manifest SHA-256 in the approved transfer record through
   a channel separate from the payload. Record preparer, reviewer, source and
   destination, custody changes, medium identifier, timestamps, malware-scan
   result, and authorized recipient. Make the staged set read-only before
   handoff.

### Disconnected receiving station

1. Verify custody and inspect the medium under local removable-media and
   malware policy. Copy it to a new, access-controlled staging directory.
2. Hash `transfer-manifest.json` using a pre-positioned trusted utility and
   compare it with the separately received digest before executing transferred
   code.
3. Verify and clone the Git bundle, check out the expected full revision, and
   run the repository's transfer verifier from that checkout:

   ```console
   python scripts/transfer.py verify \
     --root TRANSFER_ROOT \
     --architecture amd64 \
     --repository-revision REVISION \
     --lock artifacts/locks/amd64.json \
     --expected-manifest-sha256 EXPECTED_SHA256
   ```

4. Re-run `artifacts.py verify-bundle`, `verify-rpm-bundle.sh` with sources,
   and `components.py`. This re-establishes exact hashes, publisher signatures,
   NEVRA, architecture, source RPM, license tag, and vendor records after the
   trust-boundary crossing.
5. Import each OCI archive into the local Podman store. Confirm both exact
   lock-selected base references exist, then build with `PULL_BASES=0`; the
   build remains `--pull=never` and `--network none`.
6. Run native smoke and security checks and record the output image digest,
   source revision, lock and transfer-manifest hashes, tool versions, operator,
   time, and result. Retain evidence under local policy and sanitize the
   transfer workspace when authorized.

Repeat independently for ARM64. Offline advisory, vulnerability, revocation,
and scanner data is point-in-time: record its source and age, define the local
maximum age, and block release when that policy is exceeded. A successful
disconnected build does not prove that its intelligence was current.

## Failure and recovery rules

- Never repair a failed transfer by editing its manifest. Prepare a new empty
  staging set and obtain a new independently conveyed manifest digest.
- Quarantine media or mirror objects involved in unexplained hash/signature
  failures and open an incident under the owning environment's process.
- Retain the last accepted lock generation and immutable image digest until
  the new generation passes its rollback window.
- Never copy acquisition credentials, private trust anchors, private signing
  keys, or production TLS keys into an artifact bundle, transfer set, image,
  or evidence archive.

These procedures are implemented controls, but mirror operation, media
custody, offline freshness, and rollback execution require environment-specific
qualification before they can support a release claim.
