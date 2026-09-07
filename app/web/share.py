from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.core.config import Settings, get_settings

router = APIRouter(tags=["share"])


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
