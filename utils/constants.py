"""SonoCube 앱 전역 상수"""

APP_VERSION = "1.2.0"
APP_NAME = "SonoCube PoC"
DISCLAIMER = "Research use only. Not for diagnostic use."

UNSUPPORTED_METRICS = {
    "edv": "Requires LV segmentation",
    "esv": "Requires LV segmentation",
    "wall_thickness": "Requires myocardium segmentation",
    "sphericity": "Requires LV segmentation",
    "la_volume": "Requires chamber segmentation",
    "ra_volume": "Requires chamber segmentation",
    "segmentation_overlay": "Unavailable: segmentation model not connected",
    "three_d_reconstruction": "Unavailable in current version",
}

CONFIDENCE_LOW_WARNING = (
    "Low confidence: frame-wise EF predictions are unstable. "
    "Manual review is recommended."
)
CONFIDENCE_NOTE = (
    "Confidence reflects prediction stability across frames, "
    "not clinical diagnostic confidence."
)


def get_confidence_level(ef_std: float) -> str:
    """프레임별 EF 표준편차 기반 예측 안정성 지표"""
    if ef_std < 3.0:
        return "High"
    elif ef_std < 7.0:
        return "Medium"
    return "Low"


CONFIDENCE_COLORS = {
    "High": "#4caf50",
    "Medium": "#ff9800",
    "Low": "#f44336",
}
