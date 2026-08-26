from .store import Store
from .gateway import AgentGateway


class JAIPlatform:
    capabilities = ["tenant.minds", "mind.routing", "os.apps", "os.device_pairing", "os.usage", "cloud_local"]

    def __init__(self, store=None, gateway=None):
        self.store = store or Store()
        self.gateway = gateway or AgentGateway()
        self.started = False

    def start(self):
        self.started = True

    def health(self):
        return {
            "platform": "J AI SaaS",
            "status": "running" if self.started else "stopped",
            "deployment_neutral": True,
            "capabilities": self.capabilities,
        }


JOSRuntime = JAIPlatform
