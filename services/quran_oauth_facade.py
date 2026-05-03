from datetime import datetime

from auth.impl.oauth_token_provider import OAuthTokenProvider
from constants.token_config import TokenConfig
from dto.models import TokenResponse


class QuranOAuthFacade:
    def __init__(self, provider: OAuthTokenProvider) -> None:
        self._provider = provider

    def issue_access_token(self, force_refresh: bool) -> TokenResponse:
        if force_refresh:
            self._provider.clear_token()
        access_token = self._provider.get_access_token()
        remaining_seconds = TokenConfig.EXPIRY_TIME.value
        if self._provider.expiry:
            remaining_seconds = int(
                (self._provider.expiry - datetime.now()).total_seconds()
            )
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=remaining_seconds,
            scope=TokenConfig.SCOPE.value,
        )

    def token_status_view(self) -> dict:
        now = datetime.now()
        if not self._provider.access_token or not self._provider.expiry:
            return {
                "cached": False,
                "expired": None,
                "expires_in": None,
            }, "No token currently cached"

        expired = now >= self._provider.expiry
        expires_in = (
            int((self._provider.expiry - now).total_seconds()) if not expired else 0
        )
        payload = {
            "cached": True,
            "expired": expired,
            "expires_in": expires_in if not expired else None,
        }
        message = "Token expired" if expired else "Token is valid"
        return payload, message
