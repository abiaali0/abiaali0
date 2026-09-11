from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from .audit_engine import AuditError, audit_website
from .report import build_report

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "prospects.csv"
OUT = ROOT / "reports"


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    return value or "business"


def main() -> int:
    load_dotenv(ROOT / ".env")
    if not DATA.exists():
        print(f"No {DATA}. Copy data/prospects.example.csv to data/prospects.csv and add targets.")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    timeout = int(os.getenv("AUDIT_TIMEOUT_SECONDS", "10"))
    results: list[dict] = []

    with DATA.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        business = (row.get("business") or "Website Audit").strip()
        url = (row.get("url") or "").strip()
        if not url:
            continue
        print(f"Auditing {business}: {url}")
        try:
            result = audit_website(url, timeout=timeout)
            result["business"] = business
            results.append(result)
            (OUT / f"{slugify(business)}.html").write_text(build_report(result, business), encoding="utf-8")
        except AuditError as exc:
            results.append({"business": business, "requested_url": url, "error": str(exc)})

    (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    with (OUT / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["business", "url", "score", "grade", "package", "price", "error"])
        writer.writeheader()
        for item in results:
            package = item.get("suggested_package", {})
            writer.writerow({
                "business": item.get("business", ""),
                "url": item.get("final_url") or item.get("requested_url", ""),
                "score": item.get("score", ""),
                "grade": item.get("grade", ""),
                "package": package.get("name", ""),
                "price": package.get("price", ""),
                "error": item.get("error", ""),
            })

    print(f"Wrote {len(results)} result(s) to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
