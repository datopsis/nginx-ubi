# Contributor development environment

This document records the Ubuntu WSL2 environment exercised by contributors.
It is development evidence only. It does not qualify WSL2 as a supported
deployment platform or replace the exact RHEL-host evidence required before a
supported release.

## Exercised baseline

The environment was upgraded and requalified on 2026-09-10:

| Component | Exercised value |
| --- | --- |
| WSL | 2.7.13.0 |
| Ubuntu | 24.04.5 LTS |
| Kernel | 6.18.33.2-microsoft-standard-WSL2 |
| Init and cgroups | systemd with unified cgroup v2 |
| Podman | 5.8.2, upstream tag `v5.8.2` |
| Podman commit | `5b263b5f5b48004a87caac44e67349a8266d9ef4` |
| Podman build toolchain | Go 1.26.8; removed after installation |
| OCI runtime | Ubuntu `runc` 1.3.4 |
| Container monitor | Ubuntu `conmon` 2.1.10 |
| Network stack | Netavark 1.4.0 with Aardvark DNS 1.4.0 |
| Rootless port forwarding | `slirp4netns` 1.2.1 |
| Storage driver | rootless overlay with `fuse-overlayfs` 1.13 available |

Podman was built from the upstream signed Git tag after its tag object and
commit were verified. The engine is installed under `/usr/local`, which is the
filesystem hierarchy reserved for locally administered software:

```text
/usr/local/bin/podman
/usr/local/bin/podman-remote
/usr/local/libexec/podman/quadlet
/usr/local/libexec/podman/rootlessport
```

`/usr/bin/podman` is a symbolic link to `/usr/local/bin/podman`. This allows
deployment examples that use the conventional package path to invoke the same
5.8.2 engine used by the source-installed Quadlet generator. The Ubuntu Podman,
Buildah, and older `crun` packages are not installed.

Ubuntu remains the source of the runtime helpers and shared libraries. The
required packages are marked as explicitly installed so `apt autoremove` does
not remove them merely because the Ubuntu Podman package is absent.

## Rootless configuration

The contributor account has subordinate UID and GID mappings, lingering
enabled, and an active systemd user manager. Its local containers.conf drop-in
selects the supported OCI runtime and the WSL-compatible port forwarder:

```toml
[engine]
runtime = "runc"

[network]
default_rootless_network_cmd = "slirp4netns"
```

The drop-in is stored at:

```text
~/.config/containers/containers.conf.d/99-source-podman-runtime.conf
```

Podman 5.8.2 otherwise selected `pasta` by default. In this WSL environment,
same-port forwarding such as `127.0.0.1:8080:8080` reset connections even
though translated and dynamically assigned ports worked. The same mapping
worked with `slirp4netns`, so the override is a development-host compatibility
setting rather than an image requirement.

AppArmor support was compiled into Podman and the kernel module was present,
but the AppArmor security filesystem was not mounted. This run therefore does
not provide AppArmor policy-enforcement evidence. WSL2 also does not replace
the planned SELinux-enforcing RHEL qualification.

## Qualification performed

The following checks passed with a clean rootless store and again after
`wsl --shutdown` and a cold Ubuntu restart:

- Podman 5.8.2 selected `runc`, systemd cgroups, cgroup v2, Netavark, and the
  overlay storage driver.
- The development image built from the repository's digest-pinned UBI inputs.
- `tests/smoke.sh` completed without skipped assertions.
- The preview Quadlet generated successfully, including its memory limit.
- Quadlet start, health, static content, NGINX configuration validation,
  journald logging, reload, and graceful stop succeeded.
- The running service used UID/GID `999:0`, a read-only root, no effective
  capabilities, `no-new-privileges`, a 512 MiB memory limit, and a 128-process
  limit.
- systemd reached `running` after the cold restart with no failed units.

The validation images, containers, volumes, build layers, temporary Quadlet,
configuration copies, source tree, compiler toolchain, and rootless storage
were removed after qualification. The results describe repository commit
`d47148359ea6328521c05321b19a4274c76bf3e`; they are not release-candidate
evidence for later image-affecting revisions.

## Contributor checks

After changing the local runtime or upgrading a helper, recheck the engine
before building:

```console
podman version
podman info
systemctl --user is-system-running
stat -fc %T /sys/fs/cgroup
```

Then use the canonical repository workflow:

```console
podman build --format docker --file Containerfile \
  --tag localhost/nginx-ubi9:development .
CONTAINER_RUNTIME=podman IMAGE=localhost/nginx-ubi9:development \
  bash tests/smoke.sh
```

Installing Ubuntu's `podman` package can replace the `/usr/bin/podman`
symbolic link and reintroduce two engine versions. Treat that as an intentional
engine replacement: review the package plan, revalidate the dependency set,
and repeat the cold-start build and smoke checks. A future source upgrade must
also verify the upstream tag and commit, stage the install for review, and
requalify Quadlet and rootless runtime behavior.
