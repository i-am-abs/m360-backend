from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)

from app.api.deps import (
    get_broadcast_feed_service,
    get_masjid_entity_service,
    get_masjid_search_service,
    get_share_service,
)
from app.core.config import Settings, get_settings
from app.core.enums.committee_designation import CommitteeDesignation
from app.exceptions.base import ApiException
from app.utils.broadcast import resolve_share_state
from app.web.share_context import (
    _minify_places_photo,
    build_masjid_share_context,
    build_share_context,
)
from app.web.templating import env

router = APIRouter(tags=["share"])


_GENERIC_AREA_TOKENS = {
    "city", "town", "district", "tehsil", "taluka", "municipality",
    "urban", "rural", "area", "locality", "village", "mandal", "division",
}


def _is_generic_area(value: str) -> bool:
    return value.strip().lower() in _GENERIC_AREA_TOKENS


def _first_specific(by_type: dict, keys: tuple) -> str:
    for key in keys:
        value = (by_type.get(key) or "").strip()
        if value and not _is_generic_area(value):
            return value
    return ""


def _area_and_city(place: dict) -> tuple:
    """Pull a meaningful area (sublocality) and city (locality) from addressComponents."""
    by_type = {}
    for comp in place.get("addressComponents") or []:
        if not isinstance(comp, dict):
            continue
        text = comp.get("longText") or comp.get("shortText") or ""
        for t in comp.get("types") or []:
            if t and t not in by_type and text:
                by_type[t] = str(text).strip()
    area = _first_specific(by_type, (
        "sublocality_level_1",
        "sublocality",
        "neighborhood",
        "sublocality_level_2",
        "sublocality_level_3",
    ))
    city = _first_specific(by_type, (
        "locality",
        "postal_town",
        "administrative_area_level_2",
    ))
    return area, city


def _resolve_sender_profile(request: Request, message: dict, place_id: str) -> dict:
    """Resolve the announcer's name/designation/DP from the admin store."""
    store = getattr(request.app.state, "admin_store", None)
    if store is None:
        return {}
    sender = message.get("sender") or {}
    user_id = str(sender.get("user_id") or "")
    phone = str(sender.get("name") or "")
    docs = []
    try:
        if user_id:
            docs = list(store.list_by_user_id(user_id) or [])
        if not docs and phone:
            docs = list(store.list_by_phone(phone) or [])
    except Exception:
        return {}
    if not docs:
        return {}
    same_place = [
        d for d in docs
        if str(d.get("masjid_place_id") or "") == str(place_id)
    ]
    candidates = same_place or docs
    candidates.sort(key=lambda d: d.get("status") == "approved", reverse=True)
    doc = candidates[0]
    designation = doc.get("designation") or doc.get("role") or ""
    role = ""
    if designation:
        key = CommitteeDesignation.normalize(designation)
        role = CommitteeDesignation.labels().get(
            key, key.replace("_", " ").title()
        )
    return {
        "name": doc.get("name"),
        "role": role,
        "avatar_url": doc.get("profile_image"),
    }


_ATTRIBUTION_KEYS = (
    "share_id",
    "root_share_id",
    "parent_share_id",
    "utm_source",
    "utm_medium",
    "utm_campaign",
)


def _share_attribution(request: Request, share_svc, message_id: str) -> dict:
    sid = (request.query_params.get("share") or "").strip()
    record = None
    if sid and share_svc is not None:
        try:
            record = share_svc.get_share(sid)
        except Exception:
            record = None
    record = record if isinstance(record, dict) else {}
    if record and str(record.get("message_id") or "") != str(message_id or ""):
        # Never attribute a share link to a different announcement.
        return {key: "" for key in _ATTRIBUTION_KEYS}
    return {
        "share_id": str(record.get("share_id") or ""),
        "root_share_id": str(record.get("root_share_id") or ""),
        "parent_share_id": str(record.get("parent_share_id") or ""),
        "utm_source": request.query_params.get("utm_source") or str(record.get("utm_source") or ""),
        "utm_medium": request.query_params.get("utm_medium") or str(record.get("utm_medium") or ""),
        "utm_campaign": request.query_params.get("utm_campaign") or str(record.get("utm_campaign") or ""),
    }


@router.get("/.well-known/assetlinks.json")
def assetlinks(settings: Settings = Depends(get_settings)) -> JSONResponse:
    return JSONResponse(
        content=[
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": settings.android_package_name,
                    "sha256_cert_fingerprints": settings.android_sha256_cert_fingerprints,
                },
            }
        ]
    )


@router.get("/.well-known/apple-app-site-association")
def apple_app_site_association(settings: Settings = Depends(get_settings)) -> Response:
    # Without a Team ID the appID would be malformed (".com.starkinnovations.m360"),
    # which breaks Apple's Universal Links validation. Emit an empty details list
    # until APPLE_TEAM_ID is configured.
    details = (
        [{"appID": settings.apple_app_id, "paths": ["/s/*", "/m/*"]}]
        if settings.apple_app_id
        else []
    )
    payload = {"applinks": {"apps": [], "details": details}}
    return Response(content=json.dumps(payload), media_type="application/json")


def _resolve_masjid_photo(masjid_id, masjid_svc, search_svc, masjid=None):
    """Best-effort Places photo, preferring a fresh (non-expired) reference."""
    if masjid is None:
        try:
            masjid = (masjid_svc.get_masjid(masjid_id) or {}).get("masjid", {})
        except Exception:
            masjid = {}
    place_id = str(masjid.get("place_id") or masjid_id)
    try:
        place = search_svc.get_place_by_id(place_id) or {}
        photos = place.get("photos") or []
        if photos and isinstance(photos[0], dict):
            url = photos[0].get("url") or photos[0].get("name")
            if url:
                return str(url)
    except Exception:
        pass
    stored = masjid.get("photos") or (
        (masjid.get("google_place_data") or {}).get("photos") or []
    )
    for photo in stored:
        if isinstance(photo, dict):
            url = photo.get("url") or photo.get("name")
            if url:
                return str(url)
    return None


@router.get("/m/{masjid_id}/image")
def masjid_image(
    masjid_id: str,
    settings: Settings = Depends(get_settings),
    masjid_svc=Depends(get_masjid_entity_service),
    search_svc=Depends(get_masjid_search_service),
):
    """Serve a crawler-friendly preview image (small, direct, cacheable).

    WhatsApp/Messenger drop og:image when the source is multi-megabyte or needs
    redirects to a CDN, so proxy a 630px variant through our own URL.
    """
    default = (
        f"{settings.share_web_base_url.rstrip('/')}/share-static/og-default.png"
    )
    photo = _resolve_masjid_photo(masjid_id, masjid_svc, search_svc)
    if not photo:
        return RedirectResponse(default, status_code=302)
    url = _minify_places_photo(photo, 630)
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            upstream = client.get(url)
        ctype = upstream.headers.get("content-type", "")
        if upstream.status_code == 200 and ctype.startswith("image/"):
            return Response(
                content=upstream.content,
                media_type=ctype,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        pass
    return RedirectResponse(default, status_code=302)


_PREVIEW_BOT_TOKENS = (
    "bot", "crawler", "spider", "facebookexternalhit", "whatsapp",
    "telegram", "slack", "discord", "twitter", "linkedin", "pinterest",
    "embedly", "preview", "skype", "vkshare", "w3c_validator",
)


def _is_preview_bot(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(token in ua for token in _PREVIEW_BOT_TOKENS)


def _ua_is_ios(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return "iphone" in ua or "ipad" in ua or "ipod" in ua


def _ua_is_android(user_agent: str) -> bool:
    return "android" in (user_agent or "").lower()


@router.get("/m/{masjid_id}", response_class=HTMLResponse)
def masjid_page(
    masjid_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    masjid_svc=Depends(get_masjid_entity_service),
    search_svc=Depends(get_masjid_search_service),
) -> HTMLResponse:
    """Public masjid link target.

    Device with the app: Android App Links / the intent handoff open the PDP,
    so this document is never rendered. Without the app the user is sent
    straight to the store instead of landing on a page. Crawlers still get the
    OG document so WhatsApp can render the preview image.
    """
    ua = request.headers.get("user-agent", "")
    if not _is_preview_bot(ua):
        if _ua_is_ios(ua):
            return RedirectResponse(settings.app_store_url, status_code=302)
        # macOS may be an iPad in desktop mode and can still open the app, so
        # leave it to the client-side handoff.
        if not _ua_is_android(ua) and "macintosh" not in (ua or "").lower():
            return RedirectResponse(settings.play_store_url, status_code=302)
    try:
        masjid = (masjid_svc.get_masjid(masjid_id) or {}).get("masjid", {})
    except Exception:
        masjid = {}
    if not masjid:
        html = env.get_template("share_not_found.html").render(
            marketing_site_url=settings.marketing_site_url
        )
        return HTMLResponse(html, status_code=404)
    photo_url = _resolve_masjid_photo(
        masjid_id, masjid_svc, search_svc, masjid=masjid
    )
    ctx = build_masjid_share_context(
        masjid, settings, masjid_id, photo_url=photo_url
    )
    # Crawlers get a small, redirect-free image from our own endpoint.
    ctx["og_image_url"] = (
        f"{settings.share_web_base_url.rstrip('/')}/m/{masjid_id}/image"
    )
    html = env.get_template("masjid_landing.html").render(**ctx)
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@router.get("/embed/{message_id}", response_class=HTMLResponse)
def embed_page(
    message_id: str,
    request: Request,
    for_app: int = 0,
    settings: Settings = Depends(get_settings),
    feed_svc=Depends(get_broadcast_feed_service),
    masjid_svc=Depends(get_masjid_entity_service),
) -> HTMLResponse:
    try:
        message = feed_svc.get_message_raw(message_id)
        masjid = (masjid_svc.get_masjid(message["masjid_id"]) or {}).get("masjid", {})
    except Exception:
        return HTMLResponse("<html><body>Not found</body></html>", status_code=404)
    # In-app playback must work for every announcement the feed shows, even
    # when sharing is disabled; the share page itself stays gated.
    if not for_app and resolve_share_state(message) in {"unavailable", "expired"}:
        return HTMLResponse(
            "<html><body>Not available</body></html>", status_code=404
        )
    ctx = build_share_context(message, masjid, settings)
    html = env.get_template("share_embed.html").render(**ctx)
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@router.get("/s/{message_id}", response_class=HTMLResponse)
def share_page(
    message_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    feed_svc=Depends(get_broadcast_feed_service),
    masjid_svc=Depends(get_masjid_entity_service),
    search_svc=Depends(get_masjid_search_service),
    share_svc=Depends(get_share_service),
) -> HTMLResponse:
    try:
        message = feed_svc.get_message_raw(message_id)
        masjid_wrap = masjid_svc.get_masjid(message["masjid_id"])
        masjid = (masjid_wrap or {}).get("masjid", {}) if masjid_wrap else {}
    except ApiException as exc:
        status = 404 if getattr(exc, "status_code", 500) == 404 else 500
        html = env.get_template("share_not_found.html").render(
            marketing_site_url=settings.marketing_site_url
        )
        return HTMLResponse(html, status_code=status)
    except Exception:
        html = env.get_template("share_not_found.html").render(
            marketing_site_url=settings.marketing_site_url
        )
        return HTMLResponse(html, status_code=500)

    place_id = str(masjid.get("place_id") or message.get("masjid_id") or "")
    masjid_image_url = None
    area = ""
    city = ""
    try:
        place = search_svc.get_place_by_id(place_id) or {}
        photos = place.get("photos") or []
        if photos and isinstance(photos[0], dict):
            masjid_image_url = photos[0].get("name") or None
        area, city = _area_and_city(place)
    except Exception:
        masjid_image_url = None

    state = resolve_share_state(message)
    if state in {"unavailable", "expired"}:
        template = (
            "share_unavailable.html" if state == "unavailable" else "share_expired.html"
        )
        html = env.get_template(template).render(
            marketing_site_url=settings.marketing_site_url,
            play_store_url=settings.play_store_url,
            app_store_url=settings.app_store_url,
        )
        resp = HTMLResponse(html)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    sender_profile = _resolve_sender_profile(request, message, place_id)
    attribution = _share_attribution(request, share_svc, message_id)
    ctx = build_share_context(
        message,
        masjid,
        settings,
        sender_profile=sender_profile,
        masjid_image_url=masjid_image_url,
        area=area,
        city=city,
        share_attribution=attribution,
    )
    ctx.update(attribution)
    html = env.get_template("share.html").render(**ctx)
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp
