from pydantic import BaseModel, ConfigDict, Field


class MindCreate(BaseModel):
    """Create a mind routed to a server-side configured J Agent endpoint."""

    model_config = ConfigDict(extra="forbid")
    name: str
    agent_endpoint_id: str = "default"
    deployment: str = "cloud"


class AppRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    capabilities: list[str] = Field(default_factory=list)
