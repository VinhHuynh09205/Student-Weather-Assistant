import json
from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Student Weather Assistant", alias="APP_NAME")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    open_meteo_forecast_url: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        alias="OPEN_METEO_FORECAST_URL",
    )
    open_meteo_geocoding_url: str = Field(
        default="https://geocoding-api.open-meteo.com/v1/search",
        alias="OPEN_METEO_GEOCODING_URL",
    )
    http_timeout_seconds: float = Field(default=10.0, alias="HTTP_TIMEOUT_SECONDS")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"],
        validation_alias=AliasChoices("CORS_ORIGINS", "CORS_ALLOWED_ORIGINS"),
    )
    weather_provider: str = Field(default="openweather", alias="WEATHER_PROVIDER")
    weather_fallback_provider: str | None = Field(default="open_meteo", alias="WEATHER_FALLBACK_PROVIDER")
    openweather_api_key: str | None = Field(default=None, alias="OPENWEATHER_API_KEY")
    openweather_base_url: str = Field(default="https://api.openweathermap.org", alias="OPENWEATHER_BASE_URL")
    open_meteo_base_url: str = Field(default="https://api.open-meteo.com", alias="OPEN_METEO_BASE_URL")
    debug_weather_compare: bool = Field(default=False, alias="DEBUG_WEATHER_COMPARE")

    # Database & Security
    database_url: str = Field(
        default="postgresql+asyncpg://student_weather_user:secure_password_for_student_weather@localhost:15432/student_weather",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(
        default="9a1b6c7d2e3f4051a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90123456789ab",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Google OAuth
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str | None = Field(default=None, alias="GOOGLE_REDIRECT_URI")

    # SMTP Configuration for Email Notifications
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="no-reply@studentweather.org", alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    resend_api_key: str | None = Field(default=None, alias="RESEND_API_KEY")
    email_from: str | None = Field(default=None, alias="EMAIL_FROM")
    sendgrid_api_key: str | None = Field(default=None, alias="SENDGRID_API_KEY")



    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        raw_value = value.strip()
        if not raw_value:
            return []

        if raw_value.startswith("[") and raw_value.endswith("]"):
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError:
                parsed = raw_value.strip("[]").split(",")
            return [str(origin).strip().strip('"').strip("'") for origin in parsed if str(origin).strip()]

        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
