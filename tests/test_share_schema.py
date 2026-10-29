import pytest
from pydantic import ValidationError

from app.schemas.share import ShareCreateRequest


def test_share_request_accepts_valid_payload():
    req = ShareCreateRequest(
        message_id="m1",
        channel="web_native_share_sheet",
        platform="mobile_web",
    )
    assert req.parent_share_id is None
    assert req.utm_source is None


def test_share_request_rejects_unknown_channel():
    with pytest.raises(ValidationError):
        ShareCreateRequest(
            message_id="m1",
            channel="whatsapp",
            platform="mobile_web",
        )
