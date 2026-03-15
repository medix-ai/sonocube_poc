"""
영상 전처리 모듈
프레임 크롭, 리사이즈, 정규화 등 기본 전처리 수행
"""
import numpy as np
from typing import List, Tuple, Optional
from utils.spec import DEFAULT_FRAME_SIZE


def normalize_frame(frame: np.ndarray) -> np.ndarray:
    """
    프레임을 0-1 범위로 정규화
    
    Args:
        frame: 입력 프레임 (H, W, C) 또는 (H, W)
        
    Returns:
        정규화된 프레임
    """
    frame = frame.astype(np.float32)
    
    if frame.max() > 1.0:
        frame = frame / 255.0
    
    return frame


def resize_frame(frame: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
    """
    프레임을 목표 크기로 리사이즈
    
    Args:
        frame: 입력 프레임
        target_size: (height, width) 목표 크기
        
    Returns:
        리사이즈된 프레임
    """
    import cv2
    
    h, w = target_size
    resized = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
    return resized


def crop_frame(frame: np.ndarray, crop_box: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
    """
    프레임을 크롭
    
    Args:
        frame: 입력 프레임
        crop_box: (x1, y1, x2, y2) 크롭 박스. None이면 크롭하지 않음
        
    Returns:
        크롭된 프레임
    """
    if crop_box is None:
        return frame
    
    x1, y1, x2, y2 = crop_box
    return frame[y1:y2, x1:x2]


def preprocess_frames(
    frames: List[np.ndarray],
    target_size: Tuple[int, int] = DEFAULT_FRAME_SIZE,
    crop_box: Optional[Tuple[int, int, int, int]] = None,
    normalize: bool = True
) -> List[np.ndarray]:
    """
    프레임 리스트를 일괄 전처리
    
    Args:
        frames: 입력 프레임 리스트
        target_size: 목표 크기 (height, width)
        crop_box: 크롭 박스 (x1, y1, x2, y2)
        normalize: 정규화 여부
        
    Returns:
        전처리된 프레임 리스트
    """
    processed = []
    
    for frame in frames:
        # 크롭
        if crop_box is not None:
            frame = crop_frame(frame, crop_box)
        
        # 리사이즈
        if frame.shape[:2] != target_size:
            frame = resize_frame(frame, target_size)
        
        # 정규화
        if normalize:
            frame = normalize_frame(frame)
        
        processed.append(frame)
    
    return processed

