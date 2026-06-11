APP_SERVICE_SLUG = "student-weather-assistant"

ALLOWED_HOURLY_FORECAST_HOURS = {6, 12, 24, 48, 72}

SHIFT_HOUR_WINDOWS = {
    "morning": (6, 12),
    "afternoon": (12, 17),
    "evening": (17, 21),
}

STUDY_SHIFT_LABELS = {
    "morning": "buổi sáng",
    "afternoon": "buổi chiều",
    "evening": "buổi tối",
}

RAIN_PROBABILITY_HIGH = 70
RAIN_PROBABILITY_MEDIUM = 50
TOTAL_RAIN_HEAVY_MM = 5.0
APPARENT_TEMPERATURE_HOT_C = 35.0
APPARENT_TEMPERATURE_VERY_HOT_C = 38.0
WIND_SPEED_STRONG_KMH = 35.0
UV_INDEX_HIGH = 8.0
HUMIDITY_HIGH_PERCENT = 85.0

FORECAST_DAYS_FOR_HOURLY = 3
