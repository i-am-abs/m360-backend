from typing import Optional

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from starlette.responses import JSONResponse

from app.schemas.auth import TokenRequest, PhoneLoginRequest, OtpRetryRequest, OtpVerifyRequest
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran_oauth_service import QuranOAuthService
from app.utils.response import success_response

class AuthController:
    def __init__(self, phoneAuthService: PhoneAuthService, quranOAuthService: QuranOAuthService) -> None:
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
        channel = request.retry_channel
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
