from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class HttpClient(ABC):

    @abstractmethod
    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        pass
