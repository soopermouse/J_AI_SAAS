from __future__ import annotations

import os
import secrets
from fastapi import FastAPI, Header, HTTPException, Depends
from .runtime import JAIPlatform
from .models import MindCreate, AppRegistration

runtime = JAIPlatform()
runtime.start()
api = FastAPI(title="J AI SaaS Control Plane", version="1.1.2")


def member(x_j_platform_key: str | None = Header(default=None), x_j_tenant_id: str | None = Header(default=None)):
    expected = os.getenv("J_PLATFORM_SERVER_TOKEN")
    if not expected:
        raise HTTPException(503, "J_PLATFORM_SERVER_TOKEN is not configured")
    if not x_j_platform_key or not secrets.compare_digest(x_j_platform_key, expected):
        raise HTTPException(401, "invalid platform credential")
    if not x_j_tenant_id:
        raise HTTPException(400, "X-J-Tenant-ID is required")
    runtime.store.ensure_tenant(x_j_tenant_id)
    return x_j_tenant_id


def mind_or_404(tid: str, mid: str):
    try:
        return runtime.store.get_mind(tid, mid)
    except KeyError:
        raise HTTPException(404, "Mind not found")


@api.get("/health")
def health():
    return runtime.health()


@api.get("/v1/platform/capabilities")
def capabilities():
    return {"capabilities": runtime.capabilities}


@api.get("/v1/platform/minds")
def minds(tid=Depends(member)):
    return runtime.store.minds(tid)


@api.post("/v1/platform/minds")
def create_mind(body: MindCreate, tid=Depends(member)):
    try:
        runtime.gateway.endpoints.resolve(body.agent_endpoint_id)
    except KeyError:
        raise HTTPException(400, "Unknown agent_endpoint_id")
    return runtime.store.create_mind(tid, body.name, body.agent_endpoint_id, body.deployment)


@api.get("/v1/platform/minds/{mind_id}/health")
def mind_health(mind_id: str, tid=Depends(member)):
    mind = mind_or_404(tid, mind_id)
    try:
        return runtime.gateway.health(mind["agent_endpoint_id"])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))


@api.post("/v1/platform/minds/{mind_id}/pair-code")
def pair_code(mind_id: str, tid=Depends(member)):
    mind = mind_or_404(tid, mind_id)
    try:
        return runtime.gateway.pair_code(mind["agent_endpoint_id"], mind_id)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))


@api.get("/v1/platform/minds/{mind_id}/usage")
def usage(mind_id: str, tid=Depends(member)):
    mind = mind_or_404(tid, mind_id)
    try:
        return runtime.gateway.usage(mind["agent_endpoint_id"])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))


@api.get("/v1/platform/minds/{mind_id}/devices")
def devices(mind_id: str, tid=Depends(member)):
    mind = mind_or_404(tid, mind_id)
    try:
        return runtime.gateway.devices(mind["agent_endpoint_id"])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))


@api.post("/v1/platform/apps/register")
def register_app(body: AppRegistration, tid=Depends(member)):
    return runtime.store.register_app(tid, body)


@api.get("/v1/platform/apps")
def apps(tid=Depends(member)):
    return runtime.store.apps(tid)


def main():
    import uvicorn
    uvicorn.run(api, host=os.getenv("J_PLATFORM_HOST", "127.0.0.1"), port=int(os.getenv("J_PLATFORM_PORT", "8787")))
