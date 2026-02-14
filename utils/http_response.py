from __future__ import annotations

from typing import Any, Dict


def success_response(data: Any) -> Dict[str, Any]:
    return {"success": True, "data": data}


def error_response(message: str, code: str | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "message": message}
    if code is not None:
        out["code"] = code
    return out
