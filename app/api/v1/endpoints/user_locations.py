import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.models import User, UserLocation, UserSettings
from app.db.session import get_db
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate

router = APIRouter(prefix="/locations", tags=["locations"])


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth's radius in meters
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) * math.sin(d_lat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) * math.sin(d_lon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@router.get("", response_model=list[LocationResponse])
async def list_locations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserLocation)
        .where(UserLocation.user_id == current_user.id)
        .order_by(UserLocation.is_default.desc(), UserLocation.created_at.desc())
    )
    return result.scalars().all()



@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_in: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if there is already a duplicate location
    existing_res = await db.execute(
        select(UserLocation).where(UserLocation.user_id == current_user.id)
    )
    existing_locs = existing_res.scalars().all()
    for loc in existing_locs:
        distance = calculate_distance(loc.latitude, loc.longitude, location_in.latitude, location_in.longitude)
        if distance < 200 or loc.display_name.strip().lower() == location_in.display_name.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vị trí này đã được lưu.",
            )

    # Check if this is the first location or is_default is true
    result = await db.execute(select(UserLocation).where(UserLocation.user_id == current_user.id))
    has_locations = result.scalars().first() is not None


    is_default = location_in.is_default or not has_locations

    if is_default:
        # Unset previous defaults
        await db.execute(update(UserLocation).where(UserLocation.user_id == current_user.id).values(is_default=False))

    db_location = UserLocation(
        user_id=current_user.id,
        label=location_in.label,
        display_name=location_in.display_name,
        short_display_name=location_in.short_display_name,
        latitude=location_in.latitude,
        longitude=location_in.longitude,
        source=location_in.source,
        administrative_levels=location_in.administrative_levels,
        is_default=is_default,
    )
    db.add(db_location)
    await db.commit()
    await db.refresh(db_location)
    return db_location


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID,
    location_in: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserLocation).where(UserLocation.id == location_id).where(UserLocation.user_id == current_user.id)
    )
    db_location = result.scalars().first()
    if not db_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy vị trí yêu cầu hoặc bạn không có quyền truy cập.",
        )

    update_data = location_in.model_dump(exclude_unset=True)

    # Check duplicate location if updating coordinates or display name
    chk_lat = update_data.get("latitude", db_location.latitude)
    chk_lon = update_data.get("longitude", db_location.longitude)
    chk_name = update_data.get("display_name", db_location.display_name)

    if chk_lat is not None and chk_lon is not None and chk_name is not None:
        existing_res = await db.execute(
            select(UserLocation)
            .where(UserLocation.user_id == current_user.id)
            .where(UserLocation.id != location_id)
        )
        existing_locs = existing_res.scalars().all()
        for loc in existing_locs:
            distance = calculate_distance(loc.latitude, loc.longitude, chk_lat, chk_lon)
            if distance < 200 or loc.display_name.strip().lower() == chk_name.strip().lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vị trí này đã được lưu.",
                )

    if "is_default" in update_data and update_data["is_default"]:
        # Unset previous defaults
        await db.execute(update(UserLocation).where(UserLocation.user_id == current_user.id).values(is_default=False))


    for field, value in update_data.items():
        setattr(db_location, field, value)

    db.add(db_location)
    await db.commit()
    await db.refresh(db_location)
    return db_location


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserLocation).where(UserLocation.id == location_id).where(UserLocation.user_id == current_user.id)
    )
    db_location = result.scalars().first()
    if not db_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy vị trí yêu cầu hoặc bạn không có quyền truy cập.",
        )

    was_default = db_location.is_default
    await db.delete(db_location)
    await db.flush()

    if was_default:
        # Set another location as default if exists
        next_location_result = await db.execute(
            select(UserLocation)
            .where(UserLocation.user_id == current_user.id)
            .order_by(UserLocation.created_at.desc())
            .limit(1)
        )
        next_loc = next_location_result.scalars().first()
        if next_loc:
            next_loc.is_default = True
            db.add(next_loc)

    await db.commit()
    return None


@router.post("/{location_id}/set-default", response_model=LocationResponse)
async def set_default_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify location belongs to user
    result = await db.execute(
        select(UserLocation).where(UserLocation.id == location_id).where(UserLocation.user_id == current_user.id)
    )
    db_location = result.scalars().first()
    if not db_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy vị trí yêu cầu hoặc bạn không có quyền truy cập.",
        )

    # Unset other defaults
    await db.execute(update(UserLocation).where(UserLocation.user_id == current_user.id).values(is_default=False))

    db_location.is_default = True
    db.add(db_location)

    # Also update user default location in settings if settings exist
    settings_result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    db_settings = settings_result.scalars().first()
    if db_settings:
        db_settings.default_location_id = location_id
        db.add(db_settings)

    await db.commit()
    await db.refresh(db_location)
    return db_location
