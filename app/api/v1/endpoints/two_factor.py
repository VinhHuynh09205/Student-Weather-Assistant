from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.limiter import limiter
from app.db.models import User
from app.db.session import get_db
from app.schemas.user import (
    Token,
    TwoFactorLoginRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
)
from app.services.totp_service import TOTPService
from app.utils.security import create_access_token, create_long_lived_access_token

router = APIRouter(prefix="/auth/2fa", tags=["two_factor"])
totp_service = TOTPService()


@router.post("/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate TOTP secret and QR code for setup."""
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Xác thực 2 yếu tố (2FA) đã được bật trên tài khoản này.",
        )

    # Generate new secret
    secret = totp_service.generate_secret()

    # Encrypt and save to user
    current_user.totp_secret = totp_service.encrypt_secret(secret)
    current_user.is_2fa_enabled = False  # Keep disabled until verified
    db.add(current_user)
    await db.commit()

    # Generate QR Code
    username_or_email = current_user.username or current_user.email or "User"
    qr_code = totp_service.generate_qr_code_base64(secret, username_or_email)

    return TwoFactorSetupResponse(qr_code_base64=qr_code, manual_key=secret)


@router.post("/enable")
async def enable_two_factor(
    payload: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify code and enable 2FA."""
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Xác thực 2 yếu tố (2FA) đã được kích hoạt.",
        )

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng thực hiện bước thiết lập 2FA trước.",
        )

    # Decrypt secret and verify code
    secret = totp_service.decrypt_secret(current_user.totp_secret)
    if not totp_service.verify_totp(secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không chính xác.",
        )

    current_user.is_2fa_enabled = True
    db.add(current_user)
    await db.commit()

    return {"message": "Bật xác thực 2 yếu tố (2FA) thành công."}


@router.post("/disable")
async def disable_two_factor(
    payload: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA."""
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Xác thực 2 yếu tố (2FA) chưa được bật.",
        )

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy cấu hình 2FA.",
        )

    # Decrypt and verify code
    secret = totp_service.decrypt_secret(current_user.totp_secret)
    if not totp_service.verify_totp(secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không chính xác.",
        )

    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    db.add(current_user)
    await db.commit()

    return {"message": "Tắt xác thực 2 yếu tố (2FA) thành công."}


@router.post("/verify", response_model=Token)
@limiter.limit("5/minute")
async def verify_two_factor(
    request: Request,
    payload: TwoFactorLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify TOTP code during login."""
    token_data = totp_service.verify_temp_token(payload.temp_token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu đăng nhập đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.",
        )

    user_id_str, remember_me = token_data

    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id_str))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Người dùng không tồn tại.",
        )

    if not user.is_2fa_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Xác thực 2 yếu tố (2FA) chưa được kích hoạt cho tài khoản này.",
        )

    # Decrypt and verify TOTP code
    secret = totp_service.decrypt_secret(user.totp_secret)
    if not totp_service.verify_totp(secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không chính xác.",
        )

    # Issue final access token
    if remember_me:
        access_token = create_long_lived_access_token(
            subject=user.id,
            days=7,
            extra_claims={"remember": True},
        )
    else:
        access_token = create_access_token(subject=user.id)

    return Token(access_token=access_token, token_type="bearer")
