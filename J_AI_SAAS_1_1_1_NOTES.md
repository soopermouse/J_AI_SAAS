# J AI SaaS 1.1.1 — control-plane security and durability hardening

- Removes tenant-supplied `agent_base_url` from the API contract.
- Minds reference a trusted server-side `agent_endpoint_id` instead.
- J Agent endpoint credentials are endpoint-scoped and never attached to arbitrary tenant URLs.
- Gateway refuses redirects; admin Authorization is never forwarded to a redirect target.
- Endpoint URLs are limited to trusted configured HTTP(S) origins.
- `apps` identity is `(tenant_id, id)`; one tenant can no longer replace another tenant's app.
- SQLite access is serialized with a process lock and WAL/busy-timeout enabled.
- Docker persists `/data/j_platform.sqlite3` in a named volume; the unused Postgres service is removed.
- v1.1.0 databases are migrated: existing minds are routed to the trusted `default` endpoint rather than reusing their old client-supplied URL.

README intentionally unchanged.
