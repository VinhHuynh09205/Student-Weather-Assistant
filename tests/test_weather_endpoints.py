from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.weather import get_weather_service
from app.core.exceptions import CityNotFoundError, WeatherProviderError
from app.main import app
from app.models.domain import (
    CurrentWeatherReport,
    DailyForecast,
    DailyForecastReport,
    HourlyForecastReport,
    Location,
    WeatherSnapshot,
)


class FakeWeatherService:
    def __init__(self) -> None:
        self.current_city_calls: list[str] = []
        self.current_coordinate_calls: list[tuple[float, float]] = []
        self.city_forecast_calls: list[tuple[str, int]] = []
        self.coordinate_forecast_calls: list[tuple[float, float, int]] = []
        self.daily_city_calls: list[tuple[str, int]] = []
        self.daily_coordinate_calls: list[tuple[float, float, int]] = []

    async def get_current_weather(self, city: str) -> CurrentWeatherReport:
        self.current_city_calls.append(city)
        return CurrentWeatherReport(location=make_location(city), current=make_snapshot("2026-06-05T10:00"))

    async def get_current_weather_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        accuracy_meters: float | None = None,
    ) -> CurrentWeatherReport:
        self.current_coordinate_calls.append((latitude, longitude))
        return CurrentWeatherReport(
            location=Location(
                city="Vị trí hiện tại",
                country="Unknown",
                latitude=latitude,
                longitude=longitude,
                timezone="auto",
                source="coordinates",
                location_name="Vị trí hiện tại",
                display_name=f"Vị trí hiện tại · {latitude:.4f}, {longitude:.4f}",
                accuracy_meters=accuracy_meters,
            ),
            current=make_snapshot("2026-06-05T10:00"),
        )

    async def get_hourly_forecast(self, city: str, hours: int = 24) -> HourlyForecastReport:
        self.city_forecast_calls.append((city, hours))
        start_time = datetime(2026, 6, 5, 10)
        hourly = [make_snapshot(format_hour(start_time, index)) for index in range(hours)]
        return HourlyForecastReport(location=make_location(city), hourly=hourly)

    async def get_hourly_forecast_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        hours: int = 24,
        accuracy_meters: float | None = None,
    ) -> HourlyForecastReport:
        self.coordinate_forecast_calls.append((latitude, longitude, hours))
        start_time = datetime(2026, 6, 5, 10)
        hourly = [make_snapshot(format_hour(start_time, index)) for index in range(hours)]
        return HourlyForecastReport(
            location=Location(
                city="Vị trí hiện tại",
                country="Unknown",
                latitude=latitude,
                longitude=longitude,
                timezone="auto",
                source="coordinates",
                location_name="Vị trí hiện tại",
                display_name=f"Vị trí hiện tại · {latitude:.4f}, {longitude:.4f}",
                accuracy_meters=accuracy_meters,
            ),
            hourly=hourly,
        )

    async def get_daily_forecast(self, city: str, days: int = 7) -> DailyForecastReport:
        self.daily_city_calls.append((city, days))
        return DailyForecastReport(
            location=make_location(city),
            daily=[make_daily_forecast(index) for index in range(days)],
        )

    async def get_daily_forecast_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        days: int = 7,
        accuracy_meters: float | None = None,
    ) -> DailyForecastReport:
        self.daily_coordinate_calls.append((latitude, longitude, days))
        return DailyForecastReport(
            location=Location(
                city="Vị trí hiện tại",
                country="Unknown",
                latitude=latitude,
                longitude=longitude,
                timezone="auto",
                source="coordinates",
                location_name="Vị trí hiện tại",
                display_name=f"Vị trí hiện tại · {latitude:.4f}, {longitude:.4f}",
                accuracy_meters=accuracy_meters,
            ),
            daily=[make_daily_forecast(index) for index in range(days)],
        )


class CityNotFoundWeatherService(FakeWeatherService):
    async def get_current_weather(self, city: str) -> CurrentWeatherReport:
        raise CityNotFoundError(f"Không tìm thấy thành phố: {city}")


class TimeoutWeatherService(FakeWeatherService):
    async def get_current_weather(self, city: str) -> CurrentWeatherReport:
        raise WeatherProviderError("Open-Meteo timeout.")


class RateLimitedWeatherService(FakeWeatherService):
    async def get_current_weather(self, city: str) -> CurrentWeatherReport:
        raise WeatherProviderError(
            "Open-Meteo returned HTTP 429.",
            public_message="Dịch vụ thời tiết đang bị giới hạn tạm thời. Vui lòng thử lại sau ít phút.",
            status_code=503,
        )


def format_hour(start_time: datetime, offset_hours: int) -> str:
    return (start_time + timedelta(hours=offset_hours)).strftime("%Y-%m-%dT%H:%M")


def make_location(city: str = "Can Tho") -> Location:
    return Location(
        city=city,
        country="Vietnam",
        latitude=10.0333,
        longitude=105.7833,
        timezone="Asia/Ho_Chi_Minh",
    )


def make_snapshot(time: str) -> WeatherSnapshot:
    forecast_hour = int(time[11:13])
    return WeatherSnapshot(
        time=time,
        temperature_c=31.2,
        apparent_temperature_c=35.0,
        relative_humidity_percent=72,
        precipitation_probability_percent=65,
        precipitation_mm=0.2,
        rain_mm=0.1,
        weather_code=3,
        weather_description="Nhiều mây",
        wind_speed_kmh=12.5,
        uv_index=6.2,
        is_day=6 <= forecast_hour < 18,
    )


def make_daily_forecast(offset_days: int = 0) -> DailyForecast:
    date = (datetime(2026, 6, 5) + timedelta(days=offset_days)).date().isoformat()
    return DailyForecast(
        date=date,
        weather_code=3,
        weather_description="Nhiều mây",
        temperature_max_c=33.0,
        temperature_min_c=25.0,
        precipitation_probability_max_percent=65,
        rain_sum_mm=2.5,
        wind_speed_max_kmh=20.0,
        uv_index_max=7.0,
        sunrise=f"{date}T05:30",
        sunset=f"{date}T18:10",
    )


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "student-weather-assistant"}


def test_current_weather_endpoint_uses_mocked_service() -> None:
    app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    client = TestClient(app)

    try:
        response = client.get("/api/v1/weather/current", params={"city": "Can Tho"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Can Tho"
    assert data["country"] == "Vietnam"
    assert data["current"]["is_day"] is True
    assert data["current"]["weather_description"] == "Nhiều mây"


def test_current_weather_endpoint_accepts_coordinates_without_geocoding() -> None:
    weather_service = FakeWeatherService()
    app.dependency_overrides[get_weather_service] = lambda: weather_service
    client = TestClient(app)

    try:
        response = client.get(
            "/api/v1/weather/current",
            params={"latitude": 10.3759, "longitude": 106.3439},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Vị trí hiện tại"
    assert data["source"] == "coordinates"
    assert data["location_name"] == "Vị trí hiện tại"
    assert data["display_name"] == "Vị trí hiện tại · 10.3759, 106.3439"
    assert data["latitude"] == 10.3759
    assert data["longitude"] == 106.3439
    assert data["current"]["time"] == "2026-06-05T10:00"
    assert weather_service.current_city_calls == []
    assert weather_service.current_coordinate_calls == [(10.3759, 106.3439)]


@pytest.mark.parametrize(
    "city",
    [
        "bà rịa vũng tàu",
        "ba ria vung tau",
        "brvt",
        "đà nẵng",
        "da nang",
        "cần thơ",
        "can tho",
    ],
)
def test_current_weather_endpoint_accepts_vietnam_location_aliases(city: str) -> None:
    app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    client = TestClient(app)

    try:
        response = client.get("/api/v1/weather/current", params={"city": city})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["city"] == city


def test_hourly_weather_endpoint_uses_mocked_service() -> None:
    app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    client = TestClient(app)

    try:
        response = client.get("/api/v1/weather/hourly", params={"city": "Can Tho", "hours": 12})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Can Tho"
    assert len(data["hourly"]) == 12
    assert data["hourly"][0]["precipitation_probability_percent"] == 65
    assert data["hourly"][0]["is_day"] is True


def test_hourly_weather_endpoint_accepts_ba_ria_vung_tau_alias() -> None:
    app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    client = TestClient(app)

    try:
        response = client.get(
            "/api/v1/weather/hourly",
            params={"city": "ba ria vung tau", "hours": 24},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()["hourly"]) == 24


def test_hourly_weather_endpoint_accepts_coordinates_without_geocoding() -> None:
    weather_service = FakeWeatherService()
    app.dependency_overrides[get_weather_service] = lambda: weather_service
    client = TestClient(app)

    try:
        response = client.get(
            "/api/v1/weather/hourly",
            params={"latitude": 10.3759, "longitude": 106.3439, "hours": 24},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Vị trí hiện tại"
    assert data["source"] == "coordinates"
    assert data["display_name"] == "Vị trí hiện tại · 10.3759, 106.3439"
    assert data["latitude"] == 10.3759
    assert data["longitude"] == 106.3439
    assert len(data["hourly"]) == 24
    assert weather_service.city_forecast_calls == []
    assert weather_service.coordinate_forecast_calls == [(10.3759, 106.3439, 24)]


def test_daily_weather_endpoint_accepts_city() -> None:
    weather_service = FakeWeatherService()
    app.dependency_overrides[get_weather_service] = lambda: weather_service
    client = TestClient(app)

    try:
        response = client.get(
            "/api/v1/weather/daily",
            params={"city": "Can Tho", "days": 7},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Can Tho"
    assert len(data["daily"]) == 7
    assert data["daily"][0]["date"] == "2026-06-05"
    assert data["daily"][0]["temperature_max_c"] == 33.0
    assert weather_service.daily_city_calls == [("Can Tho", 7)]


def test_daily_weather_endpoint_accepts_coordinates_without_geocoding() -> None:
    weather_service = FakeWeatherService()
    app.dependency_overrides[get_weather_service] = lambda: weather_service
    client = TestClient(app)

    try:
        response = client.get(
            "/api/v1/weather/daily",
            params={"latitude": 10.3759, "longitude": 106.3439, "days": 3},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Vị trí hiện tại"
    assert data["source"] == "coordinates"
    assert len(data["daily"]) == 3
    assert weather_service.daily_city_calls == []
    assert weather_service.daily_coordinate_calls == [(10.3759, 106.3439, 3)]


def test_weather_endpoints_reject_missing_location_source() -> None:
    client = TestClient(app)

    for path in (
        "/api/v1/weather/current",
        "/api/v1/weather/hourly",
        "/api/v1/weather/daily",
    ):
        response = client.get(path)

        assert response.status_code == 422


def test_weather_endpoints_reject_partial_coordinates() -> None:
    client = TestClient(app)

    for path in (
        "/api/v1/weather/current",
        "/api/v1/weather/hourly",
        "/api/v1/weather/daily",
    ):
        response = client.get(path, params={"latitude": 10.3759})

        assert response.status_code == 422


def test_student_advice_endpoint_has_dynamic_background_fields() -> None:
    app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/weather/student-advice",
            json={
                "city": "Can Tho",
                "study_date": "2026-06-05",
                "start_time": "10:00",
                "end_time": "12:00",
                "vehicle_type": "motorbike",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["study_date"] == "2026-06-05"
    assert data["start_time"] == "10:00"
    assert data["end_time"] == "12:00"
    assert {"before_class", "during_class", "after_class"}.issubset(data["timeline"])
    assert {
        "weather_code",
        "weather_description",
        "is_day",
        "time",
        "wind_speed_kmh",
        "precipitation_probability_percent",
        "temperature_c",
    }.issubset(data)
    hourly_item = data["hourly_forecast"][0]
    assert {
        "weather_code",
        "weather_description",
        "is_day",
        "time",
        "wind_speed_kmh",
        "precipitation_probability_percent",
        "temperature_c",
    }.issubset(hourly_item)


def test_student_advice_endpoint_accepts_coordinates_without_city() -> None:
    weather_service = FakeWeatherService()
    app.dependency_overrides[get_weather_service] = lambda: weather_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/weather/student-advice",
            json={
                "latitude": 10.3759,
                "longitude": 106.3439,
                "study_date": "2026-06-05",
                "start_time": "10:00",
                "end_time": "12:00",
                "vehicle_type": "motorbike",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Vị trí hiện tại"
    assert data["location_name"] == "Vị trí hiện tại"
    assert data["source"] == "coordinates"
    assert data["display_name"] == "Vị trí hiện tại · 10.3759, 106.3439"
    assert data["country"] == "Unknown"
    assert data["latitude"] == 10.3759
    assert data["longitude"] == 106.3439
    assert weather_service.city_forecast_calls == []
    assert weather_service.coordinate_forecast_calls == [(10.3759, 106.3439, 72)]


def test_student_advice_endpoint_accepts_brvt_alias() -> None:
    app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/weather/student-advice",
            json={
                "city": "brvt",
                "study_date": "2026-06-05",
                "start_time": "10:00",
                "end_time": "12:00",
                "vehicle_type": "motorbike",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["city"] == "brvt"


def test_student_advice_endpoint_preserves_car_vehicle_type() -> None:
    app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/weather/student-advice",
            json={
                "city": "Can Tho",
                "study_date": "2026-06-05",
                "start_time": "10:00",
                "end_time": "12:00",
                "vehicle_type": "car",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["vehicle_type"] == "car"
    assert any("ô tô" in item for item in data["recommendations"])


def test_student_advice_endpoint_rejects_invalid_time_range() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/weather/student-advice",
        json={
            "city": "Can Tho",
            "study_date": "2026-06-05",
            "start_time": "11:00",
            "end_time": "10:00",
            "vehicle_type": "motorbike",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"latitude": 10.3759},
        {"longitude": 106.3439},
    ],
)
def test_student_advice_endpoint_rejects_partial_coordinates(payload: dict[str, float]) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/weather/student-advice",
        json={
            **payload,
            "study_date": "2026-06-05",
            "start_time": "10:00",
            "end_time": "12:00",
            "vehicle_type": "motorbike",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("latitude", 91),
        ("latitude", -91),
        ("longitude", 181),
        ("longitude", -181),
    ],
)
def test_student_advice_endpoint_rejects_out_of_range_coordinates(field_name: str, value: float) -> None:
    client = TestClient(app)
    payload = {
        "latitude": 10.3759,
        "longitude": 106.3439,
        "study_date": "2026-06-05",
        "start_time": "10:00",
        "end_time": "12:00",
        "vehicle_type": "motorbike",
    }
    payload[field_name] = value

    response = client.post("/api/v1/weather/student-advice", json=payload)

    assert response.status_code == 422


def test_student_advice_endpoint_rejects_missing_location_source() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/weather/student-advice",
        json={
            "study_date": "2026-06-05",
            "start_time": "10:00",
            "end_time": "12:00",
            "vehicle_type": "motorbike",
        },
    )

    assert response.status_code == 422


def test_student_advice_endpoint_rejects_invalid_study_date_format() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/weather/student-advice",
        json={
            "city": "Can Tho",
            "study_date": "06/05/2026",
            "start_time": "10:00",
            "end_time": "12:00",
            "vehicle_type": "motorbike",
        },
    )

    assert response.status_code == 422


def test_student_advice_endpoint_returns_clear_error_when_forecast_is_missing() -> None:
    app.dependency_overrides[get_weather_service] = lambda: FakeWeatherService()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/weather/student-advice",
            json={
                "city": "Can Tho",
                "study_date": "2030-01-01",
                "start_time": "10:00",
                "end_time": "12:00",
                "vehicle_type": "motorbike",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "detail" in response.json()


def test_city_not_found_returns_404_without_crashing() -> None:
    app.dependency_overrides[get_weather_service] = lambda: CityNotFoundWeatherService()
    client = TestClient(app)

    try:
        response = client.get("/api/v1/weather/current", params={"city": "Unknown"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "detail" in response.json()


def test_unknown_vietnam_location_returns_404_without_crashing() -> None:
    app.dependency_overrides[get_weather_service] = lambda: CityNotFoundWeatherService()
    client = TestClient(app)

    try:
        response = client.get(
            "/api/v1/weather/current",
            params={"city": "abcxyz123notacity"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "detail" in response.json()


def test_open_meteo_timeout_returns_502_without_crashing() -> None:
    app.dependency_overrides[get_weather_service] = lambda: TimeoutWeatherService()
    client = TestClient(app)

    try:
        response = client.get("/api/v1/weather/current", params={"city": "Can Tho"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "Open-Meteo timeout."}


def test_open_meteo_429_returns_friendly_message_without_raw_error() -> None:
    app.dependency_overrides[get_weather_service] = lambda: RateLimitedWeatherService()
    client = TestClient(app)

    try:
        response = client.get("/api/v1/weather/current", params={"city": "Can Tho"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Dịch vụ thời tiết đang bị giới hạn tạm thời. Vui lòng thử lại sau ít phút."}
    assert "Open-Meteo returned HTTP 429" not in response.text


def test_invalid_hours_request_returns_422() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/weather/hourly",
        params={"city": "Can Tho", "hours": 5},
    )

    assert response.status_code == 422


def test_cors_allows_local_react_origins() -> None:
    client = TestClient(app)

    for origin in ("http://localhost:5173", "http://localhost:3000"):
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_student_advice_endpoint_rejects_invalid_vehicle_type() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/weather/student-advice",
        json={
            "city": "Can Tho",
            "study_date": "2026-06-05",
            "start_time": "10:00",
            "end_time": "12:00",
            "vehicle_type": "rocket",
        },
    )

    assert response.status_code == 422
