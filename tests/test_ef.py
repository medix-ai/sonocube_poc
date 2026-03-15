"""
EF 계산 테스트
"""
import pytest
from utils.ef import calculate_ef, format_ef, get_ef_category


def test_calculate_ef():
    """EF 계산 테스트"""
    edv = 150.0
    esv = 50.0
    ef = calculate_ef(edv, esv)
    
    expected_ef = (150.0 - 50.0) / 150.0 * 100.0
    assert abs(ef - expected_ef) < 0.1


def test_format_ef():
    """EF 포맷팅 테스트"""
    ef = 65.5
    formatted = format_ef(ef)
    assert formatted == "65.5%"


def test_get_ef_category():
    """EF 카테고리 테스트"""
    assert get_ef_category(55.0) == "Normal"
    assert get_ef_category(45.0) == "Mildly Reduced"
    assert get_ef_category(35.0) == "Moderately Reduced"
    assert get_ef_category(25.0) == "Severely Reduced"

