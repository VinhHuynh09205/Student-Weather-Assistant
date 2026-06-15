from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, WeeklyClassSchedule
from app.schemas.weekly_class_schedule import WeeklyClassScheduleCreate, WeeklyClassScheduleUpdate


class WeeklyScheduleService:
    async def create_weekly_schedule(
        self,
        db: AsyncSession,
        user: User,
        payload: WeeklyClassScheduleCreate,
    ) -> WeeklyClassSchedule:
        schedule = WeeklyClassSchedule(
            user_id=user.id,
            subject_name=payload.subject_name,
            day_of_week=payload.day_of_week,
            start_time=payload.start_time,
            end_time=payload.end_time,
            location_name=payload.location_name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            timezone=payload.timezone,
            is_active=payload.is_active,
            notify_before_minutes=payload.notify_before_minutes,
            rain_alert_enabled=payload.rain_alert_enabled,
            storm_alert_enabled=payload.storm_alert_enabled,
            semester_start_date=payload.semester_start_date,
            semester_end_date=payload.semester_end_date,
        )
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    async def update_weekly_schedule(
        self,
        db: AsyncSession,
        user: User,
        schedule_id: UUID,
        payload: WeeklyClassScheduleUpdate,
    ) -> WeeklyClassSchedule | None:
        schedule = await self.get_weekly_schedule(db, user, schedule_id)
        if schedule is None:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        merged_start_time = update_data.get("start_time", schedule.start_time)
        merged_end_time = update_data.get("end_time", schedule.end_time)
        if merged_start_time >= merged_end_time:
            raise ValueError("start_time phai truoc end_time.")

        merged_semester_start = update_data.get("semester_start_date", schedule.semester_start_date)
        merged_semester_end = update_data.get("semester_end_date", schedule.semester_end_date)
        if (
            merged_semester_start is not None
            and merged_semester_end is not None
            and merged_semester_start > merged_semester_end
        ):
            raise ValueError("semester_start_date khong duoc sau semester_end_date.")

        for field, value in update_data.items():
            setattr(schedule, field, value)
        schedule.updated_at = datetime.utcnow()

        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    async def delete_or_disable_weekly_schedule(
        self,
        db: AsyncSession,
        user: User,
        schedule_id: UUID,
    ) -> WeeklyClassSchedule | None:
        schedule = await self.get_weekly_schedule(db, user, schedule_id)
        if schedule is None:
            return None
        schedule.is_active = False
        schedule.updated_at = datetime.utcnow()
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    async def list_weekly_schedules(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> list[WeeklyClassSchedule]:
        statement = select(WeeklyClassSchedule).where(WeeklyClassSchedule.user_id == user_id)
        if not include_inactive:
            statement = statement.where(WeeklyClassSchedule.is_active.is_(True))
        result = await db.execute(
            statement.order_by(WeeklyClassSchedule.day_of_week, WeeklyClassSchedule.start_time)
        )
        return list(result.scalars().all())

    async def get_weekly_schedule(
        self,
        db: AsyncSession,
        user: User,
        schedule_id: UUID,
    ) -> WeeklyClassSchedule | None:
        result = await db.execute(
            select(WeeklyClassSchedule)
            .where(WeeklyClassSchedule.id == schedule_id)
            .where(WeeklyClassSchedule.user_id == user.id)
        )
        return result.scalars().first()
