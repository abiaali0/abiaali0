from __future__ import annotations

import asyncio
import sqlite3
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import EvaluationRequest, EvaluationResult, FlagCreate, FlagUpdate
from .store import FlagStore

app = FastAPI(title="FlagForge API", version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://localhost:8080"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
store = FlagStore()
clients: set[WebSocket] = set()
metrics: defaultdict[str, int] = defaultdict(int)

async def broadcast(message: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
    for client in clients:
        try:
            await client.send_json(message)
        except Exception:
            dead.append(client)
    for client in dead:
        clients.discard(client)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status":"ok","service":"flagforge-api"}

@app.get("/api/flags")
def list_flags() -> list[dict[str, Any]]:
    return store.list_flags()

@app.post("/api/flags", status_code=201)
async def create_flag(payload: FlagCreate) -> dict[str, Any]:
    try:
        flag = store.create_flag(payload.model_dump())
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Flag key already exists") from exc
    await broadcast({"type":"flag_created","flag":flag})
    return flag

@app.patch("/api/flags/{flag_key}")
async def update_flag(flag_key: str, payload: FlagUpdate) -> dict[str, Any]:
    flag = store.update_flag(flag_key, payload.model_dump(exclude_unset=True))
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    await broadcast({"type":"flag_updated","flag":flag})
    return flag

@app.post("/api/evaluate", response_model=EvaluationResult)
def evaluate(payload: EvaluationRequest) -> dict[str, Any]:
    result = store.evaluate(payload.flag_key,payload.user_id,payload.attributes)
    if not result:
        raise HTTPException(status_code=404, detail="Flag not found")
    metrics[f"evaluations:{payload.flag_key}"] += 1
    metrics[f"enabled:{payload.flag_key}"] += int(result["enabled"])
    return result

@app.get("/api/audit")
def audit(limit: int = 30) -> list[dict[str, Any]]:
    return store.list_audit(min(max(limit,1),100))

@app.get("/api/metrics")
def get_metrics() -> dict[str, Any]:
    per_flag: dict[str, Any] = {}
    for flag in store.list_flags():
        key = flag["key"]
        total = metrics[f"evaluations:{key}"]
        enabled = metrics[f"enabled:{key}"]
        per_flag[key] = {"evaluations":total,"enabled_decisions":enabled,"enabled_rate":round((enabled/total*100),1) if total else 0}
    return {"flags":per_flag}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)
    except asyncio.CancelledError:
        clients.discard(websocket)
        raise
