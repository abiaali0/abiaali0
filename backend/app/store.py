from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evaluator import evaluate_flag


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FlagStore:
    def __init__(self, db_path: str | None = None) -> None:
        default_path = Path(__file__).resolve().parents[1] / "flagforge.db"
        self.db_path = db_path or os.getenv("FLAGFORGE_DB", str(default_path))
        self._lock = threading.RLock()
        self._init_schema()
        self._seed_if_empty()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS flags (
                    key TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
                    environment TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0,
                    rollout REAL NOT NULL DEFAULT 0, rules_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL,
                    flag_key TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_flag_key ON audit_events(flag_key);
            """)

    def _seed_if_empty(self) -> None:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM flags").fetchone()[0]
        if count:
            return
        self.create_flag({"key":"smart-checkout","name":"Smart Checkout","description":"Progressive rollout of the new checkout experience.","environment":"production","enabled":True,"rollout":35,"rules":[{"attribute":"plan","operator":"in","value":"pro,enterprise","enabled":True}]})
        self.create_flag({"key":"compact-nav","name":"Compact Navigation","description":"UI experiment for a denser navigation layout.","environment":"staging","enabled":True,"rollout":60,"rules":[]})

    @staticmethod
    def _row_to_flag(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["enabled"] = bool(item["enabled"])
        item["rules"] = json.loads(item.pop("rules_json"))
        return item

    def list_flags(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM flags ORDER BY updated_at DESC").fetchall()
        return [self._row_to_flag(row) for row in rows]

    def get_flag(self, key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM flags WHERE key = ?", (key,)).fetchone()
        return self._row_to_flag(row) if row else None

    def create_flag(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        with self._lock, self._connect() as conn:
            conn.execute("INSERT INTO flags(key,name,description,environment,enabled,rollout,rules_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (payload["key"],payload["name"],payload.get("description",""),payload["environment"],int(payload.get("enabled",False)),float(payload.get("rollout",0)),json.dumps(payload.get("rules",[])),now,now))
            self._audit(conn, "flag_created", payload["key"], f"Created in {payload['environment']}")
        return self.get_flag(payload["key"])  # type: ignore[return-value]

    def update_flag(self, key: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get_flag(key)
        if not current:
            return None
        merged = {**current, **{k:v for k,v in changes.items() if v is not None}}
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE flags SET name=?, description=?, enabled=?, rollout=?, rules_json=?, updated_at=? WHERE key=?", (merged["name"],merged["description"],int(merged["enabled"]),float(merged["rollout"]),json.dumps(merged["rules"]),utc_now(),key))
            self._audit(conn, "flag_updated", key, f"Updated: {', '.join(sorted(changes.keys())) or 'no-op'}")
        return self.get_flag(key)

    def evaluate(self, key: str, user_id: str, attributes: dict[str, Any]) -> dict[str, Any] | None:
        flag = self.get_flag(key)
        if not flag:
            return None
        result, reason = evaluate_flag(flag_key=key,enabled=flag["enabled"],rollout=flag["rollout"],user_id=user_id,attributes=attributes,rules=flag["rules"])
        return {"flag_key":key,"user_id":user_id,"enabled":result,"reason":reason,"environment":flag["environment"]}

    def list_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id,event_type,flag_key,detail,created_at FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _audit(conn: sqlite3.Connection, event_type: str, flag_key: str, detail: str) -> None:
        conn.execute("INSERT INTO audit_events(event_type,flag_key,detail,created_at) VALUES(?,?,?,?)", (event_type,flag_key,detail,utc_now()))
