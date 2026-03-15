from typing import Optional, Set

from pymongo.collection import Collection

from config.feature_flag_config import normalize_city_for_comparison
from db.mongo_client import get_database
from feature_flags.feature_context import FeatureContext
from feature_flags.feature_flag_provider import FeatureFlagProvider
from logger.Logger import Logger

logger = Logger.get_logger(__name__)


class MongoFeatureFlagProvider(FeatureFlagProvider):

    def _get_collection(self) -> Collection:
        return get_database()["feature_flags"]

    def is_enabled(
        self,
        flag_name: str,
        context: Optional[FeatureContext] = None,
    ) -> bool:
        doc = self._get_collection().find_one({"flag_name": flag_name})
        if doc is None:
            return True

        if not doc.get("enabled", True):
            return False

        enabled_cities = doc.get("enabled_cities")
        if not enabled_cities:
            return True

        city_set: Set[str] = {
            normalize_city_for_comparison(c) for c in enabled_cities if c
        }
        city_set.discard(None)

        if not city_set:
            return True

        context_city: Optional[str] = None
        if context:
            context_city = normalize_city_for_comparison(context.city)
        if not context_city:
            return False
        return context_city in city_set
