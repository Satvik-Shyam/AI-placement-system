"""
Authentication Utility - JWT and Password handling.

Provides:
- Password hashing with bcrypt
- JWT token creation/verification
- FastAPI dependencies for protected routes
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text

from app.core.config import get_settings
from app.db.postgres import get_db_session

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token extractor
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """
    FastAPI dependency - Get current authenticated user.
    
    Usage:
        @app.get("/protected")
        async def route(user: dict = Depends(get_current_user)):
            return user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(credentials.credentials)
    if not payload:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    # Verify user exists
    with get_db_session() as db:
        result = db.execute(
            text("SELECT user_id, email, role, is_active FROM users WHERE user_id = :id"),
            {"id": int(user_id)}
        )
        user = result.fetchone()
    
    if not user:
        raise credentials_exception
    
    if not user[3]:  # is_active
        raise HTTPException(status_code=403, detail="Account deactivated")
    
    return {"user_id": user[0], "email": user[1], "role": user[2]}


async def get_current_student(user: dict = Depends(get_current_user)) -> dict:
    """Dependency - Require student role and get student_id."""
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Students only")
    
    with get_db_session() as db:
        result = db.execute(
            text("SELECT student_id FROM students WHERE user_id = :id"),
            {"id": user["user_id"]}
        )
        row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Student profile not found. Create profile first.")
    
    user["student_id"] = row[0]
    return user


async def get_current_company(user: dict = Depends(get_current_user)) -> dict:
    """Dependency - Require company role and get company_id."""
    if user["role"] != "company":
        raise HTTPException(status_code=403, detail="Companies only")
    
    with get_db_session() as db:
        result = db.execute(
            text("SELECT company_id FROM companies WHERE user_id = :id"),
            {"id": user["user_id"]}
        )
        row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Company profile not found. Create profile first.")
    
    user["company_id"] = row[0]
    return user