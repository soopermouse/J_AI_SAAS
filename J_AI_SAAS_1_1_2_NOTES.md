# J AI SaaS 1.1.2 — Docker bind fix

Deployment-only correction.

- Docker Compose now sets `J_PLATFORM_HOST: 0.0.0.0` so the process is reachable through the published container port.
- Direct/local execution still defaults to `127.0.0.1` in `app.py`.
- No control-plane, tenancy, gateway, credential, storage, or API contract changes.
- Existing README intentionally unchanged.
