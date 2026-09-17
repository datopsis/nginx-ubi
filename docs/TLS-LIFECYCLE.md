# TLS certificate, trust, and revocation lifecycle

This runbook covers the repository's preview TLS termination, mutual-TLS, and
verified HTTPS-upstream profiles. The deployment's PKI owner remains
responsible for issuance, authorization, revocation decisions, protected key
storage, and incident response. The image consumes mounted material and does
not enroll with a CA or generate production keys.

[The TLS trust diagram](architecture/README.md#tls-trust) shows the three
trust directions and what this image does not provide.

## Mounted material contract

| Profile | Required files | Purpose |
| --- | --- | --- |
| TLS termination | `server.crt`, `server.key` | Ordered server chain and matching private key. |
| Mutual TLS | Termination files plus `client-ca.crt`, `client.crl` | Narrow client trust bundle and current issuer CRLs. |
| Verified upstream | `upstream-ca.crt`, `upstream.crl` | Narrow backend trust bundle and current issuer CRLs. |

Mount the directory read-only. Grant the runtime UID read access to the private
key through a narrowly assigned group or secret projection; do not make a
production key world-readable. Trust and CRL bundles may contain multiple PEM
objects during a controlled rotation. Include the CRL for every relevant
issuer, including intermediates.

The mTLS profile uses NGINX's `ssl_crl`; the upstream profile uses
`proxy_ssl_crl`. A revoked client certificate is rejected before application
content is served, and a revoked backend certificate produces a gateway
failure. CRLs are local deployment inputs: the image does not download them,
use an implicit network responder, or define a fail-open path.

## Lifecycle monitoring

Run the public-metadata checker against every deployed leaf certificate and
CRL. It never accepts a private-key path and emits one JSON document suitable
for a monitoring wrapper:

```console
python scripts/tls_material.py --warning-hours 720 \
  --certificate /run/nginx-tls/server.crt \
  --crl /run/nginx-tls/client.crl
```

Exit status `0` means every deadline is outside the warning window, `1` means
at least one item is warning or expired, and `2` means input or inspection
failed. Exact expiry is expired, not warning. Alert routing, acknowledgement,
escalation, maintenance suppression, clock monitoring, and proof of delivery
belong to the deployment platform. Treat status `2` as loss of monitoring, not
as evidence that material is healthy.

Monitor CRL `nextUpdate` as well as certificate `notAfter`. Choose a warning
window longer than the combined CA issuance, approval, deployment, validation,
and rollback time. The test harness uses intentionally short-lived material
only to keep the rehearsal self-contained.

## Leaf renewal

1. Issue a new leaf certificate with the same reviewed service identity and
   required extended-key usage.
2. Verify its chain, hostname, validity, key match, and file permissions before
   changing the mount source.
3. Replace the certificate and key together using the platform's atomic secret
   update mechanism.
4. Run `nginx -t -q`, reload or replace the container, and confirm the served
   serial from an independent client.
5. Retain the previous secret version until rollback and active-connection
   requirements are satisfied, then dispose of it under the key policy.

The automated rehearsal proves that a validated reload serves a new leaf
serial while the non-root master process and read-only mount remain intact.

## CA trust rotation

Use an overlap sequence; never replace the old CA before all peers present a
certificate chaining to the new CA:

1. Deploy a bundle containing the old and new CA certificates and both current
   CRL sets. Validate and reload or replace every verifier.
2. Prove the overlap bundle still accepts a peer under the old issuer.
3. Roll peer leaf certificates to the new issuer and prove the overlap bundle
   accepts them.
4. Deploy the new-only CA and CRL bundle after the rollback window closes.
5. Prove the retired old-only bundle rejects the new peer and the new-only
   bundle accepts it. Archive only the public evidence required by policy.

The TLS harness exercises all three trust states with isolated CAs. If a phase
fails, keep or restore the last working overlap bundle; do not disable hostname,
chain, or revocation verification to recover service.

## Revocation updates and incidents

Publish a new signed CRL after a revocation decision, validate its issuer and
freshness, atomically update the mounted bundle, run `nginx -t -q`, and reload
or replace the verifier. Confirm a non-revoked credential still works and the
revoked serial fails. The rehearsal covers revoked client and upstream server
certificates plus untrusted and wrong-hostname certificates.

CRL checking is not real-time. Exposure remains between the revocation decision
and successful CRL deployment, and stale CRLs become an availability risk.
Document maximum publication and deployment latency, `nextUpdate`, outage
behavior, emergency rollback authority, and how CA compromise changes the
normal overlap process.

## Cryptographic-policy boundary

The profiles constrain protocol versions and TLS 1.2 cipher suites, but the
effective algorithms, providers, implementation validation, and system-wide
policy depend on the exact UBI libraries, host/runtime, and deployment mode.
Record the image digest, NGINX build output, RPM manifest, negotiated protocol
and cipher evidence, host cryptographic policy, certificate algorithms, and
scanner versions for qualification.

These profiles do not establish that the image or deployment is FIPS validated.
Exact platform cryptographic-policy and FIPS-boundary qualification remains a
separate roadmap item.

Authoritative directive behavior is documented by NGINX for
[`ssl_crl`](https://nginx.org/en/docs/http/ngx_http_ssl_module.html#ssl_crl)
and [`proxy_ssl_crl`](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_ssl_crl).
