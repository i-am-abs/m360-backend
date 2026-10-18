from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.api.deps import get_bearer_credentials, get_phone_auth_service, get_quran_oauth_service
from app.core.enums.api_endpoints import ApiEndpoint
from app.core.enums.error_code import ErrorCode
from app.core.logging import get_logger
from app.schemas.auth import (
    OtpRetryRequest,
    OtpVerifyRequest,
    PhoneLoginRequest,
    TokenRequest,
    TruecallerLoginRequest,
)
from app.services.phone_auth_service import PhoneAuthService
from app.services.quran_oauth_service import QuranOAuthService
from app.services.truecaller_auth_service import (
    ERROR_MESSAGES,
    TruecallerAuthService,
    TruecallerLoginError,
)
from app.utils.response import error_envelope, no_store, success_response

router = APIRouter(tags=["Authentication"])
_log = get_logger(__name__)


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
def verify_phone_otp(
        request: OtpVerifyRequest,
        background: BackgroundTasks,
        svc: PhoneAuthService = Depends(get_phone_auth_service),
        fastapi_request: Request = None,
) -> JSONResponse:
    data = svc.verify_otp(request.phone_number, request.req_id, request.otp)
    if fastapi_request and request.fcm_token:
        fcm = getattr(fastapi_request.app.state, "fcm_service", None)
        if fcm:
            background.add_task(fcm.store_token, data["user"]["user_id"], request.fcm_token)
    response = success_response(data, message="OTP verified")
    response.background = background
    return response


def _truecaller_error(code: ErrorCode) -> JSONResponse:
    return no_store(error_envelope(code.value, ERROR_MESSAGES[code]))


@router.post(
    ApiEndpoint.AUTH_TRUECALLER.value,
    summary="Login / sign up with Truecaller",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": TruecallerLoginRequest.model_json_schema()}},
        },
    },
)
async def truecaller_login(request: Request, background: BackgroundTasks) -> JSONResponse:
    # Parsed by hand so that every failure uses the HTTP 200 envelope and the global
    # validation handler never logs the authorization code or PKCE verifier.
    try:
        body = TruecallerLoginRequest.model_validate(await request.json())
    except ValueError:
        return _truecaller_error(ErrorCode.VALIDATION_ERROR)

    svc: Optional[TruecallerAuthService] = getattr(request.app.state, "truecaller_auth_service", None)
    if svc is None:
        return _truecaller_error(ErrorCode.TRUECALLER_NOT_CONFIGURED)

    try:
        data = await run_in_threadpool(
            svc.login, body.authorization_code, body.code_verifier, body.oauth_state,
        )
    except TruecallerLoginError as exc:
        _log.info("truecaller_login_failed code=%s", exc.code.value)
        return _truecaller_error(exc.code)
    except Exception:
        _log.exception("truecaller_login_unexpected_error")
        return _truecaller_error(ErrorCode.INTERNAL_ERROR)

    fcm = getattr(request.app.state, "fcm_service", None)
    if fcm and body.fcm_token:
        background.add_task(fcm.store_token, data["user"]["user_id"], body.fcm_token)
    response = no_store(JSONResponse(content={"status": "success", "data": data}))
    response.background = background
    return response


@router.post(ApiEndpoint.AUTH_REFRESH.value, summary="Refresh bearer access token")
def refresh_access_token(credentials: HTTPAuthorizationCredentials = Depends(get_bearer_credentials),
                         svc: PhoneAuthService = Depends(get_phone_auth_service), ) -> JSONResponse:
    data = svc.refresh_access_token(credentials.credentials)
    return success_response(data, message="Token refreshed")
