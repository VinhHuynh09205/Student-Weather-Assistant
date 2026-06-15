from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import WeatherProviderError
from app.models.domain import (
    CurrentWeatherReport,
    DailyForecast,
    DailyForecastReport,
    HourlyForecastReport,
    Location,
    WeatherSnapshot,
)
from app.providers.weather.base import BaseWeatherProvider


class OpenWeatherProvider(BaseWeatherProvider):
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openweather_api_key
        self._base_url = settings.openweather_base_url
        self._timeout = settings.http_timeout_seconds

    @property
    def name(self) -> str:
        return "openweather"

    async def get_current_weather(self, location: Location) -> CurrentWeatherReport:
        if not self._api_key or self._api_key == "your_key_here":
            raise WeatherProviderError(
                "OpenWeather API key is not configured.",
                public_message="Cấu hình OpenWeather API key bị thiếu.",
                status_code=500,
            )

        url = f"{self._base_url}/data/2.5/weather"
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "units": "metric",
            "lang": "vi",
            "appid": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                if response.status_code == 429:
                    raise WeatherProviderError(
                        "OpenWeather returned HTTP 429.",
                        public_message="Dịch vụ thời tiết đang bị giới hạn tạm thời. Vui lòng thử lại sau ít phút.",
                        status_code=503,
                    )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise WeatherProviderError(f"Cannot connect to OpenWeather: {exc}") from exc

        return CurrentWeatherReport(
            location=location,
            current=self._parse_current(data, location.timezone),
            provider=self.name,
        )

    async def get_hourly_forecast(self, location: Location, hours: int) -> HourlyForecastReport:
        if not self._api_key or self._api_key == "your_key_here":
            raise WeatherProviderError("OpenWeather API key is not configured.")

        url = f"{self._base_url}/data/2.5/forecast"
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "units": "metric",
            "lang": "vi",
            "appid": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise WeatherProviderError(f"Cannot connect to OpenWeather: {exc}") from exc

        hourly_items = self._parse_hourly(data, limit=hours, timezone_str=location.timezone)
        return HourlyForecastReport(
            location=location,
            hourly=hourly_items,
            provider=self.name,
        )

    async def get_daily_forecast(self, location: Location, days: int) -> DailyForecastReport:
        if not self._api_key or self._api_key == "your_key_here":
            raise WeatherProviderError("OpenWeather API key is not configured.")

        url = f"{self._base_url}/data/2.5/forecast"
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "units": "metric",
            "lang": "vi",
            "appid": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise WeatherProviderError(f"Cannot connect to OpenWeather: {exc}") from exc

        daily_items = self._parse_daily(data, limit=days, timezone_str=location.timezone)
        return DailyForecastReport(
            location=location,
            daily=daily_items,
            provider=self.name,
        )

    def _parse_current(self, data: dict[str, Any], timezone_str: str) -> WeatherSnapshot:
        main = data.get("main", {})
        wind = data.get("wind", {})
        weather_list = data.get("weather", [])
        weather = weather_list[0] if weather_list else {}
        sys = data.get("sys", {})

        dt = data.get("dt", 0)
        sunrise = sys.get("sunrise", 0)
        sunset = sys.get("sunset", 0)
        is_day = sunrise <= dt <= sunset if sunrise and sunset else True

        rain = data.get("rain", {})
        rain_mm = rain.get("1h") or rain.get("3h") or 0.0

        snow = data.get("snow", {})
        showers_mm = snow.get("1h") or snow.get("3h") or 0.0

        owm_code = weather.get("id", 800)
        wmo_code = _map_owm_code_to_wmo(owm_code)

        return WeatherSnapshot(
            time=_format_unix_timestamp(dt, timezone_str),
            temperature_c=float(main.get("temp", 0.0)),
            apparent_temperature_c=float(main.get("feels_like", 0.0)),
            relative_humidity_percent=int(main.get("humidity", 0)),
            precipitation_probability_percent=None,
            precipitation_mm=rain_mm + showers_mm,
            rain_mm=float(rain_mm),
            weather_code=wmo_code,
            weather_description=weather.get("description", "Không rõ").capitalize(),
            wind_speed_kmh=float(wind.get("speed", 0.0)) * 3.6,  # Convert m/s to km/h
            uv_index=0.0,  # Not available in 2.5 weather endpoint
            is_day=is_day,
            showers_mm=float(showers_mm),
            wind_direction_degrees=wind.get("deg"),
            pressure_hpa=float(main.get("pressure", 1013.0)),
            visibility_meters=float(data.get("visibility", 10000.0)),
            cloud_cover_percent=data.get("clouds", {}).get("all", 0),
        )

    def _parse_hourly(self, data: dict[str, Any], limit: int, timezone_str: str) -> list[WeatherSnapshot]:
        forecast_list = data.get("list", [])
        hourly = []

        # We take first 8-12 items to cover 24-36 hours (since they are in 3h chunks)
        # Slicing up to the limit
        for item in forecast_list[:limit]:
            main = item.get("main", {})
            wind = item.get("wind", {})
            weather_list = item.get("weather", [])
            weather = weather_list[0] if weather_list else {}
            sys = item.get("sys", {})

            dt = item.get("dt", 0)
            is_day = sys.get("pod") == "d"

            rain = item.get("rain", {})
            rain_mm = rain.get("3h") or 0.0

            snow = item.get("snow", {})
            showers_mm = snow.get("3h") or 0.0

            owm_code = weather.get("id", 800)
            wmo_code = _map_owm_code_to_wmo(owm_code)

            hourly.append(
                WeatherSnapshot(
                    time=_format_unix_timestamp(dt, timezone_str),
                    temperature_c=float(main.get("temp", 0.0)),
                    apparent_temperature_c=float(main.get("feels_like", 0.0)),
                    relative_humidity_percent=int(main.get("humidity", 0)),
                    precipitation_probability_percent=int(float(item.get("pop", 0.0)) * 100),
                    precipitation_mm=(rain_mm + showers_mm) / 3.0,  # Average per hour
                    rain_mm=float(rain_mm) / 3.0,
                    weather_code=wmo_code,
                    weather_description=weather.get("description", "Không rõ").capitalize(),
                    wind_speed_kmh=float(wind.get("speed", 0.0)) * 3.6,
                    uv_index=0.0,  # Not available
                    is_day=is_day,
                )
            )
        return hourly

    def _parse_daily(self, data: dict[str, Any], limit: int, timezone_str: str) -> list[DailyForecast]:
        forecast_list = data.get("list", [])
        by_date: dict[str, list[dict[str, Any]]] = {}

        for item in forecast_list:
            dt = item.get("dt", 0)
            local_time = _format_unix_timestamp(dt, timezone_str)
            local_date = local_time.split("T")[0]
            by_date.setdefault(local_date, []).append(item)

        daily = []
        # Sort and take required days
        for local_date in sorted(by_date.keys())[:limit]:
            items = by_date[local_date]

            temps = [float(x.get("main", {}).get("temp", 0.0)) for x in items]
            pops = [float(x.get("pop", 0.0)) for x in items]
            winds = [float(x.get("wind", {}).get("speed", 0.0)) * 3.6 for x in items]
            rains = [float(x.get("rain", {}).get("3h", 0.0)) for x in items]
            codes = [x.get("weather", [{}])[0].get("id", 800) for x in items]
            descriptions = [x.get("weather", [{}])[0].get("description", "") for x in items]

            # Find the most frequent weather ID
            frequent_code = Counter(codes).most_common(1)[0][0]
            frequent_description = Counter(descriptions).most_common(1)[0][0]

            wmo_code = _map_owm_code_to_wmo(frequent_code)

            # Sunrise & Sunset calculations (OpenWeather 2.5 forecast doesn't return these directly)
            # We construct approximate sunrise/sunset times
            sunrise_str = f"{local_date}T06:00"
            sunset_str = f"{local_date}T18:00"

            daily.append(
                DailyForecast(
                    date=local_date,
                    weather_code=wmo_code,
                    weather_description=frequent_description.capitalize(),
                    temperature_max_c=max(temps) if temps else 0.0,
                    temperature_min_c=min(temps) if temps else 0.0,
                    precipitation_probability_max_percent=int(max(pops) * 100) if pops else 0,
                    rain_sum_mm=sum(rains) if rains else 0.0,
                    wind_speed_max_kmh=max(winds) if winds else 0.0,
                    uv_index_max=0.0,  # Not available
                    sunrise=sunrise_str,
                    sunset=sunset_str,
                )
            )
        return daily


def _map_owm_code_to_wmo(owm_id: int) -> int:
    if 200 <= owm_id <= 299:
        return 95  # Thunderstorm
    elif 300 <= owm_id <= 399:
        return 51  # Drizzle
    elif owm_id == 500:
        return 61  # Slight rain
    elif owm_id == 501:
        return 63  # Moderate rain
    elif 502 <= owm_id <= 504:
        return 65  # Heavy rain
    elif owm_id == 511:
        return 66  # Freezing rain
    elif owm_id == 520:
        return 80  # Slight rain showers
    elif owm_id == 521:
        return 81  # Rain showers
    elif owm_id in (522, 531):
        return 82  # Heavy/ragged rain showers
    elif 600 <= owm_id <= 699:
        return 71  # Snow
    elif 701 <= owm_id <= 781:
        return 45  # Fog / Atmosphere
    elif owm_id == 800:
        return 0  # Clear sky
    elif owm_id == 801:
        return 1  # Mainly clear
    elif owm_id == 802:
        return 2  # Partly cloudy
    elif owm_id in (803, 804):
        return 3  # Overcast
    return 3


def _format_unix_timestamp(dt: int, timezone_str: str) -> str:
    tz = timezone(timedelta(hours=7))  # Default to UTC+7 (Asia/Ho_Chi_Minh)
    if not timezone_str or timezone_str == "auto":
        timezone_str = "Asia/Ho_Chi_Minh"
    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo(timezone_str)
    except Exception:
        pass
    dt_obj = datetime.fromtimestamp(dt, tz=UTC).astimezone(tz)
    return dt_obj.strftime("%Y-%m-%dT%H:%M")
