from enum import Enum


class SystemConfig(Enum):
    MAX_BYTES = 10 * 1024 * 1024
    REQUEST_TIMEOUT = 10
    MONGO_CONNECTION_TIMEOUT = 5e3
