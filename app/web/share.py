from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.api.deps import get_broadcast_feed_service, get_masjid_entity_service
from app.core.config import Settings, get_settings
from app.exceptions.base import ApiException
from app.web.share_context import build_share_context

router = APIRouter(tags=["share"])

_env = Environment(
    loader=FileSystemLoader("app/web/templates"),
    autoescape=select_autoescape(["html"]),
)


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
    payload = {
        "applinks": {
            "apps": [],
            "details": [{"appID": settings.apple_app_id, "paths": ["/s/*"]}],
        }
    }
    return Response(content=json.dumps(payload), media_type="application/json")


@router.get("/s/{message_id}", response_class=HTMLResponse)
def share_page(
    message_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    feed_svc=Depends(get_broadcast_feed_service),
    masjid_svc=Depends(get_masjid_entity_service),
) -> HTMLResponse:
    try:
        message = feed_svc.get_message_raw(message_id)
        masjid_wrap = masjid_svc.get_masjid(message["masjid_id"])
        masjid = (masjid_wrap or {}).get("masjid", {}) if masjid_wrap else {}
    except ApiException as exc:
        if getattr(exc, "status_code", 500) == 404:
            html = _env.get_template("share_not_found.html").render(
                marketing_site_url=settings.marketing_site_url
            )
            return HTMLResponse(html, status_code=404)
        raise

    ctx = build_share_context(message, masjid, settings)
    html = _env.get_template("share.html").render(**ctx)
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp
