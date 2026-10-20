from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.core.dependencies import (
    authenticate_user, create_user, update_last_login, 
    set_auth_cookie, clear_auth_cookie, get_current_user
)
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, Token
from app.models.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = await create_user(db, user_data.email, user_data.password, user_data.full_name)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Set cookie
    set_auth_cookie(response, access_token)
    
    return user


@router.post("/login", response_model=UserResponse)
async def login(
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Login user."""
    user = await authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    await update_last_login(db, user)
    
    # Update streak
    from app.core.dependencies import update_streak
    await update_streak(db, user.id)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Set cookie
    set_auth_cookie(response, access_token)
    
    return user


@router.post("/logout")
async def logout(response: Response):
    """Logout user."""
    clear_auth_cookie(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """Refresh access token."""
    access_token = create_access_token(
        data={"sub": current_user.id, "email": current_user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    set_auth_cookie(response, access_token)
    
    return Token(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )