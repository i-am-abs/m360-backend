import time
from typing import Any, Dict, Optional

from httpx import Client, ConnectError, HTTPStatusError, TimeoutException
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_502_BAD_GATEWAY,
    HTTP_503_SERVICE_UNAVAILABLE,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

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

                if response.status_code == HTTP_401_UNAUTHORIZED:
                    raise ApiException(
                        "Unauthorized", status_code=HTTP_401_UNAUTHORIZED
                    )

                response.raise_for_status()

                try:
                    return response.json()
                except ValueError:
                    raise ApiException(
                        "Invalid JSON response from upstream service",
                        status_code=HTTP_502_BAD_GATEWAY,
                    )

        except ConnectError as e:
            raise ApiException(
                "Cannot reach Quran Foundation API (network or DNS failed). "
                "Check internet connection and that QURAN_BASE_URL / OAuth host are reachable.",
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            ) from e

        except TimeoutException as e:
            if retries > 0:
                time.sleep(1)
                return self.get(
                    url=url,
                    headers=headers,
                    params=params,
                    retries=retries - 1,
                )
            raise ApiException("Upstream timeout", status_code=504) from e

        except HTTPStatusError as e:
            if (
                e.response.status_code
                in (HTTP_502_BAD_GATEWAY, HTTP_503_SERVICE_UNAVAILABLE)
                and retries > 0
            ):
                time.sleep(1)
                return self.get(
                    url=url,
                    headers=headers,
                    params=params,
                    retries=retries - 1,
                )

            raise ApiException(
                f"Upstream error for {url}",
                status_code=e.response.status_code,
            ) from e

        except Exception as e:
            raise ApiException(
                "Unexpected error while calling upstream service",
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            ) from e
