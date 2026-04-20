from typing import Any, Dict, Optional, Protocol


class PhoneNumberValidator(Protocol):
    def validate_and_format(self, phone_number: str) -> str: ...


class OtpGateway(Protocol):
    def send_otp(self, formatted_mobile: str) -> Dict[str, Any]: ...

    def retry_otp(
        self,
        widget_id: str,
        req_id: str,
        retry_channel: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def verify_otp(
        self,
        widget_id: str,
        req_id: str,
        otp: str,
    ) -> Dict[str, Any]: ...
