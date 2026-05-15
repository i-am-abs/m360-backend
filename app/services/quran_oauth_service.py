from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Tuple

from app.core.enums.token import TokenConfig, TokenTiming
from app.interfaces.token_provider import TokenProvider
from app.schemas.auth import TokenResponse


class QuranOAuthService:
    def __init__(self, provider: TokenProvider) -> None:
        self._provider = provider

    def issue_access_token(self, force_refresh: bool = False) -> TokenResponse:
        if force_refresh:
            self._provider.clear_token()
        access_token = self._provider.get_access_token()
        remaining = TokenTiming.EXPIRY_SECONDS.value
        if self._provider.expiry:
            remaining = int((self._provider.expiry - datetime.now()).total_seconds())
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=remaining,
            scope=TokenConfig.SCOPE.value,
        )

    def token_status(self) -> Tuple[Dict[str, Any], str]:
        now = datetime.now()
        if not self._provider.access_token or not self._provider.expiry:
            return {"cached": False, "expired": None, "expires_in": None}, "No token currently cached"
        expired = now >= self._provider.expiry
        expires_in = int((self._provider.expiry - now).total_seconds()) if not expired else 0
        payload = {
            "cached": True,
            "expired": expired,
            "expires_in": expires_in if not expired else None,
        }
        return payload, ("Token expired" if expired else "Token is valid")
