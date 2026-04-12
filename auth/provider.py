from typing import Optional

from auth.impl.oauth_token_provider import OAuthTokenProvider
from auth.token_provider import TokenProvider

_token_provider: Optional[TokenProvider] = None


def get_token_provider(config=None) -> TokenProvider:
    global _token_provider
    if _token_provider is None:
        if config is None:
            from config.factory.quran_config_factory import create_config

            config = create_config()
        _token_provider = OAuthTokenProvider(config)
    return _token_provider
