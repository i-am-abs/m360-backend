from enum import Enum


class TokenConfig(Enum):
    GRANT_TYPE = "client_credentials"
    SCOPE = "content:read"
    EXPIRY_TIME = 3600
    TIME_DELTA = 60
