from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from http import HTTPStatus
from typing import Any, Dict, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.exceptions.base import ApiException

log = get_logger(__name__)

MUX_BASE = "https://api.mux.com"


class MuxService:
    def __init__(self) -> None:
        settings = get_settings()
        self._token_id = settings.mux_token_id
        self._token_secret = settings.mux_token_secret
        self._webhook_secret = settings.mux_webhook_secret

    def _auth_header(self) -> str:
        raw = f"{self._token_id}:{self._token_secret}"
        return f"Basic {base64.b64encode(raw.encode()).decode()}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
        }

    def create_direct_upload(self, cors_origin: str = "*") -> Dict[str, Any]:
        with httpx.Client() as client:
            resp = client.post(
                f"{MUX_BASE}/video/v1/uploads",
                headers=self._headers(),
                json={
                    "new_asset_settings": {
                        "playback_policy": ["public"],
                        "encoding_tier": "baseline",
                    },
                    "cors_origin": cors_origin,
                },
            )
            if resp.status_code != 201:
                log.error("Mux create upload failed: %s %s", resp.status_code, resp.text)
                raise ApiException(
                    "Failed to create Mux upload",
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                )
            data = resp.json().get("data", {})
            return {
                "upload_url": data.get("url"),
                "upload_id": data.get("id"),
                "asset_id": data.get("asset_id"),
                "status": data.get("status"),
            }

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        with httpx.Client() as client:
            resp = client.get(
                f"{MUX_BASE}/video/v1/assets/{asset_id}",
                headers=self._headers(),
            )
            if resp.status_code != 200:
                log.warning("Mux get asset failed: %s", resp.status_code)
                return None
            return resp.json().get("data")

    def get_playback_id(self, asset_id: str) -> Optional[str]:
        asset = self.get_asset(asset_id)
        if not asset:
            return None
        playbacks = asset.get("playback_ids") or []
        for pb in playbacks:
            if pb.get("policy") == "public":
                return pb.get("id")
        return None

    def verify_webhook(self, body: bytes, signature_header: str) -> Optional[Dict[str, Any]]:
        try:
            parts = signature_header.split(",")
            sig_parts = {}
            for part in parts:
                kv = part.split("=", 1)
                if len(kv) == 2:
                    sig_parts[kv[0]] = kv[1]

            timestamp = sig_parts.get("t", "")
            sig1 = sig_parts.get("v1", "")
            if not timestamp or not sig1:
                return None

            raw = f"{timestamp}.{body.decode()}"
            expected = hmac.new(
                self._webhook_secret.encode(),
                raw.encode(),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(expected, sig1):
                log.warning("Mux webhook signature mismatch")
                return None

            return json.loads(body)
        except Exception as e:
            log.warning("Mux webhook verify error: %s", e)
            return None
