# J AI SaaS 1.1.3 — Mind-Scoped Agent Control Plane

- Usage and device gateway calls now send `X-J-Mind-ID`.
- Tenant ownership checks remain in the SaaS query boundary; J Agent independently scopes the returned runtime state.
- Endpoint-scoped admin credentials and redirect refusal are unchanged.

Verification: 9 tests passed.
