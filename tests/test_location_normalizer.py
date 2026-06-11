from app.utils.location_normalizer import (
    build_location_candidates,
    get_location_fallback,
    normalize_location_key,
)


def test_normalize_ba_ria_vung_tau_with_accents() -> None:
    assert normalize_location_key("bà rịa vũng tàu") == "ba ria vung tau"


def test_normalize_ba_ria_vung_tau_with_uppercase_and_spaces() -> None:
    assert normalize_location_key("BÀ RỊA   VŨNG TÀU") == "ba ria vung tau"


def test_tp_hcm_maps_to_ho_chi_minh_candidate() -> None:
    assert "Ho Chi Minh" in build_location_candidates("tp.hcm")


def test_sai_gon_maps_to_ho_chi_minh_candidate() -> None:
    assert "Ho Chi Minh" in build_location_candidates("sài gòn")


def test_da_nang_maps_to_da_nang_candidate() -> None:
    assert "Da Nang" in build_location_candidates("đà nẵng")


def test_can_tho_maps_to_can_tho_candidate() -> None:
    assert "Can Tho" in build_location_candidates("cần thơ")


def test_fallback_uses_display_name_for_ba_ria_vung_tau() -> None:
    fallback = get_location_fallback("brvt")

    assert fallback is not None
    assert fallback["name"] == "Bà Rịa - Vũng Tàu"
    assert fallback["country"] == "Vietnam"
