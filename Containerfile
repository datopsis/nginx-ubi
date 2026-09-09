# syntax=docker/dockerfile:1.7

ARG UBI_MINIMAL_IMAGE="registry.access.redhat.com/ubi9/ubi-minimal:9.8@sha256:7fbeae18dc9476399f565e68255f602a3374ea8614ba3d14843565131a13ff93"
ARG UBI_MICRO_IMAGE="registry.access.redhat.com/ubi9/ubi-micro:9.8@sha256:f332c99eb8f798a8486821c91937f10ad64ee83d7e739303be2df051040918f6"

FROM ${UBI_MINIMAL_IMAGE} AS builder

ARG NGINX_RPM_VERSION="2:1.20.1-28.el9_8.5"

# Install the exact Red Hat NGINX build and its runtime dependency closure into
# a separate root. The UBI Micro final stage receives no package-management
# commands or builder caches.
# hadolint ignore=DL3041
RUN microdnf install -y dnf \
    && mkdir -p /runtime \
    && dnf install -y \
        --installroot=/runtime \
        --releasever=9 \
        --setopt=install_weak_deps=0 \
        --setopt=keepcache=0 \
        "nginx-core-${NGINX_RPM_VERSION}" \
        ca-certificates tzdata \
    && dnf clean all \
    && microdnf clean all \
    && rm -rf \
        /runtime/run/* \
        /runtime/tmp/* \
        /runtime/var/cache/dnf \
        /runtime/var/cache/nginx \
        /runtime/var/log/* \
        /runtime/var/tmp/* \
    && mkdir -p /runtime/var/log/nginx \
    && ln -s /dev/stdout /runtime/var/log/nginx/access.log \
    && ln -s /dev/stderr /runtime/var/log/nginx/error.log \
    && chown -R 0:0 /runtime/etc/nginx /runtime/usr/share/nginx \
    && chmod -R g=u /runtime/etc/nginx /runtime/usr/share/nginx

FROM ${UBI_MICRO_IMAGE}

ARG NGINX_VERSION="1.20.1"
ARG NGINX_RPM_VERSION="2:1.20.1-28.el9_8.5"

LABEL org.opencontainers.image.title="NGINX on Red Hat UBI 9" \
      org.opencontainers.image.description="A security-oriented, rootless NGINX image built on Red Hat UBI 9 Micro" \
      org.opencontainers.image.source="https://github.com/datopsis/nginx-ubi9" \
      org.opencontainers.image.documentation="https://github.com/datopsis/nginx-ubi9#readme" \
      org.opencontainers.image.licenses="BSD-2-Clause AND Apache-2.0" \
      org.opencontainers.image.vendor="Datopsis" \
      org.opencontainers.image.version="${NGINX_VERSION}" \
      io.datopsis.nginx.rpm-version="${NGINX_RPM_VERSION}"

COPY --from=builder /runtime/ /
COPY --chown=0:0 --chmod=0644 container/nginx.conf /etc/nginx/nginx.conf
COPY --chown=0:0 --chmod=0644 container/conf.d/default.conf /etc/nginx/conf.d/default.conf
COPY --chown=0:0 --chmod=0644 container/html/index.html /usr/share/nginx/html/index.html

ENV LANG="C.UTF-8" \
    TZ="UTC"

USER 999:0
WORKDIR /usr/share/nginx/html

EXPOSE 8080 8443

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["nginx", "-t", "-q"]

STOPSIGNAL SIGQUIT

ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
