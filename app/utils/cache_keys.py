from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


def stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def create_sha256_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_cache_key(prefix: str, namespace: str, payload: Any) -> str:
    clean_prefix = (prefix or "m360").strip() or "m360"
    digest = create_sha256_digest(stable_json_dumps(payload))
    return f"{clean_prefix}:cache:{namespace}:{digest}"


def create_http_get_cache_key(
        prefix: str,
        url: str,
        params: Optional[Dict[str, Any]],
) -> str:
    return create_cache_key(
        prefix,
        "http:get",
        {"url": url, "params": params or {}},
    )


def create_request_get_cache_key(
        prefix: str,
        path: str,
        query_items: Any,
        authorization_header: str,
) -> str:
    return create_cache_key(
        prefix,
        "api:get",
        {
            "path": path,
            "query_items": sorted(list(query_items or [])),
            "authorization": create_sha256_digest(authorization_header or ""),
        },
    )


def create_normalized_text_hash(value: str) -> str:
    return create_sha256_digest((value or "").strip().lower())[:32]


def create_normalized_geo_text(value: float) -> str:
    return f"{round(float(value), 5):.5f}"
