import pytest

from app.core.enums.admin import AdminRole


class TestAdminRole:
    def test_has_super_admin(self) -> None:
        assert hasattr(AdminRole, "SUPER_ADMIN")
        assert AdminRole.SUPER_ADMIN.value == "super_admin"

    def test_has_admin(self) -> None:
        assert hasattr(AdminRole, "ADMIN")
        assert AdminRole.ADMIN.value == "admin"

    def test_choices(self) -> None:
        choices = AdminRole.choices()
        assert ("super_admin", "Super Admin") in choices
        assert ("admin", "Admin") in choices
        assert len(choices) == 2
