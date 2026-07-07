from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.repositories.mongo_user_store import MongoUserStore
from app.repositories.redis_user_store import RedisUserStore
from app.repositories.local_cache_user_store import LocalCacheUserStore
from app.repositories.user_store import JsonFileUserStore


class TestUserRepositoryInterface:
    def test_has_block_user(self) -> None:
        from app.interfaces.user_repository import UserRepository
        assert hasattr(UserRepository, "block_user")
        assert getattr(getattr(UserRepository, "block_user"), "__isabstractmethod__", False)

    def test_has_unblock_user(self) -> None:
        from app.interfaces.user_repository import UserRepository
        assert hasattr(UserRepository, "unblock_user")
        assert getattr(getattr(UserRepository, "unblock_user"), "__isabstractmethod__", False)

    def test_has_list_users(self) -> None:
        from app.interfaces.user_repository import UserRepository
        assert hasattr(UserRepository, "list_users")
        assert getattr(getattr(UserRepository, "list_users"), "__isabstractmethod__", False)

    def test_has_search_users(self) -> None:
        from app.interfaces.user_repository import UserRepository
        assert hasattr(UserRepository, "search_users")
        assert getattr(getattr(UserRepository, "search_users"), "__isabstractmethod__", False)


class TestNoopStubsCanInstantiate:
    def test_redis_user_store(self) -> None:
        settings = MagicMock()
        settings.redis_key_prefix = "test"
        store = RedisUserStore(MagicMock(), settings)
        store.block_user("user-1")
        store.unblock_user("user-1")
        result = store.list_users(0, 10)
        assert result == {"users": [], "total": 0}
        result = store.search_users("test")
        assert result == []

    def test_json_file_user_store(self, tmp_path: pytest.TempPathFactory) -> None:
        path = tmp_path / "users.json"
        path.write_text('{"users_by_phone": {}, "favorites_by_user_id": {}, "sessions": {}}')
        store = JsonFileUserStore(str(path))
        store.block_user("user-1")
        store.unblock_user("user-1")
        result = store.list_users(0, 10)
        assert result == {"users": [], "total": 0}
        result = store.search_users("test")
        assert result == []

    def test_local_cache_user_store(self) -> None:
        store = LocalCacheUserStore()
        store.block_user("user-1")
        store.unblock_user("user-1")
        result = store.list_users(0, 10)
        assert result == {"users": [], "total": 0}
        result = store.search_users("test")
        assert result == []


@pytest.fixture
def mock_db():
    db = MagicMock()
    db["users"] = MagicMock()
    return db


@pytest.fixture
def mongo_store(mock_db):
    return MongoUserStore(mock_db)


class TestMongoUserStoreAdminMethods:
    def test_block_user(self, mongo_store: MongoUserStore, mock_db: MagicMock) -> None:
        mongo_store.block_user("user-1")
        mock_db["users"].update_one.assert_called_once()
        call_args = mock_db["users"].update_one.call_args[0]
        assert call_args[0] == {"user_id": "user-1"}
        assert call_args[1]["$set"]["blocked_at"] is not None

    def test_unblock_user(self, mongo_store: MongoUserStore, mock_db: MagicMock) -> None:
        mongo_store.unblock_user("user-1")
        mock_db["users"].update_one.assert_called_once_with(
            {"user_id": "user-1"},
            {"$set": {"blocked_at": None}},
        )

    def test_list_users(self, mongo_store: MongoUserStore, mock_db: MagicMock) -> None:
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.skip.return_value.limit.return_value = [
            {"user_id": "1", "phone_number": "+111", "created_at": "t1"},
            {"user_id": "2", "phone_number": "+222", "created_at": "t2"},
        ]
        mock_db["users"].find.return_value = mock_cursor
        mock_db["users"].count_documents.return_value = 5

        result = mongo_store.list_users(10, 20)
        mock_db["users"].find.assert_called_once_with({})
        mock_cursor.sort.assert_called_once_with("created_at", -1)
        mock_cursor.sort.return_value.skip.assert_called_once_with(10)
        mock_cursor.sort.return_value.skip.return_value.limit.assert_called_once_with(20)
        assert len(result["users"]) == 2
        assert result["total"] == 5
        assert result["users"][0]["user_id"] == "1"

    def test_search_users_by_phone(self, mongo_store: MongoUserStore, mock_db: MagicMock) -> None:
        mock_cursor = MagicMock()
        mock_cursor.limit.return_value = [
            {"user_id": "1", "phone_number": "+1111111111", "created_at": "t1"},
        ]
        mock_db["users"].find.return_value = mock_cursor

        result = mongo_store.search_users("+111")
        assert len(result) == 1
        assert result[0]["user_id"] == "1"
        mock_db["users"].find.assert_called_once()
        filter_arg = mock_db["users"].find.call_args[0][0]
        assert "$or" in filter_arg or "$text" in filter_arg or "phone_number" in filter_arg

    def test_as_user_dict_includes_blocked_at_and_global_role(self, mongo_store: MongoUserStore) -> None:
        doc = {
            "user_id": "u1",
            "phone_number": "+111",
            "created_at": "t1",
            "blocked_at": "2026-06-01T00:00:00+00:00",
            "global_role": "premium",
        }
        result = mongo_store._as_user_dict(doc)
        assert result["blocked_at"] == "2026-06-01T00:00:00+00:00"
        assert result["global_role"] == "premium"

    def test_as_user_dict_missing_optional_fields(self, mongo_store: MongoUserStore) -> None:
        doc = {
            "user_id": "u1",
            "phone_number": "+111",
            "created_at": "t1",
        }
        result = mongo_store._as_user_dict(doc)
        assert result["blocked_at"] is None
        assert result["global_role"] is None
