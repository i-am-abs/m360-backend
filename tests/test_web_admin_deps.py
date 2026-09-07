from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import bcrypt
import pytest
from fastapi import HTTPException, Request

from app.services.admin_auth_service import AdminAuthService
from app.web.deps import web_admin_required
from tests.conftest import InMemoryAdminUserStore, InMemorySessionsCollection


@pytest.fixture
def admin_store() -> InMemoryAdminUserStore:
    store = InMemoryAdminUserStore()
    pw_hash = bcrypt.hashpw(b"adminpass", bcrypt.gensalt()).decode()
    store.create_admin(email="admin@test.com", password_hash=pw_hash, name="Admin", role="super_admin")
    return store


@pytest.fixture
def sessions() -> InMemorySessionsCollection:
    return InMemorySessionsCollection()


@pytest.fixture
def auth_service(admin_store: InMemoryAdminUserStore, sessions: InMemorySessionsCollection) -> AdminAuthService:
    return AdminAuthService(token_ttl_seconds=3600, collection=sessions, admin_store=admin_store)


@pytest.fixture
def valid_token(auth_service: AdminAuthService) -> str:
    result = auth_service.login(email="admin@test.com", password="adminpass")
    assert result is not None
    return result["token"]


class TestWebAdminRequired:
    def test_valid_token_returns_admin(self, auth_service: AdminAuthService, valid_token: str) -> None:
        request = MagicMock(spec=Request)
        request.cookies = {"admin_token": valid_token}
        admin = web_admin_required(request, auth_service)
        assert admin is not None
        assert admin["email"] == "admin@test.com"

    def test_no_cookie_raises(self, auth_service: AdminAuthService) -> None:
        request = MagicMock(spec=Request)
        request.cookies = {}
        with pytest.raises(HTTPException) as exc:
            web_admin_required(request, auth_service)
        assert exc.value.status_code == 302

    def test_invalid_token_raises(self, auth_service: AdminAuthService) -> None:
        request = MagicMock(spec=Request)
        request.cookies = {"admin_token": "invalid-token"}
        with pytest.raises(HTTPException) as exc:
            web_admin_required(request, auth_service)
        assert exc.value.status_code == 302

    def test_expired_token_raises(self, auth_service: AdminAuthService, valid_token: str) -> None:
        with pytest.raises(HTTPException) as exc:
            auth_service._collection.delete_one({"token": valid_token})
            request = MagicMock(spec=Request)
            request.cookies = {"admin_token": valid_token}
            web_admin_required(request, auth_service)
        assert exc.value.status_code == 302
