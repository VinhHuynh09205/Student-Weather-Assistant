from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.db.models import WeeklyClassSchedule

DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"


@dataclass(frozen=True)
class ScheduleOccurrence:
    occurrence_key: str
    start_at: datetime
    end_at: datetime
    status: str = "scheduled"


class ScheduleOccurrenceService:
    def get_next_occurrence(
        self,
        schedule: WeeklyClassSchedule,
        now: datetime | None = None,
        timezone: str | None = None,
    ) -> ScheduleOccurrence | None:
        """Return the next class window in local time.

        A class scheduled for today is still considered the next occurrence while
        local time is before or exactly at end_time. Only after end_time has
        passed do we move that recurring class to the following week.
        """
        if not schedule.is_active:
            return None

        tz = _resolve_timezone(timezone or schedule.timezone)
        local_now = _coerce_to_timezone(now, tz)
        search_date = local_now.date()
        if schedule.semester_start_date and search_date < schedule.semester_start_date:
            search_date = schedule.semester_start_date

        candidate_date = _next_date_for_weekday(search_date, schedule.day_of_week)
        candidate = self._build_occurrence(schedule, candidate_date, tz)

        if candidate_date == local_now.date() and candidate.end_at < local_now:
            candidate_date = candidate_date + timedelta(days=7)
            candidate = self._build_occurrence(schedule, candidate_date, tz)

        if schedule.semester_start_date and candidate.start_at.date() < schedule.semester_start_date:
            candidate_date = _next_date_for_weekday(schedule.semester_start_date, schedule.day_of_week)
            candidate = self._build_occurrence(schedule, candidate_date, tz)

        if schedule.semester_end_date and candidate.start_at.date() > schedule.semester_end_date:
            return None

        return candidate

    def get_upcoming_occurrences(
        self,
        schedule: WeeklyClassSchedule,
        limit: int,
        now: datetime | None = None,
    ) -> list[ScheduleOccurrence]:
        if limit <= 0:
            return []

        occurrences: list[ScheduleOccurrence] = []
        cursor = now
        for _ in range(limit):
            occurrence = self.get_next_occurrence(schedule, now=cursor)
            if occurrence is None:
                break
            occurrences.append(occurrence)
            cursor = occurrence.end_at + timedelta(seconds=1)
        return occurrences

    def is_expired(self, schedule: WeeklyClassSchedule, now: datetime | None = None) -> bool:
        if schedule.semester_end_date is None:
            return False
        tz = _resolve_timezone(schedule.timezone)
        local_now = _coerce_to_timezone(now, tz)
        return local_now.date() > schedule.semester_end_date

    def _build_occurrence(
        self,
        schedule: WeeklyClassSchedule,
        occurrence_date: date,
        tz: ZoneInfo,
    ) -> ScheduleOccurrence:
        start_at = _combine_local(occurrence_date, schedule.start_time, tz)
        end_at = _combine_local(occurrence_date, schedule.end_time, tz)
        occurrence_key = f"{schedule.id}:{occurrence_date.isoformat()}:{schedule.start_time.strftime('%H:%M')}"
        return ScheduleOccurrence(
            occurrence_key=occurrence_key,
            start_at=start_at,
            end_at=end_at,
        )


def _next_date_for_weekday(start_date: date, day_of_week: int) -> date:
    days_until = (day_of_week - start_date.weekday()) % 7
    return start_date + timedelta(days=days_until)


def _resolve_timezone(value: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(value or DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


def _coerce_to_timezone(value: datetime | None, tz: ZoneInfo) -> datetime:
    if value is None:
        return datetime.now(tz)
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def _combine_local(value: date, clock: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(value, clock).replace(tzinfo=tz)
