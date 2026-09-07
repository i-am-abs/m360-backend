from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from app.core.enums.admin_status import AdminRegistrationStatus
from app.core.enums.committee_designation import CommitteeDesignation
from app.core.enums.role import UserRole
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.audit_log_repository import AuditLogRepository
from app.schemas.admin import AdminRegisterRequest
from app.services.admin_service import AdminService
from app.services.rbac_service import RbacService


class InMemoryAdminStore(AdminRepository):
    def __init__(self) -> None:
        self._docs: List[Dict[str, Any]] = []

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = {**data, "admin_id": f"admin-{len(self._docs) + 1}"}
        self._docs.append(doc)
        return doc

    def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        for doc in self._docs:
            if doc.get("admin_id") == admin_id:
                return doc
        return None

    def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        for doc in self._docs:
            if doc.get("phone") == phone:
                return doc
        return None

    def get_by_phone_and_place(
            self,
            phone: str,
            place_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        for doc in self._docs:
            if doc.get("phone") != phone:
                continue
            doc_place = doc.get("masjid_place_id")
            if place_id is None:
                if doc_place is None:
                    return doc
            elif doc_place == place_id:
                return doc
        return None

    def list_by_phone(
            self,
            phone: str,
            *,
            status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return [
            doc for doc in self._docs
            if doc.get("phone") == phone and (not status or doc.get("status") == status)
        ]

    def list_approved_for_place(self, place_id: str) -> List[Dict[str, Any]]:
        return [
            doc for doc in self._docs
            if doc.get("masjid_place_id") == place_id
            and doc.get("status") == AdminRegistrationStatus.APPROVED.value
        ]

    def list_for_place(
            self,
            place_id: str,
            *,
            status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return [
            doc for doc in self._docs
            if doc.get("masjid_place_id") == place_id and (not status or doc.get("status") == status)
        ]

    def list_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return [doc for doc in self._docs if not status or doc.get("status") == status]

    def update_status(
            self,
            admin_id: str,
            status: str,
            *,
            updated_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return self.update_fields(admin_id, {"status": status, "updated_by": updated_by})

    def update_fields(
            self,
            admin_id: str,
            fields: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        for doc in self._docs:
            if doc.get("admin_id") == admin_id:
                doc.update(fields)
                return doc
        return None

    def link_user(self, admin_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return self.update_fields(admin_id, {"user_id": user_id})

    def list_by_user_id(
            self,
            user_id: str,
            *,
            status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return [
            doc for doc in self._docs
            if doc.get("user_id") == user_id and (not status or doc.get("status") == status)
        ]


class NoOpAuditStore(AuditLogRepository):
    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    def write(self, entry: Dict[str, Any]) -> None:
        self.entries.append(entry)

    def list_by_resource(
            self,
            resource_type: str,
            resource_id: str,
            *,
            limit: int = 50,
    ) -> List[Dict[str, Any]]:
        return []


@pytest.fixture
def admin_service() -> AdminService:
    store = InMemoryAdminStore()
    rbac = RbacService(store)
    return AdminService(
        admin_store=store,
        audit_store=NoOpAuditStore(),
        rbac=rbac,
    )


class TestAdminServiceMultiMasjidRegistration:
    def test_same_phone_can_register_for_two_different_masjids(
            self,
            admin_service: AdminService,
    ) -> None:
        phone = "919850671234"
        request_a = AdminRegisterRequest(
            name="Member A",
            phone=phone,
            role=UserRole.ADMIN.value,
            masjidPlaceId="place-a",
        )
        request_b = AdminRegisterRequest(
            name="Member B",
            phone=phone,
            role=UserRole.ADMIN.value,
            masjidPlaceId="place-b",
        )

        response_a = admin_service.register(request_a)
        response_b = admin_service.register(request_b)

        assert response_a.masjid_place_id == "place-a"
        assert response_a.status == AdminRegistrationStatus.PENDING
        assert response_b.masjid_place_id == "place-b"
        assert response_b.status == AdminRegistrationStatus.PENDING

        assert admin_service.list_admins(
            {"user_id": "super", "role": UserRole.SUPER_ADMIN.value},
        )["counts"]["total"] == 2

    def test_registering_same_phone_same_place_is_idempotent(
            self,
            admin_service: AdminService,
    ) -> None:
        phone = "919850671234"
        request = AdminRegisterRequest(
            name="Member",
            phone=phone,
            role=UserRole.ADMIN.value,
            masjidPlaceId="place-a",
        )

        response1 = admin_service.register(request)
        response2 = admin_service.register(request)

        assert response1.id == response2.id
        assert admin_service.list_admins(
            {"user_id": "super", "role": UserRole.SUPER_ADMIN.value},
        )["counts"]["total"] == 1

    def test_selected_committee_role_is_preserved(
            self,
            admin_service: AdminService,
    ) -> None:
        request = AdminRegisterRequest(
            name="Imam",
            phone="919850671234",
            role=CommitteeDesignation.IMAM.value,
            masjidPlaceId="place-a",
        )

        response = admin_service.register(request)

        assert response.role == UserRole.ADMIN.value
        assert response.designation == CommitteeDesignation.IMAM.value
        assert response.designation_label == "Imam"
