from datetime import datetime, timedelta, timezone

from app.repositories.mongo_broadcast_repository import MongoBroadcastFeedRepository


class _FakeCollection:
    def __init__(self):
        self.docs = []
        self.indexes = []

    def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))

    def insert_one(self, doc):
        self.docs.append(dict(doc))

        class _R:
            inserted_id = "fake-id"

        return _R()


class _FakeDb:
    def __init__(self):
        self.col = _FakeCollection()

    def __getitem__(self, name):
        return self.col


def _repo():
    return MongoBroadcastFeedRepository(_FakeDb())


def test_create_message_defaults_sharing_true_no_expiry():
    repo = _repo()
    msg = repo.create_message(
        masjid_id="m1", sender={"user_id": "u1"}, msg_type="video",
        text="hi", video_url="v", campaign_id=None,
    )
    assert msg["allow_sharing"] is True
    assert msg["expires_at"] is None


def test_create_message_persists_expiry_and_disabled_sharing():
    repo = _repo()
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    msg = repo.create_message(
        masjid_id="m1", sender={"user_id": "u1"}, msg_type="video",
        text="hi", video_url="v", campaign_id=None,
        allow_sharing=False, expires_at=expires,
    )
    assert msg["allow_sharing"] is False
    assert msg["expires_at"] == expires
