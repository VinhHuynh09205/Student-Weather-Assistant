from app.models.domain import WeatherSnapshot
from app.services.weather_alert_service import build_weather_alerts


def make_snapshot(
    *,
    weather_code: int = 2,
    precipitation_probability_percent: int | None = 0,
    precipitation_mm: float = 0.0,
    rain_mm: float = 0.0,
    wind_speed_kmh: float = 8.0,
    uv_index: float = 0.0,
    is_day: bool | None = True,
) -> WeatherSnapshot:
    return WeatherSnapshot(
        time="2026-06-06T21:00",
        temperature_c=28.0,
        apparent_temperature_c=31.0,
        relative_humidity_percent=80,
        precipitation_probability_percent=precipitation_probability_percent,
        precipitation_mm=precipitation_mm,
        rain_mm=rain_mm,
        weather_code=weather_code,
        weather_description="Cloudy",
        wind_speed_kmh=wind_speed_kmh,
        uv_index=uv_index,
        is_day=is_day,
    )


def test_weather_alerts_do_not_warn_uv_at_night() -> None:
    alerts = build_weather_alerts(
        current=make_snapshot(uv_index=11.0, is_day=False),
    )

    assert not any("UV" in alert for alert in alerts)


def test_weather_alerts_warn_storm_only_for_storm_codes() -> None:
    rainy_alerts = build_weather_alerts(
        current=make_snapshot(weather_code=61, precipitation_probability_percent=0),
    )
    storm_alerts = build_weather_alerts(
        current=make_snapshot(weather_code=95, precipitation_probability_percent=0),
    )

    assert not any("dong" in alert.lower() for alert in rainy_alerts)
    assert any("dong" in alert.lower() for alert in storm_alerts)


def test_weather_alerts_do_not_warn_rain_for_zero_amount_and_low_probability() -> None:
    alerts = build_weather_alerts(
        current=make_snapshot(
            precipitation_probability_percent=15,
            precipitation_mm=0.0,
            rain_mm=0.0,
        ),
    )

    assert not any("mua" in alert.lower() for alert in alerts)
