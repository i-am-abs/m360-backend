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

def _flash_from_query(request: Request):
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    msgs = []
    if success:
        msgs.append(("success", success))
    if error:
        msgs.append(("error", error))
    return msgs

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

    claim_svc = getattr(request.app.state, "claim_service", None)
    total_claims = 0
    pending_claims = 0
    recent_claims = []
    if claim_svc:
        try:
            result = claim_svc.list_claims(status=None, page=1, limit=5)
            total_claims = result.get("pagination", {}).get("total", 0)
            recent_claims = result.get("claims", [])
        except Exception:
            pass
        try:
            pending = claim_svc.list_claims(status="pending", page=1, limit=1)
            pending_claims = pending.get("pagination", {}).get("total", 0)
        except Exception:
            pass

    masjid_svc = getattr(request.app.state, "masjid_entity_service", None)
    total_masjids = 0
    if masjid_svc:
        try:
            listing = masjid_svc.get_masjid_list(page=1, limit=1)
            total_masjids = listing.get("pagination", {}).get("total", 0)
        except Exception:
            pass

    stats = Stats(
        total_users=total_users,
        total_masjids=total_masjids,
        total_claims=total_claims,
        pending_claims=pending_claims,
        total_donations=0,
    )
    return templates.get_template("dashboard.html").render(
        admin=session, active_tab="dashboard", stats=stats,
        recent_users=recent_users, recent_claims=recent_claims,
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
def masjids(
    request: Request,
    session: AdminSession = Depends(admin_required),
    page: int = 1,
    q: str = "",
):
    svc = getattr(request.app.state, "masjid_entity_service", None)
    db = getattr(request.app.state, "mongo_client", None)
    masjids_list = []
    total_pages = 1
    current_page = page
    if q.strip() and db:
        try:
            from app.core.config import get_settings
            settings = get_settings()
            database = db.get_database(settings.mongodb_database)
            regex = {"$regex": q.strip(), "$options": "i"}
            docs = list(database["masjids"].find(
                {"$or": [{"name": regex}, {"city": regex}, {"place_id": regex}]},
            ).skip((page - 1) * 20).limit(20).sort("meta.created_at", -1))
            total = database["masjids"].count_documents({"$or": [{"name": regex}, {"city": regex}, {"place_id": regex}]})
            masjids_list = []
            from app.repositories.mongo_masjid_repository import MongoMasjidRepository
            for d in docs:
                masjids_list.append(MongoMasjidRepository._as_dict(d))
            total_pages = max(1, (total + 19) // 20)
        except Exception:
            pass
    elif svc:
        try:
            result = svc.get_masjid_list(page=page, limit=20)
            masjids_list = result.get("masjids", [])
            pagination = result.get("pagination", {})
            total_pages = pagination.get("pages", 1)
        except Exception:
            pass
    flash = _flash_from_query(request)
    return templates.get_template("masjids.html").render(
        admin=session, active_tab="masjids",
        masjids=masjids_list, page=current_page,
        total_pages=total_pages, q=q, flash=flash,
    )


@router.get("/masjids/new", response_class=HTMLResponse)
def new_masjid_form(session: AdminSession = Depends(admin_required)):
    return templates.get_template("masjid_new.html").render(admin=session)


@router.post("/masjids/create")
def create_masjid(
    request: Request,
    session: AdminSession = Depends(admin_required),
    name: str = Form(...),
    name_arabic: str = Form(""),
    address: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    lat: str = Form(""),
    lng: str = Form(""),
):
    db = getattr(request.app.state, "mongo_client", None)
    if not db:
        return RedirectResponse(url="/admin/masjids?error=Database+unavailable", status_code=303)
    try:
        from app.core.config import get_settings
        settings = get_settings()
        database = db.get_database(settings.mongodb_database)
        from bson import ObjectId
        doc = {
            "place_id": f"admin_{ObjectId()}",
            "name": name,
            "name_arabic": name_arabic,
            "address": address,
            "city": city,
            "state": state,
            "country": "India",
            "location": {
                "type": "Point",
                "coordinates": [float(lng), float(lat)] if lat and lng else [0, 0],
            },
            "facilities": {},
            "services": {},
            "timings": {},
            "contact": {},
            "management": {"is_claimed": False, "committee": []},
            "meta": {
                "status": "active",
                "source": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        result = database["masjids"].insert_one(doc)
        return RedirectResponse(
            url=f"/admin/masjids/{result.inserted_id}?success=Masjid+created",
            status_code=303,
        )
    except Exception:
        return RedirectResponse(url="/admin/masjids?error=Failed+to+create", status_code=303)


@router.get("/claims", response_class=HTMLResponse)
def claims(
    request: Request,
    session: AdminSession = Depends(admin_required),
    page: int = 1,
    status: str = "all",
    q: str = "",
):
    svc = getattr(request.app.state, "claim_service", None)
    admin_store = getattr(request.app.state, "admin_store", None)
    mongo_client = getattr(request.app.state, "mongo_client", None)
    user_store = getattr(request.app.state, "user_store", None)
    claims_data = {"claims": [], "pagination": {"page": 1, "pages": 1}}
    if svc:
        try:
            claims_data = svc.list_claims(
                status=None if status == "all" else status,
                page=page,
                limit=20,
            )
            if q.strip():
                ql = q.strip().lower()
                filtered = []
                for c in claims_data.get("claims", []):
                    if ql in c.get("masjid_name", "").lower() or ql in c.get("user_id", "").lower() or ql in c.get("masjid_city", "").lower():
                        filtered.append(c)
                claims_data["claims"] = filtered
            for claim in claims_data.get("claims", []):
                if user_store and claim.get("user_id"):
                    try:
                        uid = claim["user_id"]
                        user_matches = user_store.search_users(uid[:8])
                        for u in user_matches:
                            if u.get("user_id") == uid:
                                claim["user_phone"] = u.get("phone_number", "")
                                claim["user_name"] = u.get("name", "")
                                break
                    except Exception:
                        pass
        except Exception:
            pass
    # Merge pending admin registrations (submitted via /admins/register from the
    # app) into the claims list so masjid committee claim requests are visible.
    try:
        pending_admins = admin_store.list_all(status="pending") if admin_store else []
    except Exception:
        pending_admins = []
    if pending_admins:
        from app.core.enums.committee_designation import CommitteeDesignation
        masjid_name_cache: dict[str, str] = {}
        masjid_city_cache: dict[str, str] = {}
        for adm in pending_admins:
            place_id = adm.get("masjid_place_id") or ""
            name = masjid_name_cache.get(place_id)
            city = masjid_city_cache.get(place_id)
            if place_id and mongo_client and name is None:
                try:
                    database = mongo_client.get_database(_get_settings().mongodb_database)
                    doc = database["masjids"].find_one({"place_id": place_id}, {"name": 1, "city": 1})
                    name = (doc or {}).get("name", "Unknown")
                    city = (doc or {}).get("city", "")
                    masjid_name_cache[place_id] = name
                    masjid_city_cache[place_id] = city
                except Exception:
                    name = "Unknown"
            if not name:
                name = "Unknown"
            if not city:
                city = ""
            role = adm.get("designation") or "admin"
            role_label = CommitteeDesignation.labels().get(role, role.replace("_", " ").title())
            claim_item = {
                "id": adm.get("admin_id", ""),
                "kind": "admin_registration",
                "user_id": adm.get("user_id") or "",
                "user_phone": adm.get("phone") or "",
                "user_name": adm.get("name") or "",
                "masjid_id": place_id,
                "masjid_name": name,
                "masjid_city": city,
                "claimed_role": role_label,
                "applicant_note": "",
                "status": adm.get("status", "pending"),
                "created_at": adm.get("created_at"),
            }
            claims_data["claims"].append(claim_item)
        # Sort merged list by created_at desc (best effort)
        def _ts(item):
            return item.get("created_at") or ""
        claims_data["claims"].sort(key=_ts, reverse=True)
        claims_data["pagination"]["total"] = len(claims_data["claims"])
    flash = _flash_from_query(request)
    return templates.get_template("claims.html").render(
        admin=session, active_tab="claims",
        claims=claims_data.get("claims", []),
        page=claims_data["pagination"]["page"],
        total_pages=claims_data["pagination"]["pages"],
        q=q, flash=flash,
    )


@router.post("/claims/{claim_id}/approve")
def approve_claim(
    request: Request,
    claim_id: str,
    session: AdminSession = Depends(admin_required),
):
    svc = getattr(request.app.state, "claim_service", None)
    admin_store = getattr(request.app.state, "admin_store", None)
    admin_svc = getattr(request.app.state, "admin_service", None)
    # If this "claim" is actually an admin registration, route to the admin
    # approval flow (which also populates the masjid committee + listing).
    if admin_store and admin_store.get_by_id(claim_id):
        if admin_svc:
            try:
                from app.core.enums.admin_status import AdminRegistrationStatus
                from app.schemas.admin import AdminStatusUpdateRequest
                admin_svc.update_status(
                    claim_id,
                    AdminStatusUpdateRequest(status=AdminRegistrationStatus.APPROVED),
                    {"user_id": session.admin_id, "role": "super_admin"},
                )
            except Exception:
                pass
        return RedirectResponse(url="/admin/claims", status_code=303)
    if svc:
        try:
            svc.approve_claim(claim_id, session.admin_id)
        except Exception:
            pass
    return RedirectResponse(url="/admin/claims", status_code=303)


@router.get("/masjids/{masjid_id}", response_class=HTMLResponse)
def masjid_detail(
    request: Request,
    masjid_id: str,
    session: AdminSession = Depends(admin_required),
):
    svc = getattr(request.app.state, "masjid_entity_service", None)
    claim_svc = getattr(request.app.state, "claim_service", None)
    masjid = None
    if svc:
        try:
            result = svc.get_masjid(masjid_id)
            masjid = result.get("masjid")
        except Exception:
            pass
    if not masjid:
        return templates.get_template("masjid_detail.html").render(
            admin=session, masjid=None, not_found=True,
        )
    claims = []
    if claim_svc and masjid:
        try:
            mid = masjid.get("place_id") or masjid.get("id", "")
            all_claims = claim_svc.list_claims(status=None, page=1, limit=100)
            claims = [c for c in all_claims.get("claims", []) if c.get("masjid_id") == mid]
        except Exception:
            pass
    flash = _flash_from_query(request)
    return templates.get_template("masjid_detail.html").render(
        admin=session, masjid=masjid, not_found=False, flash=flash, claims=claims,
    )


def _admin_update_masjid(request: Request, masjid_id: str, updates: dict) -> bool:
    db = getattr(request.app.state, "mongo_client", None)
    if not db:
        return False
    try:
        from bson import ObjectId
        from app.core.config import get_settings
        settings = get_settings()
        database = db.get_database(settings.mongodb_database)
        from app.repositories.mongo_masjid_repository import MongoMasjidRepository
        repo = MongoMasjidRepository(database)
        internal_id = masjid_id
        if not ObjectId.is_valid(masjid_id):
            doc = database["masjids"].find_one({"$or": [{"place_id": masjid_id}, {"id": masjid_id}]}, {"_id": 1})
            if doc:
                internal_id = str(doc["_id"])
        repo.update_masjid(internal_id, updates)
        return True
    except Exception:
        return False


@router.post("/masjids/{masjid_id}/update")
def admin_update_masjid(
    request: Request,
    masjid_id: str,
    session: AdminSession = Depends(admin_required),
    name: str = Form(""),
    name_arabic: str = Form(""),
    address: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    lat: str = Form(""),
    lng: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    website: str = Form(""),
):
    updates = {}
    if name:
        updates["name"] = name
    if name_arabic:
        updates["name_arabic"] = name_arabic
    if address:
        updates["address"] = address
    if city:
        updates["city"] = city
    if state:
        updates["state"] = state
    if lat and lng:
        try:
            updates["location.coordinates"] = [float(lng), float(lat)]
        except ValueError:
            pass
    contact_updated = phone or email or website
    contact = {}
    if contact_updated:
        contact["phone"] = phone or None
        contact["email"] = email or None
        contact["website"] = website or None
        updates["contact"] = contact
    try:
        _admin_update_masjid(request, masjid_id, updates)
        return RedirectResponse(url=f"/admin/masjids/{masjid_id}?success=Basic+information+updated", status_code=303)
    except Exception:
        return RedirectResponse(url=f"/admin/masjids/{masjid_id}?error=Failed+to+update", status_code=303)


@router.post("/masjids/{masjid_id}/update-facilities")
def admin_update_facilities(
    request: Request,
    masjid_id: str,
    session: AdminSession = Depends(admin_required),
    car_parking: str = Form(""),
    two_wheeler: str = Form(""),
    iftar: str = Form(""),
    wuzu: str = Form(""),
    ac: str = Form(""),
    air_cooler: str = Form(""),
    male_washroom: str = Form(""),
    drinking_water: str = Form(""),
    wheelchair: str = Form(""),
    mushaf: str = Form(""),
    chairs: str = Form(""),
    janazah: str = Form(""),
    women_area: str = Form(""),
    children_area: str = Form(""),
):
    facilities = {}
    raw = {
        "car_parking": car_parking, "two_wheeler_parking": two_wheeler,
        "iftar": iftar, "wuzu_area": wuzu, "ac": ac,
        "air_coolers": air_cooler, "male_washroom": male_washroom,
        "drinking_water": drinking_water, "wheelchair_accessible": wheelchair,
        "mushaf_available": mushaf, "chairs": chairs,
        "janazah_carrier": janazah, "women_prayer_area": women_area,
        "children_area": children_area,
    }
    for key, val in raw.items():
        if val == "true":
            facilities[key] = True
        elif val == "false":
            facilities[key] = False
    if facilities:
        _admin_update_masjid(request, masjid_id, {"facilities": facilities})
    return RedirectResponse(url=f"/admin/masjids/{masjid_id}", status_code=303)


@router.post("/masjids/{masjid_id}/update-timings")
def admin_update_timings(
    request: Request,
    masjid_id: str,
    session: AdminSession = Depends(admin_required),
    fajr: str = Form(""),
    dhuhr: str = Form(""),
    asr: str = Form(""),
    maghrib: str = Form(""),
    isha: str = Form(""),
):
    timings = {}
    for key, val in [("fajr", fajr), ("dhuhr", dhuhr), ("asr", asr), ("maghrib", maghrib), ("isha", isha)]:
        if val:
            timings[key] = val
    if timings:
        _admin_update_masjid(request, masjid_id, {"timings": timings})
    return RedirectResponse(url=f"/admin/masjids/{masjid_id}", status_code=303)


@router.post("/masjids/{masjid_id}/committee/add")
def admin_add_committee(
    request: Request,
    masjid_id: str,
    session: AdminSession = Depends(admin_required),
    member_name: str = Form(...),
    member_role: str = Form(...),
    user_phone: str = Form(""),
):
    db = getattr(request.app.state, "mongo_client", None)
    user_store = getattr(request.app.state, "user_store", None)
    if not db:
        return RedirectResponse(url=f"/admin/masjids/{masjid_id}?error=Database+unavailable", status_code=303)
    try:
        from bson import ObjectId
        from app.core.config import get_settings
        settings = get_settings()
        database = db.get_database(settings.mongodb_database)
        from app.repositories.mongo_masjid_repository import MongoMasjidRepository
        repo = MongoMasjidRepository(database)
        internal_id = masjid_id
        if not ObjectId.is_valid(masjid_id):
            doc = database["masjids"].find_one({"$or": [{"place_id": masjid_id}, {"id": masjid_id}]}, {"_id": 1})
            if doc:
                internal_id = str(doc["_id"])
        # Look up or create user by phone
        user_id = None
        if user_phone and user_store:
            user = user_store.ensure_user(user_phone)
            user_id = user.get("user_id")
        if not user_id:
            from uuid import uuid4
            user_id = f"admin_{uuid4()}"
        repo.add_committee_member(internal_id, {
            "user_id": user_id,
            "name": member_name,
            "role": member_role,
            "phone": user_phone or None,
        })
        return RedirectResponse(url=f"/admin/masjids/{masjid_id}?success=Member+added", status_code=303)
    except Exception:
        return RedirectResponse(url=f"/admin/masjids/{masjid_id}?error=Failed+to+add+member", status_code=303)


@router.post("/masjids/{masjid_id}/committee/{user_id}/remove")
def admin_remove_committee(
    request: Request,
    masjid_id: str,
    user_id: str,
    session: AdminSession = Depends(admin_required),
):
    db = getattr(request.app.state, "mongo_client", None)
    if db:
        try:
            from bson import ObjectId
            from app.core.config import get_settings
            settings = get_settings()
            database = db.get_database(settings.mongodb_database)
            from app.repositories.mongo_masjid_repository import MongoMasjidRepository
            repo = MongoMasjidRepository(database)
            internal_id = masjid_id
            if not ObjectId.is_valid(masjid_id):
                doc = database["masjids"].find_one({"$or": [{"place_id": masjid_id}, {"id": masjid_id}]}, {"_id": 1})
                if doc:
                    internal_id = str(doc["_id"])
            repo.remove_committee_member(internal_id, user_id)
        except Exception:
            pass
    return RedirectResponse(url=f"/admin/masjids/{masjid_id}?success=Member+removed", status_code=303)


@router.get("/claims/{claim_id}", response_class=HTMLResponse)
def claim_detail(
    request: Request,
    claim_id: str,
    session: AdminSession = Depends(admin_required),
):
    svc = getattr(request.app.state, "claim_service", None)
    user_store = getattr(request.app.state, "user_store", None)
    claim = None
    if svc:
        try:
            result = svc.list_claims(status=None, page=1, limit=50)
            for c in result.get("claims", []):
                if c.get("id") == claim_id:
                    claim = c
                    break
        except Exception:
            pass
    if claim and user_store and claim.get("user_id"):
        try:
            uid = claim["user_id"]
            users_result = user_store.search_users(uid[:8])
            for u in users_result:
                if u.get("user_id") == uid:
                    claim["user_phone"] = u.get("phone_number", "")
                    claim["user_name"] = u.get("name", "")
                    break
        except Exception:
            pass
    return templates.get_template("claim_detail.html").render(
        admin=session, claim=claim,
    )


@router.post("/claims/{claim_id}/reject")
def reject_claim(
    request: Request,
    claim_id: str,
    session: AdminSession = Depends(admin_required),
):
    svc = getattr(request.app.state, "claim_service", None)
    admin_store = getattr(request.app.state, "admin_store", None)
    admin_svc = getattr(request.app.state, "admin_service", None)
    if admin_store and admin_store.get_by_id(claim_id):
        if admin_svc:
            try:
                from app.core.enums.admin_status import AdminRegistrationStatus
                from app.schemas.admin import AdminStatusUpdateRequest
                admin_svc.update_status(
                    claim_id,
                    AdminStatusUpdateRequest(status=AdminRegistrationStatus.REJECTED, message="Rejected by admin"),
                    {"user_id": session.admin_id, "role": "super_admin"},
                )
            except Exception:
                pass
        return RedirectResponse(url="/admin/claims", status_code=303)
    if svc:
        try:
            svc.reject_claim(claim_id, session.admin_id, "Rejected by admin")
        except Exception:
            pass
    return RedirectResponse(url="/admin/claims", status_code=303)


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


@router.get("/users/{user_id}", response_class=HTMLResponse)
def user_detail(
    request: Request,
    user_id: str,
    session: AdminSession = Depends(admin_required),
):
    user_store = getattr(request.app.state, "user_store", None)
    db = getattr(request.app.state, "mongo_client", None)

    user_data = None
    if user_store:
        try:
            results = user_store.search_users(user_id[:12])
            for u in results:
                if u.get("user_id") == user_id:
                    user_data = u
                    break
        except Exception:
            pass

    masjids = []
    claims = []
    sessions_count = 0
    if db and user_data:
        try:
            from app.core.config import get_settings
            settings = get_settings()
            database = db.get_database(settings.mongodb_database)
            # Committee memberships
            docs = list(database["masjids"].find(
                {"management.committee.user_id": user_id},
                {"name": 1, "city": 1, "place_id": 1},
            ).limit(100))
            for d in docs:
                masjids.append({
                    "id": str(d["_id"]),
                    "name": d.get("name", "Unknown"),
                    "city": d.get("city", ""),
                    "place_id": d.get("place_id", ""),
                })
            # Claims
            claim_docs = list(database["masjid_claims"].find({"user_id": user_id}).sort("created_at", -1).limit(100))
            for c in claim_docs:
                claims.append({
                    "id": str(c["_id"]),
                    "masjid_id": c.get("masjid_id", ""),
                    "claimed_role": c.get("claimed_role", ""),
                    "status": c.get("status", ""),
                    "created_at": c.get("created_at", ""),
                })
            # Sessions
            sessions_count = database["sessions"].count_documents({"user_id": user_id})
        except Exception:
            pass

    return templates.get_template("user_detail.html").render(
        admin=session, user=user_data, masjids=masjids,
        claims=claims, sessions_count=sessions_count,
    )
