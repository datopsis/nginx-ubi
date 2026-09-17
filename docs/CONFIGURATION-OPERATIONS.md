# Configuration operations

This guide covers mounting configuration into the image, validating a candidate
before it reaches a running container, reloading, rolling back, and the
troubleshooting and redaction rules that go with them.

It describes the development image. Nothing here is a support claim; see
[the support matrix](SUPPORT.md) for the current position, and
[the profile guide](CONFIGURATION-PROFILES.md) for what each configuration
does.

## Mounting configuration

Configuration, certificates, private keys, and trust stores are mounted
read-only. Nothing in this image writes to them, and the runtime identity needs
no write access to any of them.

The container runs as a non-root user in group `0` and can be given an
arbitrary UID. Mounted files therefore have to be readable by that identity
through their own mode and ownership. A file the container cannot read produces
a startup failure or a `403`, not a fallback.

Two failure modes are worth knowing before the first deployment, because both
look like a configuration bug rather than a permission problem:

- A directory created by `mktemp -d` is `0700`. The container identity cannot
  traverse it, so every request under it answers `403` even though the files
  inside are world-readable.
- Rootless Podman maps the invoking user onto container GID `0`, so a
  group-readable file owned by that user is readable in the container. Rootful
  Docker preserves host ownership instead, and its container GID `0` is host
  root, so the identical file is unreadable. A mount that works under one can
  fail under the other.

### Mount the directory, not the file

**Mount the directory that contains the configuration, and point NGINX at a
file inside it.** Do not bind-mount the configuration file itself.

A bind mount of a single file resolves to that file's inode. Replacing the file
by rename — which is what `sed -i`, most editors, and every "write a new file
then `mv` it into place" deployment does — creates a *new* inode. The mount
still points at the old one, so the container keeps serving the previous
configuration.

This fails silently. NGINX reports the reload as successful, because it did
successfully reload the file it can see:

```console
# Single-file mount, replaced by rename: reload succeeds, nothing changes.
podman kill --signal HUP nginx-ubi9
# ... the previous configuration is still live
```

Only an in-place rewrite that preserves the inode is picked up by a single-file
mount, which excludes most of the ways configuration actually gets deployed.
With a directory mount, an atomic rename inside the directory is picked up
normally.

## Validating a candidate

Validate a candidate configuration with the same image that will run it, before
any running container is touched. `nginx -t` parses the configuration and
exits non-zero when it is invalid, so it can gate a deployment:

```console
podman run --rm \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777 \
  --cap-drop ALL \
  --volume /path/to/config:/etc/nginx/mounted:ro \
  localhost/nginx-ubi9:development \
  -t -q -c /etc/nginx/mounted/nginx.conf
```

A valid configuration exits `0` and prints nothing with `-q`. An invalid one
exits `1` and names the file and line:

```text
nginx: [emerg] unknown directive "invalid_directive" in /etc/nginx/nginx.conf:1
nginx: configuration file /etc/nginx/nginx.conf test failed
```

Run the check with the same restrictions the deployment uses. A configuration
that validates without them can still fail to start under a read-only root or
an arbitrary UID, and finding that out during a rollout is worse than finding
it here.

`nginx -t` checks syntax and the resolvability of names used at load time. It
does not check that an upstream is reachable, that a certificate matches its
key's intended use, or that a mounted path contains what it should.

## Reloading

A reload replaces worker processes without dropping the listening socket. PID 1
is retained, so the container is not restarted and no connection is refused
during the change.

```console
podman kill --signal HUP nginx-ubi9
```

Reload applies configuration, certificates, and trust stores that are read at
load time. It does not change anything fixed when the container was created:
published ports, mounts, the user, capabilities, tmpfs sizes, and environment
all require a new container.

**Validate before reloading.** If the new configuration is invalid, NGINX keeps
running the old one and reports the error on the error stream. The service
survives, but a deployment that assumed the reload took effect is now running
something other than what it thinks.

After a reload, confirm the change took effect by observing behaviour rather
than by the absence of an error. The silent-rename case above is exactly the
situation where the reload reports success and nothing changed.

## Rolling back

Configuration and image roll back independently.

For a configuration change, restore the previous configuration into the mounted
directory and reload. Keep the previous version alongside the current one so a
rollback is a rename rather than a rebuild.

For an image change, run the previous digest. Releases are pinned by immutable
digest precisely so a rollback names an exact artifact:

```console
podman run ... registry.example/nginx-ubi9@sha256:<previous digest>
```

A configuration rollback is reversible in seconds and affects one container. An
image rollback restores a known filesystem. Neither undoes a change already
made to an upstream, a trust store held elsewhere, or data a client has already
received.

## Troubleshooting

| Symptom | Usual cause |
| --- | --- |
| Startup fails naming a path under `/tmp` | The writable `tmpfs` is missing, too small, or mounted `noexec` where execution is needed |
| Every request answers `403` | The mounted directory is not traversable by the runtime identity, commonly mode `0700` |
| Startup fails naming the configuration file and a line | A syntax error; reproduce with `nginx -t` rather than by restarting |
| Startup fails resolving an upstream name | The name is resolved at load time and the service does not exist yet |
| Reload reports success, behaviour unchanged | A single-file bind mount replaced by rename |
| Works under Podman, fails under Docker | Mounted file ownership, as described above |
| A large response fills `/tmp` | Proxy buffering spilled to the temporary path; bound it or disable disk buffering |

Startup failures print to the error stream, which the runtime captures. Read
them with `podman logs` before changing anything: this image reports the file
and line it objected to, and guessing is slower than reading.

## Logging and secret redaction

The full logging contract is in [the logging guide](LOGGING.md) and the
per-profile schemas are in
[the profile guide](CONFIGURATION-PROFILES.md). Two rules matter most when
changing configuration:

**Log the path, never the request line.** Every profile here records `$uri` and
never `$request`, `$request_uri`, or `$args`. Query strings carry credentials,
signed-link tokens, and query text — the ClickHouse profile is the clearest
case, where the interface accepts both a password and a full query as request
parameters. Logging the request line writes those into the access stream, and
from there into collectors, retention, and backups. This is a structural
exclusion, not a filter, and reintroducing `$request` removes it.

**Redaction is only as good as the whole pipeline.** A collector, error
tracker, or front proxy that records full request lines reintroduces exactly
what these profiles exclude. Check what sits downstream before treating the
access stream as redacted.

Private keys are never logged, never written into the image, and never printed
on failure. A key that cannot be read produces a startup error naming the
*path*, not the contents.

## What is not covered here

Runtime log collection, rotation ownership, retention, and pipeline failure
belong to the platform and are not qualified. Certificate and CRL lifecycle
operations are in [the TLS lifecycle guide](TLS-LIFECYCLE.md). Artifact and
image lifecycle, including mirrors and disconnected transfer, is in
[the artifact lifecycle guide](ARTIFACT-LIFECYCLE.md).
