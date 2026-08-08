from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import jwt
from fastapi import HTTPException, Request
from pydantic import BaseModel

from app.services.admin_auth_service import AdminAuthService


class AdminSession(BaseModel):
    admin_id: str
    email: str
    name: str
    role: str
    login_at: datetime
    expires_at: datetime


def web_admin_required(request: Request, auth_service: AdminAuthService) -> Dict[str, Any]:
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    admin = auth_service.verify_session(token)
    if not admin:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return admin


def admin_required(request: Request) -> AdminSession:
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    from app.core.config import get_settings
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    session = AdminSession(**payload)
    if session.expires_at.tzinfo is None:
        session.expires_at = session.expires_at.replace(tzinfo=timezone.utc)
    if session.expires_at < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return session
