"""
AI 모델 inference 엔진
이 모듈은 sonocube_research에서 제공하는 실제 모델 래퍼로 교체될 예정
현재는 더미 구현으로 전체 파이프라인 테스트용
"""
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import random

from utils.io import load_echo_clip
from utils.preprocess import preprocess_frames
from utils.ed_es import find_ed_es_frames
from utils.ef import calculate_ef


def analyze_clip(video_path: Path) -> Dict[str, Any]:
    """
    심초음파 영상 클립을 분석하여 LV 분할, EF 계산, 종양 정보 등을 반환
    
    이 함수는 sonocube_research에서 제공하는 실제 모델 inference 함수로 교체될 예정.
    현재는 더미 구현으로 전체 파이프라인 테스트가 가능하도록 함.
    
    Args:
        video_path: 심초음파 영상 파일 경로
        
    Returns:
        {
            "frames": List[np.ndarray],      # 전처리된 프레임 리스트
            "ed_frame_idx": int,              # ED 프레임 인덱스
            "es_frame_idx": int,              # ES 프레임 인덱스
            "ef": float,                      # Ejection Fraction (%)
            "lv_masks": {                     # LV segmentation 마스크
                "ed": np.ndarray,             # ED 프레임 마스크
                "es": np.ndarray,             # ES 프레임 마스크
                "all": List[np.ndarray]       # 모든 프레임 마스크 (옵션)
            },
            "tumor_mask": Optional[np.ndarray],  # 종양 마스크 (옵션)
            "volume_info": {                   # 부피 정보
                "edv": float,                  # End Diastolic Volume (ml)
                "esv": float,                   # End Systolic Volume (ml)
                "tumor_volume": Optional[float] # 종양 부피 (ml, 옵션)
            },
            "fps": float,                      # 영상 FPS
            "metadata": {                      # 추가 메타데이터
                "num_frames": int,
                "frame_size": tuple,
                "file_path": str
            }
        }
    """
    # 1. 영상 로드
    frames, fps = load_echo_clip(video_path)
    
    # 2. 전처리
    processed_frames = preprocess_frames(frames)
    
    # 3. ED/ES 프레임 찾기 (더미)
    ed_idx, es_idx = find_ed_es_frames(processed_frames)
    
    # 4. 더미 segmentation 마스크 생성
    # 실제로는 모델 inference 결과로 대체됨
    frame_shape = processed_frames[0].shape[:2]
    ed_mask = _generate_dummy_mask(frame_shape)
    es_mask = _generate_dummy_mask(frame_shape, smaller=True)
    all_masks = [_generate_dummy_mask(frame_shape) for _ in processed_frames]
    
    # 5. 더미 부피 계산
    # 실제로는 segmentation 마스크로부터 계산됨
    edv = random.uniform(100, 200)  # ml
    esv = random.uniform(40, 100)   # ml
    ef = calculate_ef(edv, esv)
    
    # 6. 종양 마스크 (옵션, 더미)
    tumor_mask = None
    tumor_volume = None
    if random.random() > 0.7:  # 30% 확률로 종양 존재
        tumor_mask = _generate_dummy_mask(frame_shape, smaller=True)
        tumor_volume = random.uniform(5, 30)  # ml
    
    return {
        "frames": processed_frames,
        "ed_frame_idx": ed_idx,
        "es_frame_idx": es_idx,
        "ef": ef,
        "lv_masks": {
            "ed": ed_mask,
            "es": es_mask,
            "all": all_masks
        },
        "tumor_mask": tumor_mask,
        "volume_info": {
            "edv": edv,
            "esv": esv,
            "tumor_volume": tumor_volume
        },
        "fps": fps,
        "metadata": {
            "num_frames": len(processed_frames),
            "frame_size": frame_shape,
            "file_path": str(video_path)
        }
    }


def _generate_dummy_mask(shape: tuple, smaller: bool = False) -> np.ndarray:
    """
    더미 segmentation 마스크 생성 (테스트용)
    
    Args:
        shape: 마스크 크기 (height, width)
        smaller: True면 더 작은 마스크 생성
        
    Returns:
        이진 마스크 (0 또는 1)
    """
    h, w = shape
    mask = np.zeros(shape, dtype=np.uint8)
    
    # 타원형 마스크 생성
    center_y, center_x = h // 2, w // 2
    if smaller:
        radius_y, radius_x = h // 4, w // 4
    else:
        radius_y, radius_x = h // 3, w // 3
    
    y, x = np.ogrid[:h, :w]
    ellipse_mask = ((x - center_x) / radius_x) ** 2 + ((y - center_y) / radius_y) ** 2 <= 1
    mask[ellipse_mask] = 1
    
    return mask

