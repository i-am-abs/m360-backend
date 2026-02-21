import time
from typing import Any, Dict, Optional

from httpx import HTTPStatusError, Client, TimeoutException

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
    ) -> Any:
        try:
            with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
                response = client.get(url, headers=headers, params=params)

                if response.status_code == 401:
                    raise ApiException("Unauthorized", status_code=401)

                response.raise_for_status()
                return response.json()

        except TimeoutException:
            if retries > 0:
                time.sleep(1)
                return self.get(url, headers, params, retries - 1)
            raise ApiException("Upstream timeout", status_code=504)

        except HTTPStatusError as e:
            if e.response.status_code in (502, 503) and retries > 0:
                time.sleep(1)
                return self.get(url, headers, params, retries - 1)
            raise ApiException(
                f"Upstream error for {url}",
                status_code=e.response.status_code,
            )
