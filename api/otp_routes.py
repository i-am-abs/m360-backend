from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from config.factory.otp_factory import get_otp_service
from constants.api_endpoints import ApiEndpoints
from dto.otp_models import OtpVerifyRequest
from logger.Logger import Logger
from otp.otp_service import OtpService
from utils.http_response import success_response

logger = Logger.get_logger(__name__)
otp_router = APIRouter(tags=["OTP"])


@otp_router.post(
    ApiEndpoints.OTP_VERIFY.value,
    summary="Verify MSG91 OTP access-token",
    description=(
        "Accepts the JWT access-token returned by the MSG91 OTP widget "
        "on the Flutter client and verifies it against MSG91's API."
    ),
)
def verify_otp(
    request: OtpVerifyRequest,
    otp_service: OtpService = Depends(get_otp_service),
):
    if not request.access_token.strip():
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="access_token must not be blank",
        )

    try:
        result = otp_service.verify_access_token(request.access_token)
        status_msg = "OTP verified" if result.get("verified") else "OTP verification failed"
        return success_response(result, message=status_msg)
    except Exception as e:
        logger.error("OTP verification error: %s", e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OTP verification failed: {str(e)}",
        )
