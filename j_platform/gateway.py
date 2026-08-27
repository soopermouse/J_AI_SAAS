from __future__ import annotations

from dataclasses import dataclass
import http.client
import json
import os
from urllib.parse import urlsplit


@dataclass(frozen=True)
class AgentEndpoint:
    id: str
    base_url: str
    admin_token: str


class EndpointRegistry:
    """Trusted J Agent endpoints loaded only from server-side configuration."""

    def __init__(self, mapping: dict[str, AgentEndpoint] | None = None):
        self._mapping = mapping or self._from_environment()

    @staticmethod
    def _validated_base_url(value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("J Agent endpoint must use http or https")
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("invalid J Agent endpoint")
        if parsed.query or parsed.fragment or (parsed.path not in {"", "/"}):
            raise ValueError("J Agent endpoint must be an origin, not a path")
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    @classmethod
    def _from_environment(cls) -> dict[str, AgentEndpoint]:
        raw = os.getenv("J_AGENT_ENDPOINTS_JSON")
        mapping: dict[str, AgentEndpoint] = {}
        if raw:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("J_AGENT_ENDPOINTS_JSON must be an object")
            for endpoint_id, record in data.items():
                if not isinstance(record, dict):
                    raise ValueError(f"invalid endpoint config for {endpoint_id}")
                token_env = record.get("admin_token_env")
                token = os.getenv(token_env, "") if token_env else record.get("admin_token", "")
                if not token:
                    raise ValueError(f"no admin token configured for endpoint {endpoint_id}")
                mapping[str(endpoint_id)] = AgentEndpoint(
                    str(endpoint_id), cls._validated_base_url(str(record.get("url", ""))), str(token)
                )
        else:
            url = os.getenv("J_AGENT_BASE_URL")
            token = os.getenv("J_AGENT_ADMIN_TOKEN")
            if url and token:
                mapping["default"] = AgentEndpoint("default", cls._validated_base_url(url), token)
        return mapping

    def resolve(self, endpoint_id: str) -> AgentEndpoint:
        try:
            return self._mapping[endpoint_id]
        except KeyError as exc:
            raise KeyError(f"unknown J Agent endpoint: {endpoint_id}") from exc

    def ids(self) -> list[str]:
        return sorted(self._mapping)


class AgentGateway:
    """J Agent control-plane client with no redirects and endpoint-scoped secrets."""

    def __init__(self, endpoints: EndpointRegistry | None = None):
        self.endpoints = endpoints or EndpointRegistry()

    @staticmethod
    def _connection(endpoint: AgentEndpoint, timeout: float = 10.0):
        parsed = urlsplit(endpoint.base_url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        return cls(parsed.hostname, port, timeout=timeout)

    def _call(self, endpoint_id: str, method: str, path: str, body=None, admin: bool = False, mind_id: str | None = None):
        endpoint = self.endpoints.resolve(endpoint_id)
        headers = {"Accept": "application/json"}
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if admin:
            headers["Authorization"] = "Bearer " + endpoint.admin_token
        if mind_id:
            headers["X-J-Mind-ID"] = mind_id

        conn = self._connection(endpoint)
        try:
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            if 300 <= response.status < 400:
                raise RuntimeError(f"J Agent redirect refused ({response.status})")
            if response.status >= 400:
                raise RuntimeError(f"J Agent returned {response.status}: {raw.decode(errors='ignore')}")
            return json.loads(raw.decode() or "null")
        except (OSError, http.client.HTTPException) as exc:
            raise RuntimeError(f"J Agent unavailable: {exc}") from exc
        finally:
            conn.close()

    def health(self, endpoint_id: str):
        return self._call(endpoint_id, "GET", "/health")

    def provision_mind(self, endpoint_id: str, mind_id: str):
        return self._call(endpoint_id, "POST", "/v1/os/minds", {"mind_id": mind_id}, admin=True)

    def pair_code(self, endpoint_id: str, mind_id: str):
        return self._call(endpoint_id, "POST", f"/v1/os/pair-code/{mind_id}", admin=True)

    def usage(self, endpoint_id: str, mind_id: str):
        return self._call(endpoint_id, "GET", "/v1/os/usage", admin=True, mind_id=mind_id)

    def devices(self, endpoint_id: str, mind_id: str):
        return self._call(endpoint_id, "GET", "/v1/os/devices", admin=True, mind_id=mind_id)
