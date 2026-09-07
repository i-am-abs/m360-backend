from __future__ import annotations

from unittest.mock import patch

import bcrypt
import pytest

from app.services.admin_auth_service import AdminAuthService
from tests.conftest import InMemoryAdminUserStore, InMemorySessionsCollection


@pytest.fixture
def service(admin_store: InMemoryAdminUserStore, sessions: InMemorySessionsCollection) -> AdminAuthService:
    return AdminAuthService(
        token_ttl_seconds=3600,
        collection=sessions,
        admin_store=admin_store,
    )


@pytest.fixture
def seeded_store(admin_store: InMemoryAdminUserStore) -> InMemoryAdminUserStore:
    pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
    admin_store.create_admin(email="admin@test.com", password_hash=pw_hash, name="Test Admin", role="super_admin")
    return admin_store


@pytest.fixture
def seeded_service(
    seeded_store: InMemoryAdminUserStore,
    sessions: InMemorySessionsCollection,
) -> AdminAuthService:
    return AdminAuthService(
        token_ttl_seconds=3600,
        collection=sessions,
        admin_store=seeded_store,
    )


class TestAdminAuthService:
    def test_login_correct_credentials(self, seeded_service: AdminAuthService) -> None:
        result = seeded_service.login(email="admin@test.com", password="password123")
        assert result is not None
        assert "admin" in result
        assert result["admin"]["email"] == "admin@test.com"
        assert "token" in result
        assert len(result["token"]) > 0

    def test_login_wrong_password(self, seeded_service: AdminAuthService) -> None:
        result = seeded_service.login(email="admin@test.com", password="wrongpassword")
        assert result is None

    def test_login_unknown_email(self, seeded_service: AdminAuthService) -> None:
        result = seeded_service.login(email="unknown@test.com", password="password123")
        assert result is None

    def test_login_inactive_admin(self, admin_store: InMemoryAdminUserStore, sessions: InMemorySessionsCollection) -> None:
        pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
        admin_store.create_admin(email="inactive@test.com", password_hash=pw_hash, name="Inactive", role="admin")
        admin_store._admins[admin_store._by_email["inactive@test.com"]]["is_active"] = False
        svc = AdminAuthService(token_ttl_seconds=3600, collection=sessions, admin_store=admin_store)
        result = svc.login(email="inactive@test.com", password="password123")
        assert result is None

    def test_verify_session_valid(self, seeded_service: AdminAuthService) -> None:
        login_result = seeded_service.login(email="admin@test.com", password="password123")
        assert login_result is not None
        admin = seeded_service.verify_session(login_result["token"])
        assert admin is not None
        assert admin["email"] == "admin@test.com"

    def test_verify_session_invalid(self, seeded_service: AdminAuthService) -> None:
        admin = seeded_service.verify_session("nonexistent-token")
        assert admin is None

    def test_logout(self, seeded_service: AdminAuthService) -> None:
        login_result = seeded_service.login(email="admin@test.com", password="password123")
        assert login_result is not None
        seeded_service.logout(login_result["token"])
        admin = seeded_service.verify_session(login_result["token"])
        assert admin is None

    def test_verify_session_expired(self, admin_store: InMemoryAdminUserStore, sessions: InMemorySessionsCollection) -> None:
        pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
        admin_store.create_admin(email="admin@test.com", password_hash=pw_hash, name="Test Admin", role="admin")
        svc = AdminAuthService(token_ttl_seconds=3600, collection=sessions, admin_store=admin_store)
        login_result = svc.login(email="admin@test.com", password="password123")
        assert login_result is not None
        with patch("app.services.admin_auth_service.datetime") as mock_dt:
            class FakeDatetime:
                @staticmethod
                def now(tz=None):
                    import datetime as real_dt
                    return real_dt.datetime(2099, 1, 1, tzinfo=tz)
            mock_dt.now.side_effect = FakeDatetime.now
            admin = svc.verify_session(login_result["token"])
            assert admin is None
