from typing import Optional

from otp.otp_service import OtpService
from otp.impl.msg91_otp_service import Msg91OtpService

_otp_service: Optional[OtpService] = None


def get_otp_service() -> OtpService:
    global _otp_service
    if _otp_service is None:
        _otp_service = Msg91OtpService()
    return _otp_service
