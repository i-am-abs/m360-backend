from typing import Any, Dict, Protocol


class PhoneNumberValidator(Protocol):
    def validate_and_format(self, phone_number: str) -> str: ...


class OtpGateway(Protocol):
    def request_otp(self, formatted_mobile: str) -> Dict[str, Any]: ...

    def verify_otp(self, formatted_mobile: str, otp: str) -> Dict[str, Any]: ...
