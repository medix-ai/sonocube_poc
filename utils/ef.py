"""
EF (Ejection Fraction) 계산 관련 유틸리티
"""
from typing import Dict, Any


def calculate_ef(edv: float, esv: float) -> float:
    """
    Ejection Fraction 계산
    
    EF = (EDV - ESV) / EDV * 100
    
    Args:
        edv: End Diastolic Volume (ml)
        esv: End Systolic Volume (ml)
        
    Returns:
        EF (%) 
    """
    if edv <= 0:
        raise ValueError("EDV must be positive")
    
    ef = (edv - esv) / edv * 100.0
    return max(0.0, min(100.0, ef))  # 0-100 범위로 클리핑


def format_ef(ef: float, decimals: int = 1) -> str:
    """
    EF 값을 포맷팅하여 문자열로 반환
    
    Args:
        ef: EF 값 (%)
        decimals: 소수점 자릿수
        
    Returns:
        포맷팅된 문자열 (예: "65.3%")
    """
    return f"{ef:.{decimals}f}%"


def get_ef_category(ef: float) -> str:
    """
    EF 값에 따른 카테고리 반환 (연구용, 진단용 아님)
    
    Args:
        ef: EF 값 (%)
        
    Returns:
        카테고리 문자열
    """
    if ef >= 50:
        return "Normal"
    elif ef >= 40:
        return "Mildly Reduced"
    elif ef >= 30:
        return "Moderately Reduced"
    else:
        return "Severely Reduced"

