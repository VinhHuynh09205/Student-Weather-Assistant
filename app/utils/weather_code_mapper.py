WEATHER_CODE_DESCRIPTIONS = {
    0: "Trời quang",
    1: "Ít mây",
    2: "Có mây",
    3: "Nhiều mây",
    45: "Sương mù",
    48: "Sương mù",
    51: "Mưa phùn",
    53: "Mưa phùn",
    55: "Mưa phùn",
    56: "Mưa phùn đóng băng",
    57: "Mưa phùn đóng băng",
    61: "Mưa",
    63: "Mưa",
    65: "Mưa",
    66: "Mưa đóng băng",
    67: "Mưa đóng băng",
    71: "Tuyết rơi",
    73: "Tuyết rơi",
    75: "Tuyết rơi",
    77: "Tuyết hạt",
    80: "Mưa rào",
    81: "Mưa rào",
    82: "Mưa rào",
    85: "Mưa tuyết",
    86: "Mưa tuyết",
    95: "Dông",
    96: "Dông kèm mưa đá",
    99: "Dông kèm mưa đá",
}


def map_weather_code(weather_code: int) -> str:
    return WEATHER_CODE_DESCRIPTIONS.get(weather_code, "Không xác định")
