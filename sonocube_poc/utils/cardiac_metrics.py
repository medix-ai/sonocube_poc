"""
심장 구조지표 계산 모듈
LA/RA 부피, Wall thickness, Sphericity index 등 계산
"""
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import cv2


def calculate_la_volume(lv_masks: List[np.ndarray], ed_idx: int) -> float:
    """
    Left Atrium (좌심방) 부피 계산
    
    Args:
        lv_masks: LV segmentation 마스크 리스트
        ed_idx: End Diastolic 프레임 인덱스
        
    Returns:
        LA 부피 (ml)
    
    Note:
        실제로는 별도의 LA segmentation이 필요하지만,
        현재는 LV 마스크 기반으로 추정 (임시 구현)
    """
    if ed_idx >= len(lv_masks):
        return 0.0
    
    # ED 프레임의 LV 마스크 사용
    ed_mask = lv_masks[ed_idx]
    
    # LA는 LV 위쪽 영역으로 추정 (간단한 휴리스틱)
    # 실제로는 별도 모델이 필요
    h, w = ed_mask.shape
    la_region = ed_mask[:h//3, :]  # 상단 1/3 영역
    
    la_pixels = np.sum(la_region > 0)
    
    # 부피 변환 (실제로는 캘리브레이션 필요)
    pixel_to_ml = 0.01
    la_volume = la_pixels * pixel_to_ml * 0.8  # LA는 LV보다 작으므로 스케일 조정
    
    return float(la_volume)


def calculate_ra_volume(lv_masks: List[np.ndarray], ed_idx: int) -> float:
    """
    Right Atrium (우심방) 부피 계산
    
    Args:
        lv_masks: LV segmentation 마스크 리스트
        ed_idx: End Diastolic 프레임 인덱스
        
    Returns:
        RA 부피 (ml)
    
    Note:
        실제로는 별도의 RA segmentation이 필요하지만,
        현재는 LV 마스크 기반으로 추정 (임시 구현)
    """
    if ed_idx >= len(lv_masks):
        return 0.0
    
    ed_mask = lv_masks[ed_idx]
    h, w = ed_mask.shape
    
    # RA는 LV 오른쪽 영역으로 추정 (간단한 휴리스틱)
    ra_region = ed_mask[:, w//2:]  # 오른쪽 절반 영역
    
    ra_pixels = np.sum(ra_region > 0)
    
    # 부피 변환
    pixel_to_ml = 0.01
    ra_volume = ra_pixels * pixel_to_ml * 0.7  # RA는 LV보다 작으므로 스케일 조정
    
    return float(ra_volume)


def calculate_wall_thickness(
    lv_mask: np.ndarray,
    frame: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    심벽 두께 (Wall Thickness) 계산
    
    Args:
        lv_mask: LV segmentation 마스크
        frame: 원본 프레임 (옵션, 더 정확한 측정을 위해)
        
    Returns:
        {
            "septal": float,      # 중격벽 두께 (mm)
            "lateral": float,     # 외측벽 두께 (mm)
            "anterior": float,    # 전벽 두께 (mm)
            "inferior": float,    # 하벽 두께 (mm)
            "average": float      # 평균 두께 (mm)
        }
    """
    if lv_mask is None or np.sum(lv_mask) == 0:
        return {
            "septal": 0.0,
            "lateral": 0.0,
            "anterior": 0.0,
            "inferior": 0.0,
            "average": 0.0
        }
    
    # LV 윤곽선 추출
    contours, _ = cv2.findContours(
        lv_mask.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    if len(contours) == 0:
        return {
            "septal": 0.0,
            "lateral": 0.0,
            "anterior": 0.0,
            "inferior": 0.0,
            "average": 0.0
        }
    
    # 가장 큰 윤곽선 사용
    largest_contour = max(contours, key=cv2.contourArea)
    
    # 중심점 계산
    M = cv2.moments(largest_contour)
    if M["m00"] == 0:
        return {
            "septal": 0.0,
            "lateral": 0.0,
            "anterior": 0.0,
            "inferior": 0.0,
            "average": 0.0
        }
    
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    
    h, w = lv_mask.shape
    
    # 거리 변환을 사용하여 벽 두께 추정
    dist_transform = cv2.distanceTransform(
        lv_mask.astype(np.uint8),
        cv2.DIST_L2,
        5
    )
    
    # 중심에서 가장 먼 점까지의 거리 (반경)
    max_dist = np.max(dist_transform)
    
    # 방향별 두께 측정 (간단한 추정)
    # 실제로는 더 정교한 방법 필요
    
    # 픽셀을 mm로 변환 (실제로는 캘리브레이션 필요)
    # 가정: 1 픽셀 = 0.1 mm (실제 값은 연구팀에서 제공)
    pixel_to_mm = 0.1
    
    # 기본 벽 두께 (정상 성인: 8-12mm)
    # 여기서는 거리 변환 기반으로 추정
    base_thickness = max_dist * pixel_to_mm * 0.3  # 스케일 조정
    
    # 방향별 두께 (현재는 평균값 사용, 실제로는 방향별 측정 필요)
    wall_thickness = {
        "septal": base_thickness * 1.1,      # 중격벽 (약간 두꺼움)
        "lateral": base_thickness * 0.9,     # 외측벽
        "anterior": base_thickness,          # 전벽
        "inferior": base_thickness,          # 하벽
        "average": base_thickness
    }
    
    return wall_thickness


def calculate_sphericity_index(
    lv_mask: np.ndarray,
    volume: float
) -> float:
    """
    Sphericity Index (구형도 지수) 계산
    
    SI = (6 * V)^(2/3) / (π^(1/3) * A)
    
    여기서:
    - V: 부피
    - A: 표면적
    
    정상값: 약 0.5-0.6
    값이 클수록 더 구형에 가까움
    
    Args:
        lv_mask: LV segmentation 마스크
        volume: LV 부피 (ml)
        
    Returns:
        Sphericity Index (0-1 범위)
    """
    if volume <= 0 or np.sum(lv_mask) == 0:
        return 0.0
    
    # 윤곽선 추출
    contours, _ = cv2.findContours(
        lv_mask.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    if len(contours) == 0:
        return 0.0
    
    # 가장 큰 윤곽선 사용
    largest_contour = max(contours, key=cv2.contourArea)
    
    # 윤곽선 길이 (표면적의 2D 근사)
    perimeter = cv2.arcLength(largest_contour, True)
    
    # 면적
    area = cv2.contourArea(largest_contour)
    
    if area == 0:
        return 0.0
    
    # 3D 표면적 추정 (간단한 근사)
    # 실제로는 3D 메시에서 표면적을 계산해야 함
    # 여기서는 2D 면적 기반으로 추정
    surface_area_2d = perimeter * 2  # 전후면 고려
    
    # 부피를 cm³로 변환 (ml = cm³)
    volume_cm3 = volume
    
    # Sphericity Index 계산
    # 정규화된 버전: (6*V)^(2/3) / (π^(1/3) * A)
    import math
    
    numerator = (6 * volume_cm3) ** (2/3)
    denominator = (math.pi ** (1/3)) * surface_area_2d
    
    if denominator == 0:
        return 0.0
    
    si = numerator / denominator
    
    # 0-1 범위로 정규화
    si = max(0.0, min(1.0, si))
    
    return float(si)


def calculate_all_structure_metrics(
    lv_masks: List[np.ndarray],
    ed_idx: int,
    es_idx: int,
    edv: float,
    esv: float,
    ed_frame: Optional[np.ndarray] = None,
    es_frame: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    모든 심장 구조지표 계산
    
    Args:
        lv_masks: LV segmentation 마스크 리스트
        ed_idx: End Diastolic 프레임 인덱스
        es_idx: End Systolic 프레임 인덱스
        edv: End Diastolic Volume (ml)
        esv: End Systolic Volume (ml)
        ed_frame: ED 프레임 (옵션)
        es_frame: ES 프레임 (옵션)
        
    Returns:
        {
            "la_volume": float,
            "ra_volume": float,
            "wall_thickness": {
                "septal": float,
                "lateral": float,
                "anterior": float,
                "inferior": float,
                "average": float
            },
            "sphericity_index": float
        }
    """
    # LA/RA 부피
    la_volume = calculate_la_volume(lv_masks, ed_idx)
    ra_volume = calculate_ra_volume(lv_masks, ed_idx)
    
    # Wall thickness (ED 프레임 기준)
    ed_mask = lv_masks[ed_idx] if ed_idx < len(lv_masks) else None
    wall_thickness = calculate_wall_thickness(ed_mask, ed_frame) if ed_mask is not None else {
        "septal": 0.0,
        "lateral": 0.0,
        "anterior": 0.0,
        "inferior": 0.0,
        "average": 0.0
    }
    
    # Sphericity Index (ED 기준)
    sphericity_index = calculate_sphericity_index(ed_mask, edv) if ed_mask is not None else 0.0
    
    return {
        "la_volume": la_volume,
        "ra_volume": ra_volume,
        "wall_thickness": wall_thickness,
        "sphericity_index": sphericity_index
    }

