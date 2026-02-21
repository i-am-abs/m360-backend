from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from core.di.container import get_jwt_service, get_user_repository
from utils.http_response import success_response
from utils.logger import Logger

security = HTTPBearer(auto_error=False)
auth_router = APIRouter(prefix="/auth", tags=["auth"])
logger = Logger.get_logger(__name__)


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


def get_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jwt_service = get_jwt_service()
    payload = jwt_service.decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


@auth_router.post("/login")
def login(request: LoginRequest):
    user_repo = get_user_repository()
    user = user_repo.find_by_username(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not pwd_context.verify(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    jwt_service = get_jwt_service()
    token = jwt_service.create_access_token(subject=request.username)
    return success_response({
        "access_token": token,
        "token_type": "bearer",
        "expires_in": jwt_service.get_expiration_seconds(),
    })


@auth_router.post("/register")
def register(request: RegisterRequest):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash(request.password)
    user_repo = get_user_repository()
    try:
        created = user_repo.create_user(
            username=request.username,
            hashed_password=hashed,
            email=request.email,
        )
        jwt_service = get_jwt_service()
        token = jwt_service.create_access_token(subject=request.username)
        return success_response({
            "user": created,
            "access_token": token,
            "token_type": "bearer",
            "expires_in": jwt_service.get_expiration_seconds(),
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
