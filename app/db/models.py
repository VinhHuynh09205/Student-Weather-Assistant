import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    Uuid,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True, nullable=True)
    normalized_username = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)  # Null for OAuth users
    auth_provider = Column(String, default="local", nullable=False)  # local, google, facebook
    provider_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


    # Relationships
    locations = relationship("UserLocation", back_populates="user", cascade="all, delete-orphan")
    schedules = relationship("StudySchedule", back_populates="user", cascade="all, delete-orphan")
    weekly_class_schedules = relationship("WeeklyClassSchedule", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    advice_history = relationship("WeatherAdviceHistory", back_populates="user", cascade="all, delete-orphan")
    local_weather_reports = relationship("LocalWeatherReport", back_populates="user", cascade="all, delete-orphan")


class UserLocation(Base):
    __tablename__ = "user_locations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label = Column(String, nullable=False)  # Nha, Truong, KTX, or custom
    display_name = Column(String, nullable=False)
    short_display_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    source = Column(String, default="user_confirmed", nullable=False)  # gps, search, user_confirmed
    administrative_levels = Column(JSON, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="locations")


class StudySchedule(Base):
    __tablename__ = "study_schedules"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    study_date = Column(String, nullable=True)  # Null for repeating schedules
    start_time = Column(String, nullable=False)  # e.g., "07:30"
    end_time = Column(String, nullable=False)  # e.g., "11:00"
    vehicle_type = Column(String, default="motorbike", nullable=False)  # motorbike, bus, walking, car, bicycle
    location_id = Column(Uuid(as_uuid=True), ForeignKey("user_locations.id", ondelete="SET NULL"), nullable=True)
    repeat_type = Column(String, default="none", nullable=False)  # none, weekly
    repeat_days = Column(JSON, nullable=True)  # e.g., ["mon", "wed", "fri"]
    note = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="schedules")
    location = relationship("UserLocation")


class WeeklyClassSchedule(Base):
    __tablename__ = "weekly_class_schedules"
    __table_args__ = (
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_weekly_class_schedules_day_of_week"),
        CheckConstraint("notify_before_minutes >= 0", name="ck_weekly_class_schedules_notify_before_minutes"),
        CheckConstraint(
            "vehicle_type IN ('motorbike', 'walking', 'bus', 'car', 'bicycle')",
            name="ck_weekly_class_schedules_vehicle_type",
        ),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_name = Column(String, nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    vehicle_type = Column(String, default="motorbike", nullable=False)
    location_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String, default="Asia/Ho_Chi_Minh", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notify_before_minutes = Column(Integer, default=60, nullable=False)
    rain_alert_enabled = Column(Boolean, default=True, nullable=False)
    storm_alert_enabled = Column(Boolean, default=True, nullable=False)
    semester_start_date = Column(Date, nullable=True)
    semester_end_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="weekly_class_schedules")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    temperature_unit = Column(String, default="celsius", nullable=False)  # celsius, fahrenheit
    theme_mode = Column(String, default="auto", nullable=False)  # auto, light, dark
    auto_refresh_enabled = Column(Boolean, default=True, nullable=False)
    notification_enabled = Column(Boolean, default=False, nullable=False)
    default_vehicle_type = Column(String, default="motorbike", nullable=False)
    default_location_id = Column(
        Uuid(as_uuid=True), ForeignKey("user_locations.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="settings")
    default_location = relationship("UserLocation")


class WeatherAdviceHistory(Base):
    __tablename__ = "weather_advice_history"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    study_schedule_id = Column(Uuid(as_uuid=True), ForeignKey("study_schedules.id", ondelete="SET NULL"), nullable=True)
    score = Column(Integer, nullable=False)
    summary = Column(String, nullable=False)
    warnings_json = Column(JSON, nullable=True)
    recommendations_json = Column(JSON, nullable=True)
    provider = Column(String, nullable=False)
    fallback_provider_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="advice_history")
    study_schedule = relationship("StudySchedule")


class LocalWeatherReport(Base):
    __tablename__ = "local_weather_reports"
    __table_args__ = (
        CheckConstraint(
            "reported_condition IN ('rain', 'no_rain', 'storm')",
            name="ck_local_weather_reports_condition",
        ),
        CheckConstraint(
            "intensity IS NULL OR intensity IN ('light', 'moderate', 'heavy')",
            name="ck_local_weather_reports_intensity",
        ),
        Index("ix_local_weather_reports_user_active_expires", "user_id", "is_active", "expires_at"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    location_name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    reported_condition = Column(String, nullable=False)
    intensity = Column(String, nullable=True)
    source = Column(String, default="user_report", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="local_weather_reports")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(Uuid(as_uuid=True), ForeignKey("study_schedules.id", ondelete="SET NULL"), nullable=True)
    type = Column(String, nullable=False)  # e.g., "weather_warning", "class_reminder"
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    channel = Column(String, nullable=False)  # email | web
    status = Column(String, default="pending", nullable=False)  # pending | sent | failed | read
    error_message = Column(String, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    occurrence_key = Column(String, nullable=True, index=True)
    risk_level = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")
    schedule = relationship("StudySchedule")
