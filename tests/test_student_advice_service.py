import asyncio

import pytest

from app.core.exceptions import InvalidWeatherDataError
from app.models.domain import HourlyForecastReport, Location, WeatherSnapshot
from app.schemas.advice import StudentAdviceRequest
from app.services.student_advice_service import StudentAdviceService


class FakeWeatherService:
    def __init__(self, hourly: list[WeatherSnapshot]) -> None:
        self._hourly = hourly
        self.city_calls: list[tuple[str, int]] = []
        self.coordinate_calls: list[tuple[float, float, int]] = []

    async def get_hourly_forecast(self, city: str, hours: int = 24) -> HourlyForecastReport:
        self.city_calls.append((city, hours))
        return HourlyForecastReport(
            location=Location(
                city=city,
                country="Vietnam",
                latitude=10.0333,
                longitude=105.7833,
                timezone="Asia/Ho_Chi_Minh",
            ),
            hourly=self._hourly,
        )

    async def get_hourly_forecast_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        hours: int = 24,
        accuracy_meters: float | None = None,
    ) -> HourlyForecastReport:
        self.coordinate_calls.append((latitude, longitude, hours))
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
            hourly=self._hourly,
        )


def make_snapshot(
    time: str,
    *,
    temperature_c: float = 32.0,
    apparent_temperature_c: float = 34.0,
    humidity: int = 75,
    precipitation_probability: int = 20,
    rain_mm: float = 0.0,
    wind_speed_kmh: float = 12.0,
    uv_index: float = 5.0,
    weather_code: int | None = None,
    is_day: bool | None = True,
) -> WeatherSnapshot:
    resolved_weather_code = weather_code if weather_code is not None else 61 if precipitation_probability >= 50 else 2
    return WeatherSnapshot(
        time=time,
        temperature_c=temperature_c,
        apparent_temperature_c=apparent_temperature_c,
        relative_humidity_percent=humidity,
        precipitation_probability_percent=precipitation_probability,
        precipitation_mm=rain_mm,
        rain_mm=rain_mm,
        weather_code=resolved_weather_code,
        weather_description="Mưa" if precipitation_probability >= 50 else "Có mây",
        wind_speed_kmh=wind_speed_kmh,
        uv_index=uv_index,
        is_day=is_day,
    )


def run_advice(
    hourly: list[WeatherSnapshot],
    *,
    study_date: str = "2026-06-06",
    start_time: str = "07:30",
    end_time: str = "11:00",
    vehicle_type: str = "motorbike",
):
    service = StudentAdviceService(FakeWeatherService(hourly))  # type: ignore[arg-type]
    request = StudentAdviceRequest(
        city="Can Tho",
        study_date=study_date,
        start_time=start_time,
        end_time=end_time,
        vehicle_type=vehicle_type,
    )
    return asyncio.run(service.get_student_advice(request))


def test_student_advice_new_request_returns_timeline() -> None:
    hourly = [
        make_snapshot("2026-06-06T07:00", precipitation_probability=20),
        make_snapshot("2026-06-06T08:00", precipitation_probability=25),
        make_snapshot("2026-06-06T09:00", precipitation_probability=30),
        make_snapshot("2026-06-06T10:00", precipitation_probability=35),
        make_snapshot("2026-06-06T11:00", precipitation_probability=40),
    ]

    advice = run_advice(hourly)

    assert advice.study_date == "2026-06-06"
    assert advice.start_time == "07:30"
    assert advice.end_time == "11:00"
    assert advice.timeline.before_class.time == "07:00"
    assert advice.timeline.during_class.time_range == "07:30 - 11:00"
    assert advice.timeline.after_class.time == "11:00"
    assert len(advice.hourly_forecast) == 4


def test_student_advice_coordinate_request_bypasses_city_forecast() -> None:
    hourly = [
        make_snapshot("2026-06-06T07:00", precipitation_probability=20),
        make_snapshot("2026-06-06T08:00", precipitation_probability=25),
        make_snapshot("2026-06-06T09:00", precipitation_probability=30),
        make_snapshot("2026-06-06T10:00", precipitation_probability=35),
        make_snapshot("2026-06-06T11:00", precipitation_probability=40),
    ]
    weather_service = FakeWeatherService(hourly)
    service = StudentAdviceService(weather_service)  # type: ignore[arg-type]
    request = StudentAdviceRequest(
        latitude=10.3759,
        longitude=106.3439,
        study_date="2026-06-06",
        start_time="07:30",
        end_time="11:00",
        vehicle_type="motorbike",
    )

    advice = asyncio.run(service.get_student_advice(request))

    assert advice.city == "Vị trí hiện tại"
    assert advice.source == "coordinates"
    assert advice.display_name == "Vị trí hiện tại · 10.3759, 106.3439"
    assert advice.latitude == 10.3759
    assert advice.longitude == 106.3439
    assert weather_service.city_calls == []
    assert weather_service.coordinate_calls == [(10.3759, 106.3439, 72)]


def test_student_advice_score_uses_schedule_window() -> None:
    hourly = [
        make_snapshot("2026-06-06T07:00", precipitation_probability=10),
        make_snapshot(
            "2026-06-06T08:00",
            apparent_temperature_c=36.5,
            precipitation_probability=72,
            rain_mm=1.0,
        ),
        make_snapshot(
            "2026-06-06T09:00",
            apparent_temperature_c=35.0,
            precipitation_probability=65,
            rain_mm=1.3,
        ),
        make_snapshot("2026-06-06T12:00", precipitation_probability=10),
    ]

    advice = run_advice(hourly, start_time="07:30", end_time="09:30")

    assert advice.score == 60
    assert advice.level == "Bình thường"
    assert advice.metrics.max_precipitation_probability_percent == 72
    assert advice.metrics.total_rain_mm == 2.3


def test_recommendations_include_after_class_rain_warning() -> None:
    hourly = [
        make_snapshot("2026-06-06T08:00", precipitation_probability=15),
        make_snapshot("2026-06-06T09:00", precipitation_probability=20),
        make_snapshot("2026-06-06T10:00", precipitation_probability=25),
        make_snapshot("2026-06-06T11:00", precipitation_probability=80),
    ]

    advice = run_advice(hourly, start_time="08:00", end_time="10:30")

    assert "Lúc tan học có khả năng mưa, hãy chuẩn bị áo mưa khi về." in advice.recommendations
    assert "Có khả năng mưa lúc tan học." in advice.warnings


def test_recommendations_change_by_vehicle_type() -> None:
    rainy_hourly = [
        make_snapshot("2026-06-06T07:00", precipitation_probability=80),
        make_snapshot("2026-06-06T08:00", precipitation_probability=75),
        make_snapshot("2026-06-06T09:00", precipitation_probability=72),
    ]

    motorbike_advice = run_advice(rainy_hourly, vehicle_type="motorbike")
    bus_advice = run_advice(rainy_hourly, vehicle_type="bus")
    walking_advice = run_advice(rainy_hourly, vehicle_type="walking")
    car_advice = run_advice(rainy_hourly, vehicle_type="car")
    bicycle_advice = run_advice(rainy_hourly, vehicle_type="bicycle")

    assert motorbike_advice.recommendations != bus_advice.recommendations
    assert walking_advice.recommendations != bus_advice.recommendations
    assert car_advice.recommendations != motorbike_advice.recommendations
    assert bicycle_advice.recommendations != motorbike_advice.recommendations
    assert motorbike_advice.vehicle_type == "motorbike"
    assert bus_advice.vehicle_type == "bus"
    assert walking_advice.vehicle_type == "walking"
    assert car_advice.vehicle_type == "car"
    assert bicycle_advice.vehicle_type == "bicycle"
    assert any("xe máy" in item for item in motorbike_advice.recommendations)
    assert any("xe buýt" in item for item in bus_advice.recommendations)
    assert any("Đi bộ" in item for item in walking_advice.recommendations)
    assert any("ô tô" in item for item in car_advice.recommendations)
    assert any("xe đạp" in item for item in bicycle_advice.recommendations)


def test_legacy_walk_vehicle_type_is_normalized_to_walking() -> None:
    rainy_hourly = [
        make_snapshot("2026-06-06T07:00", precipitation_probability=70),
        make_snapshot("2026-06-06T08:00", precipitation_probability=72),
    ]

    advice = run_advice(rainy_hourly, start_time="07:00", end_time="08:00", vehicle_type="walk")

    assert advice.vehicle_type == "walking"
    assert any("Đi bộ" in item for item in advice.recommendations)


def test_hot_schedule_recommends_water_and_sun_protection() -> None:
    hourly = [
        make_snapshot("2026-06-06T08:00", apparent_temperature_c=36.0, uv_index=8.2),
        make_snapshot("2026-06-06T09:00", apparent_temperature_c=35.5, uv_index=8.0),
        make_snapshot("2026-06-06T10:00", apparent_temperature_c=35.2, uv_index=7.8),
    ]

    advice = run_advice(hourly, vehicle_type="walking")

    assert "Nên mang nước uống, nón hoặc áo khoác nhẹ." in advice.recommendations
    assert "Đi bộ nên tránh nắng lâu và mang thêm nước." in advice.recommendations
    assert "Cảm giác nhiệt khá nóng trong buổi học." in advice.warnings


def test_missing_forecast_for_schedule_raises_clear_error() -> None:
    hourly = [
        make_snapshot("2026-06-06T08:00"),
        make_snapshot("2026-06-06T09:00"),
    ]
    service = StudentAdviceService(FakeWeatherService(hourly))  # type: ignore[arg-type]
    request = StudentAdviceRequest(
        city="Can Tho",
        study_date="2026-06-08",
        start_time="07:30",
        end_time="11:00",
        vehicle_type="motorbike",
    )

    with pytest.raises(InvalidWeatherDataError, match="Không có dữ liệu dự báo"):
        asyncio.run(service.get_student_advice(request))
