from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from typing import Optional

from auth.token_singleton import get_token_provider
from config.factory.quran_config_factory import create_config
from constants.api_endpoints import ApiEndpoints
from constants.token_config import TokenConfig
from dto.models import TokenResponse, TokenRequest
from utils.http_response import success_response
from utils.logger import Logger

auth_router = APIRouter(tags=["Authentication"])
logger = Logger.get_logger(__name__)


@auth_router.post(ApiEndpoints.AUTH_TOKEN.value, summary="Generate OAuth2 Access Token")
def generate_token(request: Optional[TokenRequest] = None) -> TokenResponse:
    try:
        config = create_config()
        token_provider = get_token_provider(config)
        if request and request.force_refresh:
            token_provider.clear_token()

        access_token = token_provider.get_access_token()
        remaining_seconds = TokenConfig.EXPIRY_TIME.value
        if token_provider.expiry:
            remaining_seconds = int(
                (token_provider.expiry - datetime.now()).total_seconds()
            )

        token = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=remaining_seconds,
            scope=TokenConfig.SCOPE.value,
        )
        return success_response(token.dict(), message="Token generated")

    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to generate authentication token: {str(e)}",
        )


@auth_router.get(
    "/auth/token/status",
    summary="Check Token Status",
    description="Check if there's a cached token and its expiry status",
)
def check_token_status():
    try:
        config = create_config()
        token_provider = get_token_provider(config)

        if not token_provider.access_token or not token_provider.expiry:
            return success_response(
                {
                    "cached": False,
                    "expired": None,
                    "expires_in": None,
                },
                message="No token currently cached",
            )
        expires_in = (
            int((token_provider.expiry - datetime.now()).total_seconds())
            if not datetime.now() >= token_provider.expiry
            else 0
        )

        return success_response(
            {
                "cached": True,
                "expired": datetime.now() >= token_provider.expiry,
                "expires_in": (
                    expires_in if not datetime.now() >= token_provider.expiry else None
                ),
            },
            message=(
                "Token expired"
                if datetime.now() >= token_provider.expiry
                else "Token is valid"
            ),
        )

    except Exception as e:
        logger.error(f"Token status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check token status: {str(e)}",
        )
