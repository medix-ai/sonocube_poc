"""
ED/ES 프레임 관련 후처리 모듈
"""
import numpy as np
from typing import List, Tuple, Optional


def find_ed_es_frames(
    frames: List[np.ndarray],
    masks: Optional[List[np.ndarray]] = None
) -> Tuple[int, int]:
    """
    ED (End Diastole)와 ES (End Systole) 프레임 인덱스를 찾음
    
    현재는 더미 구현. 실제로는 AI 모델이 제공하거나
    LV 영역 크기 변화를 기반으로 계산할 수 있음.
    
    Args:
        frames: 프레임 리스트
        masks: (옵션) 각 프레임의 segmentation 마스크
        
    Returns:
        (ed_frame_idx, es_frame_idx): ED와 ES 프레임 인덱스
    """
    # 더미 구현: 첫 프레임을 ED, 중간 프레임을 ES로 가정
    ed_idx = 0
    es_idx = len(frames) // 2
    
    return ed_idx, es_idx


def extract_ed_es_frames(
    frames: List[np.ndarray],
    ed_idx: int,
    es_idx: int
) -> Tuple[np.ndarray, np.ndarray]:
    """
    ED와 ES 프레임을 추출
    
    Args:
        frames: 프레임 리스트
        ed_idx: ED 프레임 인덱스
        es_idx: ES 프레임 인덱스
        
    Returns:
        (ed_frame, es_frame): ED와 ES 프레임
    """
    if ed_idx >= len(frames) or es_idx >= len(frames):
        raise IndexError(f"Frame index out of range. Total frames: {len(frames)}")
    
    return frames[ed_idx], frames[es_idx]

