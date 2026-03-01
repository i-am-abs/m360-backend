from enum import Enum


class TokenConfig(Enum):
    EXPIRY_TIME = 60 * 60
    TIME_DELTA = 30
    GRANT_TYPE = "client_credentials"
    SCOPE = "content"
