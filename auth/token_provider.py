from abc import ABC, abstractmethod


class TokenProvider(ABC):
    @abstractmethod
    def get_access_token(self) -> str:
        pass
