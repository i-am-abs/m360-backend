from app.core.config import Settings
from app.web.share_context import build_share_context


def _settings() -> Settings:
    return Settings(
        share_web_base_url="https://muslim360.in",
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
    default = "https://muslim360.in/share-static/masjid-default.png"
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
    assert ctx["canonical_url"] == "https://muslim360.in/s/m9"


def test_location_uses_area_and_city():
    ctx = build_share_context(
        {"id": "m10", "text": "S", "created_at": "2026-10-13T10:00:00+00:00"},
        _masjid(), _settings(), area="Ghatkopar East", city="Mumbai",
    )
    assert ctx["masjid_location"] == "Ghatkopar East, Mumbai"


def test_mux_analytics_fields():
    msg = {
        "id": "m1", "text": "S", "created_at": "2026-10-13T10:00:00+00:00",
        "mux_playback_id": "pb123", "masjid_id": "place1",
    }
    ctx = build_share_context(msg, _masjid(), _settings())
    assert ctx["mux_playback_id"] == "pb123"
    assert ctx["mux_env_key"] == _settings().mux_env_key
    assert ctx["analytics_title"] == "Masjid Al Noor announcement"
    assert ctx["analytics_sub_property_id"] == "place1"


def test_area_and_city_from_address_components():
    from app.web.share import _area_and_city
    place = {"addressComponents": [
        {"longText": "Ghatkopar East",
         "types": ["sublocality_level_1", "sublocality"]},
        {"longText": "Mumbai", "types": ["locality"]},
    ]}
    assert _area_and_city(place) == ("Ghatkopar East", "Mumbai")


def test_og_image_uses_thumbnail_without_cropping():
    msg = {
        "id": "m11", "text": "S", "created_at": "2026-10-13T10:00:00+00:00",
        "thumbnail_url": "https://image.mux.com/pb/thumbnail.jpg",
    }
    ctx = build_share_context(msg, _masjid(), _settings())
    assert ctx["og_image_url"] == "https://image.mux.com/pb/thumbnail.jpg"
    assert "smartcrop" not in ctx["og_image_url"]
    assert "fit_mode" not in ctx["og_image_url"]


def test_follow_path_points_to_masjid():
    msg = {"id": "m12", "text": "S", "created_at": "2026-10-13T10:00:00+00:00",
           "masjid_id": "placeX"}
    ctx = build_share_context(msg, {**_masjid(), "place_id": "placeX"}, _settings())
    assert ctx["follow_path"] == "/m/placeX"
    assert ctx["masjid_place_id"] == "placeX"
    assert ctx["deep_link_path"] == "/s/m12"


def test_follow_path_empty_when_masjid_unresolved():
    msg = {"id": "m13", "text": "S", "created_at": "2026-10-13T10:00:00+00:00",
           "masjid_id": "Madarsa Islamia Arabia Rahimia"}
    ctx = build_share_context(msg, {}, _settings())
    assert ctx["follow_path"] == ""
    assert ctx["masjid_place_id"] == ""


def test_follow_path_falls_back_to_masjid_id_without_place_id():
    msg = {"id": "m14", "text": "S", "created_at": "2026-10-13T10:00:00+00:00"}
    ctx = build_share_context(msg, {**_masjid(), "id": "66f1a2b3c4d5e6f7a8b9c0d1"}, _settings())
    assert ctx["follow_path"] == "/m/66f1a2b3c4d5e6f7a8b9c0d1"
    assert ctx["masjid_place_id"] == ""


def test_follow_path_skips_non_url_safe_place_id():
    msg = {"id": "m15", "text": "S", "created_at": "2026-10-13T10:00:00+00:00"}
    ctx = build_share_context(
        msg,
        {**_masjid(), "place_id": "Madarsa Islamia Arabia Rahimia", "id": "6ad9092332a8a6788572f82f"},
        _settings(),
    )
    assert ctx["follow_path"] == "/m/6ad9092332a8a6788572f82f"
