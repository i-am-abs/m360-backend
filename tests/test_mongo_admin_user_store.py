from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.repositories.mongo_admin_user_store import MongoAdminUserStore


@pytest.fixture
def mock_collection() -> MagicMock:
    return MagicMock()


@pytest.fixture
def store(mock_collection: MagicMock) -> MongoAdminUserStore:
    return MongoAdminUserStore(mock_collection)


class TestMongoAdminUserStore:
    def test_create_admin(self, store: MongoAdminUserStore, mock_collection: MagicMock) -> None:
        mock_collection.insert_one.return_value = MagicMock(inserted_id="admin-1")
        result = store.create_admin(
            email="admin@test.com",
            password_hash="$2b$12$abc",
            name="Test Admin",
            role="super_admin",
        )
        assert result["email"] == "admin@test.com"
        assert result["password_hash"] == "$2b$12$abc"
        assert result["name"] == "Test Admin"
        assert result["role"] == "super_admin"
        assert result["is_active"] is True
        assert result["id"] == "admin-1"
        mock_collection.insert_one.assert_called_once()

    def test_create_admin_lowercases_email(self, store: MongoAdminUserStore, mock_collection: MagicMock) -> None:
        mock_collection.insert_one.return_value = MagicMock(inserted_id="admin-2")
        result = store.create_admin(
            email="Admin@Test.COM",
            password_hash="hash",
            name="Admin",
            role="admin",
        )
        assert result["email"] == "admin@test.com"

    def test_get_by_email_found(self, store: MongoAdminUserStore, mock_collection: MagicMock) -> None:
        expected = {"_id": "admin-1", "email": "admin@test.com", "name": "Test"}
        mock_collection.find_one.return_value = expected
        result = store.get_by_email("admin@test.com")
        assert result is not None
        assert result["email"] == "admin@test.com"
        mock_collection.find_one.assert_called_once_with({"email": "admin@test.com"})

    def test_get_by_email_not_found(self, store: MongoAdminUserStore, mock_collection: MagicMock) -> None:
        mock_collection.find_one.return_value = None
        result = store.get_by_email("missing@test.com")
        assert result is None

    def test_get_by_id_found(self, store: MongoAdminUserStore, mock_collection: MagicMock) -> None:
        expected = {"_id": "admin-1", "email": "admin@test.com"}
        mock_collection.find_one.return_value = expected
        result = store.get_by_id("admin-1")
        assert result is not None
        assert result["email"] == "admin@test.com"
        mock_collection.find_one.assert_called_once_with({"_id": "admin-1"})

    def test_get_by_id_not_found(self, store: MongoAdminUserStore, mock_collection: MagicMock) -> None:
        mock_collection.find_one.return_value = None
        result = store.get_by_id("missing")
        assert result is None

    def test_list_admins(self, store: MongoAdminUserStore, mock_collection: MagicMock) -> None:
        mock_collection.find.return_value = [
            {"_id": "1", "email": "a@t.com"},
            {"_id": "2", "email": "b@t.com"},
        ]
        result = store.list_admins()
        assert len(result) == 2
        assert result[0]["email"] == "a@t.com"
        mock_collection.find.assert_called_once_with({})

    def test_update_last_login(self, store: MongoAdminUserStore, mock_collection: MagicMock) -> None:
        store.update_last_login("admin-1")
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args[0]
        assert call_args[0] == {"_id": "admin-1"}
        assert "$set" in call_args[1]
        assert "last_login_at" in call_args[1]["$set"]
