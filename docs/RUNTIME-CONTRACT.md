# Rootless runtime and lifecycle contract

This document defines the tested baseline behavior of the development image.
It is image-level evidence, not yet a supported-platform or release claim.

## Startup and diagnostics

NGINX is PID 1 and starts directly as UID/GID `999:0`. There is no root phase,
privilege-changing entrypoint, or startup script that edits mounted files. An
orchestrator may assign another non-root UID with primary group 0; the runtime
still receives no capabilities and cannot gain new privileges.

The default configuration requires a writable `/tmp` for its PID and bounded
NGINX temporary directories. Under a read-only root filesystem, operators must
supply the documented `rw,noexec,nosuid,nodev` tmpfs. Startup without it fails
nonzero and identifies the first affected `/tmp/nginx-*` path and filesystem
error in the container error stream.

Configuration is consumed read-only. A syntactically invalid mounted main
configuration fails through the normal image entrypoint, exits nonzero, and
identifies the directive plus `/etc/nginx/nginx.conf` line number. The image
does not replace a bad mount with packaged defaults or enter a repair shell.
Operators should retain the container logs before restart automation discards
them.

## Reload and stop

`nginx -s reload` sends SIGHUP to the PID-1 master. The test requires:

- the master PID remains 1;
- a nonempty replacement worker set starts;
- every previous worker exits; and
- health requests succeed after reconfiguration.

The OCI stop signal is `SIGQUIT`. The lifecycle test starts a rate-limited
response, confirms that bytes are in flight, requests container stop, and
requires the complete response, graceful-shutdown log event, and exit code 0.
This proves application-level draining for the test request. Deployment stop
timeouts must still be sized for the environment's longest accepted request;
the runtime may force-kill NGINX after that timeout.

## Package inventory

Assembly compares the installed RPM database with all 79 locked RPMs before
creating the final image. It then embeds the verified, architecture-specific
manifest at `/usr/share/nginx-ubi/rpm-manifest.tsv` and removes RPM and package
manager commands. The restricted-runtime test derives the expected manifest
from the matching reviewed lock and compares the complete file SHA-256 and
80-line shape (header plus 79 packages).

The embedded manifest records filename, name, epoch, version, release,
architecture, source RPM, full signer fingerprint, and RPM SHA-256. It is
immutable image metadata for inspection and comparison; the release SBOM and
publisher-signature evidence remain separately required.

## NGINX feature and module inventory

[`artifacts/nginx-features.json`](../artifacts/nginx-features.json) records the
selected RPM's three reviewed compile features and 22 optional configure-time
modules/subsystems. `scripts/nginx_features.py` compares this record with real
`nginx -V` output and rejects missing or additional optional modules,
unreviewed `--add-module` paths, feature drift, or NGINX input-version drift.

The runtime additionally requires `/usr/lib64/nginx/modules` to be empty. No
separately packaged dynamic module is installed and the default configuration
contains no `load_module` directive.

The official RPM compiles mail and stream subsystems into the binary. They are
recorded as compiled but unsupported for the first release, have no default
configuration block or listener, and must not be represented as supported
features. HTTP/3 is also compiled, but the default configuration opens no QUIC
listener; protocol-profile support remains gated on its own configuration and
qualification work.

The configure-argument inventory covers optional build flags exposed by
`nginx -V`; NGINX modules that are always built and have no configure flag are
governed through configuration review and use-case tests rather than falsely
presented as absent.

## Automated evidence

`tests/smoke.sh` runs this contract with a read-only root, hardened `/tmp`, all
capabilities dropped, and `no-new-privileges`. Native CI runs it with Podman on
AMD64 and ARM64. The same image is then transferred locally into Docker and
the suite runs again as compatibility evidence. Neither result substitutes
for the exact supported-host and OpenShift qualification still on the roadmap.
