import random
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.config import get_settings
from app.db.models import User, UserSettings
from app.db.session import get_db
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse
from app.utils.security import create_access_token, create_long_lived_access_token, get_password_hash, verify_password

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Validate username regex on backend as double check
    if not re.match(r"^[a-zA-Z0-9_.]+$", user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên đăng nhập chỉ gồm chữ cái, số, dấu gạch dưới (_) và dấu chấm (.)",
        )

    # Check if username already exists (case-insensitive)
    normalized_username = user_in.username.lower()
    result = await db.execute(select(User).where(User.normalized_username == normalized_username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên đăng nhập đã tồn tại.",
        )

    # Create new user
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        normalized_username=normalized_username,
        full_name=user_in.full_name,
        password_hash=hashed_password,
        auth_provider="local",
        is_active=True,
    )
    db.add(db_user)
    await db.flush()  # To get db_user.id

    # Create default user settings
    db_settings = UserSettings(
        user_id=db_user.id,
        temperature_unit="celsius",
        theme_mode="auto",
        auto_refresh_enabled=True,
        notification_enabled=True,
        default_vehicle_type="motorbike",
    )
    db.add(db_settings)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    normalized_username = credentials.username.lower()
    result = await db.execute(select(User).where(User.normalized_username == normalized_username))
    user = result.scalars().first()
    
    if not user or not user.password_hash or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản đã bị vô hiệu hóa.",
        )

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout():
    return {"message": "Đăng xuất thành công"}


class GoogleTokenRequest(Token):
    pass


@router.post("/google/token", response_model=Token)
async def google_token_login(req: GoogleTokenRequest, db: AsyncSession = Depends(get_db)):
    id_token = req.access_token  # Using access_token field in Token request for Google id_token

    # Verify token with Google
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token}, timeout=5.0
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="ID Token Google không hợp lệ hoặc đã hết hạn."
                )
            token_info = resp.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể xác thực ID Token với Google: {str(e)}",
        ) from e

    # Extract user info
    email = token_info.get("email")
    sub = token_info.get("sub")  # Google unique identifier
    name = token_info.get("name")
    picture = token_info.get("picture")

    if not email or not sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token Google thiếu các thông tin bắt buộc (email, sub)."
        )

    # Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        # Generate unique username for Google user
        base_username = email.split("@")[0].lower()
        base_username = re.sub(r"[^a-zA-Z0-9_.]", "_", base_username)
        username = base_username
        
        while True:
            check_result = await db.execute(select(User).where(User.normalized_username == username.lower()))
            if not check_result.scalars().first():
                break
            username = f"{base_username}_{random.randint(100, 999)}"

        # Create new user via Google
        user = User(
            email=email,
            username=username,
            normalized_username=username.lower(),
            full_name=name,
            avatar_url=picture,
            auth_provider="google",
            provider_id=sub,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create default settings
        db_settings = UserSettings(
            user_id=user.id,
            temperature_unit="celsius",
            theme_mode="auto",
            auto_refresh_enabled=True,
            notification_enabled=True,
            default_vehicle_type="motorbike",
        )
        db.add(db_settings)
        await db.commit()
        await db.refresh(user)
    else:
        # Update provider details if missing
        if user.auth_provider != "google":
            user.auth_provider = "google"
            user.provider_id = sub
        if name and not user.full_name:
            user.full_name = name
        if picture and not user.avatar_url:
            user.avatar_url = picture
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tài khoản đã bị vô hiệu hóa.")

    # Google users get a long-lived token (7 days) for persistent login
    access_token = create_long_lived_access_token(subject=user.id, days=7)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Issue a new access token for a still-authenticated user.
    
    Google users get 7-day tokens, local users get standard tokens.
    Frontend calls this before token expiry to keep users logged in.
    """
    if current_user.auth_provider == "google":
        new_token = create_long_lived_access_token(subject=current_user.id, days=7)
    else:
        new_token = create_access_token(subject=current_user.id)
    return Token(access_token=new_token, token_type="bearer")

