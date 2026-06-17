from typing import Literal

VehicleType = Literal["motorbike", "bus", "walking", "car", "bicycle"]

VALID_VEHICLE_TYPES = {"motorbike", "bus", "walking", "car", "bicycle"}


def normalize_vehicle_type(value: str | None) -> VehicleType:
    if value == "walk":
        return "walking"
    if value in VALID_VEHICLE_TYPES:
        return value  # type: ignore[return-value]
    return "motorbike"


def score_label(score: int) -> str:
    if score >= 85:
        return "Tốt"
    if score >= 70:
        return "Khá thuận lợi"
    if score >= 50:
        return "Cần chú ý"
    if score >= 30:
        return "Nên chuẩn bị kỹ"
    return "Không thuận lợi"


def build_vehicle_commute_advice(
    *,
    vehicle_type: str | None,
    rain_risk: bool,
    strong_wind: bool,
    hot_weather: bool,
    storm_risk: bool,
) -> str:
    vehicle = normalize_vehicle_type(vehicle_type)

    if vehicle == "motorbike":
        if storm_risk:
            return "Đi xe máy nên đi sớm, mang áo mưa, chạy chậm và tránh dông gió mạnh."
        if rain_risk or strong_wind:
            return "Đi xe máy nên đi sớm 10-15 phút, mang áo mưa và chú ý đường trơn, gió mạnh, tầm nhìn kém."
        return "Đi xe máy khá thuận tiện, vẫn nên kiểm tra áo mưa mỏng và tình trạng đường trước khi đi."

    if vehicle == "walking":
        if storm_risk:
            return "Đi bộ nên tránh mưa lớn hoặc dông, ưu tiên lối có mái che và chờ thời tiết dịu hơn."
        if rain_risk:
            return "Đi bộ nên mang dù, đi giày chống trượt và chọn tuyến đường có mái che nếu có."
        if hot_weather:
            return "Đi bộ nên tránh nắng lâu và mang thêm nước."
        return "Đi bộ phù hợp nếu quãng đường ngắn, nên chọn tuyến an toàn và đủ ánh sáng."

    if vehicle == "bus":
        if rain_risk or storm_risk:
            return "Đi xe buýt nên ra trạm sớm, kiểm tra thời gian chờ và chuẩn bị áo mưa cho đoạn đi bộ."
        return "Đi xe buýt nên kiểm tra lịch chuyến và ra trạm sớm vài phút để tránh lỡ xe."

    if vehicle == "car":
        if storm_risk:
            return "Đi ô tô cần lái chậm, bật đèn, giữ khoảng cách vì mưa dông làm giảm tầm nhìn."
        if rain_risk or strong_wind:
            return "Đi ô tô nên chú ý tầm nhìn, đường ngập, kẹt xe và lái chậm khi mưa hoặc gió mạnh."
        return "Đi ô tô khá an toàn, vẫn nên tính thêm thời gian nếu tuyến đường dễ kẹt xe."

    if storm_risk:
        return "Đi xe đạp không nên di chuyển khi có dông hoặc gió mạnh, hãy cân nhắc phương tiện khác."
    if rain_risk or strong_wind:
        return "Đi xe đạp nên dùng áo mưa gọn, tránh đường trơn và rất cẩn thận khi gió mạnh."
    return "Đi xe đạp thuận lợi nếu đường khô ráo, nên mang áo mưa gọn để dự phòng."


def build_vehicle_preparation_items(
    *,
    vehicle_type: str | None,
    rain_risk: bool,
    strong_wind: bool,
    hot_weather: bool,
    storm_risk: bool,
) -> list[str]:
    vehicle = normalize_vehicle_type(vehicle_type)
    items: list[str] = []

    if rain_risk or storm_risk:
        items.extend(
            [
                "Mang áo mưa hoặc ô",
                "Bọc chống nước cho laptop/sách vở",
                "Kiểm tra lại thời tiết trước khi xuất phát",
            ]
        )
    if hot_weather:
        items.extend(["Mang nước uống", "Chuẩn bị nón hoặc áo khoác nhẹ"])
    if strong_wind:
        items.append("Cẩn thận với gió mạnh khi qua đoạn đường trống")

    if vehicle == "motorbike":
        items.append("Kiểm tra áo mưa gọn và đèn xe")
    elif vehicle == "walking":
        items.append("Chọn giày chống trượt và tuyến đường có mái che")
    elif vehicle == "bus":
        items.append("Ra trạm sớm hơn vài phút")
    elif vehicle == "car":
        items.append("Dự phòng kẹt xe hoặc đường ngập")
    elif vehicle == "bicycle":
        items.append("Kiểm tra phanh và hạn chế đi khi gió mạnh")

    if not items:
        items.append("Kiểm tra lại thời tiết trước khi đi học")

    return list(dict.fromkeys(items))
