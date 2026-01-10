from http import HTTPStatus

import requests

from constants.system_config import SystemConfig
from exceptions.api_exception import ApiException
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class RequestsHttpClient:

    def get(self, url, headers=None, params=None):
        try:
            response = requests.get(
                url=url,
                headers=headers,
                params=params,
                timeout=SystemConfig.REQUEST_TIMEOUT.value,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            status_code = (
                e.response.status_code
                if e.response
                else HTTPStatus.GATEWAY_TIMEOUT.value
            )
            raise ApiException(
                message=f"Upstream HTTP error [{status_code}] for {url}",
                status_code=status_code,
            )

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout: {url}")
            raise ApiException(
                message=f"Upstream timeout for {url}",
                status_code=HTTPStatus.GATEWAY_TIMEOUT.value,
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {url}, {e}")
            raise ApiException(
                message=f"Upstream connection error for {url}",
                status_code=HTTPStatus.BAD_GATEWAY.value,
            )
