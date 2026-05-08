"""영상 품질 및 예측 안정성 체크 — 연구용 입력 품질 확인 지표"""
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

    Returns dict:
        frame_count, brightness_mean, contrast_std, blur_score,
        ef_std, failed_frame_ratio, warnings (list[str])
    """
    metrics: Dict[str, Any] = {
        "frame_count": len(frames),
        "brightness_mean": None,
        "contrast_std": None,
        "blur_score": None,
        "ef_std": None,
        "failed_frame_ratio": 0.0,
        "warnings": [],
    }

    total = max(len(frames) + failed_frames, 1)
    metrics["failed_frame_ratio"] = failed_frames / total

    if frames:
        grays = [_to_gray(f) for f in frames]
        metrics["brightness_mean"] = float(np.mean([g.mean() for g in grays]))
        metrics["contrast_std"] = float(np.mean([g.std() for g in grays]))
        metrics["blur_score"] = float(np.mean([_laplacian_var(g) for g in grays]))

    if framewise_ef:
        metrics["ef_std"] = float(np.std(framewise_ef))

    metrics["warnings"] = _generate_warnings(metrics)
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
    if m["frame_count"] < 10:
        warns.append(f"Too few frames ({m['frame_count']}). Results may be unreliable.")
    brt = m.get("brightness_mean")
    if brt is not None and brt < 20:
        warns.append(f"Low brightness (mean={brt:.1f}). Input video may be underexposed.")
    cst = m.get("contrast_std")
    if cst is not None and cst < 10:
        warns.append(f"Low contrast (std={cst:.1f}). Structural details may be unclear.")
    blur = m.get("blur_score")
    if blur is not None and blur < 50:
        warns.append(f"High blur (Laplacian var={blur:.1f}). Frame sharpness is low.")
    ef_std = m.get("ef_std")
    if ef_std is not None and ef_std >= 7.0:
        warns.append(
            f"Unstable frame-wise EF predictions (std={ef_std:.1f}%). "
            "Manual review is recommended."
        )
    ffr = m.get("failed_frame_ratio", 0.0)
    if ffr > 0.1:
        warns.append(
            f"High failed-frame ratio ({ffr * 100:.1f}%). "
            "Some frames could not be processed."
        )
    return warns
