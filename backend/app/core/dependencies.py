from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.db.session import get_db
from app.models.models import User, UserStreak
from app.schemas.schemas import TokenData


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user_optional(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user from cookie or header, return None if not authenticated."""
    token = request.cookies.get("access_token")
    
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
    
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_id: int = payload.get("sub")
    if not user_id:
        return None
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        return None
    
    return user


async def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """Require authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def set_auth_cookie(response: Response, access_token: str) -> None:
    """Set httpOnly auth cookie."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )


def clear_auth_cookie(response: Response) -> None:
    """Clear auth cookie."""
    response.delete_cookie(key="access_token", path="/", httponly=True, secure=settings.ENVIRONMENT == "production")


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


async def create_user(db: AsyncSession, email: str, password: str, full_name: str) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role="student",
        is_active=True
    )
    db.add(user)
    await db.flush()
    
    # Create streak record
    streak = UserStreak(user_id=user.id, current_streak=0, longest_streak=0)
    db.add(streak)
    
    await db.commit()
    await db.refresh(user)
    return user


async def update_last_login(db: AsyncSession, user: User) -> None:
    """Update user's last login timestamp."""
    user.last_login = datetime.utcnow()
    await db.commit()


async def update_streak(db: AsyncSession, user_id: int) -> UserStreak:
    """Update user's streak."""
    result = await db.execute(select(UserStreak).where(UserStreak.user_id == user_id))
    streak = result.scalar_one_or_none()
    
    if not streak:
        streak = UserStreak(user_id=user_id, current_streak=1, longest_streak=1, last_active_date=datetime.utcnow())
        db.add(streak)
    else:
        today = datetime.utcnow().date()
        last_active = streak.last_active_date.date() if streak.last_active_date else None
        
        if last_active != today:
            if last_active and (today - last_active).days == 1:
                streak.current_streak += 1
            elif not last_active or (today - last_active).days > 1:
                streak.current_streak = 1
            
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
            
            streak.last_active_date = datetime.utcnow()
    
    await db.commit()
    await db.refresh(streak)
    return streak