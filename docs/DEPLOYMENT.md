# Deployment guide

Production readiness is a property of an exact tested deployment, not an image
label. Pin the image digest and record the host, runtime, configuration, trust
material, network policy, and evidence used to approve it.

The standalone-host procedure below is a **preview profile** until it passes on
the release-candidate image and the exact Linux host baseline recorded in the
qualification ledger. The image-level restrictions are exercised by the smoke
suite; user systemd, SELinux, journald, boot, and host-restart behavior require
target-host evidence.

## Choose the lifecycle owner

| Environment | Lifecycle owner | Use systemd for this container? |
| --- | --- | --- |
| Interactive development | Podman CLI or Compose | Optional. |
| Standalone Linux host | User systemd with Podman Quadlet | Recommended. |
| Kubernetes or OpenShift | The orchestrator | No per-container systemd unit. |

Systemd does not run inside this image. On a standalone host it supervises the
rootless Podman process from outside the container. Do not use a root system
unit merely to make Podman rootless: a rootless Quadlet must be loaded by the
dedicated account's user systemd manager.

Podman 4.6 and later provide Quadlet. The first-release host qualification will
select an exact supported RHEL 9 and Podman combination; a newer Quadlet key
must not be added to the example without testing that baseline.

## Prepare a standalone Linux host

An administrator performs the host-owned steps once:

1. Patch the supported RHEL 9 host, install its vendor-supported Podman, retain
   enforcing SELinux, and confirm cgroup v2.
2. Create a dedicated, non-login service account with subordinate UID and GID
   ranges. Do not share the account with unrelated containers.
3. Enable lingering for that account so its user manager can start at boot and
   continue after interactive sessions end:

   ```console
   sudo loginctl enable-linger nginx-service
   ```

4. Restrict who can become or administer the service account. Root or another
   authorized host administrator can still control and inspect its processes;
   rootless is privilege reduction, not a boundary from host root.
5. Configure firewall, time synchronization, journal persistence and limits,
   log forwarding, monitoring, registry trust, and approved egress.

As the service account, verify the runtime rather than assuming it is rootless:

```console
podman info --format 'rootless={{.Host.Security.Rootless}} cgroup={{.Host.CgroupsVersion}} log={{.Host.LogDriver}}'
podman version
```

The expected result includes `rootless=true` and `cgroup=2`.

## Stage deployment inputs

Create service-account-owned directories. Configuration and content should be
readable by the container identity but not writable by it. Private keys require
a separately reviewed ownership and rotation procedure; do not make them
world-readable to solve a user-namespace problem.

```console
install -d -m 0750 "$HOME/nginx-ubi9" \
  "$HOME/nginx-ubi9/conf.d" "$HOME/nginx-ubi9/html"
install -m 0444 nginx.conf "$HOME/nginx-ubi9/nginx.conf"
cp -a conf.d/. "$HOME/nginx-ubi9/conf.d/"
cp -a html/. "$HOME/nginx-ubi9/html/"
chmod -R a-w "$HOME/nginx-ubi9/conf.d" "$HOME/nginx-ubi9/html"
```

On SELinux hosts, the example uses private `:Z` relabeling on these dedicated
trees. Do not apply `:Z` to a shared or system directory. If several containers
must share a tree, design and test an appropriate shared label instead of
disabling SELinux separation.

Before promotion, obtain the released image through the approved transfer or
registry process, verify its digest-bound signature and attestations, and load
or pull the exact digest. The service definition deliberately uses `Pull=never`
so startup cannot silently replace the approved artifact.

```console
IMAGE='ghcr.io/datopsis/nginx-ubi9@sha256:<approved-digest>'
podman pull "$IMAGE"
podman image inspect "$IMAGE"
```

## Install the rootless Quadlet

Copy [the reviewed example](examples/systemd/nginx-ubi9.container) into the
service account's rootless Quadlet search path and replace every placeholder:

```console
install -d -m 0700 "$HOME/.config/containers/systemd"
install -m 0600 docs/examples/systemd/nginx-ubi9.container \
  "$HOME/.config/containers/systemd/nginx-ubi9.container"
systemctl --user daemon-reload
QUADLET_UNIT_DIRS="$HOME/.config/containers/systemd" \
  /usr/lib/systemd/system-generators/podman-system-generator --user --dryrun
systemctl --user start nginx-ubi9.service
systemctl --user status nginx-ubi9.service
curl --fail http://127.0.0.1:8080/healthz
```

Quadlet-generated services are enabled through the source file's `[Install]`
section during generation; do not rely on `systemctl --user enable` against the
generated transient service. `WantedBy=default.target` plus lingering provides
boot start for the user manager.

The example enforces:

- an immutable image digest and no startup pull;
- container UID/GID `999:0` under a rootless Podman user namespace;
- a read-only root with only a bounded, `noexec,nosuid,nodev` `/tmp` tmpfs;
- all capabilities dropped, no new privileges, and bounded processes, memory,
  shared memory, and file descriptors;
- loopback-only HTTP publication until an exposure decision is approved;
- read-only configuration and content mounts with SELinux relabeling;
- journald collection, graceful `SIGQUIT` stop, and on-failure restart; and
- configuration health checks and an explicit reload operation.

To make the service reachable beyond the host, change the publish address only
after the firewall, upstream load balancer, TLS boundary, source-IP behavior,
and client network are approved. Rootless port forwarding can change the
address visible to NGINX; qualify the selected Podman network backend before
using an address as an identity, allow-list key, or rate-limit key.

## Operate, reload, update, and roll back

Validate configuration before reload, then use the systemd operation:

```console
podman exec nginx-ubi9 nginx -t
systemctl --user reload nginx-ubi9.service
systemctl --user is-active nginx-ubi9.service
curl --fail http://127.0.0.1:8080/healthz
```

For an update:

1. Verify and preload the new digest.
2. Validate its configuration in a disposable container with the same mounts
   and restrictions.
3. Change only `Image=` in the Quadlet and retain the previous file and digest.
4. Run `systemctl --user daemon-reload` and restart the service.
5. Verify image digest, health, logs, routes, TLS, upstream behavior, resource
   use, and alerts.
6. If acceptance fails, restore the prior Quadlet and digest, reload, restart,
   and record the rollback.

Stopping the unit sends the image's `SIGQUIT` stop signal and waits for the
configured timeout:

```console
systemctl --user stop nginx-ubi9.service
```

Measure termination during qualification. Increasing the timeout is safe when
real connections need longer drainage; forcing termination without evidence
can truncate responses.

## Logging with systemd

NGINX writes access events to stdout and error/lifecycle events to stderr.
`LogDriver=journald` makes Podman submit those streams to the host journal;
systemd also records the generated unit's start, stop, and failure messages.
These are host-side records. No logging daemon or rotating file runs in the
container.

Use both service and container views during diagnosis:

```console
journalctl --user -u nginx-ubi9.service --since today
journalctl --user -u nginx-ubi9.service --follow
podman logs --since 10m nginx-ubi9
podman inspect --format '{{.HostConfig.LogConfig.Type}}' nginx-ubi9
```

Do not assume `journalctl --user` is durable merely because it displays current
events. The host owner must configure and verify journal storage, maximum use,
free-space reserve, rate limiting, retention, reader authorization, forwarding,
and alerting for dropped or stalled logs. Persistent journal storage is also
required for complete `--user` journal views. Central forwarding should be
authenticated and encrypted and must preserve the container name, image digest,
host, timestamp, boot/restart identity, stream, and configured NGINX fields.

See [Logging](LOGGING.md) for the application field contract and sensitive-data
rules. Journald protects storage and access according to the host policy; it
does not by itself establish non-repudiation or an off-host immutable archive.

## Deployment cybersecurity package

Cybersecurity review should receive evidence for the exact deployment, not a
generic statement that the image is hardened:

- authorization boundary, data flows, ports, protocols, upstreams, DNS, trust
  anchors, administrators, and external services;
- image digest plus signature, provenance, SBOM, vulnerability, license, and
  tailored SCAP results;
- host/RHEL, kernel, Podman, OCI runtime, cgroup, SELinux, systemd, and journald
  versions and effective configuration;
- Quadlet and mounted-configuration digests, runtime inspection, process UID,
  capabilities, `NoNewPrivs`, mount flags, resource limits, and network rules;
- TLS and secret inventory, ownership, issuance, rotation, expiry monitoring,
  revocation limitations, and negative-test results;
- log schema, destination, time source, access rules, retention, capacity,
  forwarding, alerting, failure tests, and disposal;
- availability objectives, capacity and denial-of-service tests, health and
  shutdown evidence, monitoring, incident response, patching, update, rollback,
  controlled transfer, and decommissioning procedures; and
- the applicable control matrix with inherited, image-owned, deployment-owned,
  host-owned, organization-owned, not-applicable, and residual-risk decisions.

The [threat model](THREAT-MODEL.md) identifies threats and trust boundaries;
the [security-control guide](SECURITY-CONTROLS.md) defines ownership and the
component evidence supplied to a system-level authorization package.

## Qualification checklist

Before this profile becomes supported, test on every claimed architecture and
host/runtime combination:

- boot without an interactive login, logout persistence, orderly host reboot,
  unexpected process exit, restart throttling, and no restart after an
  intentional stop;
- declared and arbitrary non-root identities, read-only mounts, SELinux
  enforcement, capability and `NoNewPrivs` inspection, resource exhaustion,
  disk pressure, and temporary-directory failure;
- configuration validation, reload under traffic, graceful stop with active
  connections, update, failed update, and rollback;
- HTTP and TLS positive and negative cases, approved ingress/egress, DNS
  failure, upstream failure, source-address behavior, and firewall rules; and
- access/error/lifecycle/health events, persistent journal behavior, restart
  correlation, forwarding interruption, rate-limit loss, retention, access
  control, and recovery without secret disclosure.

Record exact commands, results, limitations, configuration hashes, timestamps,
and evidence locations in the release-candidate qualification record.

## Authoritative references

- [Podman Quadlet and rootless search paths](https://docs.podman.io/en/v5.3.2/markdown/podman-systemd.unit.5.html)
- [Current Podman container-unit options](https://docs.podman.io/en/latest/markdown/podman-container.unit.5.html)
- [RHEL 9 container management and lingering](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/htmlsingle/building_running_and_managing_containers/)
- [systemd journal querying](https://www.freedesktop.org/software/systemd/man/255/journalctl.html)
- [systemd journal storage and limits](https://www.freedesktop.org/software/systemd/man/252/journald.conf.html)
