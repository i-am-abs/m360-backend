from app.web.templating import env


def _render():
    return env.get_template("share.html").render(
        message_id="m1",
        masjid_name="Masjid Al Noor",
        masjid_location="Thane, Maharashtra",
        masjid_verified=True,
        masjid_avatar_url="https://img/m.jpg",
        sender_name="Najim Ahmed",
        sender_role="Imam",
        sender_avatar_url="https://img/u.jpg",
        is_video=True,
        video_hls_url="https://stream/x.m3u8",
        poster_url="https://img/p.jpg",
        og_image_url="https://img/og.jpg",
        og_description="Salaam",
        page_title="Masjid Al Noor — announcement | Muslim 360",
        relative_time="2 hrs ago",
        canonical_url="https://m360.vyapari.link/s/m1",
        deep_link_path="/s/m1",
        share_host="m360.vyapari.link",
        play_store_url="https://play.google.com/x",
        app_store_url="https://apps.apple.com/x",
        android_package="com.starkinnovations.m360",
        marketing_site_url="https://muslim360.app",
    )


def test_share_template_renders_new_layout():
    html = _render()
    assert "Masjid Al Noor" in html
    assert "Najim Ahmed" in html
    assert "Imam" in html
    assert "Follow Masjid" in html
    assert 'id="waBtn"' in html
    assert 'id="followBtn"' in html
    assert "intent://" in html
    assert "wa.me" in html
