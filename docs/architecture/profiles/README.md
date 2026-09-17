# Profile pages

One page per configuration profile: its request path, what its tests
qualify, and what they deliberately do not.

Every profile is **preview / unqualified**. These pages exist so a reader
can find the boundary of a profile without reading its configuration, and
so the support matrix can point at detail rather than restate it.

| Profile | Listener | Purpose |
| --- | --- | --- |
| [Static content](static.md) | `8080` | Serves a read-only tree. |
| [HTTP reverse proxy](reverse-proxy.md) | `8080` | Forwards to one explicit HTTP upstream with reviewed headers. |
| [HTTP load balancing](load-balancer.md) | `8080` | Distributes across a pool with weighted round robin, passive member failure handling, and bounded retries that never cover non-idempotent methods. |
| [WebSocket proxying](websocket.md) | `8080` | Proxies upgrade-capable traffic under /ws and ordinary HTTP elsewhere. |
| [Request and connection limiting](rate-limited.md) | `8080` | Applies three independent budgets: request rate, concurrent connections, and per-connection bandwidth. |
| [Health and readiness](health.md) | `8080 and 8081` | Separates liveness, readiness, and an operator status surface. |
| [ClickHouse HTTP proxying](clickhouse.md) | `8080` | Bounds the shape of a request to the ClickHouse HTTP interface: methods, body size, timeouts, retries, and temporary storage. |
| [Dynamic upstream resolution](dynamic-upstream.md) | `8080` | Re-resolves the upstream per request instead of once at load, for deployments that cannot reload when endpoint addresses change. |
| [TLS termination](tls-termination.md) | `8443` | Terminates TLS 1. |
| [Mutual TLS](mutual-tls.md) | `8443` | Requires a client certificate issued by a mounted authority, and enforces a mounted revocation list. |
| [Verified HTTPS upstream](tls-upstream.md) | `8080` | Proxies to an HTTPS upstream with chain and hostname verification against a mounted trust store, and enforces a mounted revocation list. |

Profiles are mounted rather than composed — one configuration file per
container. Combining two of these in a single file is not a supported
arrangement and is not tested.
