from datetime import datetime, timedelta
from typing import Any, Optional

import jwt


class JwtService:
    def __init__(
            self,
            secret_key: str,
            algorithm: str = "HS256",
            expiration_minutes: int = 60,
    ) -> None:
        self._secret = secret_key
        self._algorithm = algorithm
        self._expiration_minutes = expiration_minutes

    def create_access_token(self, subject: str, extra_claims: Optional[dict] = None) -> str:
        now = datetime.utcnow()
        payload: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(minutes=self._expiration_minutes),
        }
        if extra_claims:
            payload.update(extra_claims)
        token = jwt.encode(
            payload,
            self._secret,
            algorithm=self._algorithm,
        )
        return token if isinstance(token, str) else token.decode("utf-8")

    def decode_token(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except jwt.PyJWTError:
            return None

    def get_expiration_seconds(self) -> int:
        return self._expiration_minutes * 60
