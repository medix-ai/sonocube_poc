"""영상 품질 및 예측 안정성 — actionable warning 메시지"""
from typing import Any, Dict, List

import cv2
import numpy as np


def compute_quality_metrics(
    frames: List[np.ndarray],
    framewise_ef: List[float],
    failed_frames: int = 0,
) -> Dict[str, Any]:
    """
    프레임 시퀀스에서 품질 지표를 계산한다.
    반환값에 actionable warning 목록 포함.
    """
    metrics: Dict[str, Any] = {
        "frame_count": len(frames),
        "brightness_mean": None,
        "contrast_std": None,
        "blur_score": None,
        "ef_std": None,
        "failed_frame_ratio": 0.0,
        "warnings": [],
        "quality_level": "good",  # good / moderate / poor
    }

    total = max(len(frames) + failed_frames, 1)
    metrics["failed_frame_ratio"] = failed_frames / total

    if frames:
        grays = [_to_gray(f) for f in frames]
        metrics["brightness_mean"] = float(np.mean([g.mean() for g in grays]))
        metrics["contrast_std"]    = float(np.mean([g.std() for g in grays]))
        metrics["blur_score"]      = float(np.mean([_laplacian_var(g) for g in grays]))

    if framewise_ef:
        metrics["ef_std"] = float(np.std(framewise_ef))

    warnings = _generate_warnings(metrics)
    metrics["warnings"] = warnings
    metrics["quality_level"] = (
        "poor" if len(warnings) >= 3 else
        "moderate" if len(warnings) >= 1 else
        "good"
    )
    return metrics


def _to_gray(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 2:
        return frame.astype(np.float32)
    if frame.shape[2] == 1:
        return frame[:, :, 0].astype(np.float32)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY).astype(np.float32)


def _laplacian_var(gray: np.ndarray) -> float:
    lap = cv2.Laplacian(gray.astype(np.uint8), cv2.CV_64F)
    return float(lap.var())


def _generate_warnings(m: Dict[str, Any]) -> List[str]:
    warns = []
    n = m["frame_count"]
    if n < 10:
        warns.append(
            f"Clip is very short ({n} frames). "
            "Minimum 30 frames recommended — consider re-acquiring the clip."
        )
    elif n < 30:
        warns.append(
            f"Short clip ({n} frames). EF estimate may be less stable. "
            "Longer clips (≥30 frames covering at least 2 cardiac cycles) are preferred."
        )

    brt = m.get("brightness_mean")
    if brt is not None and brt < 20:
        warns.append(
            f"Image brightness is low (mean={brt:.0f}). "
            "Adjust ultrasound gain and re-acquire if the result is uncertain."
        )

    cst = m.get("contrast_std")
    if cst is not None and cst < 10:
        warns.append(
            f"Low image contrast (std={cst:.0f}). "
            "Poor contrast reduces feature detectability — check transducer contact and coupling."
        )

    blur = m.get("blur_score")
    if blur is not None and blur < 50:
        warns.append(
            f"High frame blur (sharpness={blur:.0f}). "
            "Check transducer position, patient movement, or image depth setting."
        )

    ef_std = m.get("ef_std")
    if ef_std is not None and ef_std >= 7.0:
        warns.append(
            f"High frame-to-frame EF variability (std={ef_std:.1f}%). "
            "This may indicate irregular cardiac rhythm, significant patient motion, "
            "or non-optimal imaging window."
        )
    elif ef_std is not None and ef_std >= 3.0:
        warns.append(
            f"Moderate EF variability (std={ef_std:.1f}%). "
            "Results should be interpreted with care."
        )

    ffr = m.get("failed_frame_ratio", 0.0)
    if ffr > 0.2:
        warns.append(
            f"High failed-frame ratio ({ffr * 100:.0f}% of frames unprocessed). "
            "EF estimate is based on a partial clip — re-acquisition recommended."
        )
    elif ffr > 0.1:
        warns.append(
            f"Some frames could not be processed ({ffr * 100:.0f}%). "
            "EF estimate may be slightly affected."
        )

    return warns
