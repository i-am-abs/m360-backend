from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class UserRepository(ABC):
    @abstractmethod
    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_user(
        self,
        username: str,
        hashed_password: str,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass
