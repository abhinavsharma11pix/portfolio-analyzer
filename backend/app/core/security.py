"""
Auth security — uses bcrypt directly (no passlib).
Avoids bcrypt 4.x / passlib incompatibility.
"""
import os
import logging
import hashlib
import hmac
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

SECRET_KEY     = os.getenv("JWT_SECRET_KEY", "dev-secret-portfolioai-change-in-prod-2024")
ALGORITHM      = "HS256"
ACCESS_EXPIRE  = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_EXPIRE = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS",   "30"))


def _prepare_password(password: str) -> bytes:
    """
    Pre-hash with SHA-256 before bcrypt to support passwords > 72 bytes.
    This is a standard pattern used by Django, Flask-Bcrypt etc.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("utf-8")


def hash_password(password: str) -> str:
    """Hash password using bcrypt with SHA-256 pre-hash."""
    prepared = _prepare_password(password)
    salt     = bcrypt.gensalt(rounds=12)
    hashed   = bcrypt.hashpw(prepared, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        prepared = _prepare_password(plain)
        return bcrypt.checkpw(prepared, hashed.encode("utf-8"))
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def create_access_token(data: Dict[str, Any]) -> str:
    payload = {
        **data,
        "exp":  datetime.now(timezone.utc) + timedelta(minutes=ACCESS_EXPIRE),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    payload = {
        **data,
        "exp":  datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def create_token_pair(user_id: int, email: str) -> Dict[str, str]:
    data = {"sub": str(user_id), "email": email}
    return {
        "access_token":  create_access_token(data),
        "refresh_token": create_refresh_token(data),
        "token_type":    "bearer",
    }