from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
from pathlib import Path
from typing import Any


class Store:
    """Thread-safe durable SaaS control-plane store."""

    def __init__(self, path: str | None = None):
        self.path = Path(path or os.getenv("J_PLATFORM_DB", "j_platform.sqlite3"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=30.0)
        self.db.row_factory = sqlite3.Row
        with self._lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA busy_timeout=30000")
            self.db.execute("PRAGMA foreign_keys=ON")
            self._migrate_schema()

    def _migrate_schema(self) -> None:
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS tenants(
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'mobile',
            monthly_token_limit INTEGER NOT NULL DEFAULT 0
        );
        """)

        mind_info = self.db.execute("PRAGMA table_info(minds)").fetchall()
        if not mind_info:
            self.db.executescript("""
            CREATE TABLE minds(
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                agent_endpoint_id TEXT NOT NULL DEFAULT 'default',
                status TEXT NOT NULL DEFAULT 'ready',
                deployment TEXT NOT NULL DEFAULT 'cloud',
                FOREIGN KEY(tenant_id) REFERENCES tenants(id)
            );
            """)
        elif "agent_base_url" in [r[1] for r in mind_info]:
            self.db.executescript("""
            ALTER TABLE minds RENAME TO minds_v110;
            CREATE TABLE minds(
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                agent_endpoint_id TEXT NOT NULL DEFAULT 'default',
                status TEXT NOT NULL DEFAULT 'ready',
                deployment TEXT NOT NULL DEFAULT 'cloud',
                FOREIGN KEY(tenant_id) REFERENCES tenants(id)
            );
            INSERT INTO minds(id,tenant_id,name,agent_endpoint_id,status,deployment)
                SELECT id,tenant_id,name,'default',status,deployment FROM minds_v110;
            DROP TABLE minds_v110;
            """)

        app_info = self.db.execute("PRAGMA table_info(apps)").fetchall()
        if app_info:
            pk_cols = [r[1] for r in app_info if r[5]]
            if pk_cols != ["tenant_id", "id"]:
                self.db.executescript("""
                ALTER TABLE apps RENAME TO apps_v110;
                CREATE TABLE apps(
                    tenant_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    capabilities TEXT NOT NULL DEFAULT '[]',
                    PRIMARY KEY(tenant_id, id),
                    FOREIGN KEY(tenant_id) REFERENCES tenants(id)
                );
                INSERT OR IGNORE INTO apps(tenant_id,id,name,capabilities)
                    SELECT tenant_id,id,name,capabilities FROM apps_v110;
                DROP TABLE apps_v110;
                """)
        else:
            self.db.executescript("""
            CREATE TABLE apps(
                tenant_id TEXT NOT NULL,
                id TEXT NOT NULL,
                name TEXT NOT NULL,
                capabilities TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY(tenant_id, id),
                FOREIGN KEY(tenant_id) REFERENCES tenants(id)
            );
            """)
        self.db.commit()

    def ensure_tenant(self, tenant_id: str, name: str | None = None, plan: str = "mobile") -> dict[str, Any]:
        with self._lock:
            self.db.execute("INSERT OR IGNORE INTO tenants(id,name,plan) VALUES(?,?,?)", (tenant_id, name or tenant_id, plan))
            self.db.commit()
            return self.tenant(tenant_id)

    def tenant(self, tenant_id: str):
        with self._lock:
            row = self.db.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
            if not row:
                raise KeyError(tenant_id)
            return dict(row)

    def create_mind(self, tenant_id: str, name: str, agent_endpoint_id: str = "default", deployment: str = "cloud"):
        with self._lock:
            self.ensure_tenant(tenant_id)
            mid = "mind_" + secrets.token_urlsafe(12)
            self.db.execute(
                "INSERT INTO minds(id,tenant_id,name,agent_endpoint_id,status,deployment) VALUES(?,?,?,?,?,?)",
                (mid, tenant_id, name, agent_endpoint_id, "ready", deployment),
            )
            self.db.commit()
            return self.get_mind(tenant_id, mid)

    def get_mind(self, tenant_id: str, mind_id: str):
        with self._lock:
            row = self.db.execute("SELECT * FROM minds WHERE tenant_id=? AND id=?", (tenant_id, mind_id)).fetchone()
            if not row:
                raise KeyError(mind_id)
            return dict(row)

    def minds(self, tenant_id: str):
        with self._lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM minds WHERE tenant_id=? ORDER BY name", (tenant_id,)).fetchall()]

    def register_app(self, tenant_id: str, app):
        with self._lock:
            self.ensure_tenant(tenant_id)
            self.db.execute("""
                INSERT INTO apps(tenant_id,id,name,capabilities) VALUES(?,?,?,?)
                ON CONFLICT(tenant_id,id) DO UPDATE SET
                    name=excluded.name,
                    capabilities=excluded.capabilities
            """, (tenant_id, app.id, app.name, json.dumps(app.capabilities)))
            self.db.commit()
            return {"id": app.id, "name": app.name, "capabilities": app.capabilities}

    def apps(self, tenant_id: str):
        with self._lock:
            rows = self.db.execute("SELECT * FROM apps WHERE tenant_id=? ORDER BY id", (tenant_id,)).fetchall()
            return [{**dict(r), "capabilities": json.loads(r["capabilities"])} for r in rows]
