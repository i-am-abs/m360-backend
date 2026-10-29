from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_share_service
from app.api.v1.endpoints import shares


class _Svc:
    def __init__(self, result=None):
        self.result = result or {
            "share_id": "s1",
            "root_share_id": "s1",
            "parent_share_id": None,
            "url": "https://muslim360.in/s/m1?share=s1",
        }
        self.kwargs = None

    def create_share(self, **kwargs):
        self.kwargs = kwargs
        return self.result


def _client(svc):
    app = FastAPI()
    app.state.user_store = None
    app.include_router(shares.router)
    app.dependency_overrides[get_share_service] = lambda: svc
    return TestClient(app)


def test_create_share_returns_tracked_url():
    svc = _Svc()
    resp = _client(svc).post(
        "/shares",
        json={
            "message_id": "m1",
            "channel": "web_native_share_sheet",
            "platform": "mobile_web",
        },
    )
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["share_id"] == "s1"
    assert body["url"].endswith("?share=s1")
    assert svc.kwargs["channel"] == "web_native_share_sheet"


def test_create_share_validates_payload():
    resp = _client(_Svc()).post("/shares", json={"message_id": "m1"})
    assert resp.status_code == 422


def test_create_share_returns_503_when_service_unavailable():
    resp = _client(None).post(
        "/shares",
        json={
            "message_id": "m1",
            "channel": "web_native_share_sheet",
            "platform": "mobile_web",
        },
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Share service not available"
