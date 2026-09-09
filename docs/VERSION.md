# Versioning and releases

The published container image is versioned independently from repository
history. Git commits identify every repository revision; release versions
identify container artifacts that this project intentionally publishes and
supports.

## Container release format

Annotated release tags use:

```text
v<nginx-version>-ubi<ubi-version>-<packaging-revision>
```

For example, `v1.28.0-ubi9.6-1` would identify:

- NGINX `1.28.0`;
- the named UBI `9.6` release; and
- Datopsis packaging revision `1` for that exact NGINX and UBI pair.

The example does not select the first release inputs. The actual NGINX and UBI
versions and image digests must be verified and recorded during the upstream
baseline work in `docs/ROADMAP.md`.

This upstream-derived format is not Semantic Versioning. The packaging
revision is a positive integer beginning at `1`. It increases monotonically
within one exact NGINX and named UBI pair, even if the project temporarily
releases another pair and later returns to it.

Release tags are immutable. Never move or reuse a release tag. Production
deployments should pin the OCI digest; a human-readable tag describes a
release, while its digest identifies exact image content.

## When to change the container version

| Change | Version action |
| --- | --- |
| Change the NGINX version | Use the new NGINX version and revision `1` if that exact NGINX/UBI pair has never been released; otherwise use its next unused revision. |
| Change the named UBI release | Use the new UBI version and revision `1` if the pair is new; otherwise use its next unused revision. |
| Refresh a pinned digest within the same named UBI release | Increment the packaging revision. |
| Change image contents, runtime behavior, default configuration, entrypoint, build inputs, or release metadata | Increment the packaging revision. |
| Change only documentation, tests, development tooling, policies, examples not copied into the image, issue templates, or analysis workflows | Do not create or change a container release version unless an image is deliberately republished. |

Every newly published image receives a new release tag, including a deliberate
rebuild whose expected filesystem is unchanged.

## Repository-only revisions

A repository-only change is identified by its pull request and full Git commit
SHA. It does not become part of an existing supported container release merely
because it is merged to `main`.

This project does not create source-only GitHub Releases or tags. GitHub
Releases represent published container images. Use:

- a full commit SHA for an exact repository revision;
- `git describe --tags --always --dirty` for a convenient local identifier;
- the `Unreleased` section of `CHANGELOG.md` for notable changes intended for
  the next container release.

Not every repository-only change requires a changelog entry. Add one when an
operator, consumer, contributor, or security reviewer would reasonably need to
discover it. At the next image release, move accumulated entries into a dated
section named for the release tag. This records repository changes since the
previous release without claiming every entry changed the image filesystem.

## Release requirements

Before an annotated release tag is pushed:

1. Verify that the tag's NGINX and UBI versions match the pinned build inputs.
2. Convert `Unreleased` changelog entries into a dated section for the tag and
   create a new empty `Unreleased` section.
3. Complete the applicable release gates in `docs/ROADMAP.md`.
4. Merge the reviewed release change to protected `main` with required checks
   passing.
5. Create the annotated tag from that exact `main` commit.
6. Allow the tag workflow to build, scan, attest, sign, publish, and create the
   GitHub Release.
7. Verify the manifest architectures, digest, signature, provenance, SBOM,
   labels, scan evidence, and release assets before announcing support.

The release workflow should also publish a `sha-<short-commit>` image tag for
traceability. It supplements but never replaces the release tag and digest.
