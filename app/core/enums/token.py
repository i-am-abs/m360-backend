from enum import Enum


class TokenConfig(str, Enum):
    GRANT_TYPE = "client_credentials"
    SCOPE = "content"


class TokenTiming(int, Enum):
    EXPIRY_SECONDS = 3600
    REFRESH_BUFFER_SECONDS = 30
