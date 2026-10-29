from app.web.templating import env


def test_privacy_page_renders_policy():
    html = env.get_template("privacy.html").render()
    assert "Privacy Policy" in html
    assert "1. Information We Collect" in html
    assert "sahil.createx@gmail.com" in html


def test_privacy_page_mentions_mixpanel_analytics():
    from app.web.templating import env

    html = env.get_template("privacy.html").render()
    assert "Mixpanel" in html


def test_landing_footer_links_privacy():
    html = env.get_template("landing.html").render(
        play_store_url="https://play.google.com/x",
        app_store_url="https://apps.apple.com/x",
        marketing_site_url="https://muslim360.in",
        stats=None,
    )
    assert 'href="/privacy-policy"' in html
