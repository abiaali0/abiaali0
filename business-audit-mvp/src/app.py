from __future__ import annotations

import html
import os

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, HttpUrl

from .audit_engine import AuditError, _assert_public_host, audit_website, normalize_url
from .report import build_report

load_dotenv()
app = FastAPI(title="AuditLead", version="1.1.0")


class AuditRequest(BaseModel):
    url: HttpUrl


def _timeout() -> int:
    try:
        return max(3, min(int(os.getenv("AUDIT_TIMEOUT_SECONDS", "10")), 30))
    except ValueError:
        return 10


def _stripe_key() -> str:
    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def _price_cents() -> int:
    try:
        return max(100, int(os.getenv("AUDIT_PRICE_CENTS", "1900")))
    except ValueError:
        return 1900


def _free_reports_enabled() -> bool:
    return os.getenv("AUDIT_ENABLE_FREE_REPORTS", "true").strip().lower() in {"1", "true", "yes", "on"}


def _currency() -> str:
    value = os.getenv("AUDIT_CURRENCY", "cad").strip().lower()
    return value if value.isalpha() and len(value) == 3 else "cad"


def _public_base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _validate_target(raw_url: str) -> str:
    url = normalize_url(raw_url)
    _assert_public_host(url)
    return url


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "payments": "enabled" if _stripe_key() else "disabled"}


@app.post("/api/audit")
def audit(payload: AuditRequest):
    if not _free_reports_enabled() and _stripe_key():
        raise HTTPException(status_code=404, detail="Free audits are disabled.")
    try:
        return audit_website(str(payload.url), timeout=_timeout())
    except AuditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/report", response_class=HTMLResponse)
def report(url: str = Query(..., min_length=4), business: str = "Website Audit"):
    if not _free_reports_enabled() and _stripe_key():
        raise HTTPException(status_code=404, detail="Free reports are disabled.")
    try:
        result = audit_website(url, timeout=_timeout())
    except AuditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(build_report(result, business_name=business))


@app.get("/checkout")
def checkout(url: str = Query(..., min_length=4), business: str = "Website Audit"):
    key = _stripe_key()
    if not key:
        if _free_reports_enabled():
            return RedirectResponse(url=f"/report?url={html.escape(url, quote=True)}&business={html.escape(business, quote=True)}", status_code=303)
        raise HTTPException(status_code=503, detail="Payments are not configured yet.")

    try:
        target = _validate_target(url)
    except AuditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stripe.api_key = key
    base = _public_base_url()
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=f"{base}/paid-report?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/?cancelled=1",
            line_items=[
                {
                    "price_data": {
                        "currency": _currency(),
                        "unit_amount": _price_cents(),
                        "product_data": {
                            "name": "Website Audit Report",
                            "description": "Automated website audit with score and prioritized recommendations",
                        },
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "target_url": target[:500],
                "business": business[:200],
            },
        )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail="Could not start checkout.") from exc

    return RedirectResponse(url=session.url, status_code=303)


@app.get("/paid-report", response_class=HTMLResponse)
def paid_report(session_id: str = Query(..., min_length=5)):
    key = _stripe_key()
    if not key:
        raise HTTPException(status_code=503, detail="Payments are not configured.")

    stripe.api_key = key
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError as exc:
        raise HTTPException(status_code=400, detail="Invalid checkout session.") from exc

    if getattr(session, "payment_status", None) != "paid":
        raise HTTPException(status_code=402, detail="Payment has not been completed.")

    metadata = getattr(session, "metadata", {}) or {}
    url = metadata.get("target_url", "")
    business = metadata.get("business", "Website Audit")
    if not url:
        raise HTTPException(status_code=400, detail="No audit target was stored with this payment.")

    try:
        result = audit_website(url, timeout=_timeout())
    except AuditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return HTMLResponse(build_report(result, business_name=business))


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    brand = html.escape(os.getenv("AUDIT_BRAND_NAME", "AuditLead"))
    paid = bool(_stripe_key())
    price = _price_cents() / 100
    currency = _currency().upper()
    action = "/checkout" if paid else "/report"
    button = f"Buy audit — {price:.2f} {currency}" if paid else "Run preview audit"
    note = (
        "Secure payment is processed by Stripe. Your report is generated after payment."
        if paid
        else "Preview mode is active because Stripe has not been configured yet."
    )
    return HTMLResponse(
        f"""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>{brand}</title>
<style>body{{font-family:system-ui;background:#f3f4f6;margin:0;color:#111827}}main{{max-width:720px;margin:10vh auto;background:white;padding:38px;border-radius:20px;border:1px solid #e5e7eb}}input{{width:100%;padding:14px;margin:8px 0 16px;border:1px solid #d1d5db;border-radius:10px;font-size:16px}}button{{padding:13px 18px;border:0;border-radius:10px;background:#111827;color:white;font-weight:700;cursor:pointer}}p{{color:#6b7280;line-height:1.6}}.fine{{font-size:13px}}</style></head><body><main><h1>{brand}</h1><p>Get a lightweight website audit with a 0–100 score, technical checks, conversion opportunities, and prioritized recommendations.</p><form method='get' action='{action}'><label>Business name</label><input name='business' placeholder='Example Business'><label>Website URL</label><input name='url' placeholder='https://example.com' required><button type='submit'>{html.escape(button)}</button></form><p class='fine'>{html.escape(note)}</p></main></body></html>"""
    )
