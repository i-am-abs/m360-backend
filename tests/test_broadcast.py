from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.core.enums.role import UserRole
from app.schemas.broadcast import BroadcastCreateRequest
from app.services.broadcast_service import BroadcastService
from app.services.notification_service import NotificationService
from app.services.rbac_service import RbacService


class FakeBroadcastStore:
    def __init__(self) -> None:
        self._items: List[Dict[str, Any]] = []
        self._seq = 0

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._seq += 1
        doc = {
            "broadcast_id": f"b{self._seq}",
            "masjid_id": data["masjid_id"],
            "caption": data["caption"],
            "video_uri": data.get("video_uri"),
            "thumbnail_uri": data.get("thumbnail_uri"),
            "message_type": data.get("message_type", "text"),
            "created_by": data.get("created_by"),
            "seq": self._seq,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        self._items.append(doc)
        return doc

    def list_by_masjid(self, masjid_id, *, limit, before_seq=None) -> Tuple[List[Dict[str, Any]], bool]:
        rows = sorted(
            [d for d in self._items if d["masjid_id"] == masjid_id],
            key=lambda d: d["seq"],
            reverse=True,
        )
        if before_seq is not None:
            rows = [d for d in rows if d["seq"] < before_seq]
        has_more = len(rows) > limit
        return rows[:limit], has_more

    def get_by_id(self, broadcast_id: str) -> Optional[Dict[str, Any]]:
        return next((d for d in self._items if d["broadcast_id"] == broadcast_id), None)


class FakeFollowStore:
    def __init__(self) -> None:
        self._follows: set[tuple[str, str]] = set()

    def follow(self, user_id, masjid_id):
        self._follows.add((user_id, masjid_id))

    def unfollow(self, user_id, masjid_id):
        self._follows.discard((user_id, masjid_id))

    def is_following(self, user_id, masjid_id):
        return (user_id, masjid_id) in self._follows

    def list_follower_user_ids(self, masjid_id):
        return [u for (u, m) in self._follows if m == masjid_id]


class FakeTokenStore:
    def __init__(self) -> None:
        self._tokens: Dict[str, str] = {}

    def register(self, user_id, token, platform=None):
        self._tokens[token] = user_id

    def list_tokens_for_users(self, user_ids):
        return [t for t, u in self._tokens.items() if u in set(user_ids)]

    def remove(self, token):
        self._tokens.pop(token, None)


class RecordingSender:
    def __init__(self) -> None:
        self.calls: List[Tuple[List[str], str, str]] = []

    def send_to_tokens(self, tokens, title, body, data=None):
        self.calls.append((tokens, title, body))
        return len(tokens), 0, []


class FakeAdminStore:
    def list_by_user_id(self, user_id: str):
        if user_id == "admin-user":
            return [{"role": "admin", "masjid_place_id": "masjid-1", "status": "approved"}]
        return []


class NoAudit:
    def write(self, entry):
        pass

    def list_by_resource(self, *a, **k):
        return []


def _build_service():
    follow = FakeFollowStore()
    tokens = FakeTokenStore()
    sender = RecordingSender()
    notifications = NotificationService(tokens, follow, sender)
    rbac = RbacService(FakeAdminStore())
    broadcast = BroadcastService(FakeBroadcastStore(), notifications, NoAudit(), rbac, default_page_size=20)
    return broadcast, notifications, sender


def test_admin_can_create_broadcast_and_notify_followers():
    broadcast, notifications, sender = _build_service()
    notifications.follow_masjid("user-1", "masjid-1")
    notifications.register_token("user-1", "tok-1", "android")

    admin = {"user_id": "admin-user", "role": UserRole.ADMIN.value}
    body = BroadcastCreateRequest(caption="Jummah at 1:30 PM", messageType="announcement")
    result = broadcast.create_broadcast("masjid-1", body, admin)

    assert result.recipients == 1
    assert result.sent == 1
    assert len(sender.calls) == 1


def test_non_admin_cannot_create_broadcast():
    broadcast, _, _ = _build_service()
    user = {"user_id": "random", "role": UserRole.USER.value}
    body = BroadcastCreateRequest(caption="hello")
    try:
        broadcast.create_broadcast("masjid-1", body, user)
        assert False, "expected forbidden"
    except Exception as exc:
        assert "permission" in str(exc).lower() or "admin" in str(exc).lower()


def test_list_broadcasts_is_reverse_sorted_and_paginates():
    broadcast, _, _ = _build_service()
    admin = {"user_id": "admin-user", "role": UserRole.ADMIN.value}
    for i in range(3):
        broadcast.create_broadcast("masjid-1", BroadcastCreateRequest(caption=f"msg {i}"), admin)

    page = broadcast.list_broadcasts("masjid-1", limit=2)
    assert len(page.items) == 2
    assert page.items[0].seq == 3  # newest first
    assert page.has_more is True
    assert page.next_cursor == 2

    older = broadcast.list_broadcasts("masjid-1", limit=2, before_id=page.next_cursor)
    assert older.items[0].seq == 1
    assert older.has_more is False
