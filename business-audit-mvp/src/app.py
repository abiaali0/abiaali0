from __future__ import annotations

import html
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl

from .audit_engine import AuditError, audit_website
from .report import build_report

load_dotenv()
app = FastAPI(title="AuditLead", version="1.0.0")


class AuditRequest(BaseModel):
    url: HttpUrl


def _timeout() -> int:
    try:
        return max(3, min(int(os.getenv("AUDIT_TIMEOUT_SECONDS", "10")), 30))
    except ValueError:
        return 10


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/audit")
def audit(payload: AuditRequest):
    try:
        return audit_website(str(payload.url), timeout=_timeout())
    except AuditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/report", response_class=HTMLResponse)
def report(url: str = Query(..., min_length=4), business: str = "Website Audit"):
    try:
        result = audit_website(url, timeout=_timeout())
    except AuditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(build_report(result, business_name=business))


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    brand = html.escape(os.getenv("AUDIT_BRAND_NAME", "AuditLead"))
    return HTMLResponse(
        f"""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>{brand}</title>
<style>body{{font-family:system-ui;background:#f3f4f6;margin:0;color:#111827}}main{{max-width:720px;margin:10vh auto;background:white;padding:38px;border-radius:20px;border:1px solid #e5e7eb}}input{{width:100%;padding:14px;margin:8px 0 16px;border:1px solid #d1d5db;border-radius:10px;font-size:16px}}button{{padding:13px 18px;border:0;border-radius:10px;background:#111827;color:white;font-weight:700;cursor:pointer}}p{{color:#6b7280;line-height:1.6}}</style></head><body><main><h1>{brand}</h1><p>Run a lightweight website audit and generate a client-friendly report.</p><form method='get' action='/report'><label>Business name</label><input name='business' placeholder='Example Business'><label>Website URL</label><input name='url' placeholder='https://example.com' required><button type='submit'>Run audit</button></form></main></body></html>"""
    )
