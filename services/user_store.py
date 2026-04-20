import json
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from constants.env_keys import EnvKeys
from exceptions.api_exception import ApiException
from services.google_places.support.env import load_project_dotenv


class UserStore:
    def __init__(self):
        load_project_dotenv()
        self._path = os.getenv(EnvKeys.USER_STORE_FILE.value, "").strip()
        if not self._path:
            raise ApiException(
                "USER_STORE_FILE is not configured",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
        self._lock = RLock()
        self._bootstrap_store()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _bootstrap_store(self) -> None:
        with self._lock:
            parent = os.path.dirname(self._path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            if not os.path.exists(self._path):
                self._write(
                    {
                        "users_by_phone": {},
                        "favorites_by_user_id": {},
                        "sessions": {},
                    }
                )

    def _read(self) -> Dict[str, Any]:
        with open(self._path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, payload: Dict[str, Any]) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)

    def ensure_user(self, phone_number: str) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            user = data["users_by_phone"].get(phone_number)
            if user is None:
                user = {
                    "user_id": str(uuid4()),
                    "phone_number": phone_number,
                    "created_at": self._now_iso(),
                }
                data["users_by_phone"][phone_number] = user
                self._write(data)
            return user

    def create_session(self, user_id: str, ttl_seconds: int) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            token = str(uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            data["sessions"][token] = {
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
            }
            self._write(data)
            return {"access_token": token, "expires_in": ttl_seconds}

    def get_user_by_session(self, access_token: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            session = data["sessions"].get(access_token)
            if not session:
                return None
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.now(timezone.utc) >= expires_at:
                del data["sessions"][access_token]
                self._write(data)
                return None

            user_id = session["user_id"]
            for user in data["users_by_phone"].values():
                if user.get("user_id") == user_id:
                    return user
            return None

    def list_favorites(self, user_id: str) -> List[str]:
        with self._lock:
            data = self._read()
            return list(data["favorites_by_user_id"].get(user_id, []))

    def add_favorite(self, user_id: str, place_id: str) -> List[str]:
        with self._lock:
            data = self._read()
            favorites = data["favorites_by_user_id"].setdefault(user_id, [])
            if place_id not in favorites:
                favorites.append(place_id)
                self._write(data)
            return list(favorites)

    def remove_favorite(self, user_id: str, place_id: str) -> List[str]:
        with self._lock:
            data = self._read()
            favorites = data["favorites_by_user_id"].setdefault(user_id, [])
            data["favorites_by_user_id"][user_id] = [
                pid for pid in favorites if pid != place_id
            ]
            self._write(data)
            return list(data["favorites_by_user_id"][user_id])
