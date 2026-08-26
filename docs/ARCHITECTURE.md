# Architecture

J AI Cloud is a deployment of J OS, not a replacement for it.

J OS is the runtime/platform.
J Agent runs on J OS.
Applications connect to J OS.
J Agent manages/orchestrates applications.

The Symfony website is the account/control plane only.

## Cloud

Member -> Symfony -> J AI Cloud -> J OS -> J Agent -> Apps

## Local

Client -> local J OS -> J Agent -> Apps

The same `/v1/os/*` contract is used in both deployments.

## 1.1.1 trusted agent routing

Tenant requests never supply a J Agent URL. A mind stores an `agent_endpoint_id`, which is resolved from the SaaS server's trusted endpoint registry. Endpoint credentials are scoped to that registry entry. Administrative requests never follow redirects, so an Agent or proxy cannot redirect the Authorization header to another origin.

For managed cloud deployments, configure endpoints server-side with `J_AGENT_ENDPOINTS_JSON`, or use `J_AGENT_BASE_URL` plus `J_AGENT_ADMIN_TOKEN` for a single `default` endpoint. Customer-owned/local deployments remain supported, but their endpoint must be enrolled into the trusted deployment registry rather than being accepted directly from an ordinary member request.
