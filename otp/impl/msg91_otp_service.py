import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from httpx import Client, ConnectError, HTTPStatusError, TimeoutException
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_502_BAD_GATEWAY,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from constants.system_config import SystemConfig
from exceptions.api_exception import ApiException
from logger.Logger import Logger
from otp.otp_service import OtpService

logger = Logger.get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_env() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _get_auth_key() -> str:
    _load_env()
    key = os.getenv("MSG91_AUTH_KEY", "").strip()
    if not key:
        raise ValueError("Missing MSG91_AUTH_KEY. Set it in .env to use OTP service.")
    return key


class Msg91OtpService(OtpService):
    """MSG91 OTP widget access-token verifier.

    Flow:
        1. Flutter app renders the MSG91 OTP widget.
        2. User completes phone verification in the widget.
        3. Widget returns a JWT access-token to the Flutter app.
        4. Flutter sends that token to our  POST /otp/verify  endpoint.
        5. This service calls MSG91's verifyAccessToken API to confirm validity.
    """

    VERIFY_URL = SystemConfig.MSG91_VERIFY_TOKEN_URL.value

    def verify_access_token(self, access_token: str) -> Dict[str, Any]:
        auth_key = _get_auth_key()

        payload = {
            "authkey": auth_key,
            "access-token": access_token,
        }

        try:
            with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
                response = client.post(
                    self.VERIFY_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                body = response.json() if response.text else {}
                logger.debug("MSG91 verify response: status=%s body=%s", response.status_code, body)

                if response.status_code == HTTP_401_UNAUTHORIZED:
                    return {
                        "verified": False,
                        "message": body.get("message", "Invalid or expired OTP token"),
                        "type": body.get("type", ""),
                    }

                response.raise_for_status()

                return {
                    "verified": True,
                    "message": body.get("message", "Token verified successfully"),
                    "type": body.get("type", ""),
                }

        except ConnectError as e:
            logger.error("MSG91 API unreachable: %s", e)
            raise ApiException(
                "Cannot reach MSG91 API. Check network.",
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

        except TimeoutException:
            raise ApiException("MSG91 API timeout", status_code=504)

        except HTTPStatusError as e:
            logger.error("MSG91 API error: %s", e.response.text)
            raise ApiException(
                f"MSG91 API error: {e.response.status_code}",
                status_code=HTTP_502_BAD_GATEWAY,
            ) from e
