from concurrent.futures import ThreadPoolExecutor
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from pydantic import ValidationError

from j_platform.gateway import AgentEndpoint, AgentGateway, EndpointRegistry
from j_platform.models import MindCreate, AppRegistration
from j_platform.runtime import JAIPlatform
from j_platform.store import Store


def registry_for(url: str, token: str = "secret"):
    return EndpointRegistry({"default": AgentEndpoint("default", url, token)})


def test_platform_and_tenant_isolation(tmp_path):
    r = JAIPlatform(store=Store(str(tmp_path / "p.db")), gateway=AgentGateway(registry_for("http://agent.invalid")))
    r.start()
    assert r.health()["platform"] == "J AI SaaS"
    a = r.store.create_mind("tenant_a", "Alice J", "default")
    r.store.create_mind("tenant_b", "Bob J", "default")
    assert [m["id"] for m in r.store.minds("tenant_a")] == [a["id"]]
    with pytest.raises(KeyError):
        r.store.get_mind("tenant_b", a["id"])


def test_store_survives_restart(tmp_path):
    p = str(tmp_path / "p.db")
    s = Store(p)
    m = s.create_mind("t", "J", "default")
    s2 = Store(p)
    assert s2.get_mind("t", m["id"])["agent_endpoint_id"] == "default"


def test_client_cannot_submit_agent_base_url():
    with pytest.raises(ValidationError):
        MindCreate.model_validate({"name": "J", "agent_base_url": "http://evil.invalid"})


def test_gateway_control_plane_contract_and_no_redirect_following():
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, obj):
            b = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            seen.append((self.command, self.path, self.headers.get("Authorization")))
            if self.path == "/health":
                self._send({"status": "ok"})
            elif self.path == "/v1/os/usage":
                self._send({"lifetime": {"total_tokens": 42}})
            elif self.path == "/v1/os/devices":
                self._send({"devices": [{"device_id": "d1"}]})
            elif self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:1/leak")
                self.end_headers()

        def do_POST(self):
            seen.append((self.command, self.path, self.headers.get("Authorization")))
            self._send({"code": "ABCD-EF01"})

    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{srv.server_port}"
    g = AgentGateway(registry_for(base))
    assert g.health("default")["status"] == "ok"
    assert g.usage("default", "default")["lifetime"]["total_tokens"] == 42
    assert g.devices("default", "default")["devices"][0]["device_id"] == "d1"
    assert g.pair_code("default", "mind_x")["code"] == "ABCD-EF01"
    with pytest.raises(RuntimeError, match="redirect refused"):
        g._call("default", "GET", "/redirect", admin=True)
    srv.shutdown()
    assert seen[0][2] is None
    assert all(x[2] == "Bearer secret" for x in seen[1:4])


def test_apps_are_tenant_scoped(tmp_path):
    s = Store(str(tmp_path / "p.db"))
    s.register_app("tenant_a", AppRegistration(id="crm", name="A CRM", capabilities=["read"]))
    s.register_app("tenant_b", AppRegistration(id="crm", name="B CRM", capabilities=["write"]))
    assert s.apps("tenant_a")[0]["name"] == "A CRM"
    assert s.apps("tenant_b")[0]["name"] == "B CRM"
    s.register_app("tenant_b", AppRegistration(id="crm", name="B2 CRM", capabilities=[]))
    assert s.apps("tenant_a")[0]["name"] == "A CRM"
    assert s.apps("tenant_b")[0]["name"] == "B2 CRM"


def test_sqlite_concurrent_writes_are_serialized(tmp_path):
    s = Store(str(tmp_path / "p.db"))

    def create(i):
        return s.create_mind("tenant", f"J {i}", "default")["id"]

    with ThreadPoolExecutor(max_workers=12) as pool:
        ids = list(pool.map(create, range(40)))
    assert len(set(ids)) == 40
    assert len(s.minds("tenant")) == 40


def test_compose_binds_container_to_all_interfaces():
    from pathlib import Path
    compose = (Path(__file__).resolve().parents[1] / "docker-compose.local.yml").read_text()
    assert "J_PLATFORM_HOST: 0.0.0.0" in compose


def test_local_code_keeps_loopback_default():
    from pathlib import Path
    app = (Path(__file__).resolve().parents[1] / "j_platform" / "app.py").read_text()
    assert 'os.getenv("J_PLATFORM_HOST", "127.0.0.1")' in app

def test_gateway_scopes_usage_and_devices_with_mind_header():
    from j_platform.gateway import AgentGateway, EndpointRegistry, AgentEndpoint
    captured=[]
    class FakeResponse:
        status=200
        def read(self): return b'{}'
    class FakeConnection:
        def request(self, method, path, body=None, headers=None): captured.append((method,path,dict(headers or {})))
        def getresponse(self): return FakeResponse()
        def close(self): pass
    gateway=AgentGateway(EndpointRegistry({'e':AgentEndpoint('e','http://agent','secret')}))
    gateway._connection=lambda endpoint, timeout=10.0: FakeConnection()
    gateway.usage('e','acme')
    gateway.devices('e','beta')
    assert captured[0][2]['X-J-Mind-ID']=='acme'
    assert captured[1][2]['X-J-Mind-ID']=='beta'
    assert captured[0][2]['Authorization']=='Bearer secret'


def test_gateway_can_provision_mind_with_admin_auth():
    from j_platform.gateway import AgentGateway, EndpointRegistry, AgentEndpoint
    captured=[]
    class R:
        status=200
        def read(self): return b'{"mind_id":"mind_acme","created":true}'
    class C:
        def request(self, method, path, body=None, headers=None): captured.append((method,path,body,dict(headers or {})))
        def getresponse(self): return R()
        def close(self): pass
    g=AgentGateway(EndpointRegistry({'e':AgentEndpoint('e','http://agent','secret')}))
    g._connection=lambda endpoint, timeout=10.0: C()
    out=g.provision_mind('e','mind_acme')
    assert out['created'] is True
    assert captured[0][0:2] == ('POST','/v1/os/minds')
    assert captured[0][3]['Authorization']=='Bearer secret'
    assert b'mind_acme' in captured[0][2]

def test_store_provisioning_status_transition(tmp_path):
    s=Store(str(tmp_path/'p.db'))
    m=s.create_mind('tenant','J','default', mind_id='mind_fixed', status='provisioning')
    assert m['status']=='provisioning'
    assert s.set_mind_status('tenant','mind_fixed','ready')['status']=='ready'
