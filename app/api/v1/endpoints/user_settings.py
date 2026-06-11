from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.models import User, UserSettings
from app.db.session import get_db
from app.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    db_settings = result.scalars().first()
    if not db_settings:
        # Create default settings if not exists for some reason
        db_settings = UserSettings(
            user_id=current_user.id,
            temperature_unit="celsius",
            theme_mode="auto",
            auto_refresh_enabled=True,
            notification_enabled=True,
            default_vehicle_type="motorbike",
        )
        db.add(db_settings)
        await db.commit()
        await db.refresh(db_settings)
    return db_settings


@router.put("", response_model=SettingsResponse)
async def update_settings(
    settings_in: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    db_settings = result.scalars().first()
    if not db_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cài đặt cho người dùng này.",
        )

    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_settings, field, value)

    db.add(db_settings)
    await db.commit()
    await db.refresh(db_settings)
    return db_settings
