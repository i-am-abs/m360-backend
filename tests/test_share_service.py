import pytest

from app.core.config import Settings
from app.exceptions.base import ApiException
from app.services.share_service import ShareService

MESSAGE = {
    "id": "m1",
    "masjid_id": "place1",
    "masjid_name": "Masjid Al Noor",
    "mux_playback_id": "pb1",
    "allow_sharing": True,
}


class _Repo:
    def __init__(self):
        self.docs = {}

    def create(self, data):
        self.docs[data["share_id"]] = dict(data)
        return dict(data)

    def get_by_share_id(self, share_id):
        return self.docs.get(share_id)


class _Feed:
    def __init__(self, message=None):
        self.message = message

    def get_message_raw(self, message_id):
        if self.message is None:
            raise ApiException("Broadcast not found", status_code=404)
        return self.message


def _service(message=None):
    return ShareService(
        share_repo=_Repo(),
        feed_service=_Feed(message if message is not None else dict(MESSAGE)),
        settings=Settings(share_web_base_url="https://muslim360.in"),
    )


def test_new_share_is_its_own_root():
    svc = _service()
    out = svc.create_share(
        message_id="m1", channel="web_native_share_sheet", platform="mobile_web"
    )
    assert out["root_share_id"] == out["share_id"]
    assert out["parent_share_id"] is None
    assert out["url"].startswith("https://muslim360.in/s/m1?share=")


def test_child_share_inherits_root_and_parent():
    svc = _service()
    root = svc.create_share(
        message_id="m1", channel="web_native_share_sheet", platform="mobile_web"
    )
    child = svc.create_share(
        message_id="m1",
        parent_share_id=root["share_id"],
        channel="android_native_share_sheet",
        platform="android_app",
    )
    assert child["root_share_id"] == root["share_id"]
    assert child["parent_share_id"] == root["share_id"]


def test_parent_from_another_message_is_rejected():
    svc = _service()
    other = svc.create_share(
        message_id="m2", channel="web_native_share_sheet", platform="mobile_web"
    )
    with pytest.raises(ApiException) as err:
        svc.create_share(
            message_id="m1",
            parent_share_id=other["share_id"],
            channel="web_native_share_sheet",
            platform="mobile_web",
        )
    assert err.value.status_code == 422


def test_sharing_disabled_is_rejected():
    svc = _service({**MESSAGE, "allow_sharing": False})
    with pytest.raises(ApiException) as err:
        svc.create_share(
            message_id="m1", channel="web_native_share_sheet", platform="mobile_web"
        )
    assert err.value.status_code == 409


def test_unknown_parent_share_id_is_rejected():
    svc = _service()
    with pytest.raises(ApiException) as err:
        svc.create_share(
            message_id="m1",
            parent_share_id="does-not-exist",
            channel="web_native_share_sheet",
            platform="mobile_web",
        )
    assert err.value.status_code == 404


def test_expired_announcement_is_rejected():
    svc = _service({**MESSAGE, "expires_at": "2000-01-01T00:00:00+00:00"})
    with pytest.raises(ApiException) as err:
        svc.create_share(
            message_id="m1", channel="web_native_share_sheet", platform="mobile_web"
        )
    assert err.value.status_code == 409


def test_get_share_returns_known_share():
    svc = _service()
    created = svc.create_share(
        message_id="m1", channel="web_native_share_sheet", platform="mobile_web"
    )
    assert svc.get_share(created["share_id"])["share_id"] == created["share_id"]


def test_get_share_returns_none_for_unknown_share():
    svc = _service()
    assert svc.get_share("does-not-exist") is None


def test_utm_params_are_appended_to_the_url():
    svc = _service()
    out = svc.create_share(
        message_id="m1",
        channel="web_native_share_sheet",
        platform="mobile_web",
        utm_source="whatsapp",
        utm_medium="social",
    )
    assert "utm_source=whatsapp" in out["url"]
    assert "utm_medium=social" in out["url"]


class _MasjidRepo:
    def __init__(self, masjid=None):
        self._masjid = masjid

    def get_by_id(self, masjid_id):
        return self._masjid


def _service_with_masjid(message, masjid):
    return ShareService(
        share_repo=_Repo(),
        feed_service=_Feed(message),
        settings=Settings(share_web_base_url="https://muslim360.in"),
        masjid_repo=_MasjidRepo(masjid),
    )


def test_masjid_name_is_resolved_from_the_masjid_repository():
    message = {
        "id": "m1",
        "masjid_id": "place1",
        "mux_playback_id": "pb1",
        "allow_sharing": True,
    }
    svc = _service_with_masjid(message, {"name": "Masjid Al Noor"})
    out = svc.create_share(
        message_id="m1", channel="web_native_share_sheet", platform="mobile_web"
    )
    assert out["masjid_name"] == "Masjid Al Noor"
