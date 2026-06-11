from datetime import datetime


def parse_open_meteo_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_hour_from_iso_time(value: str) -> int:
    return parse_open_meteo_time(value).hour
