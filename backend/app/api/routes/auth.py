import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, EmailStr, Field, validator
from app.core.security import (
    hash_password, verify_password, create_token_pair,
    decode_token, REFRESH_EXPIRE
)
from app.db.user_repository import UserRepository, RefreshTokenRepository
from app.api.dependencies import get_current_user

logger     = logging.getLogger(__name__)
router     = APIRouter(default_response_class=ORJSONResponse)
user_repo  = UserRepository()
token_repo = RefreshTokenRepository()


class RegisterRequest(BaseModel):
    email:    EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=8, max_length=100)

    @validator("username")
    def clean_username(cls, v):
        v = v.lower().strip()
        if not all(c.isalnum() or c in "_-" for c in v):
            raise ValueError("Username: letters, numbers, _ and - only")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _safe(user: dict) -> dict:
    return {k: user[k] for k in ["id","email","username","created_at","last_login"] if k in user}

def _save_rt(user_id: int, token: str):
    expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE)
    token_repo.save(user_id, token, expires)


@router.post("/register", status_code=201)
async def register(req: RegisterRequest):
    if user_repo.email_exists(str(req.email)):
        raise HTTPException(400, "Email already registered")
    if user_repo.username_exists(req.username):
        raise HTTPException(400, "Username already taken")
    user = user_repo.create(str(req.email), req.username, hash_password(req.password))
    if not user:
        raise HTTPException(500, "Registration failed")
    tokens = create_token_pair(user["id"], user["email"])
    _save_rt(user["id"], tokens["refresh_token"])
    return {**tokens, "user": _safe(user)}


@router.post("/login")
async def login(req: LoginRequest):
    user = user_repo.get_by_email(str(req.email))
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid email or password")
    user_repo.update_last_login(user["id"])
    tokens = create_token_pair(user["id"], user["email"])
    _save_rt(user["id"], tokens["refresh_token"])
    return {**tokens, "user": _safe(user)}


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    user_id = token_repo.verify_and_rotate(req.refresh_token)
    if not user_id:
        raise HTTPException(401, "Token expired or already used")
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(401, "User not found")
    tokens = create_token_pair(user["id"], user["email"])
    _save_rt(user["id"], tokens["refresh_token"])
    return {**tokens, "user": _safe(user)}


@router.post("/logout")
async def logout(req: RefreshRequest, current_user: dict = Depends(get_current_user)):
    token_repo.revoke_all(current_user["id"])
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return _safe(current_user)