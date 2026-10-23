from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app.api.deps import (
    get_broadcast_feed_service,
    get_masjid_entity_service,
    get_masjid_search_service,
)
from app.core.config import Settings, get_settings
from app.core.enums.committee_designation import CommitteeDesignation
from app.exceptions.base import ApiException
from app.utils.broadcast import resolve_share_state
from app.web.share_context import build_share_context
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
    ctx = build_share_context(
        message,
        masjid,
        settings,
        sender_profile=sender_profile,
        masjid_image_url=masjid_image_url,
        area=area,
        city=city,
    )
    html = env.get_template("share.html").render(**ctx)
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp
