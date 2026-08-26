# J AI SaaS 1.1 — current-runtime control plane

- Replaces the 1.0 in-memory pseudo-J-OS store with a durable SaaS control plane.
- Tenant-scoped mind records route members to concrete J Agent deployments.
- Symfony/member calls are server-to-server authenticated with `J_PLATFORM_SERVER_TOKEN` and `X-J-Tenant-ID`.
- J Agent admin credentials remain server-side.
- Members-area pairing codes are issued by the actual J Agent pairing registry, not by the SaaS itself.
- Adds members-area control-plane endpoints for mind health, durable usage and connected devices.
- Keeps cloud and local deployments as first-class mind routing choices.
- Does not duplicate J OS cognition in the website/control plane.

Requires the companion J Agent 4.2.5 control-plane endpoints for usage/device views. Mobile protocol is unchanged.

The existing README is intentionally unchanged.
