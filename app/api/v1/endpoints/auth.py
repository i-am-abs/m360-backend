from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from starlette.responses import JSONResponse

from app.api.deps import get_bearer_credentials, get_phone_auth_service, get_quran_oauth_service
from app.core.enums.api_endpoints import ApiEndpoint
from app.schemas.auth import OtpRetryRequest, OtpVerifyRequest, PhoneLoginRequest, TokenRequest
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran_oauth_service import QuranOAuthService
from app.utils.response import success_response

router = APIRouter(tags=["Authentication"])


class AuthController:
    def __init__(
            self,
            phoneAuthService: PhoneAuthService,
            quranOAuthService: QuranOAuthService,
    ) -> None:
        self.phoneAuthService = phoneAuthService
        self.quranOAuthService = quranOAuthService

    def generateToken(self, body: Optional[TokenRequest] = None) -> JSONResponse:
        force = bool(body.force_refresh) if body else False
        token = self.quranOAuthService.issue_access_token(force)
        return success_response(token.model_dump(), message="Token generated")

    def checkTokenStatus(self) -> JSONResponse:
        payload, message = self.quranOAuthService.token_status()
        return success_response(payload, message=message)

    def handleRequestOtp(self, request: PhoneLoginRequest) -> JSONResponse:
        data = self.phoneAuthService.requestOtp(request.phone_number)
        return success_response(data, message="OTP sent")

    def retryPhoneOtp(self, request: OtpRetryRequest) -> JSONResponse:
        channel = request.retry_channel.value if request.retry_channel else None
        data = self.phoneAuthService.retryOtp(request.phone_number, request.req_id, channel)
        return success_response(data, message="OTP resent")

    def verifyPhoneOtp(self, request: OtpVerifyRequest) -> JSONResponse:
        data = self.phoneAuthService.verifyOtp(request.phone_number, request.req_id, request.otp)
        return success_response(data, message="OTP verified")

    def refreshAccessToken(self, credentials: HTTPAuthorizationCredentials) -> JSONResponse:
        data = self.phoneAuthService.refreshAccessToken(credentials.credentials)
        return success_response(data, message="Token refreshed")


def get_auth_controller(request: Request) -> AuthController:
    return AuthController(
        phoneAuthService=request.app.state.phone_auth_service,
        quranOAuthService=request.app.state.quran_oauth_service,
    )


@router.post(ApiEndpoint.AUTH_TOKEN.value, summary="Generate OAuth2 Access Token")
def generate_token(
        body: Optional[TokenRequest] = None,
        controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    return controller.generateToken(body)


@router.get(ApiEndpoint.AUTH_TOKEN_STATUS.value, summary="Check Token Status")
def check_token_status(
        controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    return controller.checkTokenStatus()


@router.post(ApiEndpoint.AUTH_PHONE_REQUEST_OTP.value, summary="Send OTP to phone")
def request_phone_otp(
        request: PhoneLoginRequest,
        controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    return controller.handleRequestOtp(request)


@router.post(ApiEndpoint.AUTH_LOGIN.value, summary="Phone login (alias)")
def auth_login(
        request: PhoneLoginRequest,
        controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    return controller.handleRequestOtp(request)


@router.post(ApiEndpoint.AUTH_PHONE_RETRY_OTP.value, summary="Retry / resend OTP")
def retry_phone_otp(
        request: OtpRetryRequest,
        controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    return controller.retryPhoneOtp(request)


@router.post(ApiEndpoint.AUTH_PHONE_VERIFY_OTP.value, summary="Verify OTP")
def verify_phone_otp(
        request: OtpVerifyRequest,
        controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    return controller.verifyPhoneOtp(request)


@router.post(ApiEndpoint.AUTH_REFRESH.value, summary="Refresh bearer access token")
def refresh_access_token(
        credentials: HTTPAuthorizationCredentials = Depends(get_bearer_credentials),
        controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    return controller.refreshAccessToken(credentials)
