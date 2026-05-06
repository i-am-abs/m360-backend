from enum import Enum

_BASE = "https://api.msg91.com/api/v5/widget"


class Msg91Endpoint(str, Enum):
    SEND_OTP = f"{_BASE}/sendOtp"
    RETRY_OTP = f"{_BASE}/retryOtp"
    VERIFY_OTP = f"{_BASE}/verifyOtp"


class RetryChannel(str, Enum):
    SMS = "sms"
    VOICE = "voice"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
