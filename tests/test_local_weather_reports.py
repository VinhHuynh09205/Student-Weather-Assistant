from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.api.v1.endpoints.weather import get_weather_service
from app.db.models import LocalWeatherReport, Notification, StudySchedule, User, UserSettings
from app.db.session import async_session, engine
from app.main import app
from app.models.domain import CurrentWeatherReport, HourlyForecastReport, Location, WeatherSnapshot


@pytest.fixture(scope="function")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def clean_local_weather_data():
    async with async_session() as session:
        async with session.begin():
            await session.execute(delete(Notification))
            await session.execute(delete(LocalWeatherReport))
            await session.execute(delete(UserSettings))
            await session.execute(delete(StudySchedule))
            await session.execute(delete(User))
    yield
    async with async_session() as session:
        async with session.begin():
            await session.execute(delete(Notification))
            await session.execute(delete(LocalWeatherReport))
            await session.execute(delete(UserSettings))
            await session.execute(delete(StudySchedule))
            await session.execute(delete(User))
    await engine.dispose()


class CloudyWeatherService:
    async def get_current_weather_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        accuracy_meters: float | None = None,
    ) -> CurrentWeatherReport:
        return CurrentWeatherReport(
            location=_make_location(latitude, longitude, accuracy_meters),
            current=_make_snapshot(datetime.utcnow().replace(microsecond=0), probability=17, code=3),
            provider="openweather",
        )

    async def get_current_weather(self, city: str) -> CurrentWeatherReport:
        return CurrentWeatherReport(
            location=Location(
                city=city,
                country="Vietnam",
                latitude=10.7,
                longitude=106.7,
                timezone="Asia/Ho_Chi_Minh",
            ),
            current=_make_snapshot(datetime.utcnow().replace(microsecond=0), probability=17, code=3),
            provider="openweather",
        )

    async def get_hourly_forecast_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        hours: int = 72,
        accuracy_meters: float | None = None,
    ) -> HourlyForecastReport:
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        return HourlyForecastReport(
            location=_make_location(latitude, longitude, accuracy_meters),
            hourly=[_make_snapshot(now + timedelta(hours=offset), probability=17, code=3) for offset in range(6)],
            provider="openweather",
        )

    async def get_hourly_forecast(self, city: str, hours: int = 72) -> HourlyForecastReport:
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        return HourlyForecastReport(
            location=Location(
                city=city,
                country="Vietnam",
                latitude=10.7,
                longitude=106.7,
                timezone="Asia/Ho_Chi_Minh",
            ),
            hourly=[_make_snapshot(now + timedelta(hours=offset), probability=17, code=3) for offset in range(6)],
            provider="openweather",
        )


@pytest.mark.anyio
async def test_create_and_get_active_local_weather_report():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, "local_report_user")

        create_response = await client.post(
            "/api/v1/weather/local-report",
            headers=_auth_headers(token),
            json=_report_payload(),
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["reported_condition"] == "rain"
        assert created["intensity"] == "moderate"
        assert created["source"] == "user_report"
        assert created["is_active"] is True

        active_response = await client.get(
            "/api/v1/weather/local-report/active",
            headers=_auth_headers(token),
            params={"latitude": 10.708, "longitude": 106.703},
        )
        assert active_response.status_code == 200
        assert active_response.json()["id"] == created["id"]


@pytest.mark.anyio
async def test_expired_local_weather_report_is_not_active():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, "expired_report_user")
        user_id = await _get_user_id("expired_report_user")
        async with async_session() as session:
            async with session.begin():
                session.add(
                    LocalWeatherReport(
                        user_id=user_id,
                        location_name="Campus",
                        latitude=10.708,
                        longitude=106.703,
                        reported_condition="rain",
                        intensity="moderate",
                        source="user_report",
                        is_active=True,
                        created_at=datetime.utcnow() - timedelta(hours=3),
                        updated_at=datetime.utcnow() - timedelta(hours=3),
                        expires_at=datetime.utcnow() - timedelta(minutes=1),
                    )
                )

        active_response = await client.get("/api/v1/weather/local-report/active", headers=_auth_headers(token))
        assert active_response.status_code == 200
        assert active_response.json() is None


@pytest.mark.anyio
async def test_user_cannot_access_other_users_local_weather_report():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token_a = await _register_and_login(client, "local_report_owner")
        token_b = await _register_and_login(client, "local_report_other")

        created = await client.post(
            "/api/v1/weather/local-report",
            headers=_auth_headers(token_a),
            json=_report_payload(),
        )
        assert created.status_code == 200

        other_active = await client.get("/api/v1/weather/local-report/active", headers=_auth_headers(token_b))
        assert other_active.status_code == 200
        assert other_active.json() is None

        other_clear = await client.delete("/api/v1/weather/local-report/active", headers=_auth_headers(token_b))
        assert other_clear.status_code == 200
        assert other_clear.json() == {"cleared": False}

        owner_active = await client.get("/api/v1/weather/local-report/active", headers=_auth_headers(token_a))
        assert owner_active.status_code == 200
        assert owner_active.json()["id"] == created.json()["id"]


@pytest.mark.anyio
async def test_current_weather_uses_user_report_as_effective_condition_without_changing_provider_condition():
    app.dependency_overrides[get_weather_service] = lambda: CloudyWeatherService()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            token = await _register_and_login(client, "current_override_user")
            await client.post("/api/v1/weather/local-report", headers=_auth_headers(token), json=_report_payload())

            response = await client.get(
                "/api/v1/weather/current",
                headers=_auth_headers(token),
                params={"latitude": 10.708, "longitude": 106.703},
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["provider_condition"] == "cloudy"
    assert data["effective_condition"] == "rain"
    assert data["override_source"] == "user_report"
    assert data["provider_weather_description"] == "May den u am"
    assert data["current"]["weather_code"] == 63
    assert data["current"]["weather_code"] not in {95, 96, 99}
    assert data["current"]["weather_description"] == "Đang mưa tại vị trí của bạn"


@pytest.mark.anyio
async def test_student_advice_uses_local_rain_report_without_inventing_thunderstorm():
    app.dependency_overrides[get_weather_service] = lambda: CloudyWeatherService()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            token = await _register_and_login(client, "advice_override_user")
            await client.post("/api/v1/weather/local-report", headers=_auth_headers(token), json=_report_payload())

            now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            response = await client.post(
                "/api/v1/weather/student-advice",
                headers=_auth_headers(token),
                json={
                    "latitude": 10.708,
                    "longitude": 106.703,
                    "study_date": now.date().isoformat(),
                    "start_time": (now + timedelta(hours=1)).time().strftime("%H:%M"),
                    "end_time": (now + timedelta(hours=2)).time().strftime("%H:%M"),
                    "vehicle_type": "motorbike",
                },
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["provider_condition"] == "cloudy"
    assert data["effective_condition"] == "rain"
    assert data["override_source"] == "user_report"
    assert data["weather_code"] in {61, 63, 65}
    assert data["weather_code"] not in {95, 96, 99}
    assert any("xác nhận" in item for item in data["recommendations"])
    assert any("Mưa cục bộ" in item for item in data["warnings"])


async def _register_and_login(client: AsyncClient, username: str) -> str:
    password = "localweather123"
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "confirm_password": password,
            "full_name": "Local Weather Tester",
        },
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password, "remember_me": True},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


async def _get_user_id(username: str):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalars().one()
        return user.id


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _report_payload() -> dict[str, object]:
    return {
        "location_name": "Le Van Luong, Phuoc Kien, Nha Be",
        "latitude": 10.708,
        "longitude": 106.703,
        "reported_condition": "rain",
        "intensity": "moderate",
        "expires_in_minutes": 120,
    }


def _make_location(latitude: float, longitude: float, accuracy_meters: float | None = None) -> Location:
    return Location(
        city="Nha Be",
        country="Vietnam",
        latitude=latitude,
        longitude=longitude,
        timezone="Asia/Ho_Chi_Minh",
        source="coordinates",
        location_name="Le Van Luong, Phuoc Kien, Nha Be",
        display_name="Le Van Luong, Phuoc Kien, Nha Be",
        accuracy_meters=accuracy_meters,
    )


def _make_snapshot(timestamp: datetime, *, probability: int, code: int) -> WeatherSnapshot:
    return WeatherSnapshot(
        time=timestamp.isoformat(timespec="minutes"),
        temperature_c=30.0,
        apparent_temperature_c=35.0,
        relative_humidity_percent=72,
        precipitation_probability_percent=probability,
        precipitation_mm=0.0,
        rain_mm=0.0,
        weather_code=code,
        weather_description="May den u am",
        wind_speed_kmh=8.0,
        uv_index=0.0,
        is_day=False,
        cloud_cover_percent=100,
    )
