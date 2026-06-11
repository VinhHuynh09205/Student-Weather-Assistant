from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.models import StudySchedule, User, UserLocation
from app.db.session import get_db
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(StudySchedule).where(StudySchedule.user_id == current_user.id).order_by(StudySchedule.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_in: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Enforce maximum of 8 schedules
    count_res = await db.execute(
        select(StudySchedule).where(StudySchedule.user_id == current_user.id)
    )
    if len(count_res.scalars().all()) >= 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn chỉ được lưu tối đa 8 lịch học.",
        )

    # Validate study date range (today up to 8 days later)
    if schedule_in.study_date:
        try:
            s_date = datetime.strptime(schedule_in.study_date, "%Y-%m-%d").date()
            today_date = (datetime.utcnow() + timedelta(hours=7)).date()
            max_date = today_date + timedelta(days=8)
            if s_date < today_date or s_date > max_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ngày học phải nằm trong khoảng từ hôm nay đến 8 ngày tới.",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Định dạng ngày học không hợp lệ. Vui lòng sử dụng định dạng YYYY-MM-DD.",
            ) from None

    # Check duplicate schedule (same date and same time window)
    if schedule_in.study_date:
        existing_res = await db.execute(
            select(StudySchedule)
            .where(StudySchedule.user_id == current_user.id)
            .where(StudySchedule.study_date == schedule_in.study_date)
            .where(StudySchedule.start_time == schedule_in.start_time)
            .where(StudySchedule.end_time == schedule_in.end_time)
        )
        if existing_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lịch học này đã tồn tại.",
            )

    # Verify location belongs to user if provided
    if schedule_in.location_id:
        loc_res = await db.execute(
            select(UserLocation)
            .where(UserLocation.id == schedule_in.location_id)
            .where(UserLocation.user_id == current_user.id)
        )
        if not loc_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vị trí đã chọn không hợp lệ.",
            )

    db_schedule = StudySchedule(
        user_id=current_user.id,
        title=schedule_in.title,
        study_date=schedule_in.study_date,
        start_time=schedule_in.start_time,
        end_time=schedule_in.end_time,
        vehicle_type=schedule_in.vehicle_type,
        location_id=schedule_in.location_id,
        repeat_type=schedule_in.repeat_type,
        repeat_days=schedule_in.repeat_days,
        note=schedule_in.note,
        is_active=schedule_in.is_active,
    )
    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)
    return db_schedule
@router.get("/upcoming", response_model=ScheduleResponse | None)
async def get_upcoming_schedule(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get all active schedules for the user
    result = await db.execute(
        select(StudySchedule)
        .where(StudySchedule.user_id == current_user.id)
        .where(StudySchedule.is_active)
    )
    schedules = result.scalars().all()
    if not schedules:
        return None

    # Find the one that has the closest next occurrence
    current_dt = datetime.utcnow() + timedelta(hours=7)  # Local Vietnam Time
    upcoming_candidates: list[tuple[StudySchedule, datetime]] = []

    weekday_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

    for sched in schedules:
        try:
            sh, sm = map(int, sched.start_time.split(":"))
        except Exception:
            continue

        if sched.repeat_type == "none":
            if not sched.study_date:
                continue
            try:
                s_date = datetime.strptime(sched.study_date, "%Y-%m-%d").date()
                s_dt = datetime.combine(s_date, datetime.min.time().replace(hour=sh, minute=sm))
                if s_dt > current_dt:
                    upcoming_candidates.append((sched, s_dt))
            except Exception:
                continue
        elif sched.repeat_type == "weekly":
            days = sched.repeat_days
            if not days:
                continue

            for i in range(8):  # Check today and next 7 days
                test_date = current_dt.date() + timedelta(days=i)
                test_weekday = test_date.weekday()
                matching_days = [d for d in days if weekday_map.get(d.lower()) == test_weekday]
                if matching_days:
                    test_dt = datetime.combine(test_date, datetime.min.time().replace(hour=sh, minute=sm))
                    if test_dt > current_dt:
                        upcoming_candidates.append((sched, test_dt))
                        break  # Only get the earliest occurrence for this schedule

    if not upcoming_candidates:
        # Fallback to the latest created active schedule if all are in the past
        return schedules[0] if schedules else None

    # Sort by next occurrence datetime
    upcoming_candidates.sort(key=lambda x: x[1])
    return upcoming_candidates[0][0]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(StudySchedule).where(StudySchedule.id == schedule_id).where(StudySchedule.user_id == current_user.id)
    )
    db_schedule = result.scalars().first()
    if not db_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch học hoặc bạn không có quyền truy cập.",
        )
    return db_schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    schedule_in: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(StudySchedule).where(StudySchedule.id == schedule_id).where(StudySchedule.user_id == current_user.id)
    )
    db_schedule = result.scalars().first()
    if not db_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch học hoặc bạn không có quyền truy cập.",
        )

    # Validate study date range if updated
    if schedule_in.study_date:
        try:
            s_date = datetime.strptime(schedule_in.study_date, "%Y-%m-%d").date()
            today_date = (datetime.utcnow() + timedelta(hours=7)).date()
            max_date = today_date + timedelta(days=8)
            if s_date < today_date or s_date > max_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ngày học phải nằm trong khoảng từ hôm nay đến 8 ngày tới.",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Định dạng ngày học không hợp lệ. Vui lòng sử dụng định dạng YYYY-MM-DD.",
            ) from None

    # Check duplicate schedule if date or time range is updated
    chk_date = schedule_in.study_date if schedule_in.study_date is not None else db_schedule.study_date
    chk_start = schedule_in.start_time if schedule_in.start_time is not None else db_schedule.start_time
    chk_end = schedule_in.end_time if schedule_in.end_time is not None else db_schedule.end_time

    if chk_date and chk_start and chk_end:
        existing_res = await db.execute(
            select(StudySchedule)
            .where(StudySchedule.user_id == current_user.id)
            .where(StudySchedule.id != schedule_id)
            .where(StudySchedule.study_date == chk_date)
            .where(StudySchedule.start_time == chk_start)
            .where(StudySchedule.end_time == chk_end)
        )
        if existing_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lịch học này đã tồn tại.",
            )

    # Verify location belongs to user if updated
    if schedule_in.location_id:
        loc_res = await db.execute(
            select(UserLocation)
            .where(UserLocation.id == schedule_in.location_id)
            .where(UserLocation.user_id == current_user.id)
        )
        if not loc_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vị trí đã chọn không hợp lệ.",
            )

    update_data = schedule_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_schedule, field, value)

    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)
    return db_schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(StudySchedule).where(StudySchedule.id == schedule_id).where(StudySchedule.user_id == current_user.id)
    )
    db_schedule = result.scalars().first()
    if not db_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch học hoặc bạn không có quyền truy cập.",
        )

    await db.delete(db_schedule)
    await db.commit()
    return None
