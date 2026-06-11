from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import TypedDict


class LocationFallback(TypedDict):
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str


_SPECIAL_CHARS_RE = re.compile(r"[^a-z0-9]+")
_SPACE_RE = re.compile(r"\s+")
_MAX_CANDIDATES = 10


def _fallback(name: str, latitude: float, longitude: float) -> LocationFallback:
    return {
        "name": name,
        "country": "Vietnam",
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Asia/Ho_Chi_Minh",
    }


VIETNAM_LOCATION_ALIASES: dict[str, list[str]] = {
    "an giang": ["An Giang", "Long Xuyen"],
    "ba ria": ["Ba Ria", "Vung Tau", "Ba Ria-Vung Tau"],
    "ba ria vung tau": ["Vung Tau", "Ba Ria", "Ba Ria-Vung Tau"],
    "bac giang": ["Bac Giang"],
    "bac kan": ["Bac Kan"],
    "bac lieu": ["Bac Lieu"],
    "bac ninh": ["Bac Ninh"],
    "baria vungtau": ["Vung Tau", "Ba Ria", "Ba Ria-Vung Tau"],
    "ben tre": ["Ben Tre"],
    "binh dinh": ["Binh Dinh", "Quy Nhon"],
    "binh duong": ["Binh Duong", "Thu Dau Mot"],
    "binh phuoc": ["Binh Phuoc", "Dong Xoai"],
    "binh thuan": ["Binh Thuan", "Phan Thiet"],
    "br vt": ["Vung Tau", "Ba Ria", "Ba Ria-Vung Tau"],
    "brvt": ["Vung Tau", "Ba Ria", "Ba Ria-Vung Tau"],
    "ca mau": ["Ca Mau"],
    "can tho": ["Can Tho"],
    "cao bang": ["Cao Bang"],
    "da lat": ["Da Lat", "Lam Dong"],
    "da nang": ["Da Nang"],
    "dak lak": ["Dak Lak", "Buon Ma Thuot"],
    "dak nong": ["Dak Nong", "Gia Nghia"],
    "dien bien": ["Dien Bien", "Dien Bien Phu"],
    "dong nai": ["Dong Nai", "Bien Hoa"],
    "dong thap": ["Dong Thap", "Cao Lanh", "Sa Dec"],
    "gia lai": ["Gia Lai", "Pleiku"],
    "ha giang": ["Ha Giang"],
    "ha nam": ["Ha Nam", "Phu Ly"],
    "ha noi": ["Ha Noi", "Hanoi"],
    "ha tinh": ["Ha Tinh"],
    "hai duong": ["Hai Duong"],
    "hai phong": ["Hai Phong"],
    "hanoi": ["Hanoi", "Ha Noi"],
    "hau giang": ["Hau Giang", "Vi Thanh"],
    "hcm": ["Ho Chi Minh", "Saigon"],
    "ho chi minh": ["Ho Chi Minh", "Ho Chi Minh City", "Saigon"],
    "hoa binh": ["Hoa Binh"],
    "hue": ["Hue", "Thua Thien Hue"],
    "hung yen": ["Hung Yen"],
    "khanh hoa": ["Khanh Hoa", "Nha Trang"],
    "kien giang": ["Kien Giang", "Rach Gia", "Phu Quoc"],
    "kon tum": ["Kon Tum"],
    "lai chau": ["Lai Chau"],
    "lam dong": ["Lam Dong", "Da Lat"],
    "lang son": ["Lang Son"],
    "lao cai": ["Lao Cai", "Sa Pa"],
    "long an": ["Long An", "Tan An"],
    "nam dinh": ["Nam Dinh"],
    "nghe an": ["Nghe An", "Vinh"],
    "nha trang": ["Nha Trang", "Khanh Hoa"],
    "ninh binh": ["Ninh Binh"],
    "ninh thuan": ["Ninh Thuan", "Phan Rang"],
    "phu tho": ["Phu Tho", "Viet Tri"],
    "phu yen": ["Phu Yen", "Tuy Hoa"],
    "quang binh": ["Quang Binh", "Dong Hoi"],
    "quang nam": ["Quang Nam", "Tam Ky", "Hoi An"],
    "quang ngai": ["Quang Ngai"],
    "quang ninh": ["Quang Ninh", "Ha Long"],
    "quang tri": ["Quang Tri", "Dong Ha"],
    "sai gon": ["Ho Chi Minh", "Saigon"],
    "saigon": ["Ho Chi Minh", "Saigon"],
    "soc trang": ["Soc Trang"],
    "son la": ["Son La"],
    "tay ninh": ["Tay Ninh"],
    "thai binh": ["Thai Binh"],
    "thai nguyen": ["Thai Nguyen"],
    "thanh hoa": ["Thanh Hoa"],
    "thanh pho can tho": ["Can Tho"],
    "thanh pho da nang": ["Da Nang"],
    "thanh pho ha noi": ["Ha Noi", "Hanoi"],
    "thanh pho hai phong": ["Hai Phong"],
    "thanh pho ho chi minh": ["Ho Chi Minh", "Ho Chi Minh City", "Saigon"],
    "thua thien hue": ["Hue", "Thua Thien Hue"],
    "tien giang": ["Tien Giang", "My Tho"],
    "tp can tho": ["Can Tho"],
    "tp da nang": ["Da Nang"],
    "tp ha noi": ["Ha Noi", "Hanoi"],
    "tp hai phong": ["Hai Phong"],
    "tp hcm": ["Ho Chi Minh", "Saigon"],
    "tp ho chi minh": ["Ho Chi Minh", "Ho Chi Minh City", "Saigon"],
    "tphcm": ["Ho Chi Minh", "Saigon"],
    "tra vinh": ["Tra Vinh"],
    "tuyen quang": ["Tuyen Quang"],
    "vinh long": ["Vinh Long"],
    "vinh phuc": ["Vinh Phuc", "Vinh Yen"],
    "vung tau": ["Vung Tau", "Ba Ria", "Ba Ria-Vung Tau"],
    "yen bai": ["Yen Bai"],
}

VIETNAM_LOCATION_FALLBACKS: dict[str, LocationFallback] = {
    "an giang": _fallback("An Giang", 10.3864, 105.4352),
    "ba ria": _fallback("Bà Rịa - Vũng Tàu", 10.5417, 107.2429),
    "ba ria vung tau": _fallback("Bà Rịa - Vũng Tàu", 10.5417, 107.2429),
    "bac giang": _fallback("Bac Giang", 21.2731, 106.1946),
    "bac kan": _fallback("Bac Kan", 22.1470, 105.8348),
    "bac lieu": _fallback("Bac Lieu", 9.2940, 105.7278),
    "bac ninh": _fallback("Bac Ninh", 21.1861, 106.0763),
    "ben tre": _fallback("Ben Tre", 10.2433, 106.3756),
    "binh dinh": _fallback("Binh Dinh", 13.7829, 109.2197),
    "binh duong": _fallback("Binh Duong", 10.9804, 106.6519),
    "binh phuoc": _fallback("Binh Phuoc", 11.5349, 106.8832),
    "binh thuan": _fallback("Binh Thuan", 10.9333, 108.1000),
    "br vt": _fallback("Bà Rịa - Vũng Tàu", 10.5417, 107.2429),
    "brvt": _fallback("Bà Rịa - Vũng Tàu", 10.5417, 107.2429),
    "ca mau": _fallback("Ca Mau", 9.1768, 105.1524),
    "can tho": _fallback("Cần Thơ", 10.0452, 105.7469),
    "cao bang": _fallback("Cao Bang", 22.6657, 106.2570),
    "da lat": _fallback("Lâm Đồng", 11.9404, 108.4583),
    "da nang": _fallback("Đà Nẵng", 16.0544, 108.2022),
    "dak lak": _fallback("Đắk Lắk", 12.6667, 108.0500),
    "dak nong": _fallback("Đắk Nông", 12.0042, 107.6907),
    "dien bien": _fallback("Dien Bien", 21.3860, 103.0230),
    "dong nai": _fallback("Dong Nai", 10.9574, 106.8427),
    "dong thap": _fallback("Dong Thap", 10.4602, 105.6329),
    "gia lai": _fallback("Gia Lai", 13.9833, 108.0000),
    "ha giang": _fallback("Ha Giang", 22.8233, 104.9836),
    "ha nam": _fallback("Ha Nam", 20.5835, 105.9230),
    "ha noi": _fallback("Hà Nội", 21.0278, 105.8342),
    "ha tinh": _fallback("Hà Tĩnh", 18.3559, 105.8877),
    "hai duong": _fallback("Hai Duong", 20.9386, 106.3207),
    "hai phong": _fallback("Hai Phong", 20.8449, 106.6881),
    "hanoi": _fallback("Hà Nội", 21.0278, 105.8342),
    "hau giang": _fallback("Hau Giang", 9.7845, 105.4701),
    "hcm": _fallback("Hồ Chí Minh", 10.8231, 106.6297),
    "ho chi minh": _fallback("Hồ Chí Minh", 10.8231, 106.6297),
    "hoa binh": _fallback("Hòa Bình", 20.8172, 105.3376),
    "hue": _fallback("Huế", 16.4637, 107.5909),
    "hung yen": _fallback("Hung Yen", 20.6464, 106.0511),
    "khanh hoa": _fallback("Khánh Hòa", 12.2388, 109.1967),
    "kien giang": _fallback("Kien Giang", 10.0125, 105.0809),
    "kon tum": _fallback("Kon Tum", 14.3545, 108.0076),
    "lai chau": _fallback("Lai Chau", 22.3964, 103.4582),
    "lam dong": _fallback("Lâm Đồng", 11.9404, 108.4583),
    "lang son": _fallback("Lang Son", 21.8526, 106.7610),
    "lao cai": _fallback("Lao Cai", 22.4856, 103.9707),
    "long an": _fallback("Long An", 10.5333, 106.4167),
    "nam dinh": _fallback("Nam Dinh", 20.4388, 106.1621),
    "nghe an": _fallback("Nghe An", 18.6796, 105.6813),
    "nha trang": _fallback("Khanh Hoa", 12.2388, 109.1967),
    "ninh binh": _fallback("Ninh Binh", 20.2539, 105.9744),
    "ninh thuan": _fallback("Ninh Thuan", 11.5643, 108.9886),
    "phu tho": _fallback("Phu Tho", 21.3227, 105.4020),
    "phu yen": _fallback("Phu Yen", 13.0955, 109.3209),
    "quang binh": _fallback("Quang Binh", 17.4833, 106.6000),
    "quang nam": _fallback("Quang Nam", 15.5736, 108.4740),
    "quang ngai": _fallback("Quang Ngai", 15.1205, 108.7923),
    "quang ninh": _fallback("Quang Ninh", 20.9500, 107.0833),
    "quang tri": _fallback("Quang Tri", 16.8163, 107.1003),
    "sai gon": _fallback("Hồ Chí Minh", 10.8231, 106.6297),
    "saigon": _fallback("Hồ Chí Minh", 10.8231, 106.6297),
    "soc trang": _fallback("Soc Trang", 9.6036, 105.9800),
    "son la": _fallback("Son La", 21.3270, 103.9141),
    "tay ninh": _fallback("Tay Ninh", 11.3100, 106.0983),
    "thai binh": _fallback("Thai Binh", 20.4463, 106.3366),
    "thai nguyen": _fallback("Thai Nguyen", 21.5942, 105.8482),
    "thanh hoa": _fallback("Thanh Hoa", 19.8067, 105.7852),
    "thanh pho can tho": _fallback("Cần Thơ", 10.0452, 105.7469),
    "thanh pho da nang": _fallback("Đà Nẵng", 16.0544, 108.2022),
    "thanh pho ha noi": _fallback("Hà Nội", 21.0278, 105.8342),
    "thanh pho hai phong": _fallback("Hai Phong", 20.8449, 106.6881),
    "thanh pho ho chi minh": _fallback("Hồ Chí Minh", 10.8231, 106.6297),
    "thua thien hue": _fallback("Huế", 16.4637, 107.5909),
    "tien giang": _fallback("Tiền Giang", 10.3600, 106.3600),
    "tp can tho": _fallback("Cần Thơ", 10.0452, 105.7469),
    "tp da nang": _fallback("Đà Nẵng", 16.0544, 108.2022),
    "tp ha noi": _fallback("Hà Nội", 21.0278, 105.8342),
    "tp hai phong": _fallback("Hai Phong", 20.8449, 106.6881),
    "tp hcm": _fallback("Hồ Chí Minh", 10.8231, 106.6297),
    "tp ho chi minh": _fallback("Hồ Chí Minh", 10.8231, 106.6297),
    "tphcm": _fallback("Hồ Chí Minh", 10.8231, 106.6297),
    "tra vinh": _fallback("Tra Vinh", 9.9347, 106.3453),
    "tuyen quang": _fallback("Tuyen Quang", 21.8233, 105.2181),
    "vinh long": _fallback("Vinh Long", 10.2537, 105.9722),
    "vinh phuc": _fallback("Vinh Phuc", 21.3089, 105.6049),
    "vung tau": _fallback("Bà Rịa - Vũng Tàu", 10.5417, 107.2429),
    "yen bai": _fallback("Yen Bai", 21.7168, 104.8986),
    "tien giang cai lay": _fallback("Tiền Giang", 10.4100, 106.1900),
    "tien giang cai be": _fallback("Tiền Giang", 10.3300, 105.9700),
    "tien giang cho gao": _fallback("Tiền Giang", 10.3500, 106.4500),
    "tien giang go cong": _fallback("Tiền Giang", 10.3500, 106.6300),
    "tien giang tan phu dong": _fallback("Tiền Giang", 10.2700, 106.7000),
    "ben tre cho lach": _fallback("Bến Tre", 10.2600, 106.1500),
    "ben tre ba tri": _fallback("Bến Tre", 10.2100, 106.6000),
    "ben tre thanh phu": _fallback("Bến Tre", 10.0800, 106.5000),
    "vinh long vung liem": _fallback("Vinh Long", 10.1200, 106.1800),
    "vinh long tra on": _fallback("Vinh Long", 9.9700, 105.9800),
    "vinh long binh minh": _fallback("Vinh Long", 10.0800, 105.8200),
    "dong thap sa dec": _fallback("Dong Thap", 10.2900, 105.7600),
    "dong thap thap muoi": _fallback("Dong Thap", 10.4500, 105.8000),
    "dong thap hong ngu": _fallback("Dong Thap", 10.8200, 105.2900),
    "long an can duoc": _fallback("Long An", 10.5200, 106.6300),
    "long an duc hoa": _fallback("Long An", 10.8300, 106.4500),
    "long an tan hung": _fallback("Long An", 10.8800, 105.7700),
    "hau giang nga bay": _fallback("Hau Giang", 9.8000, 105.8200),
    "hau giang long my": _fallback("Hau Giang", 9.7000, 105.4200),
    "kien giang phu quoc": _fallback("Kien Giang", 10.2800, 103.9600),
    "kien giang ha tien": _fallback("Kien Giang", 10.3800, 104.4800),
    "kien giang vinh thuan": _fallback("Kien Giang", 9.5300, 105.1800),
    "an giang chau doc": _fallback("An Giang", 10.7000, 105.1200),
    "an giang tri ton": _fallback("An Giang", 10.4000, 105.0000),
    "ho chi minh can gio": _fallback("Hồ Chí Minh", 10.4800, 106.8800),
    "ho chi minh cu chi": _fallback("Hồ Chí Minh", 10.9800, 106.4800),
}


def normalize_location_key(value: str) -> str:
    """Normalize a Vietnamese location string into a lookup key."""
    stripped = value.strip().lower()
    without_accents = _strip_vietnamese_accents(stripped)
    without_special_chars = _SPECIAL_CHARS_RE.sub(" ", without_accents)
    return _SPACE_RE.sub(" ", without_special_chars).strip()


def build_location_candidates(value: str) -> list[str]:
    stripped = value.strip()
    normalized_key = normalize_location_key(stripped)
    aliases = VIETNAM_LOCATION_ALIASES.get(normalized_key, [])
    if aliases:
        return _unique_candidates([*aliases, stripped, normalized_key])[:_MAX_CANDIDATES]
    return _unique_candidates([stripped, *aliases, normalized_key])[:_MAX_CANDIDATES]


def get_location_fallback(value: str) -> LocationFallback | None:
    normalized_key = normalize_location_key(value)
    return VIETNAM_LOCATION_FALLBACKS.get(normalized_key)


def _strip_vietnamese_accents(value: str) -> str:
    value = value.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFD", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _unique_candidates(candidates: Iterable[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue

        dedupe_key = _SPACE_RE.sub(" ", candidate.lower()).strip()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        unique.append(candidate)
    return unique
