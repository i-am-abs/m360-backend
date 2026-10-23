from app.web.templating import env


def _render():
    return env.get_template("landing.html").render(
        play_store_url="https://play.google.com/x",
        app_store_url="https://apps.apple.com/x",
        marketing_site_url="https://muslim360.in",
    )


def test_landing_template_renders_core_sections():
    html = _render()
    assert "Everything your masjid, in one app." in html
    assert "https://play.google.com/x" in html
    assert "https://apps.apple.com/x" in html
    assert 'id="features"' in html
    assert 'id="screenshots"' in html
    assert 'id="faq"' in html
    assert "/share-static/logo.png" in html
    assert "/share-static/landing/screen-1.webp" in html
    assert "/share-static/landing/screen-2.webp" in html
