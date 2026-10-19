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


def test_whitespace_sender_avatar_falls_back_to_masjid_photo():
    msg = {
        "id": "m3",
        "text": "Salaam",
        "created_at": "2026-10-13T10:00:00+00:00",
        "sender": {"name": "Najim Ahmed", "avatar_url": "   "},
    }
    ctx = build_share_context(msg, _masjid(), _settings())
    assert ctx["sender_avatar_url"] == "https://img/masjid.jpg"


def test_masjid_without_photo_uses_default_masjid_image():
    masjid = _masjid()
    masjid.pop("photo_url")
    msg = {"id": "m4", "text": "Salaam", "created_at": "2026-10-13T10:00:00+00:00"}
    ctx = build_share_context(msg, masjid, _settings())
    default = "https://m360.vyapari.link/share-static/masjid-default.png"
    assert ctx["sender_avatar_url"] == default
    assert ctx["masjid_avatar_url"] == default


def test_sender_profile_overrides_phone_name_and_role():
    msg = {
        "id": "m5",
        "text": "Salaam",
        "created_at": "2026-10-13T10:00:00+00:00",
        "sender": {"user_id": "u1", "name": "919769476367", "role": "admin"},
    }
    ctx = build_share_context(
        msg, _masjid(), _settings(),
        sender_profile={"name": "rajesh", "role": "Imam",
                        "avatar_url": "https://img/dp.jpg"},
    )
    assert ctx["sender_name"] == "rajesh"
    assert ctx["sender_role"] == "Imam"
    assert ctx["sender_avatar_url"] == "https://img/dp.jpg"


def test_phone_like_sender_name_is_not_displayed():
    msg = {
        "id": "m6",
        "text": "Salaam",
        "created_at": "2026-10-13T10:00:00+00:00",
        "sender": {"name": "919769476367", "role": "admin"},
    }
    ctx = build_share_context(msg, _masjid(), _settings())
    assert ctx["sender_name"] == "Admin"
    assert ctx["sender_role"] == "Admin"


def test_masjid_image_url_override_is_used():
    ctx = build_share_context(
        {"id": "m7", "text": "Salaam", "created_at": "2026-10-13T10:00:00+00:00"},
        _masjid(), _settings(),
        masjid_image_url="https://fresh/photo.jpg",
    )
    assert ctx["masjid_avatar_url"] == "https://fresh/photo.jpg"


def test_places_photo_is_requested_at_avatar_size():
    url = (
        "https://places.googleapis.com/v1/places/x/photos/y/media"
        "?maxHeightPx=4096&key=K"
    )
    ctx = build_share_context(
        {"id": "m8", "text": "S", "created_at": "2026-10-13T10:00:00+00:00"},
        _masjid(), _settings(), masjid_image_url=url,
    )
    assert "maxHeightPx=96" in ctx["masjid_avatar_url"]
    assert "maxHeightPx=4096" not in ctx["masjid_avatar_url"]


def test_share_url_uses_share_cta_base_url():
    ctx = build_share_context(
        {"id": "m9", "text": "S", "created_at": "2026-10-13T10:00:00+00:00"},
        _masjid(), _settings(),
    )
    assert ctx["share_url"] == "https://muslim360.in/s/m9"
    assert ctx["canonical_url"] == "https://m360.vyapari.link/s/m9"
