from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.masjid_entity_service import MasjidEntityService

router = APIRouter(prefix="/admin", tags=["admin"])
bearer = HTTPBearer(auto_error=False)


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    token: str
    admin_id: str
    email: str
    name: str
    role: str
    expires_at: str


class AdminProfile(BaseModel):
    admin_id: str
    email: str
    name: str
    role: str


class UserItem(BaseModel):
    user_id: str
    phone_number: str
    created_at: Optional[str] = None
    blocked_at: Optional[str] = None
    global_role: Optional[str] = None


class UserListResponse(BaseModel):
    users: List[UserItem]
    total: int
    page: int
    total_pages: int


class DashboardStats(BaseModel):
    total_users: int
    total_masjids: int
    total_claims: int
    total_donations: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_users: List[UserItem]


class MessageResponse(BaseModel):
    message: str


def _get_admin_creds():
    settings = get_settings()
    raw = settings.super_admins
    creds: Dict[str, str] = {}
    if raw:
        for entry in raw.split(","):
            entry = entry.strip()
            if ":" in entry:
                email, pw = entry.split(":", 1)
                creds[email.strip()] = pw.strip()
    return creds


def admin_api_required(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> Dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key.get_secret_value(),
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    expires_at = payload.get("expires_at")
    if expires_at:
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(tz=timezone.utc):
            raise HTTPException(status_code=401, detail="Token expired")
    return payload


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(body: AdminLoginRequest):
    creds = _get_admin_creds()
    if body.email not in creds or creds[body.email] != body.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(seconds=settings.admin_session_ttl_seconds)

    payload = {
        "admin_id": str(uuid4()),
        "email": body.email,
        "name": body.email.split("@")[0],
        "role": "super_admin",
        "login_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }

    token = jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )

    return AdminLoginResponse(
        token=token,
        admin_id=payload["admin_id"],
        email=payload["email"],
        name=payload["name"],
        role=payload["role"],
        expires_at=payload["expires_at"],
    )


@router.get("/me", response_model=AdminProfile)
def admin_me(admin: Dict[str, Any] = Depends(admin_api_required)):
    return AdminProfile(
        admin_id=admin["admin_id"],
        email=admin["email"],
        name=admin["name"],
        role=admin["role"],
    )


@router.get("/dashboard", response_model=DashboardResponse)
def admin_dashboard(
    request: Request,
    admin: Dict[str, Any] = Depends(admin_api_required),
):
    user_store = getattr(request.app.state, "user_store", None)
    total_users = 0
    recent_users: List[UserItem] = []

    if user_store:
        try:
            result = user_store.list_users(skip=0, limit=5)
            total_users = result.get("total", 0)
            recent_users = [_to_user_item(u) for u in result.get("users", [])]
        except Exception:
            pass

    svc: Optional[MasjidEntityService] = getattr(request.app.state, "masjid_entity_service", None)
    total_masjids = 0
    if svc:
        try:
            listing = svc.get_masjid_list(page=1, limit=1)
            total_masjids = listing.get("pagination", {}).get("total", 0)
        except Exception:
            pass

    return DashboardResponse(
        stats=DashboardStats(
            total_users=total_users,
            total_masjids=total_masjids,
            total_claims=0,
            total_donations=0,
        ),
        recent_users=recent_users,
    )


@router.get("/users", response_model=UserListResponse)
def admin_users(
    request: Request,
    page: int = Query(1, ge=1),
    q: str = Query("", alias="q"),
    admin: Dict[str, Any] = Depends(admin_api_required),
):
    user_store = getattr(request.app.state, "user_store", None)
    per_page = 20

    if not user_store:
        return UserListResponse(users=[], total=0, page=page, total_pages=1)

    try:
        if q.strip():
            results = user_store.search_users(q.strip())
            users = [_to_user_item(u) for u in results]
            total = len(users)
        else:
            result = user_store.list_users(skip=(page - 1) * per_page, limit=per_page)
            users = [_to_user_item(u) for u in result.get("users", [])]
            total = result.get("total", 0)
    except Exception:
        return UserListResponse(users=[], total=0, page=page, total_pages=1)

    total_pages = max(1, (total + per_page - 1) // per_page)
    return UserListResponse(users=users, total=total, page=page, total_pages=total_pages)


@router.post("/users/{user_id}/block", response_model=MessageResponse)
def admin_block_user(
    request: Request,
    user_id: str,
    admin: Dict[str, Any] = Depends(admin_api_required),
):
    user_store = getattr(request.app.state, "user_store", None)
    if user_store:
        try:
            user_store.block_user(user_id)
        except Exception:
            pass
    return MessageResponse(message="User blocked")


@router.post("/users/{user_id}/unblock", response_model=MessageResponse)
def admin_unblock_user(
    request: Request,
    user_id: str,
    admin: Dict[str, Any] = Depends(admin_api_required),
):
    user_store = getattr(request.app.state, "user_store", None)
    if user_store:
        try:
            user_store.unblock_user(user_id)
        except Exception:
            pass
    return MessageResponse(message="User unblocked")


@router.get("/masjids")
def admin_masjids(
    request: Request,
    page: int = Query(1, ge=1),
    q: str = Query("", alias="q"),
    admin: Dict[str, Any] = Depends(admin_api_required),
):
    svc: Optional[MasjidEntityService] = getattr(request.app.state, "masjid_entity_service", None)
    if not svc:
        return {"masjids": [], "total": 0, "page": page, "total_pages": 1}

    try:
        per_page = 20
        result = svc.get_masjid_list(page=page, limit=per_page, city=q.strip() or None)
        items = result.get("masjids", [])
        pagination = result.get("pagination", {})
        return {
            "masjids": items,
            "total": pagination.get("total", len(items)),
            "page": pagination.get("page", page),
            "total_pages": pagination.get("pages", 1),
        }
    except Exception:
        return {"masjids": [], "total": 0, "page": page, "total_pages": 1}


@router.post("/masjids/import")
def admin_import_masjids(
    request: Request,
    city: str = Query(..., description="City name to search masjids in"),
    max_results: int = Query(10, ge=1, le=50),
    admin: Dict[str, Any] = Depends(admin_api_required),
):
    svc: Optional[MasjidEntityService] = getattr(request.app.state, "masjid_entity_service", None)
    if not svc:
        raise HTTPException(status_code=503, detail="Masjid service not available (MongoDB required)")

    places_svc = getattr(request.app.state, "masjid_search_service", None)
    if not places_svc:
        raise HTTPException(status_code=503, detail="Google Places search service not available")

    try:
        result = svc.search_by_name(city, limit=max_results, page=1)
        imported = len(result.get("masjids", []))
        return {"imported": imported, "city": city, "message": f"Imported {imported} masjids for '{city}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/claims")
def admin_claims(
    request: Request,
    admin: Dict[str, Any] = Depends(admin_api_required),
):
    return {"claims": [], "total": 0, "page": 1, "total_pages": 1}


@router.get("/donations")
def admin_donations(
    request: Request,
    admin: Dict[str, Any] = Depends(admin_api_required),
):
    return {"donations": [], "total": 0, "page": 1, "total_pages": 1}


def _to_user_item(data: Dict[str, Any]) -> UserItem:
    return UserItem(
        user_id=str(data.get("user_id", "")),
        phone_number=str(data.get("phone_number", "")),
        created_at=str(data.get("created_at") or "") or None,
        blocked_at=str(data.get("blocked_at") or "") or None,
        global_role=str(data.get("global_role") or "") or None,
    )
