from typing import List, Optional

from pydantic import BaseModel, Field

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