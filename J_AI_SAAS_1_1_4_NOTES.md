# J AI SaaS 1.1.4 — Mind Provisioning Lifecycle

- Creating a SaaS mind now provisions it on the selected J Agent endpoint.
- Control-plane rows move `provisioning -> ready` only after Agent acceptance.
- Failed Agent provisioning is persisted as `failed` and returned as HTTP 502.
