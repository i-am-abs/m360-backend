from enum import Enum

_BASE = "https://api.msg91.com/api/v5/widget"


class Msg91Config(Enum):
    WIDGET_SEND_OTP_URL = f"{_BASE}/sendOtp"
    WIDGET_RETRY_OTP_URL = f"{_BASE}/retryOtp"
    WIDGET_VERIFY_OTP_URL = f"{_BASE}/verifyOtp"
