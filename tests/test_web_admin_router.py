from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

# Set env before any app imports
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["SUPER_ADMINS"] = "admin@test.com:password123"
os.environ["MONGODB_ENABLED"] = "false"
os.environ["ADMIN_PANEL_ENABLED"] = "true"
os.environ["APP_ENV"] = "test"

from app.core.config import get_settings  # noqa: E402
from app.web import router as admin_router  # noqa: E402
from app.web.deps import AdminSession  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_caches():
    """Reset module-level caches before each test to ensure clean state."""
    admin_router._settings = None
    admin_router.ADMIN_CREDENTIALS = {}
    get_settings.cache_clear()
    yield


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.mount(
        "/admin/static",
        StaticFiles(directory="app/web/static"),
        name="admin_static",
    )
    application.include_router(admin_router.router)
    return application


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


def _make_token(overrides: Dict[str, Any] = None) -> str:
    """Helper: create a valid admin JWT for testing."""
    now = datetime.now(tz=timezone.utc)
    payload: Dict[str, Any] = {
        "admin_id": "test-admin-uuid",
        "email": "admin@test.com",
        "name": "admin",
        "role": "super_admin",
        "login_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }
    if overrides:
        payload.update(overrides)
    settings = get_settings()
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm="HS256")


class TestLoginPage:
    def test_get_login_page_without_cookie_returns_200(self, client: TestClient):
        resp = client.get("/admin/login", follow_redirects=False)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/html")
        assert "Sign in" in resp.text
        assert "Muslim360" in resp.text

    def test_get_login_page_sets_no_cache_headers(self, client: TestClient):
        resp = client.get("/admin/login", follow_redirects=False)
        assert (
            resp.headers.get("cache-control")
            == "no-store, no-cache, must-revalidate, max-age=0"
        )
        assert resp.headers.get("pragma") == "no-cache"
        assert resp.headers.get("expires") == "0"

    def test_get_login_page_with_valid_cookie_redirects_to_dashboard(
        self, client: TestClient
    ):
        token = _make_token()
        resp = client.get(
            "/admin/login", cookies={"admin_token": token}, follow_redirects=False
        )
        assert resp.status_code == 303
        assert resp.headers.get("location") == "/admin/dashboard"

    def test_get_login_page_with_expired_cookie_returns_200(self, client: TestClient):
        expired = (datetime.now(tz=timezone.utc) - timedelta(hours=2)).isoformat()
        token = _make_token({"expires_at": expired})
        resp = client.get(
            "/admin/login", cookies={"admin_token": token}, follow_redirects=False
        )
        assert resp.status_code == 200
        assert "Sign in" in resp.text

    def test_get_login_page_with_invalid_token_returns_200(self, client: TestClient):
        resp = client.get(
            "/admin/login", cookies={"admin_token": "garbage-token"}, follow_redirects=False
        )
        assert resp.status_code == 200
        assert "Sign in" in resp.text


class TestLoginSubmit:
    def test_correct_credentials_redirects_and_sets_cookie(self, client: TestClient):
        resp = client.post(
            "/admin/login",
            data={"email": "admin@test.com", "password": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers.get("location") == "/admin/dashboard"
        set_cookie = resp.headers.get("set-cookie", "")
        assert "admin_token=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Max-Age=" in set_cookie
        assert "Path=/;" in set_cookie or "Path=/" in set_cookie

    def test_wrong_password_returns_error_message(self, client: TestClient):
        resp = client.post(
            "/admin/login",
            data={"email": "admin@test.com", "password": "wrongpassword"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "Invalid email or password." in resp.text

    def test_unknown_email_returns_error_message(self, client: TestClient):
        resp = client.post(
            "/admin/login",
            data={"email": "unknown@test.com", "password": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "Invalid email or password." in resp.text

    def test_missing_fields_returns_422(self, client: TestClient):
        resp = client.post("/admin/login", data={}, follow_redirects=False)
        assert resp.status_code == 422


class TestDashboard:
    def test_without_cookie_redirects_to_login(self, client: TestClient):
        resp = client.get("/admin/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"

    def test_with_valid_cookie_returns_200(self, client: TestClient):
        token = _make_token()
        resp = client.get(
            "/admin/dashboard", cookies={"admin_token": token}, follow_redirects=False
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/html")
        assert "Dashboard" in resp.text

    def test_with_invalid_token_redirects_to_login(self, client: TestClient):
        resp = client.get(
            "/admin/dashboard", cookies={"admin_token": "garbage"}, follow_redirects=False
        )
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"

    def test_with_expired_token_redirects_to_login(self, client: TestClient):
        expired = (datetime.now(tz=timezone.utc) - timedelta(hours=2)).isoformat()
        token = _make_token({"expires_at": expired})
        resp = client.get(
            "/admin/dashboard", cookies={"admin_token": token}, follow_redirects=False
        )
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"


class TestUsersPage:
    def test_without_cookie_redirects_to_login(self, client: TestClient):
        resp = client.get("/admin/users", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"

    def test_with_valid_cookie_returns_200(self, client: TestClient):
        token = _make_token()
        resp = client.get(
            "/admin/users", cookies={"admin_token": token}, follow_redirects=False
        )
        assert resp.status_code == 200
        assert "Users" in resp.text


class TestMasjidsPage:
    def test_without_cookie_redirects_to_login(self, client: TestClient):
        resp = client.get("/admin/masjids", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"

    def test_with_valid_cookie_returns_200(self, client: TestClient):
        token = _make_token()
        resp = client.get(
            "/admin/masjids", cookies={"admin_token": token}, follow_redirects=False
        )
        assert resp.status_code == 200
        assert "Masjids" in resp.text


class TestClaimsPage:
    def test_without_cookie_redirects_to_login(self, client: TestClient):
        resp = client.get("/admin/claims", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"

    def test_with_valid_cookie_returns_200(self, client: TestClient):
        token = _make_token()
        resp = client.get(
            "/admin/claims", cookies={"admin_token": token}, follow_redirects=False
        )
        assert resp.status_code == 200
        assert "Claims" in resp.text


class TestDonationsPage:
    def test_without_cookie_redirects_to_login(self, client: TestClient):
        resp = client.get("/admin/donations", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"

    def test_with_valid_cookie_returns_200(self, client: TestClient):
        token = _make_token()
        resp = client.get(
            "/admin/donations", cookies={"admin_token": token}, follow_redirects=False
        )
        assert resp.status_code == 200
        assert "Donations" in resp.text


class TestLogout:
    def test_logout_redirects_to_login_and_deletes_cookie(self, client: TestClient):
        token = _make_token()
        resp = client.get(
            "/admin/logout", cookies={"admin_token": token}, follow_redirects=False
        )
        assert resp.status_code == 303
        assert resp.headers.get("location") == "/admin/login"
        set_cookie = resp.headers.get("set-cookie", "")
        assert "admin_token=" in set_cookie
        # Max-Age=0 is the standard way to delete a cookie
        assert "Max-Age=0" in set_cookie

    def test_logout_without_cookie_still_redirects(self, client: TestClient):
        resp = client.get("/admin/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers.get("location") == "/admin/login"


class TestStaticFiles:
    def test_style_css_served(self, client: TestClient):
        resp = client.get("/admin/static/style.css", follow_redirects=False)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/css")


class TestFullLoginFlow:
    def test_login_then_access_protected_pages(self, client: TestClient):
        resp = client.post(
            "/admin/login",
            data={"email": "admin@test.com", "password": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        token_cookie = resp.cookies.get("admin_token")
        assert token_cookie is not None

        for path in [
            "/admin/dashboard",
            "/admin/users",
            "/admin/masjids",
            "/admin/claims",
            "/admin/donations",
        ]:
            resp2 = client.get(
                path, cookies={"admin_token": token_cookie}, follow_redirects=False
            )
            assert resp2.status_code == 200, f"{path} returned {resp2.status_code}"


class TestBlockUser:
    def test_without_cookie_redirects_to_login(self, client: TestClient):
        resp = client.post("/admin/users/some-uuid/block", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"

    def test_with_valid_cookie_redirects_to_users(self, client: TestClient):
        token = _make_token()
        resp = client.post(
            "/admin/users/some-uuid/block",
            cookies={"admin_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers.get("location") == "/admin/users"


class TestUnblockUser:
    def test_without_cookie_redirects_to_login(self, client: TestClient):
        resp = client.post("/admin/users/some-uuid/unblock", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"

    def test_with_valid_cookie_redirects_to_users(self, client: TestClient):
        token = _make_token()
        resp = client.post(
            "/admin/users/some-uuid/unblock",
            cookies={"admin_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers.get("location") == "/admin/users"


class TestSearchUsers:
    def test_without_cookie_redirects_to_login(self, client: TestClient):
        resp = client.get("/admin/users/search?q=test", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/admin/login"

    def test_with_valid_cookie_returns_partial(self, client: TestClient):
        token = _make_token()
        resp = client.get(
            "/admin/users/search?q=test",
            cookies={"admin_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "No users found" in resp.text

    def test_empty_query_returns_no_results(self, client: TestClient):
        token = _make_token()
        resp = client.get(
            "/admin/users/search?q=",
            cookies={"admin_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "No users found" in resp.text
