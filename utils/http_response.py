from __future__ import annotations

from typing import Any, Dict, Optional


def success_response(data: Any) -> Dict[str, Any]:
    return {"success": True, "data": data}


def error_response(message: str, code: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "message": message}
    if code is not None:
        out["code"] = code
    return out
