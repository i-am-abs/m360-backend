from app.web.templating import env


def _render(**overrides):
    ctx = dict(
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
    ctx.update(overrides)
    return env.get_template("share.html").render(**ctx)


def test_share_template_renders_new_layout():
    html = _render()
    assert "Masjid Al Noor" in html
    assert "Najim Ahmed" in html
    assert "Imam" in html
    assert "Follow Masjid" in html
    assert 'class="applogo"' in html
    assert "/share-static/logo.png" in html
    assert 'id="followBtn"' in html
    assert 'id="shareBtn"' in html
    assert "intent://" in html


def test_text_only_post_shows_announcement_and_no_media():
    html = _render(is_video=False, video_hls_url=None, poster_url=None)
    assert '<p class="text">Salaam</p>' in html
    assert '<main class="media"' not in html


def test_none_description_does_not_leak_into_page():
    html = _render(og_description=None)
    assert "None" not in html


def test_video_post_renders_media_and_play_control():
    html = _render()
    assert '<main class="media"' in html
    assert 'id="play"' in html


def _media_block(html: str) -> str:
    start = html.index('<main class="media"')
    end = html.index("</main>", start) + len("</main>")
    return html[start:end]


def test_video_without_poster_uses_dark_placeholder_not_og_card():
    html = _render(
        poster_url=None,
        og_image_url="https://m360.vyapari.link/share-static/og-default.png",
    )
    media = _media_block(html)
    assert 'class="poster placeholder"' in media
    assert "og-default.png" not in media
    assert '<img class="poster"' not in media


def test_non_video_with_poster_renders_image_and_caption_below():
    html = _render(
        is_video=False,
        video_hls_url=None,
        poster_url="https://img/p.jpg",
    )
    media = _media_block(html)
    assert '<img class="poster" src="https://img/p.jpg"' in media
    assert '<p class="text">Salaam</p>' in html
    assert html.index('<main class="media"') < html.index('<div class="textwrap')
    assert '<div class="textwrap">' in html
    assert ".textwrap{flex:0 1 auto" in html
    assert ".textwrap.full{flex:1" in html


def test_text_only_post_text_fills_available_space():
    html = _render(is_video=False, video_hls_url=None, poster_url=None)
    assert '<div class="textwrap full">' in html
