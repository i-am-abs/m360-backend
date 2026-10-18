from app.core.config import Settings
from app.web.share_context import build_share_context


def _settings() -> Settings:
    return Settings(
        share_web_base_url="https://m360.vyapari.link",
        android_package_name="com.starkinnovations.m360",
    )


def _masjid() -> dict:
    return {
        "name": "Masjid Al Noor",
        "city": "Thane",
        "state": "Maharashtra",
        "photo_url": "https://img/masjid.jpg",
        "management": {"is_claimed": True},
    }


def test_sender_fields_from_message():
    msg = {
        "id": "m1",
        "text": "Salaam",
        "created_at": "2026-10-13T10:00:00+00:00",
        "sender": {"user_id": "u1", "name": "Najim Ahmed", "role": "Imam",
                   "avatar_url": "https://img/u1.jpg"},
    }
    ctx = build_share_context(msg, _masjid(), _settings())
    assert ctx["sender_name"] == "Najim Ahmed"
    assert ctx["sender_role"] == "Imam"
    assert ctx["sender_avatar_url"] == "https://img/u1.jpg"


def test_sender_fallbacks_when_missing():
    msg = {"id": "m2", "text": "Salaam", "created_at": "2026-10-13T10:00:00+00:00"}
    ctx = build_share_context(msg, _masjid(), _settings())
    assert ctx["sender_name"] == "Admin"
    assert ctx["sender_role"] == "Admin"
    assert ctx["sender_avatar_url"] == "https://img/masjid.jpg"
