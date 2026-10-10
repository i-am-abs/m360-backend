from datetime import datetime, timedelta, timezone

from app.utils.broadcast import (
    compute_expires_at,
    is_expired,
    resolve_share_state,
)

NOW = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)


def test_compute_expires_at_none_when_no_days():
    assert compute_expires_at(None, now=NOW) is None


def test_compute_expires_at_adds_30_days():
    assert compute_expires_at(30, now=NOW) == (NOW + timedelta(days=30)).isoformat()


def test_is_expired_false_for_none():
    assert is_expired(None, now=NOW) is False


def test_is_expired_false_for_future():
    future = (NOW + timedelta(days=1)).isoformat()
    assert is_expired(future, now=NOW) is False


def test_is_expired_true_for_past():
    past = (NOW - timedelta(days=1)).isoformat()
    assert is_expired(past, now=NOW) is True


def test_resolve_available_default():
    assert resolve_share_state({}, now=NOW) == "available"


def test_resolve_unavailable_when_sharing_disabled():
    assert resolve_share_state({"allow_sharing": False}, now=NOW) == "unavailable"


def test_resolve_unavailable_beats_expired():
    msg = {"allow_sharing": False, "expires_at": (NOW - timedelta(days=1)).isoformat()}
    assert resolve_share_state(msg, now=NOW) == "unavailable"


def test_resolve_expired_when_past():
    msg = {"expires_at": (NOW - timedelta(days=1)).isoformat()}
    assert resolve_share_state(msg, now=NOW) == "expired"


def test_templates_render_with_context():
    from app.web.templating import env

    for name in ("share_unavailable.html", "share_expired.html"):
        html = env.get_template(name).render(
            marketing_site_url="https://m360.app",
            play_store_url="https://play.google.com/x",
            app_store_url="https://apps.apple.com/x",
        )
        assert "Get it on Google Play" in html
        assert "Get it on the App Store" in html
