from __future__ import annotations

import html
import os
from typing import Any


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def build_report(result: dict[str, Any], business_name: str = "Website Audit") -> str:
    brand = os.getenv("AUDIT_BRAND_NAME", "Digital Support")
    contact_name = os.getenv("AUDIT_CONTACT_NAME", "")
    contact_email = os.getenv("AUDIT_CONTACT_EMAIL", "")
    contact_phone = os.getenv("AUDIT_CONTACT_PHONE", "")

    status_icon = {"pass": "✓", "warn": "!", "fail": "×"}
    checks_html = "".join(
        f"""
        <tr>
          <td><span class='status {c['status']}'>{status_icon[c['status']]}</span></td>
          <td><strong>{_e(c['label'])}</strong></td>
          <td>{_e(c['detail'])}</td>
        </tr>
        """
        for c in result["checks"]
    )

    recommendations = "".join(f"<li>{_e(item)}</li>" for item in result["recommendations"])
    broken = "".join(f"<li>{_e(item)}</li>" for item in result.get("broken_internal_links", []))
    package = result["suggested_package"]

    contact_parts = [part for part in [contact_name, contact_email, contact_phone] if part]
    contact_line = " · ".join(_e(part) for part in contact_parts)

    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{_e(business_name)} — Digital Audit</title>
<style>
:root{{--ink:#111827;--muted:#6b7280;--panel:#f8fafc;--line:#e5e7eb;--pass:#166534;--warn:#a16207;--fail:#b91c1c;}}
*{{box-sizing:border-box}} body{{margin:0;background:#f3f4f6;color:var(--ink);font:15px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}}
.wrap{{max-width:920px;margin:40px auto;padding:0 20px}} .card{{background:white;border:1px solid var(--line);border-radius:18px;padding:28px;box-shadow:0 10px 30px rgba(0,0,0,.05);margin-bottom:18px}}
h1,h2{{line-height:1.2}} h1{{margin:0 0 6px;font-size:32px}} h2{{margin-top:0;font-size:21px}} .muted{{color:var(--muted)}}
.hero{{display:flex;gap:24px;align-items:center;justify-content:space-between}} .score{{min-width:116px;height:116px;border-radius:50%;display:grid;place-items:center;background:#111827;color:white;font-size:32px;font-weight:800}} .score small{{font-size:12px;display:block;font-weight:500;text-align:center}}
table{{width:100%;border-collapse:collapse}} td{{padding:12px 8px;border-top:1px solid var(--line);vertical-align:top}} td:first-child{{width:36px}} .status{{display:inline-grid;place-items:center;width:25px;height:25px;border-radius:50%;font-weight:800}} .status.pass{{background:#dcfce7;color:var(--pass)}} .status.warn{{background:#fef3c7;color:var(--warn)}} .status.fail{{background:#fee2e2;color:var(--fail)}}
.package{{border-left:5px solid #111827}} .price{{font-size:26px;font-weight:800}} ul{{padding-left:22px}} .footer{{text-align:center;color:var(--muted);font-size:13px;padding:8px}}
@media(max-width:640px){{.hero{{align-items:flex-start;flex-direction:column-reverse}} .score{{width:96px;height:96px;min-width:96px}}}}
</style>
</head>
<body><main class='wrap'>
<section class='card hero'>
<div><div class='muted'>{_e(brand)} · Website audit</div><h1>{_e(business_name)}</h1><div class='muted'>{_e(result['final_url'])}</div><p>This report highlights lightweight technical and conversion opportunities found automatically on the public website.</p></div>
<div class='score'><div>{result['score']}<small>Grade {result['grade']}</small></div></div>
</section>
<section class='card'><h2>Audit checks</h2><table>{checks_html}</table></section>
<section class='card'><h2>Recommended next fixes</h2><ul>{recommendations or '<li>No major recommendations from the lightweight scan.</li>'}</ul></section>
{f"<section class='card'><h2>Sampled broken links</h2><ul>{broken}</ul></section>" if broken else ''}
<section class='card package'><div class='muted'>Suggested service option</div><h2>{_e(package['name'])}</h2><div class='price'>{_e(package['price'])}</div><p>{_e(package['reason'])}</p><p class='muted'>Final scope and pricing should always be confirmed after a human review.</p></section>
<section class='card'><h2>Want these items fixed?</h2><p>The audit can be turned into a one-time cleanup, a broader digital refresh, or ongoing support depending on what the business actually needs.</p>{f'<p><strong>{contact_line}</strong></p>' if contact_line else ''}</section>
<div class='footer'>{_e(result['disclaimer'])}</div>
</main></body></html>"""
