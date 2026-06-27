from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from starlette.responses import JSONResponse

from app.api.deps import get_bearer_credentials, get_phone_auth_service, get_quran_oauth_service
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.auth import OtpRetryRequest, OtpVerifyRequest, PhoneLoginRequest, TokenRequest
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran_oauth_service import QuranOAuthService
from app.utils.response import success_response

router = APIRouter(tags=["Authentication"])


@router.post(ApiEndpoint.AUTH_TOKEN.value, summary="Generate OAuth2 Access Token")
def generate_token(
        body: Optional[TokenRequest] = None,
        svc: QuranOAuthService = Depends(get_quran_oauth_service),
) -> JSONResponse:
    force = bool(body.force_refresh) if body else False
    token = svc.issue_access_token(force)
    return success_response(token.model_dump(), message="Token generated")


@router.get(ApiEndpoint.AUTH_TOKEN_STATUS.value, summary="Check Token Status")
def check_token_status(
        svc: QuranOAuthService = Depends(get_quran_oauth_service),
) -> JSONResponse:
    payload, message = svc.token_status()
    return success_response(payload, message=message)


def handle_request_otp(request: PhoneLoginRequest, svc: PhoneAuthService) -> JSONResponse:
    data = svc.request_otp(request.phone_number)
    return success_response(data, message="OTP sent")


@router.post(ApiEndpoint.AUTH_PHONE_REQUEST_OTP.value, summary="Send OTP to phone")
def request_phone_otp(request: PhoneLoginRequest,
                      svc: PhoneAuthService = Depends(get_phone_auth_service), ) -> JSONResponse:
    return handle_request_otp(request, svc)


@router.post(ApiEndpoint.AUTH_LOGIN.value, summary="Phone login (alias)")
def auth_login(request: PhoneLoginRequest, svc: PhoneAuthService = Depends(get_phone_auth_service), ) -> JSONResponse:
    return handle_request_otp(request, svc)


@router.post(ApiEndpoint.AUTH_PHONE_RETRY_OTP.value, summary="Retry / resend OTP")
def retry_phone_otp(request: OtpRetryRequest,
                    svc: PhoneAuthService = Depends(get_phone_auth_service), ) -> JSONResponse:
    channel = request.retry_channel.value if request.retry_channel else None
    data = svc.retry_otp(request.phone_number, request.req_id, channel)
    return success_response(data, message="OTP resent")


@router.post(ApiEndpoint.AUTH_PHONE_VERIFY_OTP.value, summary="Verify OTP")
def verify_phone_otp(request: OtpVerifyRequest,
                     svc: PhoneAuthService = Depends(get_phone_auth_service), ) -> JSONResponse:
    data = svc.verify_otp(request.phone_number, request.req_id, request.otp)
    return success_response(data, message="OTP verified")


@router.post(ApiEndpoint.AUTH_REFRESH.value, summary="Refresh bearer access token")
def refresh_access_token(credentials: HTTPAuthorizationCredentials = Depends(get_bearer_credentials),
                         svc: PhoneAuthService = Depends(get_phone_auth_service), ) -> JSONResponse:
    data = svc.refresh_access_token(credentials.credentials)
    return success_response(data, message="Token refreshed")
