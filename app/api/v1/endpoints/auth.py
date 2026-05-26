from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from starlette.responses import JSONResponse

from app.api.deps import get_bearer_credentials
from app.api.v1.endpoints.auth_controller import AuthController, get_auth_controller
from app.schemas.auth import OtpRetryRequest, OtpVerifyRequest, PhoneLoginRequest, TokenRequest

router = APIRouter(tags=["Authentication"])


@router.post("/auth/token", summary="Generate OAuth2 Access Token")
def generate_token(body: Optional[TokenRequest] = None,
                   controller: AuthController = Depends(get_auth_controller)) -> JSONResponse:
    return controller.generateToken(body)


@router.get("/auth/token/status", summary="Check Token Status")
def check_token_status(controller: AuthController = Depends(get_auth_controller)) -> JSONResponse:
    return controller.checkTokenStatus()


@router.post("/auth/phone/request-otp", summary="Send OTP to phone")
def request_phone_otp(request: PhoneLoginRequest,
                      controller: AuthController = Depends(get_auth_controller)) -> JSONResponse:
    return controller.handleRequestOtp(request)


@router.post("/auth/login", summary="Phone login (alias)")
def auth_login(request: PhoneLoginRequest,
               controller: AuthController = Depends(get_auth_controller)) -> JSONResponse:
    return controller.handleRequestOtp(request)


@router.post("/auth/phone/retry-otp", summary="Retry / resend OTP")
def retry_phone_otp(request: OtpRetryRequest,
                    controller: AuthController = Depends(get_auth_controller)) -> JSONResponse:
    return controller.retryPhoneOtp(request)


@router.post("/auth/phone/verify-otp", summary="Verify OTP")
def verify_phone_otp(request: OtpVerifyRequest,
                     controller: AuthController = Depends(get_auth_controller)) -> JSONResponse:
    return controller.verifyPhoneOtp(request)


@router.post("/auth/refresh", summary="Refresh bearer access token")
def refresh_access_token(credentials: HTTPAuthorizationCredentials = Depends(get_bearer_credentials),
                         controller: AuthController = Depends(get_auth_controller)) -> JSONResponse:
    return controller.refreshAccessToken(credentials)
