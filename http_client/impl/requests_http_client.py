import time
from http import HTTPStatus
from typing import Any, Dict, Optional

from httpx import ConnectError, HTTPStatusError, Client, TimeoutException

from constants.system_config import SystemConfig
from exceptions.api_exception import ApiException
from http_client.http_client import HttpClient


class RequestsHttpClient(HttpClient):

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 2,
        **kwargs: Any,
    ) -> Any:
        try:
            with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
                response = client.get(url, headers=headers, params=params)

                if response.status_code == HTTPStatus.UNAUTHORIZED.value:
                    raise ApiException(
                        "Unauthorized", status_code=HTTPStatus.UNAUTHORIZED.value
                    )

                response.raise_for_status()
                return response.json()

        except ConnectError as e:
            raise ApiException(
                "Cannot reach Quran Foundation API (network or DNS failed). "
                "Check internet connection and that QURAN_BASE_URL / OAuth host are reachable.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
            ) from e
        except TimeoutException:
            if retries > 0:
                time.sleep(1)
                return self.get(url, headers, params, retries - 1)
            raise ApiException(
                "Upstream timeout", status_code=HTTPStatus.GATEWAY_TIMEOUT.value
            )

        except HTTPStatusError as e:
            if (
                e.response.status_code
                in (HTTPStatus.BAD_GATEWAY.value, HTTPStatus.SERVICE_UNAVAILABLE.value)
                and retries > 0
            ):
                time.sleep(1)
                return self.get(url, headers, params, retries - 1)
            raise ApiException(
                f"Upstream error for {url}",
                status_code=e.response.status_code,
            )
