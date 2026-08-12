from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.enums.admin_status import AdminRegistrationStatus
from app.core.enums.role import UserRole
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_follow_repository import MasjidFollowRepository
from app.interfaces.user_repository import UserRepository
from app.schemas.feature_flag import (
    MasjidTabBanners,
    MasjidTabLists,
    MasjidTabNearbyMode,
    MasjidTabResponse,
)
from app.services.feature_flag_service import FeatureFlagService
from app.services.rbac_service import RbacService
from app.utils.admin_link import ensure_admin_user_link
from app.utils.structured_log import log_event


class MasjidTabService:
    """Resolves Masjid-tab UX from region enablement + user role."""

    def __init__(
            self,
            feature_flags: FeatureFlagService,
            follow_store: MasjidFollowRepository,
            user_store: UserRepository,
            admin_store: AdminRepository,
            rbac: RbacService,
    ) -> None:
        self._feature_flags = feature_flags
        self._follow_store = follow_store
        self._user_store = user_store
        self._admin_store = admin_store
        self._rbac = rbac

    def resolve_tab(
            self,
            *,
            current_user: Optional[Dict[str, Any]],
            latitude: Optional[float] = None,
            longitude: Optional[float] = None,
            location_key: Optional[str] = None,
            country: Optional[str] = None,
            state: Optional[str] = None,
            city: Optional[str] = None,
    ) -> MasjidTabResponse:
        region_enabled = self._feature_flags.is_masjid_region_enabled(
            latitude=latitude,
            longitude=longitude,
            location_key=location_key,
            country=country,
            state=state,
            city=city,
        )

        followed_ids = self._followed_ids(current_user)
        admin_ids = self._admin_place_ids(current_user)
        user_type = self._user_type(
            current_user=current_user,
            followed_count=len(followed_ids),
            admin_count=len(admin_ids),
        )

        payload = self._build_payload(
            region_enabled=region_enabled,
            user_type=user_type,
            followed_count=len(followed_ids),
            admin_count=len(admin_ids),
        )
        log_event(
            "masjid_tab",
            "resolved",
            user_type=user_type,
            region_enabled=region_enabled,
            primary_screen=payload.primary_screen,
            followed_count=len(followed_ids),
            admin_count=len(admin_ids),
        )
        return payload

    def _followed_ids(self, current_user: Optional[Dict[str, Any]]) -> List[str]:
        if not current_user:
            return []
        user_id = str(current_user.get("user_id") or "")
        phone = str(current_user.get("phone_number") or "")
        ids: List[str] = []
        if user_id:
            ids.extend(self._follow_store.list_followed_masjid_ids(user_id))
        if phone:
            ids.extend(self._user_store.list_favorites(phone))
        # Preserve order, drop empties/dupes.
        seen = set()
        ordered: List[str] = []
        for pid in ids:
            if not pid or pid in seen:
                continue
            seen.add(pid)
            ordered.append(str(pid))
        return ordered

    def _admin_place_ids(self, current_user: Optional[Dict[str, Any]]) -> List[str]:
        if not current_user:
            return []
        user_id = str(current_user.get("user_id") or "")
        phone = current_user.get("phone_number")
        if not user_id:
            return []
        docs = ensure_admin_user_link(
            self._admin_store,
            user_id=user_id,
            phone=str(phone) if phone else None,
        )
        place_ids: List[str] = []
        for doc in docs:
            if doc.get("status") != AdminRegistrationStatus.APPROVED.value:
                continue
            pid = doc.get("masjid_place_id")
            if pid:
                place_ids.append(str(pid))
        return place_ids

    def _user_type(
            self,
            *,
            current_user: Optional[Dict[str, Any]],
            followed_count: int,
            admin_count: int,
    ) -> str:
        if not current_user:
            return "guest"
        if admin_count > 0:
            return "admin"
        role = self._rbac.resolve_user_role(current_user)
        if role in UserRole.admin_roles() and admin_count > 0:
            return "admin"
        if followed_count > 0:
            return "follower"
        return "user"

    @staticmethod
    def _build_payload(
            *,
            region_enabled: bool,
            user_type: str,
            followed_count: int,
            admin_count: int,
    ) -> MasjidTabResponse:
        # Guest / logged-in non-follower
        if user_type in {"guest", "user"}:
            if region_enabled:
                return MasjidTabResponse(
                    region_enabled=True,
                    user_type=user_type,
                    primary_screen="nearby",
                    banners=MasjidTabBanners(
                        enable_location=True,
                        tap_to_see_nearby=False,
                    ),
                    lists=MasjidTabLists(nearby=True, followed=False, admin=False),
                    nearby_screen=MasjidTabNearbyMode(
                        available=True,
                        banners=MasjidTabBanners(
                            enable_location=True,
                            tap_to_see_nearby=False,
                        ),
                    ),
                    followed_count=followed_count,
                    admin_count=admin_count,
                )
            return MasjidTabResponse(
                region_enabled=False,
                user_type=user_type,
                primary_screen="coming_soon",
                banners=MasjidTabBanners(
                    enable_location=False,
                    tap_to_see_nearby=False,
                ),
                lists=MasjidTabLists(nearby=False, followed=False, admin=False),
                nearby_screen=MasjidTabNearbyMode(available=False),
                followed_count=followed_count,
                admin_count=admin_count,
            )

        # Follower
        if user_type == "follower":
            if region_enabled:
                return MasjidTabResponse(
                    region_enabled=True,
                    user_type=user_type,
                    primary_screen="followed_list",
                    banners=MasjidTabBanners(
                        enable_location=False,
                        tap_to_see_nearby=True,
                    ),
                    lists=MasjidTabLists(nearby=False, followed=True, admin=False),
                    nearby_screen=MasjidTabNearbyMode(
                        available=True,
                        banners=MasjidTabBanners(
                            enable_location=True,
                            tap_to_see_nearby=False,
                        ),
                    ),
                    followed_count=followed_count,
                    admin_count=admin_count,
                )
            return MasjidTabResponse(
                region_enabled=False,
                user_type=user_type,
                primary_screen="followed_list",
                banners=MasjidTabBanners(
                    enable_location=False,
                    tap_to_see_nearby=False,
                ),
                lists=MasjidTabLists(nearby=False, followed=True, admin=False),
                nearby_screen=MasjidTabNearbyMode(available=False),
                followed_count=followed_count,
                admin_count=admin_count,
            )

        # Admin
        if region_enabled:
            return MasjidTabResponse(
                region_enabled=True,
                user_type="admin",
                primary_screen="admin_followed_list",
                banners=MasjidTabBanners(
                    enable_location=False,
                    tap_to_see_nearby=True,
                ),
                lists=MasjidTabLists(nearby=False, followed=True, admin=True),
                nearby_screen=MasjidTabNearbyMode(
                    available=True,
                    banners=MasjidTabBanners(
                        enable_location=True,
                        tap_to_see_nearby=False,
                    ),
                ),
                followed_count=followed_count,
                admin_count=admin_count,
            )
        return MasjidTabResponse(
            region_enabled=False,
            user_type="admin",
            primary_screen="admin_followed_list",
            banners=MasjidTabBanners(
                enable_location=False,
                tap_to_see_nearby=False,
            ),
            lists=MasjidTabLists(nearby=False, followed=True, admin=True),
            nearby_screen=MasjidTabNearbyMode(available=False),
            followed_count=followed_count,
            admin_count=admin_count,
        )
