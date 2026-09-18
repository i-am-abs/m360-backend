import pytest

from app.interfaces.admin_user_repository import AdminUserRepository


class TestAdminUserRepositoryInterface:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            AdminUserRepository()  # type: ignore[abstract]

    def test_all_methods_abstract(self) -> None:
        missing = []
        for method in ["create_admin", "get_by_email", "get_by_id", "list_admins", "update_last_login"]:
            if not hasattr(AdminUserRepository, method):
                missing.append(method)
            elif not getattr(getattr(AdminUserRepository, method), "__isabstractmethod__", False):
                missing.append(f"{method} (not abstract)")
        assert not missing, f"Non-abstract methods: {missing}"
