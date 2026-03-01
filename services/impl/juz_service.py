from constants.api_endpoints import ApiEndpoints
from services.base_service import BaseService


class JuzService(BaseService):
    def get_juzs(self, language: str = "en"):
        return self._get(
            f"{ApiEndpoints.CONTENT_API_V4.value}/juzs", {"language": language}
        )
