"""
Authentication Routes

POST /auth/register - Register new user
POST /auth/login - Login and get JWT token
GET /auth/me - Get current user info
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import text

from app.db.postgres import get_db_session
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user
from app.schemas.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserResponse, MessageResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(request: RegisterRequest):
    """
    Register a new user account.
    
    After registration, login to get access token, then create profile.
    """
    with get_db_session() as db:
        # Check email exists
        result = db.execute(
            text("SELECT user_id FROM users WHERE email = :email"),
            {"email": request.email}
        )
        if result.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        db.execute(
            text("""
                INSERT INTO users (email, password_hash, role)
                VALUES (:email, :password_hash, :role)
            """),
            {
                "email": request.email,
                "password_hash": hash_password(request.password),
                "role": request.role.value
            }
        )
    
    return MessageResponse(message=f"Registered successfully as {request.role.value}. Please login.")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login and receive JWT access token.
    
    Include token in requests: Authorization: Bearer <token>
    """
    with get_db_session() as db:
        result = db.execute(
            text("SELECT user_id, password_hash, role, is_active FROM users WHERE email = :email"),
            {"email": request.email}
        )
        user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_id, password_hash, role, is_active = user
    
    if not is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    
    if not verify_password(request.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": str(user_id), "role": role})
    
    return TokenResponse(access_token=token, user_id=user_id, role=role)


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user's info."""
    with get_db_session() as db:
        result = db.execute(
            text("SELECT user_id, email, role, is_active, created_at FROM users WHERE user_id = :id"),
            {"id": user["user_id"]}
        )
        row = result.fetchone()
    
    return UserResponse(
        user_id=row[0], email=row[1], role=row[2], is_active=row[3], created_at=row[4]
    )