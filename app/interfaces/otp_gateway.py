from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class OtpGateway(ABC):
    @abstractmethod
    def send_otp(self, formatted_mobile: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def retry_otp(
            self,
            widget_id: str,
            req_id: str,
            retry_channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def verify_otp(
            self,
            widget_id: str,
            req_id: str,
            otp: str,
    ) -> Dict[str, Any]:
        pass
