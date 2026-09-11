"""Tiny zero-dependency Python SDK for FlagForge."""
from __future__ import annotations
import json
import urllib.request
from typing import Any

class FlagForgeClient:
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")

    def enabled(self, flag_key: str, user_id: str, **attributes: Any) -> bool:
        payload = json.dumps({"flag_key":flag_key,"user_id":user_id,"attributes":attributes}).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/api/evaluate",data=payload,headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(request, timeout=2) as response:
            result = json.loads(response.read())
        return bool(result["enabled"])
