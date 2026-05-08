"""
LV Segmentation placeholder interface — v1.1

향후 LV segmentation 모델 연결을 위한 인터페이스.
현재 버전에서는 모든 함수가 None 또는 unavailable 상태를 반환합니다.
v1.5에서 실제 모델로 교체 예정.
"""
import numpy as np
from typing import Optional, Dict, Any


def predict_lv_mask(frame: np.ndarray) -> Optional[np.ndarray]:
    """
    Placeholder for future LV segmentation model.

    TODO (v1.5): Load and run actual segmentation ONNX model.
    Expected input:  (H, W, 3) uint8 RGB frame
    Expected output: (H, W)   float32 mask in [0, 1]

    Returns:
        None — segmentation model not connected in v1.1
    """
    return None


def compute_edv_esv_from_masks(
    ed_mask: Optional[np.ndarray],
    es_mask: Optional[np.ndarray],
    pixel_spacing: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Placeholder for segmentation-derived EDV/ESV calculation.

    TODO (v1.5): Implement Simpson's biplane or disc-summation method
                 using actual segmentation masks and calibrated pixel spacing.

    Returns:
        Dict with unavailable status for all metrics
    """
    from utils.constants import UNSUPPORTED_METRICS
    return {
        "edv": None,
        "esv": None,
        "edv_status": UNSUPPORTED_METRICS["edv"],
        "esv_status": UNSUPPORTED_METRICS["esv"],
    }


def compute_wall_thickness(mask_sequence: list) -> Dict[str, Any]:
    """
    TODO (v1.5): Compute myocardial wall thickness from mask sequence.
    """
    from utils.constants import UNSUPPORTED_METRICS
    return {"status": UNSUPPORTED_METRICS["wall_thickness"]}


def compute_sphericity(ed_mask: Optional[np.ndarray]) -> Dict[str, Any]:
    """
    TODO (v1.5): Compute LV sphericity index from ED mask.
    """
    from utils.constants import UNSUPPORTED_METRICS
    return {"status": UNSUPPORTED_METRICS["sphericity"]}
