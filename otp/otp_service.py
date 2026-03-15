from abc import ABC, abstractmethod
from typing import Any, Dict


class OtpService(ABC):
    """Strategy interface for OTP verification providers."""

    @abstractmethod
    def verify_access_token(self, access_token: str) -> Dict[str, Any]:
        """Verify an OTP widget access-token and return verification result.

        Returns a dict with at least:
            - verified (bool)
            - message  (str)
            - type     (str)   e.g. "phone" / "email"

        Raises ApiException on upstream / network failures.
        """
        pass
