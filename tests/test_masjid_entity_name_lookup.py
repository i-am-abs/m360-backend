import pytest

from app.exceptions.base import ApiException
from app.services.masjid_entity_service import MasjidEntityService

NAME = "Madarsa Islamia Arabia Rahimia"


class _Repo:
    def __init__(self, by_name=None, by_id=None):
        self._by_name = by_name
        self._by_id = by_id

    def get_by_id(self, _):
        return self._by_id

    def get_by_place_id(self, _):
        return None

    def get_by_name(self, name):
        return self._by_name if name == NAME else None


def test_get_masjid_resolves_legacy_name():
    repo = _Repo({"id": "x", "place_id": "ChIJabc", "name": NAME})
    service = MasjidEntityService(repo, google_places=None)
    out = service.get_masjid(NAME)
    assert out["masjid"]["place_id"] == "ChIJabc"


def test_get_masjid_raises_for_unknown_name():
    service = MasjidEntityService(_Repo(), google_places=None)
    with pytest.raises(ApiException):
        service.get_masjid("Unknown Masjid")


def test_get_masjid_resolves_legacy_admin_id():
    repo = _Repo(by_id={"id": "admin_x", "place_id": "admin_6ad9092332a8a6788572f82f"})
    service = MasjidEntityService(repo, google_places=None)
    out = service.get_masjid("admin_6ad9092332a8a6788572f82f")
    assert out["masjid"]["place_id"] == "admin_6ad9092332a8a6788572f82f"
