from app.web.templating import env


def _render(stats=None):
    return env.get_template("landing.html").render(
        play_store_url="https://play.google.com/x",
        app_store_url="https://apps.apple.com/x",
        marketing_site_url="https://muslim360.in",
        stats=stats,
    )


def test_landing_template_renders_core_sections():
    html = _render(stats={"masjids": 111, "cities": 27, "announcements": 44})
    assert "Everything your masjid, in one app." in html
    assert "https://play.google.com/x" in html
    assert "https://apps.apple.com/x" in html
    assert 'id="features"' in html
    assert 'id="screenshots"' in html
    assert 'id="how"' in html
    assert 'id="faq"' in html
    assert "How it works" in html
    assert "Stay close to your masjid" in html
    assert "/share-static/logo.png" in html
    assert "/share-static/landing/screen-1.webp" in html
    assert "/share-static/landing/screen-2.webp" in html


def test_landing_template_shows_real_stats():
    html = _render(stats={"masjids": 111, "cities": 27, "announcements": 44})
    assert "<b>111</b>" in html
    assert "<b>27</b>" in html
    assert "<b>44</b>" in html


def test_landing_template_hides_stats_when_unavailable():
    html = _render(stats=None)
    assert 'class="stats"' not in html
