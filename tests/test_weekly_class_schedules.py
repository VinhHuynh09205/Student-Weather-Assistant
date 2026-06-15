import uuid
from datetime import date, datetime, time

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.api.v1.endpoints.class_schedules import get_class_schedule_forecast_service
from app.db.models import Notification, User, UserSettings, WeeklyClassSchedule
from app.db.session import async_session, engine
from app.main import app
from app.models.domain import HourlyForecastReport, Location, WeatherSnapshot
from app.services.class_schedule_forecast_service import ClassScheduleForecastService
from app.services.schedule_occurrence_service import ScheduleOccurrenceService


@pytest.fixture(scope="function")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def clean_weekly_schedule_data():
    async with async_session() as session:
        async with session.begin():
            await session.execute(delete(Notification))
            await session.execute(delete(WeeklyClassSchedule))
            await session.execute(delete(UserSettings))
            await session.execute(delete(User))
    yield
    async with async_session() as session:
        async with session.begin():
            await session.execute(delete(Notification))
            await session.execute(delete(WeeklyClassSchedule))
            await session.execute(delete(UserSettings))
            await session.execute(delete(User))
    await engine.dispose()


class FakeWeatherService:
    def __init__(self, snapshots: list[WeatherSnapshot]) -> None:
        self.snapshots = snapshots
        self.coordinate_calls = 0

    async def get_hourly_forecast_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        hours: int = 72,
        accuracy_meters: float | None = None,
    ) -> HourlyForecastReport:
        self.coordinate_calls += 1
        return HourlyForecastReport(
            location=Location(
                city="Campus",
                country="Vietnam",
                latitude=latitude,
                longitude=longitude,
                timezone="Asia/Ho_Chi_Minh",
            ),
            hourly=self.snapshots,
            provider="openweather",
        )

    async def get_hourly_forecast(self, city: str, hours: int = 72) -> HourlyForecastReport:
        return HourlyForecastReport(
            location=Location(
                city=city,
                country="Vietnam",
                latitude=10.0,
                longitude=106.0,
                timezone="Asia/Ho_Chi_Minh",
            ),
            hourly=self.snapshots,
            provider="openweather",
        )


class FailingWeatherService(FakeWeatherService):
    async def get_hourly_forecast_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        hours: int = 72,
        accuracy_meters: float | None = None,
    ) -> HourlyForecastReport:
        self.coordinate_calls += 1
        raise RuntimeError("weather provider failed")

    async def get_hourly_forecast(self, city: str, hours: int = 72) -> HourlyForecastReport:
        raise RuntimeError("geocoding failed")


def make_schedule(**overrides) -> WeeklyClassSchedule:
    values = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "subject_name": "Lap trinh Web",
        "day_of_week": 0,
        "start_time": time(7, 0),
        "end_time": time(9, 30),
        "location_name": "Campus",
        "latitude": 10.3419,
        "longitude": 106.1223,
        "timezone": "Asia/Ho_Chi_Minh",
        "is_active": True,
        "notify_before_minutes": 45,
        "rain_alert_enabled": True,
        "storm_alert_enabled": True,
        "semester_start_date": None,
        "semester_end_date": None,
    }
    values.update(overrides)
    return WeeklyClassSchedule(**values)


def make_snapshot(
    timestamp: str,
    *,
    code: int = 3,
    probability: int = 0,
    rain_mm: float = 0.0,
    wind: float = 8.0,
    apparent: float = 30.0,
) -> WeatherSnapshot:
    return WeatherSnapshot(
        time=timestamp,
        temperature_c=28.0,
        apparent_temperature_c=apparent,
        relative_humidity_percent=80,
        precipitation_probability_percent=probability,
        precipitation_mm=rain_mm,
        rain_mm=rain_mm,
        weather_code=code,
        weather_description="Dong" if code == 95 else "Mua" if code in {61, 63, 65} else "Nhieu may",
        wind_speed_kmh=wind,
        uv_index=0.0,
        is_day=True,
    )


async def register_and_login(client: AsyncClient, username: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "password123",
            "confirm_password": "password123",
            "full_name": username,
        },
    )
    login = await client.post("/api/v1/auth/login", json={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.anyio
async def test_create_weekly_schedule_successfully(clean_weekly_schedule_data):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await register_and_login(client, "weekly_user")
        response = await client.post(
            "/api/v1/class-schedules",
            headers=headers,
            json={
                "subject_name": "Lap trinh Web",
                "day_of_week": 0,
                "start_time": "07:00",
                "end_time": "09:30",
                "location_name": "Campus",
                "latitude": 10.3419,
                "longitude": 106.1223,
                "rain_alert_enabled": True,
                "storm_alert_enabled": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["subject_name"] == "Lap trinh Web"
        assert data["day_of_week"] == 0
        assert data["is_active"] is True


@pytest.mark.anyio
async def test_create_weekly_schedule_with_vietnamese_location_and_coordinates_then_list(clean_weekly_schedule_data):
    location_name = (
        "Đại học Giao thông Vận tải, Lê Văn Việt, Phường Tăng Nhơn Phú, "
        "Thành phố Thủ Đức, Thành phố Hồ Chí Minh, Việt Nam"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await register_and_login(client, "weekly_unicode_user")
        create_response = await client.post(
            "/api/v1/class-schedules",
            headers=headers,
            json={
                "subject_name": "Cấu trúc dữ liệu",
                "day_of_week": 0,
                "start_time": "07:00",
                "end_time": "09:30",
                "location_name": location_name,
                "latitude": 10.8452193,
                "longitude": 106.7939485,
                "notify_before_minutes": 120,
                "rain_alert_enabled": True,
                "storm_alert_enabled": True,
                "is_active": True,
            },
        )
        list_response = await client.get("/api/v1/class-schedules", headers=headers)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"]
    assert created["location_name"] == location_name
    assert created["latitude"] == 10.8452193
    assert created["longitude"] == 106.7939485

    assert list_response.status_code == 200
    schedules = list_response.json()
    assert any(item["id"] == created["id"] and item["location_name"] == location_name for item in schedules)


@pytest.mark.anyio
async def test_delete_weekly_schedule_soft_deactivates_and_hides_from_default_list(clean_weekly_schedule_data):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await register_and_login(client, "weekly_delete_user")
        create_response = await client.post(
            "/api/v1/class-schedules",
            headers=headers,
            json={
                "subject_name": "Trí tuệ nhân tạo",
                "day_of_week": 2,
                "start_time": "12:15",
                "end_time": "14:45",
                "location_name": "Đại học Giao thông Vận tải",
            },
        )
        schedule_id = create_response.json()["id"]

        delete_response = await client.delete(f"/api/v1/class-schedules/{schedule_id}", headers=headers)
        list_response = await client.get("/api/v1/class-schedules", headers=headers)
        include_inactive_response = await client.get("/api/v1/class-schedules?include_inactive=true", headers=headers)

    assert delete_response.status_code == 200
    deleted = delete_response.json()
    assert deleted == {
        "success": True,
        "message": "Đã xóa lịch học",
        "schedule_id": schedule_id,
        "is_active": False,
    }

    assert list_response.status_code == 200
    assert all(item["id"] != schedule_id for item in list_response.json())

    assert include_inactive_response.status_code == 200
    inactive_items = [item for item in include_inactive_response.json() if item["id"] == schedule_id]
    assert len(inactive_items) == 1
    assert inactive_items[0]["is_active"] is False

    async with async_session() as session:
        result = await session.execute(
            select(WeeklyClassSchedule).where(WeeklyClassSchedule.id == uuid.UUID(schedule_id))
        )
        db_schedule = result.scalars().one()
    assert db_schedule.is_active is False


@pytest.mark.anyio
async def test_upcoming_forecasts_ignore_soft_deleted_weekly_schedule(clean_weekly_schedule_data):
    current_weekday = datetime.now().weekday()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await register_and_login(client, "weekly_upcoming_delete_user")
        deleted_schedule_response = await client.post(
            "/api/v1/class-schedules",
            headers=headers,
            json={
                "subject_name": "Lịch sẽ xóa",
                "day_of_week": current_weekday,
                "start_time": "07:00",
                "end_time": "09:00",
                "location_name": "Campus A",
            },
        )
        active_schedule_response = await client.post(
            "/api/v1/class-schedules",
            headers=headers,
            json={
                "subject_name": "Lịch còn lại",
                "day_of_week": current_weekday,
                "start_time": "10:00",
                "end_time": "12:00",
                "location_name": "Campus B",
            },
        )
        deleted_schedule_id = deleted_schedule_response.json()["id"]
        active_schedule_id = active_schedule_response.json()["id"]
        await client.delete(f"/api/v1/class-schedules/{deleted_schedule_id}", headers=headers)

        app.dependency_overrides[get_class_schedule_forecast_service] = lambda: ClassScheduleForecastService(
            FakeWeatherService([make_snapshot(datetime.now().strftime("%Y-%m-%dT10:00"), code=3)])
        )
        try:
            forecast_response = await client.get("/api/v1/class-schedules/upcoming-forecasts?limit=10", headers=headers)
        finally:
            app.dependency_overrides.pop(get_class_schedule_forecast_service, None)

    assert forecast_response.status_code == 200
    forecast_schedule_ids = {item["schedule"]["id"] for item in forecast_response.json()}
    assert deleted_schedule_id not in forecast_schedule_ids
    assert active_schedule_id in forecast_schedule_ids


@pytest.mark.anyio
async def test_create_weekly_schedule_with_manual_location_without_coordinates(clean_weekly_schedule_data):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await register_and_login(client, "weekly_manual_location_user")
        response = await client.post(
            "/api/v1/class-schedules",
            headers=headers,
            json={
                "subject_name": "Nhap mon AI",
                "day_of_week": 2,
                "start_time": "13:00",
                "end_time": "15:00",
                "location_name": "Phong B1, co so tam thoi",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["location_name"] == "Phong B1, co so tam thoi"
    assert data["latitude"] is None
    assert data["longitude"] is None


@pytest.mark.anyio
async def test_reject_invalid_day_of_week(clean_weekly_schedule_data):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await register_and_login(client, "invalid_day_user")
        response = await client.post(
            "/api/v1/class-schedules",
            headers=headers,
            json={
                "subject_name": "Lap trinh Web",
                "day_of_week": 8,
                "start_time": "07:00",
                "end_time": "09:30",
            },
        )

        assert response.status_code == 422


@pytest.mark.anyio
async def test_reject_start_time_after_or_equal_end_time(clean_weekly_schedule_data):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await register_and_login(client, "invalid_time_user")
        response = await client.post(
            "/api/v1/class-schedules",
            headers=headers,
            json={
                "subject_name": "Lap trinh Web",
                "day_of_week": 0,
                "start_time": "09:30",
                "end_time": "09:30",
            },
        )

        assert response.status_code == 422


def test_next_occurrence_uses_today_when_class_has_not_ended():
    service = ScheduleOccurrenceService()
    schedule = make_schedule(day_of_week=0)
    now = datetime(2026, 6, 15, 6, 30)

    occurrence = service.get_next_occurrence(schedule, now=now)

    assert occurrence is not None
    assert occurrence.start_at.date() == date(2026, 6, 15)


def test_next_occurrence_moves_to_next_week_after_end_time():
    service = ScheduleOccurrenceService()
    schedule = make_schedule(day_of_week=0)
    now = datetime(2026, 6, 15, 10, 0)

    occurrence = service.get_next_occurrence(schedule, now=now)

    assert occurrence is not None
    assert occurrence.start_at.date() == date(2026, 6, 22)


def test_next_occurrence_moves_to_next_week_when_this_weekday_passed():
    service = ScheduleOccurrenceService()
    schedule = make_schedule(day_of_week=0)
    now = datetime(2026, 6, 16, 8, 0)

    occurrence = service.get_next_occurrence(schedule, now=now)

    assert occurrence is not None
    assert occurrence.start_at.date() == date(2026, 6, 22)


def test_next_occurrence_none_when_semester_ended():
    service = ScheduleOccurrenceService()
    schedule = make_schedule(day_of_week=0, semester_end_date=date(2026, 6, 14))
    now = datetime(2026, 6, 15, 6, 0)

    assert service.get_next_occurrence(schedule, now=now) is None


@pytest.mark.anyio
async def test_forecast_available_when_occurrence_is_in_supported_range():
    schedule = make_schedule(day_of_week=0)
    now = datetime(2026, 6, 15, 6, 0)
    weather = FakeWeatherService([make_snapshot("2026-06-15T07:00", code=61, probability=80, rain_mm=1.0)])
    service = ClassScheduleForecastService(weather)  # type: ignore[arg-type]

    result = await service.get_forecast_for_next_occurrence(schedule, now=now)

    assert result.forecast_status == "available"
    assert result.risk_level == "PREPARE"
    assert weather.coordinate_calls == 1


@pytest.mark.anyio
async def test_weekly_forecast_recommendation_keeps_vietnamese_accents():
    schedule = make_schedule(
        subject_name="Trí tuệ nhân tạo",
        day_of_week=2,
        start_time=time(12, 15),
        end_time=time(14, 45),
    )
    now = datetime(2026, 6, 15, 6, 0)
    weather = FakeWeatherService([make_snapshot("2026-06-17T12:15", code=61, probability=80, rain_mm=1.0)])
    service = ClassScheduleForecastService(weather)  # type: ignore[arg-type]

    result = await service.get_forecast_for_next_occurrence(schedule, now=now)

    assert result.recommendation_message == (
        "Buổi học Trí tuệ nhân tạo lúc 12:15 Thứ 4 có khả năng mưa hoặc thời tiết xấu. "
        "Nên chuẩn bị áo mưa và đi sớm."
    )
    assert "Buoi hoc" not in result.recommendation_message
    assert "Tri tue" not in result.recommendation_message
    assert "Thu 4" not in result.recommendation_message


@pytest.mark.anyio
async def test_forecast_pending_when_occurrence_is_outside_supported_range():
    schedule = make_schedule(day_of_week=0)
    now = datetime(2026, 6, 16, 6, 0)
    weather = FakeWeatherService([make_snapshot("2026-06-16T07:00", code=61, probability=90, rain_mm=2.0)])
    service = ClassScheduleForecastService(weather)  # type: ignore[arg-type]

    result = await service.get_forecast_for_next_occurrence(schedule, now=now)

    assert result.forecast_status == "pending"
    assert weather.coordinate_calls == 0


@pytest.mark.anyio
async def test_forecast_error_does_not_raise_and_prefers_coordinates():
    schedule = make_schedule(day_of_week=0, latitude=10.8452193, longitude=106.7939485)
    now = datetime(2026, 6, 15, 6, 0)
    weather = FailingWeatherService([])
    service = ClassScheduleForecastService(weather)  # type: ignore[arg-type]

    result = await service.get_forecast_for_next_occurrence(schedule, now=now)

    assert result.forecast_status == "error"
    assert result.schedule is schedule
    assert result.next_occurrence is not None
    assert result.risk_level == "SAFE"
    assert weather.coordinate_calls == 1


@pytest.mark.anyio
async def test_upcoming_forecasts_keep_schedule_when_weather_service_fails():
    schedule = make_schedule(day_of_week=0, latitude=10.8452193, longitude=106.7939485)
    now = datetime(2026, 6, 15, 6, 0)
    weather = FailingWeatherService([])
    service = ClassScheduleForecastService(weather)  # type: ignore[arg-type]

    results = await service.get_upcoming_forecasts([schedule], limit=5, now=now)

    assert len(results) == 1
    assert results[0].schedule is schedule
    assert results[0].forecast_status == "error"


@pytest.mark.anyio
async def test_thunderstorm_risk_only_uses_real_thunderstorm_code():
    schedule = make_schedule(day_of_week=0)
    now = datetime(2026, 6, 15, 6, 0)
    rainy_weather = FakeWeatherService([make_snapshot("2026-06-15T07:00", code=65, probability=95, rain_mm=4.0)])
    storm_weather = FakeWeatherService([make_snapshot("2026-06-15T07:00", code=95, probability=70, rain_mm=1.0)])

    rainy = await ClassScheduleForecastService(rainy_weather).get_forecast_for_next_occurrence(schedule, now=now)  # type: ignore[arg-type]
    storm = await ClassScheduleForecastService(storm_weather).get_forecast_for_next_occurrence(schedule, now=now)  # type: ignore[arg-type]

    assert rainy.weather_code == 65
    assert rainy.risk_level == "PREPARE"
    assert storm.weather_code == 95
    assert storm.risk_level == "DANGER"


@pytest.mark.anyio
async def test_weekly_class_notification_is_not_duplicated(clean_weekly_schedule_data):
    schedule = make_schedule(day_of_week=0)
    now = datetime(2026, 6, 15, 6, 0)
    weather = FakeWeatherService([make_snapshot("2026-06-15T07:00", code=61, probability=80, rain_mm=1.0)])
    service = ClassScheduleForecastService(weather)  # type: ignore[arg-type]

    async with async_session() as session:
        user = User(username="notif_weekly", normalized_username="notif_weekly", full_name="Notif Weekly")
        session.add(user)
        await session.flush()
        session.add(UserSettings(user_id=user.id, notification_enabled=True))
        schedule.user_id = user.id
        session.add(schedule)
        await session.commit()
        await session.refresh(schedule)
        await session.refresh(user)

        forecast = await service.get_forecast_for_next_occurrence(schedule, now=now)
        first = await service.ensure_forecast_notification(session, user, forecast, now=now)
        second = await service.ensure_forecast_notification(session, user, forecast, now=now)

        assert forecast.next_occurrence is not None
        notifications = (
            await session.execute(
                select(Notification).where(Notification.occurrence_key == forecast.next_occurrence.occurrence_key)
            )
        ).scalars().all()

    assert first == 2
    assert second == 0
    assert len(notifications) == 2


@pytest.mark.anyio
async def test_user_cannot_update_or_delete_other_users_schedule(clean_weekly_schedule_data):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner_headers = await register_and_login(client, "owner_weekly")
        other_headers = await register_and_login(client, "other_weekly")
        create_response = await client.post(
            "/api/v1/class-schedules",
            headers=owner_headers,
            json={
                "subject_name": "Lap trinh Web",
                "day_of_week": 0,
                "start_time": "07:00",
                "end_time": "09:30",
            },
        )
        schedule_id = create_response.json()["id"]

        patch_response = await client.patch(
            f"/api/v1/class-schedules/{schedule_id}",
            headers=other_headers,
            json={"subject_name": "Hack"},
        )
        delete_response = await client.delete(f"/api/v1/class-schedules/{schedule_id}", headers=other_headers)

    assert patch_response.status_code == 404
    assert delete_response.status_code == 404
