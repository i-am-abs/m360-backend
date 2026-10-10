from datetime import datetime, timedelta, timezone

from app.repositories.mongo_broadcast_repository import MongoBroadcastFeedRepository


class _FakeQuery:
    def __init__(self, collection, docs):
        self._collection = collection
        self._docs = docs

    def sort(self, key, direction):
        self._collection.last_sort = (key, direction)
        return self

    def limit(self, count):
        self._collection.last_limit = count
        return self

    def __iter__(self):
        return iter(self._docs)


def _matches(doc, query):
    if "$and" in query:
        return all(_matches(doc, clause) for clause in query["$and"])
    if "$or" in query:
        return any(_matches(doc, clause) for clause in query["$or"])
    for field, condition in query.items():
        value = doc.get(field)
        if isinstance(condition, dict):
            if "$exists" in condition and (field in doc) != condition["$exists"]:
                return False
            if "$gt" in condition and not (value is not None and value > condition["$gt"]):
                return False
            if "$lt" in condition and not (value is not None and value < condition["$lt"]):
                return False
        elif value != condition:
            return False
    return True


class _FakeCollection:
    def __init__(self):
        self.docs = []
        self.indexes = []
        self.last_query = None
        self.last_sort = None
        self.last_limit = None

    def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))

    def insert_one(self, doc):
        self.docs.append(dict(doc))

        class _R:
            inserted_id = "fake-id"

        return _R()

    def find(self, query):
        self.last_query = query
        matched = [dict(doc) for doc in self.docs if _matches(doc, query)]
        return _FakeQuery(self, matched)


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


def test_get_messages_excludes_expired_keeps_future_and_legacy():
    repo = _repo()
    col = repo._messages
    now = datetime.now(timezone.utc)
    past = (now - timedelta(days=1)).isoformat()
    future = (now + timedelta(days=1)).isoformat()

    def doc(_id, **extra):
        base = {
            "_id": _id,
            "masjid_id": "m1",
            "created_at": "2026-10-10T12:00:00+00:00",
            "updated_at": "2026-10-10T12:00:00+00:00",
            "reactions": {},
        }
        base.update(extra)
        return base

    col.docs = [
        doc("expired", expires_at=past),
        doc("future", expires_at=future),
        doc("legacy-none", expires_at=None),
        doc("legacy-absent"),
        doc("other-masjid", masjid_id="m2", expires_at=future),
    ]

    result = repo.get_messages(masjid_id="m1", cursor=None, since=None, limit=10)
    ids = {m["id"] for m in result["messages"]}
    assert ids == {"future", "legacy-none", "legacy-absent"}

    query = col.last_query
    assert {"masjid_id": "m1"} in query["$and"]
    expiry_or = next(clause["$or"] for clause in query["$and"] if "$or" in clause)
    assert {"expires_at": None} in expiry_or
    assert any(
        isinstance(clause.get("expires_at"), dict) and "$gt" in clause["expires_at"]
        for clause in expiry_or
    )
    assert not any(
        isinstance(clause.get("expires_at"), dict) and "$exists" in clause["expires_at"]
        for clause in expiry_or
    )
    assert col.last_sort == ("created_at", -1)
    assert col.last_limit == 10
