# syntax=docker/dockerfile:1.7

ARG UBI_MINIMAL_IMAGE="registry.access.redhat.com/ubi9/ubi-minimal:9.8@sha256:e5161a7d7d99cf22e4f34b72e111211a399d956d9b0e8714da18e9c4c8151041"
ARG UBI_MICRO_IMAGE="registry.access.redhat.com/ubi9/ubi-micro:9.8@sha256:7a0454cbd9bd847e8f6a63b6f0254a6efbeb6e0ed71a5d824a4f6cccbe626650"

# The caller overrides this empty stage with a verified local named context.
# Keeping the fallback empty makes a missing bundle fail instead of pulling an
# image that happens to use the context name.
FROM scratch AS artifact_bundle

FROM ${UBI_MINIMAL_IMAGE} AS builder

ARG ARTIFACT_LOCK_SHA256

COPY --from=artifact_bundle / /bundle/
COPY --chmod=0755 scripts/install-rpm-bundle.sh /usr/local/bin/install-rpm-bundle

# Installation consumes only the complete local RPM closure. Network access
# and base-image pulling are disabled by the invoking build command.
RUN test -n "${ARTIFACT_LOCK_SHA256}" \
    && test "$(tr -d '\n' </bundle/LOCK-SHA256)" = "${ARTIFACT_LOCK_SHA256}" \
    && /usr/local/bin/install-rpm-bundle /bundle /runtime \
    && rm -rf \
        /runtime/run/* \
        /runtime/tmp/* \
        /runtime/var/cache/* \
        /runtime/var/log/* \
        /runtime/var/tmp/* \
    && mkdir -p /runtime/var/log/nginx \
    && ln -s /dev/stdout /runtime/var/log/nginx/access.log \
    && ln -s /dev/stderr /runtime/var/log/nginx/error.log \
    && chown -R 0:0 /runtime/etc/nginx /runtime/usr/share/nginx \
    && chmod -R g=u /runtime/etc/nginx /runtime/usr/share/nginx

FROM ${UBI_MICRO_IMAGE}

LABEL org.opencontainers.image.title="NGINX on Red Hat UBI 9" \
      org.opencontainers.image.description="A security-oriented, rootless NGINX image built on Red Hat UBI 9 Micro" \
      org.opencontainers.image.source="https://github.com/datopsis/nginx-ubi" \
      org.opencontainers.image.documentation="https://github.com/datopsis/nginx-ubi#readme" \
      org.opencontainers.image.licenses="BSD-2-Clause AND Apache-2.0" \
      org.opencontainers.image.vendor="Datopsis" \
      org.opencontainers.image.version="1.30.4" \
      io.datopsis.nginx.rpm-version="2:1.30.4-1.el9.ngx"

COPY --from=builder /runtime/ /
RUN rm -rf /etc/yum.repos.d
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
