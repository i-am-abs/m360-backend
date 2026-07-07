from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from app.core.config import get_settings, Settings
from app.web.deps import AdminSession, admin_required

router = APIRouter(prefix="/admin")

def _noop_flashed(with_categories=False):
    return []

templates = Environment(
    loader=FileSystemLoader("app/web/templates"),
    autoescape=True,
)
templates.globals["get_flashed_messages"] = _noop_flashed

_settings: Settings | None = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


ADMIN_CREDENTIALS: dict[str, str] = {}


def _get_admin_creds() -> dict[str, str]:
    if not ADMIN_CREDENTIALS:
        raw = _get_settings().super_admins
        if raw:
            for entry in raw.split(","):
                entry = entry.strip()
                if ":" in entry:
                    email, pw = entry.split(":", 1)
                    ADMIN_CREDENTIALS[email.strip()] = pw.strip()
    return ADMIN_CREDENTIALS


class Stats(BaseModel):
    total_users: int = 0
    total_masjids: int = 0
    total_claims: int = 0
    pending_claims: int = 0
    total_donations: int = 0


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    token = request.cookies.get("admin_token")
    if token:
        try:
            payload = jwt.decode(token, _get_settings().secret_key.get_secret_value(), algorithms=["HS256"])
            expires_at = payload.get("expires_at")
            if expires_at:
                expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires > datetime.now(tz=timezone.utc):
                    return RedirectResponse(url="/admin/dashboard", status_code=303)
        except jwt.PyJWTError:
            pass
    return templates.get_template("login.html").render()


@router.post("/login")
async def login_submit(response: Response, email: str = Form(...), password: str = Form(...)):
    creds = _get_admin_creds()
    if email not in creds or creds[email] != password:
        return templates.get_template("login.html").render(error="Invalid email or password.")

    session = AdminSession(
        admin_id=str(uuid4()),
        email=email,
        name=email.split("@")[0],
        role="super_admin",
        login_at=datetime.now(tz=timezone.utc),
        expires_at=datetime.now(tz=timezone.utc)
        + timedelta(seconds=_get_settings().admin_session_ttl_seconds),
    )

    token = jwt.encode(
        session.model_dump(mode="json"),
        _get_settings().secret_key.get_secret_value(),
        algorithm="HS256",
    )

    resp = RedirectResponse(url="/admin/dashboard", status_code=303)
    resp.set_cookie(
        key="admin_token",
        value=token,
        max_age=_get_settings().admin_session_ttl_seconds,
        httponly=True,
        samesite="strict",
    )
    return resp


@router.get("/logout")
def logout(response: Response):
    resp = RedirectResponse(url="/admin/login", status_code=303)
    resp.delete_cookie("admin_token")
    return resp


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, session: AdminSession = Depends(admin_required)):
    total_users = 0
    recent_users = []
    user_store = getattr(request.app.state, "user_store", None)
    if user_store:
        try:
            result = user_store.list_users(skip=0, limit=5)
            total_users = result.get("total", 0)
            recent_users = result.get("users", [])
        except Exception:
            pass

    stats = Stats(
        total_users=total_users,
        total_masjids=0,
        pending_claims=0,
        total_donations=0,
    )
    return templates.get_template("dashboard.html").render(
        admin=session, active_tab="dashboard", stats=stats,
        recent_users=recent_users, recent_claims=[],
    )


@router.get("/users", response_class=HTMLResponse)
def users(
    request: Request,
    session: AdminSession = Depends(admin_required),
    page: int = 1,
):
    per_page = 20
    user_store = getattr(request.app.state, "user_store", None)

    users_list = []
    total_pages = 1
    current_page = page

    if user_store:
        try:
            result = user_store.list_users(skip=(page - 1) * per_page, limit=per_page)
            users_list = result.get("users", [])
            total = result.get("total", 0)
            total_pages = max(1, (total + per_page - 1) // per_page)
        except Exception:
            pass

    return templates.get_template("users.html").render(
        admin=session, active_tab="users", users=users_list,
        page=current_page, total_pages=total_pages,
    )


@router.get("/masjids", response_class=HTMLResponse)
def masjids(session: AdminSession = Depends(admin_required)):
    return templates.get_template("masjids.html").render(
        admin=session, active_tab="masjids", masjids=[], page=1, total_pages=1
    )


@router.get("/claims", response_class=HTMLResponse)
def claims(session: AdminSession = Depends(admin_required)):
    return templates.get_template("claims.html").render(
        admin=session, active_tab="claims", claims=[], page=1, total_pages=1
    )


@router.get("/donations", response_class=HTMLResponse)
def donations(request: Request, session: AdminSession = Depends(admin_required)):
    return templates.get_template("donations.html").render(
        admin=session, active_tab="donations", donations=[], page=1, total_pages=1
    )


@router.post("/users/{user_id}/block")
def block_user(
    request: Request,
    user_id: str,
    session: AdminSession = Depends(admin_required),
):
    user_store = getattr(request.app.state, "user_store", None)
    if user_store:
        try:
            user_store.block_user(user_id)
        except Exception:
            pass
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/unblock")
def unblock_user(
    request: Request,
    user_id: str,
    session: AdminSession = Depends(admin_required),
):
    user_store = getattr(request.app.state, "user_store", None)
    if user_store:
        try:
            user_store.unblock_user(user_id)
        except Exception:
            pass
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/users/search", response_class=HTMLResponse)
def search_users(
    request: Request,
    q: str = "",
    session: AdminSession = Depends(admin_required),
):
    user_store = getattr(request.app.state, "user_store", None)
    users_list = []
    if q.strip():
        if user_store:
            try:
                users_list = user_store.search_users(q.strip())
            except Exception:
                pass

    return templates.get_template("_user_rows.html").render(users=users_list)
