from auth.impl.oauth_token_provider import OAuthTokenProvider

_token_provider = None

def get_token_provider(config):
    global _token_provider
    if _token_provider is None:
        _token_provider = OAuthTokenProvider(config)
    return _token_provider
