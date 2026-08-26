# Symfony integration

The existing Symfony website should expose the J AI functionality inside its authenticated members area.

Server-side calls should provision and manage agents through:

* `POST /v1/os/agents`
* `GET /v1/os/agents`
* `POST /v1/os/pair-code/{agent_id}`

The J AI Cloud credential must stay server-side. The browser receives only member-facing data.

The website remains a website; J OS remains the runtime.

## 1.1.1 mind creation

The members area sends an `agent_endpoint_id`, not a URL. The endpoint list is deployment configuration owned by J AI SaaS. Do not expose J Agent admin credentials or allow the browser/member to choose an arbitrary target origin.
