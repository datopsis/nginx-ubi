# Repository governance

## Protected default branch

The active `Protect main` ruleset targets the default branch and:

- blocks deletion and non-fast-forward pushes;
- requires changes through pull requests and resolved review threads;
- requires up-to-date `lint`, `configuration security`, and aggregate `image`
  checks;
- requires approval for unattributed changes; and
- has no bypass actors.

Required approving reviews and Code Owner review currently remain zero. Enable
them only when enough independent maintainers are regularly available to avoid
deadlocking changes. Any emergency relaxation must be time bounded, justified
in the pull request, approved by a maintainer, and restored immediately.

## Security and automation settings

Keep dependency graph and vulnerability alerts, Dependabot security updates,
secret scanning, push protection, and private vulnerability reporting enabled.
Workflow permissions remain read-only by default; jobs receive write access
only for a documented publication step. Third-party Actions must use immutable
commit SHAs.

Verify these controls after a repository rename, transfer, visibility change,
or organization-policy change. Settings outside Git cannot be proven by the
presence of this document alone.

## Release tags

Before the first release, add an active tag ruleset matching the release format
in `VERSION.md`. It must block tag deletion and updates, prohibit bypass, and
allow creation only through the reviewed release procedure. Do not create a
tag rule before the release workflow and authorized actors are defined well
enough to avoid either bypassing protection or blocking every legitimate
release.

## Review ownership

`CODEOWNERS` identifies review responsibility but does not grant access or
replace branch protection. Image, workflow, test, and release-sensitive changes
require explicit security and release-impact review through the pull request
template.
